"""
docx_reader.py
Deeply reads a DOCX document (template or friend's report) across:
  - Paragraphs
  - Tables (including Table of Contents index tables)
  - Headers and Footers
  - Page breaks / Section breaks

Applies Rules:
  - Strips instructional guidelines inside << ... >> and font hints (12, bold, ...)
  - Detects Solo vs Team (1 to 4+ members)
  - Extracts Faculty details with pre-fill defaults (Guide, HOD, Principal)
  - Extracts clean Index & Chapter headings from both Paragraphs and TOC Tables
  - Supports extracting text from user-uploaded research paper PDFs
"""

import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

from core.report_rules import clean_instruction_text, DEFAULT_FACULTY

try:
    import pypdf
    _PYPDF_AVAILABLE = True
except ImportError:
    _PYPDF_AVAILABLE = False


# ── Alignment enum → string ───────────────────────────────────────────────────
ALIGN_MAP = {
    WD_ALIGN_PARAGRAPH.LEFT:      "left",
    WD_ALIGN_PARAGRAPH.CENTER:    "center",
    WD_ALIGN_PARAGRAPH.RIGHT:     "right",
    WD_ALIGN_PARAGRAPH.JUSTIFY:   "justify",
    None:                         "left",
}

PLACEHOLDER_REGEXES = [
    re.compile(r"\[([^\[\]\n\r]{2,80})\]"),               # [Student Name]
    re.compile(r"\{\{([^{}\n\r]{2,80})\}\}"),             # {{STUDENT_NAME}}
    re.compile(r"<<([^<>\n\r]{2,80})>>"),                 # <<Project Title>>
    re.compile(r"<([^<>\n\r]{2,80})>"),                   # <Guide Name>
    re.compile(r"_{3,}\s*([a-zA-Z0-9 /]{2,40})\s*_{3,}"), # ___Topic___
    re.compile(r"\(([A-Z][A-Za-z0-9 _/]{3,50})\)"),       # (PROJECT TITLE)
]

UNDERLINE_BLANK_RE = re.compile(
    r"(name(?:\s*of\s*student)?|roll\s*no|seat\s*no|prn|guide(?:\s*name)?|hod|teacher|supervisor|topic|title)\s*[:=-]\s*([_.]{3,})",
    re.IGNORECASE,
)

HEADING_STYLE_RE = re.compile(r"^(?:heading\s*(\d+)|chapter|title)", re.IGNORECASE)

CHAPTER_TEXT_RE = re.compile(
    r"^(?:chapter\s*\d+|section\s*\d+|\d+\.\s+[A-Z]|abstract|introduction|literature|methodology|system\s*design|implementation|results|discussion|conclusion|references|bibliography|acknowledgement|certificate|declaration)",
    re.IGNORECASE,
)

FIELD_LABELS = {
    "topic": "Project / report topic",
    "student_name": "Student name",
    "roll_no": "Roll number / PRN",
    "exam_seat_no": "Exam seat number",
    "guide_name": "College guide",
    "hod_name": "Head of department",
    "principal_name": "Principal",
    "department_name": "Department",
    "college_name": "College",
    "university_name": "University",
    "academic_year": "Academic year",
    "group_no": "Group number",
    "company_name": "Company / organisation",
    "internship_mentor_name": "Internship mentor",
}

ROLE_PATTERNS = {
    "guide_name": ("Guide", r"(?:project\s+)?guide|supervisor|guided\s+by"),
    "co_guide_name": ("Co-guide", r"co[ -]?guide|joint\s+guide"),
    "hod_name": ("Head of Department", r"head\s+of\s+(?:the\s+)?department|\bh\.?o\.?d\.?\b"),
    "principal_name": ("Principal", r"\bprincipal\b"),
    "coordinator_name": ("Coordinator", r"(?:pbl|project|department)\s+coordinator"),
}


def _extract_placeholders_from_text(text: str) -> List[Dict[str, str]]:
    results = []
    if not text or not text.strip():
        return results

    for pat in PLACEHOLDER_REGEXES:
        for m in pat.finditer(text):
            raw_match = m.group(0)
            inner = m.group(1).strip()
            if re.match(r"^\d+$", inner):
                continue
            if any(kw in inner.lower() for kw in ["this chapter", "covers", "summarized", "should be there", "mandatory", "write about", "mention"]):
                continue
            results.append({
                "raw": raw_match,
                "clean": inner,
                "type": _classify_placeholder(inner),
            })

    for m in UNDERLINE_BLANK_RE.finditer(text):
        label = m.group(1).strip()
        results.append({
            "raw": m.group(0),
            "clean": label,
            "type": _classify_placeholder(label),
        })

    return results


def _classify_placeholder(name: str) -> str:
    n = name.lower()
    if any(k in n for k in ["topic", "title", "subject", "project name", "seminar title", "name of project"]):
        return "topic"
    if any(k in n for k in ["guide", "supervisor", "guided by", "internal guide", "external guide", "mentor", "name of the guide"]):
        return "guide"
    if any(k in n for k in ["hod", "head of department", "h.o.d"]):
        return "hod"
    if any(k in n for k in ["principal", "director", "dean"]):
        return "principal"
    if any(k in n for k in ["examiner", "external examiner", "internal examiner"]):
        return "examiner"
    if any(k in n for k in ["roll", "seat no", "prn", "reg no", "registration", "enrolment", "exam seat"]):
        return "roll_no"
    if any(k in n for k in ["student", "candidate", "submitted by", "prepared by", "name of candidate", "member", "author"]):
        return "student_name"
    if any(k in n for k in ["academic year", "year", "batch", "session"]):
        return "academic_year"
    return "general"


def _clean_value(value: Optional[str]) -> str:
    """Normalise DOCX text without assuming python-docx returned a string.

    Some documents contain empty or malformed runs whose ``.text`` resolves to
    ``None``.  Parsing a reference report must never fail because of one such
    run; an empty value simply contributes no extracted field.
    """
    return re.sub(r"\s+", " ", (value or "").replace("\xa0", " ")).strip(" :-\t")


def _looks_like_heading(para) -> bool:
    text = _clean_value(para.text)
    if not text or len(text) > 150:
        return False
    style_name = (getattr(para.style, "name", "") or "").lower()
    if style_name.startswith("heading") or style_name in {"title", "subtitle"}:
        return True
    if re.match(r"^(?:chapter\s*[-–:]?\s*\d+|\d+(?:\.\d+){0,3}[.)]?\s+)", text, re.I):
        return True
    return text.upper() in {
        "ABSTRACT", "ACKNOWLEDGEMENT", "ACKNOWLEDGMENTS", "CERTIFICATE",
        "DECLARATION", "REFERENCES", "BIBLIOGRAPHY", "INTRODUCTION",
        "CONCLUSION", "LIST OF FIGURES", "LIST OF TABLES",
    }


def _is_editable_body_heading(title: str) -> bool:
    """Reject TOC noise, figure captions and list items masquerading as headings."""
    t = _clean_value(title)
    lower = t.lower()
    if not t or any(token in lower for token in (
        "table of content", "figure ", "architecture diagram",
        "block diagram", "circuit diagram",
    )):
        return False
    if re.match(r"^\d+\.\s+(?:arduino|temperature sensor|dc motor|motor driver|jumper wire)\b", t, re.I):
        return False
    if re.match(r"^\d+\.\s+(?:integration with|smart automation|mobile app|sensor expansion|energy harvesting|machine learning|enhanced safety)", t, re.I):
        return False
    # PBL sections use chapter numbers (1.1, 3.4.1, etc.) or named front/body pages.
    return bool(
        re.match(r"^\d+\.\d+(?:\.\d+)?\s+", t)
        or t.upper() in {"ABSTRACT", "REFERENCES", "BIBLIOGRAPHY"}
    )


def _detect_sections(doc: Document) -> List[Dict[str, Any]]:
    """Return editable body sections from the actual document, never a syllabus default."""
    heading_indexes = [idx for idx, para in enumerate(doc.paragraphs) if _looks_like_heading(para)]
    # Styles in many college files mark every cover-page line as Heading.  Body begins
    # at the first real Abstract/Chapter marker, never at the cover page.
    body_start = next((idx for idx, para in enumerate(doc.paragraphs)
                       if idx > 15 and re.match(r"^(?:abstract|chapter\s*[-–:]?\s*\d+)", _clean_value(para.text), re.I)), None)
    if body_start is None:
        body_start = next((idx for idx in heading_indexes if idx > 15), len(doc.paragraphs))
    body_heading_indexes = [idx for idx in heading_indexes if idx >= body_start and _is_editable_body_heading(doc.paragraphs[idx].text)]
    sections: List[Dict[str, Any]] = []
    for pos, start in enumerate(body_heading_indexes):
        title = _clean_value(doc.paragraphs[start].text)
        if "bottom of form" in title.lower() and start + 1 < len(doc.paragraphs):
            following = _clean_value(doc.paragraphs[start + 1].text)
            if following.upper() == "OBJECTIVES":
                title = re.sub(r"bottom of form", "OBJECTIVES", title, flags=re.I)
        end = body_heading_indexes[pos + 1] if pos + 1 < len(body_heading_indexes) else len(doc.paragraphs)
        # Front-matter headings are retained but are not AI body sections.
        if title.upper() in {"CERTIFICATE", "DECLARATION", "ACKNOWLEDGEMENT", "ACKNOWLEDGMENTS", "LIST OF FIGURES", "LIST OF TABLES", "INDEX", "TABLE OF CONTENTS"} or re.match(r"^chapter\s*[-–:]?\s*\d+", title, re.I):
            continue
        sections.append({"title": title, "start": start, "end": end})
    return sections


def _first_nonempty_after(paragraphs: List[str], label: str) -> str:
    for idx, text in enumerate(paragraphs[:-1]):
        if _clean_value(text).lower() == label.lower():
            for candidate in paragraphs[idx + 1: idx + 5]:
                candidate = _clean_value(candidate)
                if candidate:
                    return candidate
    return ""


def _detect_field_values(doc: Document, placeholders: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """Find only values visible in the uploaded document so the user can confirm them."""
    values: Dict[str, List[str]] = {key: [] for key in FIELD_LABELS}
    text_items = [_clean_value(p.text) for p in doc.paragraphs if _clean_value(p.text)]
    # Cover pages frequently put university/college labels in drawing text
    # boxes, which python-docx omits from ``doc.paragraphs``. Read their text
    # nodes directly so confirmation data is not lost.
    try:
        textbox_text = _clean_value(" ".join(node.text or "" for node in doc.element.iter(qn("w:t"))))
        if textbox_text:
            text_items.extend(part.strip() for part in re.split(r"\s{2,}", textbox_text) if part.strip())
    except Exception:
        pass
    joined = "\n".join(text_items)

    def add(key: str, value: str):
        value = _clean_value(value).strip('“”"')
        if value and not value.startswith(("<", "[", "{{")) and value.lower() not in {"xxxx", "name of student", "name of the candidate", "name of the guide", "on"} and value not in values[key]:
            values[key].append(value)

    # University names on graphical cover pages are often embedded in one long
    # drawing-text-box string rather than a standalone paragraph.
    for match in re.finditer(r"\b([A-Z][A-Z ]{3,80}?\s+UNIVERSITY)\b", joined):
        add("university_name", match.group(1))

    for item in text_items:
        for key, pattern in {
            "roll_no": r"(?:roll\s*(?:no\.?|number)|prn)\s*[:.]?\s*([^\n|]{3,60})",
            "exam_seat_no": r"exam\s*seat\s*(?:no\.?)?\s*[:.]?\s*([^\n|]{3,60})",
            "academic_year": r"\b(20\d{2}\s*[-–/]\s*\d{2,4})\b",
            "group_no": r"\b(group\s*(?:no\.?)?\s*\d+[A-Za-z-]*)\b",
        }.items():
            match = re.search(pattern, item, re.I)
            if match:
                add(key, match.group(1))
        if "department of" in item.lower():
            add("department_name", item)
        if "college" in item.lower() and len(item) < 120:
            add("college_name", item)
        if "university" in item.lower() and len(item) < 140:
            add("university_name", item)

    add("student_name", _first_nonempty_after(text_items, "By"))
    submitted = _first_nonempty_after(text_items, "Submitted by")
    if submitted:
        add("student_name", submitted)
    add("guide_name", _first_nonempty_after(text_items, "Under the guidance of"))
    for idx, item in enumerate(text_items[:-1]):
        if "report entitled" in item.lower():
            candidate = _clean_value(text_items[idx + 1])
            if candidate and "submitted to" not in candidate.lower():
                add("topic", candidate)

    for item in text_items:
        if re.match(r"^(?:Prof\.?|Dr\.?)\s+", item) and "guide" not in item.lower():
            if "principal" not in item.lower() and "head" not in item.lower():
                add("guide_name", item)
        if "principal" in item.lower() and item != "Principal":
            add("principal_name", item.replace("Principal", ""))

    for match in re.finditer(r"carried out at\s+(.+?),\s*under the guidance of\s+(.+?)(?:\s+and\s|\s+it\s)", joined, re.I):
        add("company_name", match.group(1))
        add("internship_mentor_name", match.group(2))

    for ph in placeholders:
        key = ph["type"]
        if key in values:
            add(key, ph["raw"])
    return {key: value for key, value in values.items() if value}


def _detect_role_records(doc: Document) -> List[Dict[str, str]]:
    """Extract names with their actual title from cover/certificate pages.

    The report format is the source of truth: a college may use roles other than
    Guide, HOD, and Principal, so we preserve every recognised designation.
    """
    lines = [_clean_value(p.text) for p in doc.paragraphs if _clean_value(p.text)]
    lines.extend(
        _clean_value(p.text)
        for table in doc.tables for row in table.rows for cell in row.cells
        for p in cell.paragraphs if _clean_value(p.text)
    )
    records: List[Dict[str, str]] = []

    def add(key: str, label: str, name: str):
        name = _clean_value(name).strip(" :-,\t")
        # Do not treat labels/placeholders as names.
        if not name or len(name) < 4 or not re.search(r"[A-Za-z]", name):
            return
        if re.fullmatch(r"(?i)(?:the\s+)?" + re.escape(label), name):
            return
        # A valid signatory is a short personal name, never an acknowledgement
        # sentence which happens to mention a designation.
        if len(name) > 90 or re.search(r"\b(?:who|whose|that|for|and|would|with|provided|guidance|support)\b", name, re.I):
            return
        if not re.search(r"(?:Prof\.?|Dr\.?|Mr\.?|Ms\.?|Mrs\.?)\s+(?:[A-Z]\.?\s*)*[A-Za-z]{3,}", name):
            return
        item = {"id": key, "label": label, "value": name}
        if item not in records:
            records.append(item)

    # Certificate signatories are commonly laid out as two distinct paragraphs:
    # one name, then one designation.  Process this unambiguous form first.
    for index, line in enumerate(lines[1:], start=1):
        prior = lines[index - 1]
        if not re.match(r"^(?:Prof\.?|Dr\.?|Mr\.?|Ms\.?|Mrs\.?)\s+", prior, re.I):
            continue
        for key, (label, role_pattern) in ROLE_PATTERNS.items():
            if re.fullmatch(r"\s*(?:" + role_pattern + r")\s*", line, re.I):
                add(key, label, prior)

    for index, line in enumerate(lines):
        for key, (label, role_pattern) in ROLE_PATTERNS.items():
            # Same line: "Prof. A. Name — Guide" or "Guide: Prof. A. Name"
            match = re.search(r"((?:Prof\.?|Dr\.?|Mr\.?|Ms\.?|Mrs\.?)\s*[A-Za-z][A-Za-z .'-]{2,80}?)\s*(?:[-–,]|\s{2,})\s*" + role_pattern, line, re.I)
            if match:
                add(key, label, match.group(1))
                continue
            # Narrative acknowledgement wording: "Head of Department Dr. A. Name
            # who...". Capture only the honorific/name portion, never its prose.
            match = re.search(role_pattern + r"\s+(?:is\s+)?((?:Prof\.?|Dr\.?|Mr\.?|Ms\.?|Mrs\.?)\s*[A-Za-z][A-Za-z .'-]{2,80}?)(?:\s+(?:who|whose|for|and|with|provided|is|was)\b|[,.;]|$)", line, re.I)
            if match:
                add(key, label, match.group(1))
                continue
            match = re.search(role_pattern + r"\s*[:\-–]?\s*((?:Prof\.?|Dr\.?|Mr\.?|Ms\.?|Mrs\.?)\s*[A-Za-z][A-Za-z .'-]{2,80})", line, re.I)
            if match:
                add(key, label, match.group(1))
                continue
    return records


def extract_pdf_research_paper(pdf_path: str) -> Dict[str, str]:
    if not _PYPDF_AVAILABLE or not os.path.exists(pdf_path):
        return {}
    try:
        reader = pypdf.PdfReader(pdf_path)
        first_page_text = reader.pages[0].extract_text() if reader.pages else ""
        lines = [l.strip() for l in first_page_text.split("\n") if l.strip()]
        title = lines[0] if lines else "Research Paper"

        full_text = "\n".join(p.extract_text() for p in reader.pages[:3] if p.extract_text())
        abstract_match = re.search(r"abstract[\s:—-]+([\s\S]*?)(?:index terms|keywords|1\.?\s+introduction)", full_text, re.IGNORECASE)
        abstract = abstract_match.group(1).strip() if abstract_match else full_text[:400]

        return {
            "title": title,
            "abstract": abstract,
            "filename": os.path.basename(pdf_path),
        }
    except Exception as e:
        print(f"[DocxReader] PDF extract error: {e}")
        return {}


def extract_supporting_material(file_path: str, max_chars: int = 30000) -> str:
    """Extract project facts from a user-provided PDF, DOCX, PPTX, or text file."""
    suffix = os.path.splitext(file_path)[1].lower()
    try:
        if suffix == ".docx":
            doc = Document(file_path)
            parts = [p.text for p in doc.paragraphs]
            parts.extend(cell.text for table in doc.tables for row in table.rows for cell in row.cells)
            return "\n".join(parts)[:max_chars]
        if suffix == ".pdf" and _PYPDF_AVAILABLE:
            reader = pypdf.PdfReader(file_path)
            return "\n".join(page.extract_text() or "" for page in reader.pages)[:max_chars]
        if suffix == ".pptx":
            from pptx import Presentation
            presentation = Presentation(file_path)
            return "\n".join(shape.text for slide in presentation.slides for shape in slide.shapes if hasattr(shape, "text"))[:max_chars]
        if suffix in {".txt", ".md"}:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as source:
                return source.read(max_chars)
    except Exception as exc:
        print(f"[DocxReader] Supporting-material extract error: {exc}")
    return ""


def analyze_docx(file_path: str) -> Dict[str, Any]:
    doc = Document(file_path)

    all_raw_placeholders: List[Dict[str, Any]] = []
    seen_raw_tokens: Set[str] = set()

    # 1. Scan Paragraphs for Placeholders & Pre-fills
    for idx, para in enumerate(doc.paragraphs):
        text = para.text
        para_placeholders = _extract_placeholders_from_text(text)
        for ph in para_placeholders:
            if ph["raw"] not in seen_raw_tokens:
                seen_raw_tokens.add(ph["raw"])
                all_raw_placeholders.append({**ph, "location": "paragraph", "para_idx": idx})

    # 2. Scan Tables for Placeholders
    for t_idx, table in enumerate(doc.tables):
        for r_idx, row in enumerate(table.rows):
            for c_idx, cell in enumerate(row.cells):
                cell_text = cell.text.strip()
                cell_placeholders = _extract_placeholders_from_text(cell_text)
                for ph in cell_placeholders:
                    if ph["raw"] not in seen_raw_tokens:
                        seen_raw_tokens.add(ph["raw"])
                        all_raw_placeholders.append({
                            **ph,
                            "location": "table",
                            "table_idx": t_idx,
                            "row_idx": r_idx,
                            "cell_idx": c_idx,
                        })

    # The uploaded DOCX—not a fixed syllabus—is the document contract.
    sections = _detect_sections(doc)
    field_values = _detect_field_values(doc, all_raw_placeholders)
    role_records = _detect_role_records(doc)
    candidate_lines = [p.text.strip() for p in doc.paragraphs[:80] if re.search(r"(?:candidate|exam\s*seat|roll\s*no|submitted by)", p.text, re.I)]
    detected_student_count = min(4, max(1, len(field_values.get("student_name", [])), len(candidate_lines) // 2))

    confirmed_fields = []
    for key, label in FIELD_LABELS.items():
        old_values = field_values.get(key, [])
        if old_values or key in {"student_name", "roll_no", "exam_seat_no", "academic_year"}:
            confirmed_fields.append({
                "id": key,
                "key": key,
                "label": label,
                "default_value": old_values[0] if old_values else "",
                "source_values": old_values,
                "required": key in {"student_name", "academic_year"},
                "type": "text",
            })

    is_template = len(all_raw_placeholders) >= 2 or not any(s.get("end", 0) - s.get("start", 0) > 5 for s in sections)

    return {
        "file_path": file_path,
        "is_template": is_template,
        "default_student_count": detected_student_count,
        "title_page_fields": [field for field in confirmed_fields if field["key"] in {"topic", "student_name", "roll_no", "exam_seat_no", "academic_year"}],
        "faculty_fields": [field for field in confirmed_fields if field["key"] in {"guide_name", "hod_name", "principal_name", "department_name", "college_name", "university_name", "company_name", "internship_mentor_name"}],
        "role_records": role_records,
        "confirmed_fields": confirmed_fields,
        "detected_values": field_values,
        "all_placeholders": all_raw_placeholders,
        "headings": [section["title"] for section in sections],
        "sections": sections,
        "total_paragraphs": len(doc.paragraphs),
        "total_tables": len(doc.tables),
    }
