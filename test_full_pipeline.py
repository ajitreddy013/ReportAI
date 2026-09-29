"""
test_full_pipeline.py
Comprehensive End-to-End Integration & Unit Test Suite for ReportAI.

Validates the full lifecycle of document processing:
1.  API Status & Config verification
2.  Template DOCX Parsing & Structural Mapping (upload_doc)
3.  Existing Report DOCX Parsing & Auto-Extraction (upload_doc)
4.  Weekly Attendance Diary Generator (Mon-Fri 5-day cycle)
5.  Internship Report Generation End-to-End (generate)
6.  Project Report (Template Mode) Generation End-to-End (generate)
7.  Project Report (Swap Mode) Generation End-to-End (generate)
8.  Multi-Page Academic HTML Preview Rendering (preview)
9.  DOCX Binary Structural Validation (python-docx integrity check)
10. Store Persistence & Reboot Recovery (_save_stores / _load_stores)
"""

import os
import sys
import json
import io
import asyncio
import tempfile
import docx
from starlette.datastructures import UploadFile, Headers

# Force deterministic fast generation
os.environ["GEMINI_API_KEY"] = ""

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
sys.path.insert(0, BACKEND_DIR)

from main import (
    status,
    upload_doc,
    upload_source,
    generate,
    preview,
    download_docx,
    _doc_store,
    _report_store,
    _save_report_store,
    _save_doc_store,
    _load_stores,
)
from core.report_rules import (
    STANDARD_INTERNSHIP_CHAPTERS,
    STANDARD_PROJECT_CHAPTERS,
    generate_weekly_attendance_diary,
    UML_DIAGRAM_SLOTS,
)


class MockRequest:
    """Mock Starlette Request for testing FastAPI endpoints."""
    def __init__(self, form_data: dict):
        self._form_data = form_data

    async def form(self):
        return self._form_data


def create_upload_file(file_path: str, content_type: str = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"):
    """Helper to create a Starlette UploadFile from local file path."""
    with open(file_path, "rb") as f:
        file_bytes = f.read()
    bio = io.BytesIO(file_bytes)
    filename = os.path.basename(file_path)
    headers = Headers({"content-type": content_type})
    return UploadFile(file=bio, filename=filename, headers=headers)


def run_async(coro):
    return asyncio.run(coro)


print("\n" + "=" * 65)
print("🚀 STARTING COMPREHENSIVE REPORTAI FULL PIPELINE TEST SUITE")
print("=" * 65)


# -------------------------------------------------------------
# TEST 1: Status & Config
# -------------------------------------------------------------
def test_1_status():
    print("\n[TEST 1] Testing API Status & Environment Config...")
    res = status()
    assert res["status"] == "ok"
    assert "gemini_available" in res
    print(f"  ✓ System status OK (gemini_available={res['gemini_available']}, using_ai={res['using_ai']})")


# -------------------------------------------------------------
# TEST 2: Template DOCX Upload & Structural Analysis
# -------------------------------------------------------------
def test_2_upload_template():
    print("\n[TEST 2] Testing Template DOCX Upload & Layout Parsing...")
    template_path = os.path.join(BASE_DIR, "test_assets", "Report_format.docx")
    assert os.path.exists(template_path), f"Missing template at {template_path}"

    uf = create_upload_file(template_path)
    res = run_async(upload_doc(uf))

    assert "doc_id" in res
    assert res["is_template"] is True
    assert len(res["headings"]) > 0
    assert len(res["uml_slots"]) == len(UML_DIAGRAM_SLOTS)
    assert res["total_paragraphs"] > 0
    print(f"  ✓ Template uploaded & analyzed: doc_id={res['doc_id']}")
    print(f"  ✓ Identified {len(res['headings'])} headings and {len(res['uml_slots'])} diagram slots.")
    return res["doc_id"], res["headings"]


# -------------------------------------------------------------
# TEST 3: Existing Student Report DOCX Upload (Friend's Report)
# -------------------------------------------------------------
def test_3_upload_friend_report():
    print("\n[TEST 3] Testing Friend's Completed Report Upload & Extraction...")
    uploads_dir = os.path.join(BACKEND_DIR, "uploads")
    sample_files = [f for f in os.listdir(uploads_dir) if (f.startswith("sample_TalkAR") or "Preliminary" in f) and f.endswith(".docx")]

    if sample_files:
        sample_path = os.path.join(uploads_dir, sample_files[0])
        uf = create_upload_file(sample_path)
        res = run_async(upload_doc(uf))
        assert "doc_id" in res
        assert isinstance(res["is_template"], bool)
        print(f"  ✓ Existing report parsed: doc_id={res['doc_id']} (is_template={res['is_template']})")
        print(f"  ✓ Extracted {len(res['headings'])} sections and metadata.")
        return res["doc_id"]
    else:
        print("  ℹ No existing report found in uploads; using template.")
        return None


# -------------------------------------------------------------
# TEST 4: Weekly Attendance Diary Generator
# -------------------------------------------------------------
def test_4_weekly_attendance():
    print("\n[TEST 4] Testing 4-Week Mon-Fri Attendance Diary Synthesis...")
    diary = generate_weekly_attendance_diary(
        topic="Autonomous Mobile Robotics & SLAM",
        company="RoboTech Innovations Pvt Ltd",
        start_date_str="2025-01-06",
        weeks_count=4
    )
    assert len(diary) == 4, f"Expected 4 weeks, got {len(diary)}"
    total_days = sum(len(w["entries"]) for w in diary)
    assert total_days == 20, f"Expected 20 days (4 weeks x 5 Mon-Fri days), got {total_days}"

    days_set = set()
    for week in diary:
        assert week["week_num"] in [1, 2, 3, 4]
        assert len(week["week_label"]) >= 5
        for entry in week["entries"]:
            days_set.add(entry["day"])
            assert entry["status"] == "Completed"
            assert len(entry["topic"]) > 10

    # Ensure strictly weekdays (No Saturday/Sunday)
    assert days_set == {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday"}
    print(f"  ✓ Attendance Diary verified: 4 Weeks, 20 Mon-Fri entries, realistic engineering tasks.")


# -------------------------------------------------------------
# TEST 5: Full Internship Report Generation End-to-End
# -------------------------------------------------------------
def test_5_internship_generation(template_doc_id):
    print("\n[TEST 5] Testing Full Internship Report Generation End-to-End...")
    form_data = {
        "doc_id": template_doc_id,
        "report_type": "internship",
        "topic": "Cloud-Native Microservices & React Architecture",
        "mode": "template",
        "student_name": "Ajit Satish Kolpuke",
        "roll_no": "T190058501",
        "prn_no": "72283921B",
        "department": "Department of Computer Engineering",
        "college_name": "Smt. Kashibai Navale College of Engineering, Vadgaon (Bk), Pune - 411041",
        "company_name": "NeuAI Labs LLP",
        "company_address": "Tech Park, Hinjewadi Phase 1, Pune - 411057",
        "company_mentor_name": "Mr. Subham Asbe",
        "company_mentor_designation": "Technical Lead & Engineering Manager",
        "guide_name": "Prof. N. G. Bhojne",
        "hod_name": "Dr. M. P. Wankhade",
        "principal_name": "Dr. S. D. Lokhande",
        "academic_year": "2024-25",
        "internship_start_date": "2025-01-01",
        "internship_duration_weeks": "4",
        "stipend": "Rs. 15,000 / month",
        "reference_notes": "React 18, FastAPI, PostgreSQL, Docker, AWS ECS, CI/CD",
        "images_json": "[]",
        "papers_json": "[]",
        "source_ids_json": "[]",
    }

    req = MockRequest(form_data)
    res = run_async(generate(req))

    assert "report_id" in res
    assert res["report_type"] == "internship"
    assert len(res["sections"]) == 20
    report_id = res["report_id"]
    print(f"  ✓ Internship Report generated: report_id={report_id} (20 sections)")

    # Test HTML Preview
    preview_resp = preview(report_id)
    html = preview_resp.body.decode("utf-8")
    assert "INTERNSHIP" in html.upper()
    assert "AJIT SATISH KOLPUKE" in html.upper()
    assert "NEUAI LABS" in html.upper()
    assert "SUBHAM ASBE" in html.upper()
    assert "BHOJNE" in html.upper()
    assert "ATTENDANCE" in html.upper()
    assert "ANNEXURE 1" in html.upper()
    assert "ANNEXURE 2" in html.upper()
    print(f"  ✓ Academic Multi-Page Preview Verified ({len(html)} chars rendered directly from DOCX binary).")

    # Test DOCX File & Binary Integrity
    docx_resp = download_docx(report_id)
    docx_file_path = docx_resp.path
    assert os.path.exists(docx_file_path)

    doc = docx.Document(docx_file_path)
    assert len(doc.paragraphs) > 40
    assert len(doc.tables) >= 2
    print(f"  ✓ DOCX Binary Structure Verified: {len(doc.paragraphs)} paragraphs, {len(doc.tables)} tables, {os.path.getsize(docx_file_path)} bytes.")
    return report_id


# -------------------------------------------------------------
# TEST 6: Project Report Generation - Template Mode
# -------------------------------------------------------------
def test_6_project_template_generation(template_doc_id, headings):
    print("\n[TEST 6] Testing Project Report Generation - Template Mode...")
    form_data = {
        "doc_id": template_doc_id,
        "report_type": "project",
        "topic": "TalkAR – AI-Powered Lip-Sync Augmented Reality System",
        "mode": "template",
        "group_no": "Group No. 50",
        "guide_name": "Prof. P. M. Kamde",
        "hod_name": "Dr. R. H. Borhade",
        "principal_name": "Dr. S. D. Lokhande",
        "academic_year": "2025-26",
        "department": "Department of Computer Engineering",
        "college_name": "Smt. Kashibai Navale College of Engineering, Pune",
        "student_name_1": "Ajit Kolpuke",
        "roll_no_1": "72283921B",
        "student_name_2": "Rameshwar Ghadge",
        "roll_no_2": "72283922C",
        "student_name_3": "Pratik Patil",
        "roll_no_3": "72283923D",
        "student_name_4": "Rohit Sharma",
        "roll_no_4": "72283924E",
        "reference_notes": "Incremental Model, WebSockets, Python, MediaPipe, OpenCV, Android ARCore",
        "images_json": "[]",
        "papers_json": "[]",
        "source_ids_json": "[]",
    }

    req = MockRequest(form_data)
    res = run_async(generate(req))

    assert "report_id" in res
    report_id = res["report_id"]
    print(f"  ✓ Project Report generated: report_id={report_id}")

    # Preview
    preview_resp = preview(report_id)
    html = preview_resp.body.decode("utf-8")
    assert "TALKAR" in html.upper()
    assert "AJIT KOLPUKE" in html.upper()
    assert "KAMDE" in html.upper()
    print(f"  ✓ Project HTML Preview Verified ({len(html)} chars).")

    # DOCX Check
    docx_resp = download_docx(report_id)
    doc = docx.Document(docx_resp.path)
    assert len(doc.paragraphs) > 30
    print(f"  ✓ Project DOCX Verified: {len(doc.paragraphs)} paragraphs, {os.path.getsize(docx_resp.path)} bytes.")
    return report_id


# -------------------------------------------------------------
# TEST 7: Project Report Generation - Swap Mode
# -------------------------------------------------------------
def test_7_project_swap_generation(doc_id):
    target_id = doc_id
    if not target_id:
        print("\n[TEST 7] Skipping Swap Mode test.")
        return None

    print("\n[TEST 7] Testing Project Report Generation - Swap Mode...")
    form_data = {
        "doc_id": target_id,
        "report_type": "project",
        "topic": "SafeDrive – Driver Drowsiness Detection System",
        "mode": "swap",
        "group_no": "Group No. 12",
        "guide_name": "Prof. A. S. Shinde",
        "hod_name": "Dr. R. H. Borhade",
        "principal_name": "Dr. S. D. Lokhande",
        "academic_year": "2025-26",
        "student_name_1": "Sagar Jadhav",
        "roll_no_1": "72283950K",
        "student_name_2": "Vikas Shinde",
        "roll_no_2": "72283951L",
        "student_name_3": "Snehal Pawar",
        "roll_no_3": "72283952M",
        "student_name_4": "Pooja Patil",
        "roll_no_4": "72283953N",
        "reference_notes": "CNN, Eye Aspect Ratio, Raspberry Pi, Twilio SMS alerts",
        "images_json": "[]",
        "papers_json": "[]",
        "source_ids_json": "[]",
    }

    req = MockRequest(form_data)
    res = run_async(generate(req))
    assert "report_id" in res
    report_id = res["report_id"]
    print(f"  ✓ Swap Mode Report generated: report_id={report_id}")

    preview_resp = preview(report_id)
    html = preview_resp.body.decode("utf-8")
    assert "SAFEDRIVE" in html.upper() or "DROWSINESS" in html.upper()
    assert "SAGAR JADHAV" in html.upper()
    print(f"  ✓ Swapped Report Preview Verified ({len(html)} chars).")
    return report_id


# -------------------------------------------------------------
# TEST 8: Store Persistence & Reboot Recovery
# -------------------------------------------------------------
def test_8_persistence_and_recovery(report_id):
    print("\n[TEST 8] Testing Store Persistence & Reboot Recovery...")
    assert report_id in _report_store

    # Force save to disk
    _save_report_store()
    _save_doc_store()

    # Verify JSON file on disk
    store_path = os.path.join(BACKEND_DIR, "outputs", "_report_store.json")
    assert os.path.exists(store_path)
    with open(store_path, "r") as f:
        disk_data = json.load(f)
    assert report_id in disk_data

    # Wipe in-memory dictionary to simulate server restart
    _report_store.clear()
    assert report_id not in _report_store

    # Reload stores
    _load_stores()
    assert report_id in _report_store, "Failed to restore report from disk store!"

    # Verify preview works seamlessly after recovery
    preview_resp = preview(report_id)
    assert preview_resp.status_code == 200
    print(f"  ✓ Store persisted, restored, and preview served successfully after reboot simulation.")


# -------------------------------------------------------------
# TEST 9: 6-Week Extended Internship Attendance Test
# -------------------------------------------------------------
def test_9_internship_6_weeks():
    print("\n[TEST 9] Testing 6-Week Extended Internship Attendance Generation...")
    diary_6w = generate_weekly_attendance_diary(
        topic="Machine Learning DevOps Pipeline",
        company="TechCorp Solutions",
        start_date_str="2025-02-03",
        weeks_count=6
    )
    assert len(diary_6w) == 6
    total_days = sum(len(w["entries"]) for w in diary_6w)
    assert total_days == 30, f"Expected 30 entries (6 weeks x 5 days), got {total_days}"
    print(f"  ✓ 6-Week Extended Internship Attendance verified (6 weeks, 30 Mon-Fri entries).")


# -------------------------------------------------------------
# TEST 10: Supporting Material / Source File Upload & Extraction
# -------------------------------------------------------------
def test_10_upload_source_material():
    print("\n[TEST 10] Testing Supporting Material Upload (/api/upload-source)...")
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w", encoding="utf-8") as tmp:
        tmp.write("TalkAR Architecture: WebSocket server connects Android AR client with Python deep learning model. Latency benchmark is 32ms.")
        tmp_path = tmp.name

    try:
        uf = create_upload_file(tmp_path, content_type="text/plain")
        res = run_async(upload_source(uf))
        assert "source_id" in res
        assert res["characters_extracted"] > 50
        print(f"  ✓ Supporting source material uploaded and extracted ({res['characters_extracted']} chars).")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


if __name__ == "__main__":
    test_1_status()
    template_doc_id, headings = test_2_upload_template()
    friend_doc_id = test_3_upload_friend_report()
    test_4_weekly_attendance()
    internship_rep_id = test_5_internship_generation(template_doc_id)
    project_rep_id = test_6_project_template_generation(template_doc_id, headings)
    swap_rep_id = test_7_project_swap_generation(friend_doc_id or template_doc_id)
    test_8_persistence_and_recovery(internship_rep_id)
    test_9_internship_6_weeks()
    test_10_upload_source_material()

    print("\n" + "=" * 65)
    print("🏆 ALL 10 FULL-PIPELINE TEST PHASES PASSED WITH 100% SUCCESS!")
    print("=" * 65 + "\n")
