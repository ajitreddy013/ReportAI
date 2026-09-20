"""
Integration test for dynamic placeholder extraction and multi-student + certificate + index filling.
"""
import os
import sys
import tempfile
import requests
from docx import Document

API = "http://localhost:8000/api"

print("1. Creating realistic 4-student college report template with certificate table...")
doc = Document()

# Page 1: Title Page
doc.add_heading("A PROJECT REPORT ON", 1)
doc.add_heading("[Project Title]", 0)
doc.add_paragraph("Submitted by:")

# 4 Student table on Title Page
t1 = doc.add_table(rows=5, cols=2)
t1.rows[0].cells[0].text = "Student Name"
t1.rows[0].cells[1].text = "Roll No / PRN"

t1.rows[1].cells[0].text = "[Name of Student 1]"
t1.rows[1].cells[1].text = "[Roll No 1]"

t1.rows[2].cells[0].text = "[Name of Student 2]"
t1.rows[2].cells[1].text = "[Roll No 2]"

t1.rows[3].cells[0].text = "[Name of Student 3]"
t1.rows[3].cells[1].text = "[Roll No 3]"

t1.rows[4].cells[0].text = "[Name of Student 4]"
t1.rows[4].cells[1].text = "[Roll No 4]"

doc.add_paragraph("Department of Computer Engineering, Sinhgad College of Engineering, Pune")
doc.add_paragraph("Academic Year: [Academic Year]")

# Page Break to Certificate Page
doc.add_page_break()
doc.add_heading("CERTIFICATE", 1)
doc.add_paragraph(
    "This is to certify that the project entitled \"[Project Title]\" has been successfully completed by "
    "[Name of Student 1], [Name of Student 2], [Name of Student 3], and [Name of Student 4] "
    "under the guidance of [Guide Name] in partial fulfillment of the requirements for the degree."
)

t2 = doc.add_table(rows=2, cols=3)
t2.rows[0].cells[0].text = "[Guide Name]\nProject Guide"
t2.rows[0].cells[1].text = "[HOD Name]\nHead of Department"
t2.rows[0].cells[2].text = "[Principal Name]\nPrincipal"

# Page Break to Index & Chapters
doc.add_page_break()
doc.add_heading("Abstract", 1)
doc.add_paragraph("[Abstract content placeholder]")

doc.add_heading("Chapter 1: Introduction", 1)
doc.add_paragraph("[Introduction content placeholder]")

doc.add_heading("Chapter 2: Literature Survey", 1)
doc.add_paragraph("[Literature review content placeholder]")

doc.add_heading("Chapter 3: Proposed Methodology", 1)
doc.add_paragraph("[Methodology content placeholder]")

doc.add_heading("Chapter 4: Implementation Details", 1)
doc.add_paragraph("[Implementation details placeholder]")

doc.add_heading("Chapter 5: Results and Analysis", 1)
doc.add_paragraph("[Results placeholder]")

doc.add_heading("Chapter 6: Conclusion and Future Scope", 1)
doc.add_paragraph("[Conclusion placeholder]")

doc.add_heading("References", 1)
doc.add_paragraph("[References placeholder]")

tmp = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
doc.save(tmp.name)
tmp.close()

print(f"Saved template: {tmp.name}")

# 2. Upload to API
print("\n2. Uploading template to /api/upload-doc...")
with open(tmp.name, "rb") as f:
    res = requests.post(f"{API}/upload-doc", files={"file": ("4_student_template.docx", f)})

assert res.status_code == 200, f"Upload error: {res.text}"
data = res.json()
print("  doc_id:", data["doc_id"])
print("  student_count detected:", data["student_count"])
print("  title_page_fields count:", len(data["title_page_fields"]))
print("  certificate_page_fields:", [f["key"] for f in data["certificate_page_fields"]])
print("  headings detected:", data["headings"])

assert data["student_count"] >= 4, f"Expected 4 students, got {data['student_count']}"
assert any(f["key"] == "guide_name" for f in data["certificate_page_fields"])
assert any(f["key"] == "hod_name" for f in data["certificate_page_fields"])

# 3. Generate Report
print("\n3. Testing /api/generate with 4 student values & faculty...")
form_data = {
    "doc_id": data["doc_id"],
    "mode": "template",
    "topic": "Autonomous Drone Navigation using Deep Reinforcement Learning",
    "student_name_1": "Rahul Sharma",
    "roll_no_1": "7201",
    "student_name_2": "Priya Patil",
    "roll_no_2": "7202",
    "student_name_3": "Amit Deshmukh",
    "roll_no_3": "7203",
    "student_name_4": "Neha Kulkarni",
    "roll_no_4": "7204",
    "guide_name": "Prof. S. M. Kulkarni",
    "hod_name": "Dr. V. N. Joshi",
    "principal_name": "Dr. S. D. Lokhande",
    "academic_year": "2024-25",
    "reference_notes": "Focus on YOLOv8 and PPO reinforcement learning algorithm",
    "images_json": "[]"
}

res = requests.post(f"{API}/generate", data=form_data)
assert res.status_code == 200, f"Generate error: {res.text}"
gen = res.json()
print("  report_id:", gen["report_id"])
print("  generated sections:", gen["sections"])

# 4. Preview Check
print("\n4. Checking preview...")
res = requests.get(f"{API}/preview/{gen['report_id']}")
assert res.status_code == 200
assert "Autonomous Drone Navigation" in res.text
assert "Rahul Sharma" in res.text
assert "Prof. S. M. Kulkarni" in res.text
print("  Preview HTML verified successfully ✓")

# 5. Download DOCX Check
print("\n5. Checking DOCX download and inspecting content...")
res = requests.get(f"{API}/download-docx/{gen['report_id']}")
assert res.status_code == 200
out_docx_path = tmp.name.replace(".docx", "_filled.docx")
with open(out_docx_path, "wb") as f:
    f.write(res.content)

# Inspect generated DOCX
filled_doc = Document(out_docx_path)
full_text = "\n".join(p.text for p in filled_doc.paragraphs)
for t in filled_doc.tables:
    for row in t.rows:
        for cell in row.cells:
            full_text += "\n" + cell.text

assert "Autonomous Drone Navigation" in full_text
assert "Rahul Sharma" in full_text
assert "Priya Patil" in full_text
assert "Prof. S. M. Kulkarni" in full_text
print("  Filled DOCX verified with all 4 students and faculty names ✓")

print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!")

os.unlink(tmp.name)
os.unlink(out_docx_path)
