"""Real, recent research-paper discovery for the Literature Survey.

Queries two free, key-less scholarly APIs over plain HTTPS (stdlib ``urllib``,
no new dependencies):

  * Semantic Scholar Graph API — rich metadata (abstract, citation count) but an
    aggressively rate-limited free tier (frequent HTTP 429).
  * CrossRef REST API — dependable workhorse with real DOI metadata.

Both are filtered to the last ``years_back`` years.  Every provider failure is
swallowed and simply yields fewer results, so report generation never breaks
because a search API is down or throttled.  Returned papers carry verifiable
metadata (title/authors/year/venue/DOI) so citations are real, not invented.
"""

import datetime
import json
import re
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

_USER_AGENT = {
    "User-Agent": "ReportAI/1.0 (academic report generator; mailto:reportai@example.com)"
}
_TIMEOUT = 12

_STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "into", "over", "under",
    "using", "use", "based", "via", "towards", "toward", "system", "systems",
    "application", "applications", "approach", "study", "review", "analysis",
    "design", "implementation", "project", "report", "smart", "automatic",
    "automated", "real", "time", "new", "novel", "efficient", "using",
}


def _http_json(url: str) -> Any:
    request = urllib.request.Request(url, headers=_USER_AGENT)
    with urllib.request.urlopen(request, timeout=_TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def _build_query(topic: str, notes: str = "") -> str:
    """Derive concise, high-signal search keywords from the topic and notes."""
    text = f"{topic or ''} {notes or ''}"
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9\-]{2,}", text)
    ordered: List[str] = []
    seen = set()
    for token in tokens:
        low = token.lower()
        if low in _STOPWORDS or low in seen:
            continue
        seen.add(low)
        ordered.append(token)
    query = " ".join(ordered[:12]).strip()
    return query or (topic or "").strip()


def _normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (title or "").lower()).strip()


def _search_semantic_scholar(query: str, min_year: int, max_year: int, limit: int) -> List[Dict[str, Any]]:
    url = "https://api.semanticscholar.org/graph/v1/paper/search?" + urllib.parse.urlencode({
        "query": query,
        "year": f"{min_year}-{max_year}",
        "limit": limit,
        "fields": "title,authors,year,venue,abstract,externalIds,citationCount",
    })
    payload = _http_json(url)
    papers: List[Dict[str, Any]] = []
    for item in payload.get("data", []) or []:
        title = (item.get("title") or "").strip()
        if not title:
            continue
        external = item.get("externalIds") or {}
        doi = external.get("DOI")
        papers.append({
            "title": title,
            "authors": [a.get("name", "") for a in (item.get("authors") or []) if a.get("name")],
            "year": item.get("year"),
            "venue": (item.get("venue") or "").strip(),
            "abstract": (item.get("abstract") or "").strip(),
            "doi": doi,
            "url": external.get("URL") or (f"https://doi.org/{doi}" if doi else None),
            "citation_count": item.get("citationCount") or 0,
            "source": "semanticscholar",
        })
    return papers


def _search_crossref(query: str, min_year: int, limit: int) -> List[Dict[str, Any]]:
    url = "https://api.crossref.org/works?" + urllib.parse.urlencode({
        "query": query,
        "filter": f"from-pub-date:{min_year}-01-01",
        "rows": limit,
        "select": "title,author,issued,container-title,abstract,DOI,is-referenced-by-count",
    })
    payload = _http_json(url)
    papers: List[Dict[str, Any]] = []
    for item in payload.get("message", {}).get("items", []) or []:
        title = ((item.get("title") or [""])[0] or "").strip()
        if not title:
            continue
        authors = [
            f"{a.get('given', '')} {a.get('family', '')}".strip()
            for a in (item.get("author") or [])
        ]
        authors = [a for a in authors if a]
        date_parts = (item.get("issued", {}).get("date-parts") or [[None]])[0]
        year = date_parts[0] if date_parts else None
        doi = item.get("DOI")
        abstract = re.sub(r"<[^>]+>", "", item.get("abstract") or "").strip()
        papers.append({
            "title": title,
            "authors": authors,
            "year": year,
            "venue": ((item.get("container-title") or [""])[0] or "").strip(),
            "abstract": abstract,
            "doi": doi,
            "url": f"https://doi.org/{doi}" if doi else None,
            "citation_count": item.get("is-referenced-by-count", 0) or 0,
            "source": "crossref",
        })
    return papers


def find_recent_papers(
    topic: str,
    notes: str = "",
    max_results: int = 5,
    years_back: int = 3,
    per_provider: int = 6,
) -> List[Dict[str, Any]]:
    """Return up to ``max_results`` real papers from the last ``years_back`` years.

    Semantic Scholar is attempted first for its abstracts/citation counts; CrossRef
    always runs as the dependable complement.  Results are de-duplicated by title,
    preferring records that carry an abstract and DOI, then by citation count.
    """
    query = _build_query(topic, notes)
    if not query:
        return []
    max_year = datetime.date.today().year
    min_year = max_year - years_back

    collected: List[Dict[str, Any]] = []
    try:
        collected.extend(_search_semantic_scholar(query, min_year, max_year, per_provider))
    except Exception as exc:  # 429 / network / schema — never fatal
        print(f"[PaperSearch] Semantic Scholar unavailable ({type(exc).__name__}: {exc}); using CrossRef.")
    try:
        collected.extend(_search_crossref(query, min_year, per_provider))
    except Exception as exc:
        print(f"[PaperSearch] CrossRef unavailable ({type(exc).__name__}: {exc}).")

    best: Dict[str, Dict[str, Any]] = {}
    for paper in collected:
        key = _normalize_title(paper["title"])
        if not key:
            continue
        existing = best.get(key)
        if existing is None or _rank(paper) > _rank(existing):
            best[key] = paper

    ranked = sorted(best.values(), key=_rank, reverse=True)
    return ranked[:max_results]


def _rank(paper: Dict[str, Any]) -> tuple:
    return (
        1 if paper.get("abstract") else 0,
        1 if paper.get("doi") else 0,
        int(paper.get("citation_count") or 0),
        int(paper.get("year") or 0),
    )


def merge_papers(
    primary: List[Dict[str, Any]],
    secondary: List[Dict[str, Any]],
    limit: int = 8,
) -> List[Dict[str, Any]]:
    """Merge two paper lists, de-duplicating by normalized title.

    ``primary`` (e.g. user-uploaded papers) keeps its ordering and wins on
    conflicts; missing metadata fields are enriched from ``secondary`` (e.g.
    auto-discovered papers) when the same title appears in both.
    """
    best: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []
    for paper in list(primary or []) + list(secondary or []):
        key = _normalize_title(paper.get("title", ""))
        if not key:
            continue
        if key not in best:
            best[key] = dict(paper)
            order.append(key)
        else:
            for field in ("abstract", "doi", "year", "venue", "url", "authors", "citation_count"):
                if not best[key].get(field) and paper.get(field):
                    best[key][field] = paper[field]
    return [best[key] for key in order][:limit]


def _format_authors(authors: List[str]) -> str:
    authors = [a for a in (authors or []) if a]
    if not authors:
        return ""
    if len(authors) == 1:
        return authors[0]
    if len(authors) == 2:
        return f"{authors[0]} and {authors[1]}"
    return ", ".join(authors[:-1]) + f", and {authors[-1]}"


def format_ieee(paper: Dict[str, Any], index: int) -> str:
    """Render one paper as an IEEE-style reference line.

    Robust to missing metadata (e.g. a user-uploaded PDF whose authors/year could
    not be resolved): absent fields are simply omitted rather than shown as
    placeholders.
    """
    authors = _format_authors(paper.get("authors") or [])
    title = (paper.get("title") or "").strip().rstrip(".")
    venue = (paper.get("venue") or "").strip()
    year = paper.get("year")

    lead = f"[{index}] "
    if authors:
        lead += f"{authors}, "
    lead += f'"{title}"'

    tail = [part for part in (venue, str(year) if year else "") if part]
    reference = lead + (", " + ", ".join(tail) if tail else "") + "."
    doi = paper.get("doi")
    if doi:
        reference += f" doi: {doi}."
    return reference


def format_ieee_list(papers: List[Dict[str, Any]]) -> str:
    return "\n".join(format_ieee(p, i + 1) for i, p in enumerate(papers or []))


def _token_set(text: str) -> set:
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))


def enrich_paper_by_title(title: str) -> Dict[str, Any]:
    """Resolve full metadata (authors/year/venue/DOI) for a paper from its title.

    Used to upgrade a user-uploaded PDF — where only the title/abstract could be
    extracted — into a properly citable record via CrossRef.  Returns {} when no
    confident title match is found, so a wrong paper is never attached.
    """
    title = (title or "").strip()
    if not title:
        return {}
    url = "https://api.crossref.org/works?" + urllib.parse.urlencode({
        "query.bibliographic": title,
        "rows": 1,
        "select": "title,author,issued,container-title,DOI,is-referenced-by-count",
    })
    try:
        payload = _http_json(url)
    except Exception as exc:
        print(f"[PaperSearch] Title enrichment failed ({type(exc).__name__}: {exc}).")
        return {}

    items = payload.get("message", {}).get("items", []) or []
    if not items:
        return {}
    item = items[0]
    matched_title = ((item.get("title") or [""])[0] or "").strip()
    wanted, got = _token_set(title), _token_set(matched_title)
    if not wanted or not got:
        return {}
    jaccard = len(wanted & got) / len(wanted | got)
    if jaccard < 0.5:
        print(f"[PaperSearch] Enrichment skipped, weak title match ({jaccard:.2f}) for '{title[:50]}'.")
        return {}

    authors = [
        f"{a.get('given', '')} {a.get('family', '')}".strip()
        for a in (item.get("author") or [])
    ]
    date_parts = (item.get("issued", {}).get("date-parts") or [[None]])[0]
    year = date_parts[0] if date_parts else None
    doi = item.get("DOI")
    return {
        "authors": [a for a in authors if a],
        "year": year,
        "venue": ((item.get("container-title") or [""])[0] or "").strip(),
        "doi": doi,
        "url": f"https://doi.org/{doi}" if doi else None,
        "citation_count": item.get("is-referenced-by-count", 0) or 0,
        "source": "crossref",
    }
