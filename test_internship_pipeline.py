"""
test_internship_pipeline.py
Unit and integration test for both Project Report and Internship Report pipelines.
"""

import os
import sys

# Ensure fast unit test execution without network timeout
os.environ["GEMINI_API_KEY"] = ""

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))


from core.report_rules import (
    STANDARD_INTERNSHIP_CHAPTERS,
    STANDARD_PROJECT_CHAPTERS,
    generate_weekly_attendance_diary,
    DEFAULT_INTERNSHIP_FACULTY,
    DEFAULT_FACULTY,
)
from core.gemini_engine import generate_content, _synthesize_distinct_section
from core.docx_writer import generate_internship_docx, fill_template
from core.preview_renderer import render_report_html
from core.docx_reader import analyze_docx


def test_weekly_attendance_generator():
    diary = generate_weekly_attendance_diary(
        topic="Full-Stack Web Engineering",
        company="NeuAI Labs LLP",
        start_date_str="2025-01-01",
        weeks_count=4
    )
    assert len(diary) == 4, f"Expected 4 weeks, got {len(diary)}"
    total_entries = sum(len(w["entries"]) for w in diary)
    assert total_entries == 20, f"Expected 20 entries (4 weeks x 5 days), got {total_entries}"
    for w in diary:
        for entry in w["entries"]:
            assert entry["day"] in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
            assert entry["status"] == "Completed"
    print(f"✓ Weekly Attendance Log: {len(diary)} weeks, {total_entries} Mon-Fri daily entries verified.")



def test_internship_content_synthesis():
    topic = "Cloud-Native Web Services & Modern Frontend Architecture"
    sections = [s for chap in STANDARD_INTERNSHIP_CHAPTERS for s in chap["subsections"]]
    student_info = {
        "report_type": "internship",
        "student_name": "Ajit Satish Kolpuke",
        "roll_no": "T190058501",
        "prn_no": "72283921B",
        "company_name": "NeuAI Labs LLP",
        "company_mentor_name": "Mr. Subham Asbe",
        "company_mentor_designation": "Technical Lead",
        "guide_name": "Prof. N. G. Bhojne",
        "hod_name": "Dr. M. P. Wankhade",
        "principal_name": "Dr. S. D. Lokhande",
        "academic_year": "2024-25",
        "internship_start_date": "2025-01-01",
        "internship_duration_weeks": 4,
    }

    content = generate_content(
        topic=topic,
        sections=sections,
        student_info=student_info,
        reference_notes="React 18, Node.js, PostgreSQL",
    )

    assert len(content) == len(sections)
    for s in sections:
        assert len(content[s].strip()) > 30, f"Section {s} has empty content"
    print(f"✓ Internship Content Synthesis: {len(content)} distinct sections generated.")

    # Test DOCX generation
    docx_path = generate_internship_docx(
        student_info=student_info,
        ai_sections=content,
        images=[],
        output_filename="Test_Internship_Report.docx"
    )
    assert os.path.exists(docx_path)
    file_size = os.path.getsize(docx_path)
    assert file_size > 15000, f"DOCX too small: {file_size} bytes"
    print(f"✓ Internship DOCX generated successfully: {docx_path} ({file_size} bytes).")

    # Test HTML preview rendering
    report_data = {
        "student_info": student_info,
        "ai_content": content,
        "sections": sections,
        "topic": topic,
        "report_type": "internship",
    }
    html_out = render_report_html(docx_path, report_data)
    assert "A REPORT OF INTERNSHIP" in html_out or "INTERNSHIP" in html_out
    assert "NeuAI Labs LLP" in html_out
    assert "Mr. Subham Asbe" in html_out
    assert "Prof. N. G. Bhojne" in html_out
    assert "Weekly Activity & Attendance Log" in html_out or "attendance-container" in html_out
    assert "Annexure 1: Company Offer Letter" in html_out
    print(f"✓ Internship HTML Preview verified ({len(html_out)} characters, all A4 pages rendered).")





def test_project_report_pipeline():
    template_path = os.path.join(os.path.dirname(__file__), "test_assets", "Report_format.docx")
    doc_map = analyze_docx(template_path)
    assert doc_map["is_template"] is True

    topic = "TalkAR – AI-Powered Lip-Sync AR Application"
    student_info = {
        "report_type": "project",
        "topic": topic,
        "group_no": "Group No. 50",
        "guide_name": "Prof. P. M. Kamde",
        "hod_name": "Dr. R. H. Borhade",
        "principal_name": "Dr. S. D. Lokhande",
        "academic_year": "2025-26",
        "student_name_1": "Ajit Kolpuke",
        "roll_no_1": "72283921B",
        "student_name_2": "Rameshwar Ghadge",
        "roll_no_2": "72283922C",
    }

    sections = doc_map.get("headings", [])
    content = generate_content(
        topic=topic,
        sections=sections,
        student_info=student_info,
        reference_notes="Incremental Model, Android ARCore, Node.js",
    )

    docx_path = fill_template(
        source_docx_path=template_path,
        doc_map=doc_map,
        student_info=student_info,
        ai_sections=content,
        images=[],
        output_filename="Test_Project_Report.docx"
    )
    assert os.path.exists(docx_path)
    file_size = os.path.getsize(docx_path)
    assert file_size > 15000
    print(f"✓ Project Report DOCX generated successfully: {docx_path} ({file_size} bytes).")

    report_data = {
        "student_info": student_info,
        "ai_content": content,
        "sections": sections,
        "topic": topic,
        "report_type": "project",
    }
    html_out = render_report_html(docx_path, report_data)
    assert "TalkAR" in html_out
    assert "Prof. P. M. Kamde" in html_out
    assert "Dr. R. H. Borhade" in html_out
    print(f"✓ Project Report HTML Preview verified ({len(html_out)} characters).")


if __name__ == "__main__":
    test_weekly_attendance_generator()
    test_internship_content_synthesis()
    test_project_report_pipeline()
    print("\n==========================================")
    print("ALL TESTS PASSED WITH 100% SUCCESS!")
    print("==========================================")

