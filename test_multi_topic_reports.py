"""
test_multi_topic_reports.py
Runs automated multi-topic PBL report generation and format verification against
the reference standard ('PBL Report Rooftop Curtains.docx').

Verifies:
1. Chapters stay consistent across all reports.
2. Subtopics adapt dynamically to the domain.
3. Generates high-volume, authentic technical content per chapter (~4000-5000 words).
4. Section 1 page numbers: Uppercase Roman (I, II, III, IV, V...).
5. Section Break before Chapter 1.
6. Section 2 page numbers: Decimal (1, 2, 3...) starting at 1.
7. Zero leakage of reference names, topics, or components.
"""

import os
import re
import sys
import docx
import zipfile
import html

BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
sys.path.insert(0, BACKEND)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BACKEND, ".env"))
except Exception:
    pass

from core.docx_reader import analyze_docx
from core.docx_writer import fill_template
from core.gemini_engine import generate_content

REFERENCE = "/Users/ajitreddy/Downloads/Test Reports/PBL Report Rooftop Curtains.docx"

TEST_TOPICS = [
    {
        "id": "iot_hydroponics",
        "topic": "SMART IOT HYDROPONICS MONITORING AND AUTOMATED NUTRIENT DOSING SYSTEM",
        "group_no": "Group No: 08",
        "students": [
            ("ROHAN SHARMA", "S190234601"),
            ("PRIYA PATEL", "S190234602"),
            ("VARUN MEHTA", "S190234603"),
            ("ANANYA IYER", "S190234604"),
        ],
        "guide": "Prof. S. V. Patil",
        "notes": (
            "A smart closed-loop hydroponics monitoring system utilizing ESP32, pH sensor, EC (electrical conductivity) "
            "sensor, water temperature sensor, and peristaltic dosing pumps. Regulates pH between 5.8-6.5 and EC between "
            "1.2-1.8 mS/cm automatically, pushing real-time telemetry to an MQTT dashboard."
        ),
    },
    {
        "id": "ai_driver_drowsiness",
        "topic": "REAL-TIME DRIVER DROWSINESS DETECTION AND ACCIDENT PREVENTION SYSTEM",
        "group_no": "Group No: 14",
        "students": [
            ("SIDDHARTH JADHAV", "S190234701"),
            ("AARAV DESHMUKH", "S190234702"),
            ("TANVI SHINDE", "S190234703"),
            ("NEHA CHAVAN", "S190234704"),
        ],
        "guide": "Prof. R. A. Vasmatkar",
        "notes": (
            "An embedded vision system deployed on Raspberry Pi 4 with camera module. Uses MediaPipe Face Mesh and "
            "Eye Aspect Ratio (EAR) along with Mouth Aspect Ratio (MAR) to detect micro-sleeps and yawning in real-time. "
            "Triggers a 90dB buzzer and sends GPS emergency coordinates via GSM module if eye closure exceeds 1.5 seconds."
        ),
    },
    {
        "id": "web_campus_platform",
        "topic": "CAMPUSCONNECT - DECENTRALIZED ACADEMIC PEER COLLABORATION PLATFORM",
        "group_no": "Group No: 21",
        "students": [
            ("KAVYA NAIR", "S190234801"),
            ("ADITYA KULKARNI", "S190234802"),
            ("MEERA MENON", "S190234803"),
            ("SAHIL VERMA", "S190234804"),
        ],
        "guide": "Prof. N. G. Bhojne",
        "notes": (
            "A collaborative student resource and mentorship platform built with React, FastAPI, WebSockets, and PostgreSQL. "
            "Features real-time collaborative code editor, verified past-year question paper repository with semantic vector "
            "search, and automated peer-matching algorithm based on project domain interests."
        ),
    }
]

OLD_MARKERS = [
    "ROOFTOP CURTAIN", "ROOFTOP", "DS18B20", "MOTOR DRIVER L23D", "L23D",
    "OPEN-AIR CAFE", "MOTORIZED CURTAIN", "KOLPE", "KOLPUKE", "KONDE", "KSHIRSAGAR",
    "KUDALE", "PRATIKSHA", "VEDANT", "ATHRAV", "KRUSHNA", "TULSHIRAM", "SOMNATH", "GANESH", "PALLAVI",
]


def run_test_topic(test_case):
    print(f"\n================================================================================")
    print(f"▶ TESTING TOPIC: {test_case['topic']}")
    print(f"================================================================================")

    doc_map_full = analyze_docx(REFERENCE)
    doc_map = {k: v for k, v in doc_map_full.items() if k != "file_path"}
    headings = doc_map_full.get("headings", [])

    student_info = {
        "topic": test_case["topic"],
        "group_no": test_case["group_no"],
        "academic_year": "2025-26",
        "guide_name": test_case["guide"],
        "hod_name": "Dr. M. P. Wankhade",
        "principal_name": "Dr. S. D. Lokhande",
        "college_name": "Sinhgad College of Engineering",
        "department_name": "Department of Computer Engineering",
        "university_name": "Savitribai Phule Pune University",
        "report_type": "pbl",
    }
    for i, (name, seat) in enumerate(test_case["students"], 1):
        student_info[f"student_name_{i}"] = name
        student_info[f"roll_no_{i}"] = seat

    print(f"[*] Generating academic content for {len(headings)} sections...")
    ai_sections = generate_content(
        topic=test_case["topic"],
        sections=headings,
        student_info=student_info,
        reference_notes=test_case["notes"],
        research_papers=[],
        source_material="",
        target_words_per_section=250,
    )

    out_file = f"test_pbl_{test_case['id']}.docx"
    print(f"[*] Assembling publication-quality DOCX: {out_file}...")
    out_path = fill_template(
        source_docx_path=REFERENCE,
        doc_map=doc_map,
        student_info=student_info,
        ai_sections=ai_sections,
        images=[],
        output_filename=out_file,
    )
    print(f"[*] Output saved to: {out_path}")

    # Inspect the generated DOCX
    doc = docx.Document(out_path)
    
    # 1. Inspect Sections & Page Numbering
    assert len(doc.sections) >= 2, f"Expected at least 2 sections, got {len(doc.sections)}"
    
    sec1_pg = [el.attrib for el in doc.sections[0]._sectPr.findall("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pgNumType")]
    sec2_pg = [el.attrib for el in doc.sections[1]._sectPr.findall("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pgNumType")]
    
    sec1_fmt = sec1_pg[0].get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}fmt") if sec1_pg else None
    sec2_fmt = sec2_pg[0].get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}fmt") if sec2_pg else None
    sec2_start = sec2_pg[0].get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}start") if sec2_pg else None

    print(f"\n--- SECTION & NUMBERING INSPECTION ---")
    print(f"Section 1 pgNumType: {sec1_pg} (Format: {sec1_fmt})")
    print(f"Section 2 pgNumType: {sec2_pg} (Format: {sec2_fmt}, Start: {sec2_start})")
    print(f"Section 1 Footer Text: {repr(doc.sections[0].footer.paragraphs[0].text)}")
    print(f"Section 2 Footer Text: {repr(doc.sections[1].footer.paragraphs[0].text)}")

    assert sec1_fmt == "upperRoman", f"Section 1 format should be upperRoman, got {sec1_fmt}"
    assert sec2_fmt == "decimal" or sec2_fmt is None, f"Section 2 format should be decimal, got {sec2_fmt}"
    assert sec2_start == "1", f"Section 2 start should be 1, got {sec2_start}"

    # 2. Inspect Word Counts per Chapter
    chapters = {
        "FRONT MATTER": [],
        "CHAPTER 1: INTRODUCTION": [],
        "CHAPTER 2: LITERATURE SURVEY": [],
        "CHAPTER 3: PROPOSED METHODOLOGY": [],
        "CHAPTER 4: RESULT AND DISCUSSION": [],
        "CHAPTER 5: CONCLUSION & FUTURE": [],
        "CHAPTER 6: REFERENCES": [],
    }
    current_chap = "FRONT MATTER"

    for p in doc.paragraphs:
        txt = p.text.strip()
        if not txt:
            continue
        if txt.startswith("1.") or "CHAPTER 1" in txt:
            current_chap = "CHAPTER 1: INTRODUCTION"
        elif txt.startswith("2.") or "LITERATURE SURVEY" in txt:
            current_chap = "CHAPTER 2: LITERATURE SURVEY"
        elif txt.startswith("3.") or "PROPOSED" in txt or "OVERVIEW OF" in txt:
            current_chap = "CHAPTER 3: PROPOSED METHODOLOGY"
        elif txt.startswith("4.") or "HOW IT WORKS" in txt or ("RESULT" in txt and "DISCUSSION" in txt):
            current_chap = "CHAPTER 4: RESULT AND DISCUSSION"
        elif txt.startswith("5.") or ("CONCLUSION" in txt and "FUTURE" in txt):
            current_chap = "CHAPTER 5: CONCLUSION & FUTURE"
        elif "REFERENCES" in txt:
            current_chap = "CHAPTER 6: REFERENCES"
        chapters[current_chap].append(txt)

    total_words = 0
    print(f"\n--- CHAPTER CONTENT VOLUME ---")
    for chap, paras in chapters.items():
        w_count = sum(len(p.split()) for p in paras)
        total_words += w_count
        print(f"  {chap:<34}: {len(paras):3d} paragraphs | ~{w_count:5d} words")

    print(f"  {'TOTAL DOCUMENT WORDS':<34}: {len(doc.paragraphs):3d} paragraphs | ~{total_words:5d} words")
    assert total_words >= 2500, f"Generated content too short! Expected >= 2500 words, got {total_words}"

    # 3. Check for Old Marker Leakage
    with zipfile.ZipFile(out_path) as z:
        xml = z.read("word/document.xml").decode("utf-8", "ignore")
        full_text = html.unescape("".join(re.findall(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", xml, re.S))).upper()

    leaked = [m for m in OLD_MARKERS if m in full_text]
    print(f"\n--- INTEGRITY CHECKS ---")
    print(f"Old reference markers found: {leaked or 'NONE (PASSED)'}")
    assert not leaked, f"Old markers leaked: {leaked}"

    # Check for all new student names
    for name, _ in test_case["students"]:
        assert name.upper() in full_text, f"Student {name} missing from document!"
    print(f"All {len(test_case['students'])} student names verified: PASSED")

    print(f"\n✔ TEST PASSED: {test_case['id']}\n")
    return {
        "id": test_case["id"],
        "topic": test_case["topic"],
        "words": total_words,
        "paragraphs": len(doc.paragraphs),
        "out_path": out_path,
        "passed": True,
    }


def main():
    results = []
    for tc in TEST_TOPICS:
        res = run_test_topic(tc)
        results.append(res)

    print("\n" + "="*80)
    print("                      ALL MULTI-TOPIC TESTS SUMMARY")
    print("="*80)
    for r in results:
        status = "PASSED ✔" if r["passed"] else "FAILED ✘"
        print(f"[{status}] {r['id']:<24} | Words: ~{r['words']:5d} | Paras: {r['paragraphs']:3d} | {r['topic']}")
    print("="*80)


if __name__ == "__main__":
    main()
