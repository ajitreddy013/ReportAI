"""Deterministic second-year PBL DOCX renderer.

Completed student reports are references, not safe document templates: their
cover pages often live in drawing text boxes that python-docx cannot edit.  This
module renders a clean report from verified structured facts while retaining the
college identity and chapter sequence discovered from the uploaded reference.
"""

import os
import re
import uuid
import zipfile
import tempfile
from typing import Any, Dict, List

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION
from docx.shared import Inches, Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from core.report_rules import pbl_section_list

OUTPUTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")


def _set_font(run, size=12, bold=False):
    run.font.name = "Times New Roman"
    run._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
    run._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
    run.font.size = Pt(size)
    run.bold = bold


def _paragraph(doc, text="", size=12, bold=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY, before=0, after=6):
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.line_spacing = 1.5 if size <= 12 else 1.0
    r = p.add_run(text)
    _set_font(r, size, bold)
    return p


def _set_section_page_numbering(section, fmt="upperRoman", start=1):
    sectPr = section._sectPr
    for el in list(sectPr.findall(qn("w:pgNumType"))):
        sectPr.remove(el)
    pgNumType = OxmlElement("w:pgNumType")
    pgNumType.set(qn("w:fmt"), fmt)
    if start is not None:
        pgNumType.set(qn("w:start"), str(start))
    sectPr.append(pgNumType)


def _page_number(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run("Page ")
    _set_font(run, 9)
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    paragraph._p.append(fld)


def _setup_section(section, topic, group, college, department, year, fmt="upperRoman", start=1, diff_first_page=True):
    section.top_margin = Inches(0.75)
    section.bottom_margin = Inches(0.75)
    section.left_margin = Inches(1.0)
    section.right_margin = Inches(1.0)
    section.different_first_page_header_footer = diff_first_page
    _set_section_page_numbering(section, fmt=fmt, start=start)
    header = section.header.paragraphs[0]
    header.text = ""
    header.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = header.add_run(f"{topic}    |    {group}")
    _set_font(r, 9)
    footer = section.footer.paragraphs[0]
    footer.text = ""
    r = footer.add_run(f"{college} — {department} — {year}     ")
    _set_font(r, 9)
    _page_number(footer)


def _page_break(doc):
    doc.add_page_break()


def _clear_table_borders(table):
    tbl_pr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = OxmlElement(f"w:{edge}")
        tag.set(qn("w:val"), "nil")
        borders.append(tag)
    tbl_pr.append(borders)


def _reference_logo(reference_docx_path):
    """Return a temporary copy of the known college logo, if present."""
    if not reference_docx_path or not os.path.exists(reference_docx_path):
        return None
    try:
        with zipfile.ZipFile(reference_docx_path) as archive:
            data = archive.read("word/media/image1.jpg")
        fd, target = tempfile.mkstemp(prefix="reportai-logo-", suffix=".jpg")
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        return target
    except Exception:
        return None


def _cover(doc, info, logo_path=None):
    college = info["college_name"].upper()
    department = info["department_name"].upper()
    if logo_path and os.path.exists(logo_path):
        logo = doc.add_paragraph()
        logo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        logo.add_run().add_picture(logo_path, width=Inches(2.15))
    _paragraph(doc, "A PBL REPORT", 17, True, WD_ALIGN_PARAGRAPH.CENTER, before=10, after=16)
    _paragraph(doc, "ON", 13, True, WD_ALIGN_PARAGRAPH.CENTER, after=14)
    _paragraph(doc, info["topic"].upper(), 18, True, WD_ALIGN_PARAGRAPH.CENTER, after=22)
    _paragraph(doc, "SUBMITTED TO", 11, True, WD_ALIGN_PARAGRAPH.CENTER, after=2)
    _paragraph(doc, info["university_name"].upper(), 13, True, WD_ALIGN_PARAGRAPH.CENTER, after=12)
    _paragraph(doc, "IN PARTIAL FULFILMENT OF THE REQUIREMENTS FOR THE AWARD OF THE DEGREE OF", 10, False, WD_ALIGN_PARAGRAPH.CENTER, after=2)
    _paragraph(doc, "BACHELOR OF ENGINEERING", 13, True, WD_ALIGN_PARAGRAPH.CENTER, after=20)
    _paragraph(doc, "SUBMITTED BY", 11, True, WD_ALIGN_PARAGRAPH.CENTER, after=8)
    table = doc.add_table(rows=0, cols=2)
    _clear_table_borders(table)
    for student in info["students"]:
        cells = table.add_row().cells
        cells[0].text = student["name"].upper()
        cells[1].text = f"Exam Seat No: {student['seat']}"
        for cell in cells:
            for p in cell.paragraphs:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for r in p.runs: _set_font(r, 10)
    _paragraph(doc, "", after=6)
    _paragraph(doc, "UNDER THE GUIDANCE OF", 10, True, WD_ALIGN_PARAGRAPH.CENTER, after=4)
    _paragraph(doc, info["guide_name"], 12, True, WD_ALIGN_PARAGRAPH.CENTER, after=20)
    _paragraph(doc, department, 13, True, WD_ALIGN_PARAGRAPH.CENTER, after=3)
    _paragraph(doc, college, 13, True, WD_ALIGN_PARAGRAPH.CENTER, after=3)
    _paragraph(doc, f"ACADEMIC YEAR {info['academic_year']}", 11, True, WD_ALIGN_PARAGRAPH.CENTER)


def _certificate(doc, info):
    _page_break(doc)
    _paragraph(doc, "CERTIFICATE", 16, True, WD_ALIGN_PARAGRAPH.CENTER, before=20, after=20)
    names = ", ".join(f"{s['name']} ({s['seat']})" for s in info["students"])
    text = (f"This is to certify that the PBL report entitled “{info['topic']}” submitted by {names} "
            f"is a bonafide work carried out under the guidance of {info['guide_name']}. "
            f"It is submitted to {info['university_name']} in partial fulfilment of the requirements "
            f"for the award of the degree of Bachelor of Engineering in {info['department_name']} "
            f"during the academic year {info['academic_year']}.")
    _paragraph(doc, text, after=56)
    table = doc.add_table(rows=2, cols=2)
    table.autofit = True
    left, right = table.rows[0].cells
    left.text = f"{info['guide_name']}\nGuide"
    right.text = f"{info['hod_name']}\nHead of Department"
    table.rows[1].cells[0].text = ""
    table.rows[1].cells[1].text = f"{info['principal_name']}\nPrincipal"
    for row in table.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for r in p.runs: _set_font(r, 11)


def _acknowledgement(doc, info):
    _page_break(doc)
    _paragraph(doc, "ACKNOWLEDGEMENT", 16, True, WD_ALIGN_PARAGRAPH.CENTER, before=20, after=20)
    text = (f"We express our sincere gratitude to our project guide, {info['guide_name']}, for guidance and support throughout this PBL work. "
            f"We thank {info['hod_name']}, Head of the Department of {info['department_name']}, and "
            f"{info['principal_name']}, Principal, for providing the facilities and encouragement required for this project. "
            f"We also thank our college, friends, and family for their support.")
    _paragraph(doc, text, after=28)
    for student in info["students"]:
        _paragraph(doc, student["name"], 11, False, WD_ALIGN_PARAGRAPH.RIGHT, after=2)


def _front_matter(doc, info, ai_sections, headings, images):
    _page_break(doc)
    _paragraph(doc, "ABSTRACT", 16, True, WD_ALIGN_PARAGRAPH.CENTER, before=20, after=16)
    _paragraph(doc, ai_sections.get("ABSTRACT") or ai_sections.get("Abstract") or "", after=8)
    _page_break(doc)
    _paragraph(doc, "LIST OF FIGURES", 16, True, WD_ALIGN_PARAGRAPH.CENTER, before=20, after=16)
    if images:
        for index, image in enumerate(images, 1):
            _paragraph(doc, f"Figure {index}: {image.get('caption') or 'Project figure'}", 11, align=WD_ALIGN_PARAGRAPH.LEFT, after=3)
    else:
        _paragraph(doc, "No project figures were submitted at the time of generation.", 11, align=WD_ALIGN_PARAGRAPH.LEFT)
    _page_break(doc)
    _paragraph(doc, "TABLE OF CONTENTS", 16, True, WD_ALIGN_PARAGRAPH.CENTER, before=20, after=16)
    
    table = doc.add_table(rows=0, cols=3)
    table.autofit = True
    _clear_table_borders(table)
    
    front_items = [
        ("Title Page", "I"),
        ("Certificate", "II"),
        ("Acknowledgement", "III"),
        ("Abstract", "IV"),
        ("List of Figures", "V"),
        ("Table of Contents", "VI"),
    ]
    for title, pg in front_items:
        row = table.add_row()
        row.cells[0].text = ""
        row.cells[1].text = title
        row.cells[2].text = pg
        for p in row.cells[1].paragraphs:
            for r in p.runs: _set_font(r, 11)
        for p in row.cells[2].paragraphs:
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            for r in p.runs: _set_font(r, 11)

    for heading in headings:
        if heading.upper() not in {"ABSTRACT", "REFERENCES"}:
            row = table.add_row()
            row.cells[0].text = ""
            row.cells[1].text = heading
            row.cells[2].text = ""
            for p in row.cells[1].paragraphs:
                for r in p.runs: _set_font(r, 11)

    row = table.add_row()
    row.cells[0].text = ""
    row.cells[1].text = "REFERENCES"
    row.cells[2].text = ""
    for p in row.cells[1].paragraphs:
        for r in p.runs: _set_font(r, 11)


def _chapter_number(heading):
    match = re.match(r"^(\d+)", heading)
    return match.group(1) if match else None


def _body(doc, headings, ai_sections, images):
    active_chapter = None
    figure_index = 0
    for heading in headings:
        if heading.upper() == "ABSTRACT":
            continue
        chapter = _chapter_number(heading)
        if chapter and chapter != active_chapter:
            if active_chapter is not None:
                _page_break(doc)
            active_chapter = chapter
            _paragraph(doc, f"CHAPTER {chapter}", 15, True, WD_ALIGN_PARAGRAPH.CENTER, before=16, after=14)
        if heading.upper() == "REFERENCES":
            _page_break(doc)
        _paragraph(doc, heading.upper(), 12, True, WD_ALIGN_PARAGRAPH.LEFT, before=10, after=7)
        content = ai_sections.get(heading, "")
        for block in [item.strip() for item in content.split("\n\n") if item.strip()]:
            _paragraph(doc, block, after=7)
        target = heading.lower()
        for image in images:
            if image.get("target_section", "").lower() in target and os.path.exists(image.get("path", "")):
                p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.add_run().add_picture(image["path"], width=Inches(5.5))
                figure_index += 1
                _paragraph(doc, f"Figure {figure_index}: {image.get('caption', 'Project figure')}", 10, False, WD_ALIGN_PARAGRAPH.CENTER)


def render_pbl_report(student_info: Dict[str, Any], doc_map: Dict[str, Any], ai_sections: Dict[str, str], images: List[Dict[str, Any]], output_filename=None) -> str:
    detected = doc_map.get("detected_values", {})
    def value(key, fallback):
        if student_info.get(key):
            return str(student_info[key]).strip()
        candidates = [str(item).strip() for item in detected.get(key, []) if str(item).strip()]
        # A graphical cover may expose both a long concatenated text-box value
        # and the clean label. Prefer the most specific short candidate.
        return (min(candidates, key=len) if candidates else fallback).strip()
    students = []
    for i in range(1, 21):
        name = str(student_info.get(f"student_name_{i}") or "").strip()
        if name:
            students.append({"name": name, "seat": str(student_info.get(f"roll_no_{i}") or "xxxx").strip()})
    if not students:
        raise ValueError("At least one student is required for a PBL report.")
    info = {
        "topic": value("topic", "PBL Report"), "students": students,
        "guide_name": value("guide_name", "Project Guide"), "hod_name": value("hod_name", "Head of Department"),
        "principal_name": value("principal_name", "Principal"), "academic_year": value("academic_year", ""),
        "college_name": value("college_name", "College Name"), "department_name": value("department_name", "Department"),
        "university_name": value("university_name", "University Name"), "group_no": value("group_no", ""),
    }
    # Body structure comes from the clean, topic-agnostic PBL outline so the
    # report follows the college format without inheriting the reference's
    # topic-specific section titles. The reference still supplies college
    # identity, cover, logo and fonts (see _cover / _reference_logo above).
    headings = pbl_section_list()
    reference_docx_path = student_info.get("_reference_docx_path")
    logo_path = _reference_logo(reference_docx_path)
    doc = Document()
    
    # Section 1: Front Matter with Roman numerals (I, II, III, ...)
    _setup_section(
        doc.sections[0],
        info["topic"],
        info["group_no"],
        info["college_name"],
        info["department_name"],
        info["academic_year"],
        fmt="upperRoman",
        start=1,
        diff_first_page=True,
    )
    _cover(doc, info, logo_path)
    _certificate(doc, info)
    _acknowledgement(doc, info)
    _front_matter(doc, info, ai_sections, headings, images)
    
    # Section 2: Core Chapters (Separated by Section Break, starts at Page 1 in decimal)
    body_section = doc.add_section(WD_SECTION.NEW_PAGE)
    _setup_section(
        body_section,
        info["topic"],
        info["group_no"],
        info["college_name"],
        info["department_name"],
        info["academic_year"],
        fmt="decimal",
        start=1,
        diff_first_page=False,
    )
    
    _body(doc, headings, ai_sections, images)
    if not output_filename:
        safe = "".join(char for char in info["topic"] if char.isalnum() or char in " _-")[:36]
        output_filename = f"PBL_Report_{safe.replace(' ', '_')}_{uuid.uuid4().hex[:6]}.docx"
    output = os.path.join(OUTPUTS_DIR, output_filename)
    doc.save(output)
    if logo_path and os.path.exists(logo_path):
        os.remove(logo_path)
    return output
