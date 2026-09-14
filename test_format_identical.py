"""Format-identical harness: run the in-place pipeline on the friend's reference
report with a NEW topic/names, then diff the output against the reference on the
format attributes that must stay identical.

Usage:  cd backend && python3 ../test_format_identical.py
"""
import os
import re
import sys
import html
import zipfile

BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
sys.path.insert(0, BACKEND)

from core.docx_reader import analyze_docx          # noqa: E402
from core.docx_writer import fill_template          # noqa: E402
from core.gemini_engine import generate_content     # noqa: E402

REFERENCE = "/Users/ajitreddy/Downloads/Test Reports/Smart_RoofTop_Report.docx"

TOPIC = "SMART IRRIGATION SYSTEM USING SOIL MOISTURE SENSOR AND ARDUINO"
STUDENTS = [
    ("AJIT REDDY", "S190234501"),
    ("PRIYA SHARMA", "S190234502"),
    ("RAHUL DESHMUKH", "S190234503"),
]
GROUP_NO = "Group No: 12"
YEAR = "2024-25"
GUIDE = "Prof. R. A. Vasmatkar"
HOD = "Dr. M. P. Wankhade"
PRINCIPAL = "Dr. S. D. Lokhande"

OLD_TOPIC_MARKERS = ["ROOFTOP", "CURTAIN", "TEMPERATURE SENSOR"]
# Friend's candidate + signature names. "AJIT" is excluded because our sample
# student is "AJIT REDDY"; the remaining tokens are unique to the reference.
OLD_NAME_MARKERS = [
    "KOLHE", "KOLPE", "KOLPUKE", "SHREYASH", "PRATIKSHA", "SUDHIR", "TULSHIRAM",
    "SATISH", "VEDANT", "KONDE", "ATHRAV", "KSHIRSAGAR", "KRUSHNA", "KUDALE",
]


def build_student_info():
    info = {
        "topic": TOPIC,
        "group_no": GROUP_NO,
        "academic_year": YEAR,
        "guide_name": GUIDE,
        "hod_name": HOD,
        "principal_name": PRINCIPAL,
        "college_name": "Sinhgad College of Engineering",
        "department_name": "Computer Engineering",
        "university_name": "Savitribai Phule Pune University",
        "report_type": "pbl",
    }
    for i, (name, seat) in enumerate(STUDENTS, 1):
        info[f"student_name_{i}"] = name
        info[f"roll_no_{i}"] = seat
    return info


def run_pipeline():
    doc_map_full = analyze_docx(REFERENCE)
    doc_map = {k: v for k, v in doc_map_full.items() if k != "file_path"}
    headings = doc_map_full.get("headings", [])
    student_info = build_student_info()

    print(f"[harness] reference headings: {len(headings)}")
    ai_sections = generate_content(
        topic=TOPIC,
        sections=headings,
        student_info=student_info,
        reference_notes="An Arduino-based drip irrigation controller using a soil moisture sensor and a relay-driven water pump.",
        research_papers=[],
        source_material="",
        target_words_per_section=220,
    )
    print(f"[harness] generated sections: {len(ai_sections)}")

    out = fill_template(
        source_docx_path=REFERENCE,
        doc_map=doc_map,
        student_info=student_info,
        ai_sections=ai_sections,
        images=[],
        output_filename="harness_irrigation.docx",
    )
    print(f"[harness] wrote: {out}")
    return out, headings, ai_sections


# ---------- comparison helpers ----------

def _read_zip(path):
    with zipfile.ZipFile(path) as z:
        return {n: z.read(n) for n in z.namelist()}


def _media_names(files):
    return sorted(n for n in files if n.startswith("word/media/"))


def _hf_parts(files):
    return sorted(n for n in files if re.match(r"word/(header|footer)\d*\.xml", n))


def _all_text(data):
    """Concatenate w:t text nodes (like python-docx), including text boxes.

    Tag-stripping inserts a space per removed tag, which corrupts headings whose
    runs are split character-by-character; joining w:t contents avoids that.
    """
    xml = data.decode("utf-8", "ignore")
    parts = re.findall(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", xml, re.S)
    return html.unescape("".join(parts))


def _sect_pr(path):
    """Return page size + margin attrs from the first sectPr in document.xml."""
    files = _read_zip(path)
    xml = files["word/document.xml"].decode("utf-8", "ignore")
    m = re.search(r"<w:pgSz[^/]*/>", xml)
    pg = m.group(0) if m else "(none)"
    m2 = re.search(r"<w:pgMar[^/]*/>", xml)
    mar = m2.group(0) if m2 else "(none)"
    title_pg = "<w:titlePg" in xml
    return pg, mar, title_pg


def compare(ref, out, headings, ai_sections):
    results = []

    def check(name, ok, detail=""):
        results.append((name, ok, detail))

    rf, of = _read_zip(ref), _read_zip(out)

    # 1. page size + margins + first-page flag
    rpg, rmar, rtp = _sect_pr(ref)
    opg, omar, otp = _sect_pr(out)
    check("page size identical", rpg == opg, f"ref={rpg} out={opg}")
    check("margins identical", rmar == omar, f"ref={rmar} out={omar}")
    check("titlePg flag unchanged", rtp == otp, f"ref={rtp} out={otp}")

    # 2. media / logos
    rm, om = _media_names(rf), _media_names(of)
    check("media files preserved", rm == om, f"ref={len(rm)} out={len(om)}")

    # 3. header/footer parts exist
    rh, oh = _hf_parts(rf), _hf_parts(of)
    check("header/footer parts preserved", rh == oh, f"ref={rh} out={oh}")

    # 4. header text carries NEW topic, not old mismatched topic
    header_text = " ".join(_all_text(of[n]) for n in oh if "header" in n).upper()
    check("header shows new topic", TOPIC.upper()[:20] in header_text,
          header_text[:120])
    check("header has no old topic", not any(m in header_text for m in ["OPINION MINING", "TEXT SUMMARIZATION"]),
          header_text[:120])

    # 5. footer text preserved exactly (college identity + layout)
    ref_footers = {n: re.sub(r"\s+", " ", _all_text(rf[n])).strip() for n in rh if "footer" in n}
    out_footers = {n: re.sub(r"\s+", " ", _all_text(of[n])).strip() for n in oh if "footer" in n}
    check("footers preserved verbatim", ref_footers == out_footers,
          f"ref={ref_footers} out={out_footers}")

    # 6. document.xml text: new topic + new names present, old gone
    doc_text = _all_text(of["word/document.xml"]).upper()
    doc_norm = re.sub(r"\s+", " ", doc_text)
    check("new topic present in body/cover", TOPIC.upper()[:25] in doc_norm)
    for name, _ in STUDENTS:
        check(f"new student '{name}' present", name.upper() in doc_norm)
    leaked_topic = [m for m in OLD_TOPIC_MARKERS if m in doc_norm]
    check("no old topic leakage", not leaked_topic, f"found={leaked_topic}")
    leaked_names = [m for m in OLD_NAME_MARKERS if m in doc_norm]
    check("no old student-name leakage", not leaked_names, f"found={leaked_names}")

    # 7. headings preserved (structure identical); normalize run-split whitespace.
    # Match on the heading's TEXT part (number prefix stripped) because a legacy
    # form field can split "1.6 OBJECTIVES" across two paragraphs, so the full
    # string is never contiguous even though the heading is intact.
    def text_part(h):
        t = re.sub(r"\s+", " ", h.upper()).strip()
        return re.sub(r"^\d+(?:\.\d+)*\.?\s*", "", t).strip() or t

    missing = [h for h in headings if text_part(h) not in doc_norm]
    check("all reference headings preserved", not missing, f"missing={missing}")

    # 8. body content is about the new topic (spot-check a generated section landed)
    sample_keys = [h for h in ai_sections if re.sub(r"\s+", " ", h.upper()) in doc_norm][:3]
    check("generated sections landed in body", len(sample_keys) >= 1, f"keys={sample_keys}")

    return results


def main():
    out, headings, ai_sections = run_pipeline()
    results = compare(REFERENCE, out, headings, ai_sections)
    print("\n================ FORMAT / CONTENT DIFF ================")
    passed = 0
    for name, ok, detail in results:
        flag = "PASS" if ok else "FAIL"
        passed += ok
        line = f"[{flag}] {name}"
        if detail and not ok:
            line += f"  ->  {detail}"
        print(line)
    print(f"-------------------------------------------------------")
    print(f"{passed}/{len(results)} checks passed")
    print(f"output: {out}")


if __name__ == "__main__":
    main()
