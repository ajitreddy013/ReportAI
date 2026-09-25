"""
docx_writer.py
Assembles publication-quality college engineering reports in DOCX,
incorporating all Header/Footer rules and 8-chapter structure from '1234567678.pdf'.

Header & Footer Implementation:
  - Header Top: [Topic Name] (Left) | [Group No. XX] (Right)
  - Header Bottom: SCOE, Dept. of Computer Engineering (Left) | Year 2025-26 (Right)
  - Front Matter Header: SCOE, Dept. of Computer Engineering | Year 2025-26
  - Typography: Times New Roman 12pt body, 1.5 line spacing, Justified alignment
"""

import copy
import io
import os
import re
import uuid
import zipfile
import tempfile
from typing import Any, Dict, List, Optional, Tuple

from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from lxml import etree

from core.report_rules import (
    clean_instruction_text,
    UML_DIAGRAM_SLOTS,
    DEFAULT_FACULTY,
    DEFAULT_INTERNSHIP_FACULTY,
    STANDARD_INTERNSHIP_CHAPTERS,
    generate_weekly_attendance_diary,
)

OUTPUTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")
os.makedirs(OUTPUTS_DIR, exist_ok=True)



def _copy_run_format(src_run, dst_run):
    try:
        if src_run.font.name:
            dst_run.font.name = src_run.font.name
        if src_run.font.size:
            dst_run.font.size = src_run.font.size
        if src_run.bold is not None:
            dst_run.bold = src_run.bold
        if src_run.italic is not None:
            dst_run.italic = src_run.italic
        if src_run.underline is not None:
            dst_run.underline = src_run.underline
    except Exception:
        pass


def _clear_paragraph_runs(para):
    for run in list(para.runs):
        p_elem = run._element.getparent()
        if p_elem is not None:
            p_elem.remove(run._element)


def _set_paragraph_text(para, text: str, reference_run=None):
    _clear_paragraph_runs(para)
    new_run = para.add_run(text)
    if reference_run:
        _copy_run_format(reference_run, new_run)
    else:
        new_run.font.name = "Times New Roman"
        new_run.font.size = Pt(12)


def _replace_in_paragraph(para, replacements: Dict[str, str]):
    full_text = para.text
    if not full_text:
        return

    for run in para.runs:
        for old_txt, new_txt in replacements.items():
            if old_txt and old_txt in run.text:
                run.text = run.text.replace(old_txt, new_txt)

    for old_txt, new_txt in replacements.items():
        if old_txt and old_txt in para.text:
            first_run = para.runs[0] if para.runs else None
            new_para_text = para.text.replace(old_txt, new_txt)
            _set_paragraph_text(para, new_para_text, first_run)


def _replace_in_tables(doc: Document, replacements: Dict[str, str]):
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    _replace_in_paragraph(para, replacements)


def _iter_document_paragraphs(doc: Document):
    """Yield paragraphs everywhere a user can put personal data."""
    for para in doc.paragraphs:
        yield para
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                yield from cell.paragraphs
    for section in doc.sections:
        for container in (section.header, section.footer, section.first_page_header,
                          section.first_page_footer, section.even_page_header,
                          section.even_page_footer):
            # Skip linked containers: reading their paragraphs would lazily create
            # a new header/footer part (and sectPr reference) that the source
            # document never had, breaking format identity.
            if container.is_linked_to_previous:
                continue
            for para in container.paragraphs:
                yield para
            for table in container.tables:
                for row in table.rows:
                    for cell in row.cells:
                        yield from cell.paragraphs


def _value_from_inputs(key: str, student_info: Dict[str, Any]) -> str:
    if key == "student_name":
        return str(student_info.get("student_name_1") or student_info.get("student_name") or "").strip()
    if key == "roll_no":
        return str(student_info.get("roll_no_1") or student_info.get("roll_no") or "").strip()
    return str(student_info.get(key, "")).strip()


def _build_replacements(doc_map: Dict[str, Any], student_info: Dict[str, Any]) -> Dict[str, str]:
    replacements: Dict[str, str] = {}
    
    # Only replace explicit placeholder syntax: {{TOKEN}}, [Token], <Token>, <<Token>>
    aliases = {
        "PROJECT_TITLE": "topic", "TOPIC": "topic", "STUDENT_NAME": "student_name",
        "ROLL_NO": "roll_no", "PRN": "roll_no", "EXAM_SEAT_NO": "exam_seat_no",
        "GUIDE_NAME": "guide_name", "HOD_NAME": "hod_name", "PRINCIPAL_NAME": "principal_name",
        "COLLEGE_NAME": "college_name", "DEPARTMENT": "department_name",
        "ACADEMIC_YEAR": "academic_year", "GROUP_NO": "group_no", "COMPANY_NAME": "company_name",
        "INTERNSHIP_MENTOR": "internship_mentor_name",
    }
    for token, key in aliases.items():
        value = _value_from_inputs(key, student_info)
        if value:
            replacements[f"{{{{{token}}}}}"] = value
            replacements[f"[{token}]"] = value
            replacements[f"<{token}>"] = value
            replacements[f"<<{token}>>"] = value
            replacements[f"[{token.replace('_', ' ').title()}]"] = value
            replacements[f"<{token.replace('_', ' ').title()}>"] = value
            replacements[f"<<{token.replace('_', ' ').title()}>>"] = value

    for ph in doc_map.get("all_placeholders", []):
        raw_ph = ph.get("raw", "")
        ph_type = ph.get("type", "")
        if ph_type in aliases:
            val = _value_from_inputs(aliases[ph_type], student_info)
            if val and raw_ph:
                replacements[raw_ph] = val

    return replacements


def _sync_title_page(doc: Document, students: List[Dict], topic: str, guide: str, year: str):
    guide_title = _normalize_guide_name(guide)
    acad_year_idx = None

    for i, p in enumerate(doc.paragraphs[:38]):
        txt = p.text.strip()
        if not txt:
            continue
        if "CERTIFICATE" in txt.upper() or "Date:" in txt:
            break
        if "A PRELIMINARY PROJECT REPORT ON" in txt or "A REPORT ON" in txt or "A PROJECT REPORT ON" in txt:
            pass
        elif ("TALKAR" in txt.upper() or "[PROJECT TITLE]" in txt.upper() or "[TOPIC]" in txt.upper()
              or ("AUTOMATIC ROOFTOP CURTAINS" in txt.upper() and i < 45)):
            p.text = topic.upper()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif "NAME OF THE CANDIDATE_4" in txt:
            p.text = f"{students[3]['name'].upper():<35} Exam Seat No: {students[3]['seat']}" if len(students) > 3 else ""
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif "NAME OF THE CANDIDATE_3" in txt:
            p.text = f"{students[2]['name'].upper():<35} Exam Seat No: {students[2]['seat']}" if len(students) > 2 else ""
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif "NAME OF THE CANDIDATE_2" in txt:
            p.text = f"{students[1]['name'].upper():<35} Exam Seat No: {students[1]['seat']}" if len(students) > 1 else ""
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif "AJIT SATISH KOLPUKE" in txt or "NAME OF THE CANDIDATE" in txt or "NAME OF THE CANDIDATE_1" in txt:
            p.text = f"{students[0]['name'].upper():<35} Exam Seat No: {students[0]['seat']}"
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif "Under the guidance of" in txt:
            pass
        elif "Prof. S. V. PATIL" in txt or "NAME OF THE GUIDE" in txt:
            p.text = guide_title.upper()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif "[Project Title]" in txt or "[Topic]" in txt:
            p.text = p.text.replace("[Project Title]", topic).replace("[Topic]", topic)
        elif "2024-25" in txt or "2025-26" in txt or re.match(r"^20\d\d-\d\d$", txt):
            p.text = year
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            acad_year_idx = i

    # Clean up excess blank lines before Certificate
    if acad_year_idx is not None:
        for i in range(acad_year_idx + 1, min(len(doc.paragraphs), acad_year_idx + 10)):
            if "CERTIFICATE" in doc.paragraphs[i].text.upper() or "Date:" in doc.paragraphs[i].text:
                break
            doc.paragraphs[i].text = ""

    # Also sync candidate table on title page (common in completed student reports)
    for table in doc.tables[:2]:
        is_candidate_table = False
        for row in table.rows:
            row_text = " ".join(c.text for c in row.cells).upper()
            if any(kw in row_text for kw in ["PRN", "SEAT", "KOLPUKE", "CANDIDATE", "MOHITE", "KALBHOR", "GAIKWAD"]):
                is_candidate_table = True
                break
        if is_candidate_table:
            for s_idx, student in enumerate(students):
                if s_idx < len(table.rows):
                    row = table.rows[s_idx]
                    if len(row.cells) >= 2:
                        row.cells[0].text = student['name'].upper()
                        seat_val = student['seat']
                        if seat_val and seat_val != "xxxx":
                            row.cells[1].text = f"PRN: {seat_val}" if not seat_val.upper().startswith("PRN") else seat_val
                        else:
                            row.cells[1].text = "PRN: xxxx"
                    elif len(row.cells) == 1:
                        row.cells[0].text = f"{student['name'].upper():<35} PRN: {student['seat']}"
            for s_idx in range(len(students), len(table.rows)):
                for cell in table.rows[s_idx].cells:
                    cell.text = ""


def _sync_student_identity_rows(doc: Document, students: List[Dict], slots_per_page: int = 0):
    """Replace completed-report candidate rows across cover and certificate pages.

    These reports frequently use ordinary paragraphs rather than placeholders,
    and may repeat the candidate list on a duplicate cover page and certificate.
    When the team has fewer members than the reference's candidate slots, the
    spare slots are blanked rather than filled with a repeat of the first member
    (which previously printed one name across every cover line).
    """
    if not students:
        return
    rows = [p for p in doc.paragraphs if re.search(r"(?:exam\s*seat\s*no|\bprn\s*:)", p.text or "", re.I)]
    span = slots_per_page if slots_per_page and slots_per_page >= len(students) else len(students)
    for index, paragraph in enumerate(rows):
        slot = index % span
        if slot >= len(students):
            _set_paragraph_text(paragraph, "")
            continue
        student = students[slot]
        label = "Exam Seat No" if re.search(r"exam\s*seat", paragraph.text, re.I) else "PRN"
        _set_paragraph_text(paragraph, f"{student['name'].upper():<35} {label}: {student['seat']}")


def _source_candidate_names(path: str) -> List[str]:
    """Read candidate names from a reference's drawing text boxes."""
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with zipfile.ZipFile(path, "r") as source:
        root = etree.fromstring(source.read("word/document.xml"))
    names = []
    for para in root.xpath(".//w:p", namespaces=namespace):
        text = "".join(node.text or "" for node in para.xpath(".//w:t", namespaces=namespace))
        match = re.search(r"^\s*(.*?)\s+Exam\s*Seat\s*No", text, re.I)
        if match:
            name = match.group(1).strip()
            # A drawing text box can contain an entire cover page. Only keep a
            # short, name-like candidate prefix—not the preceding cover text.
            if name and len(name) <= 80 and 1 <= len(name.split()) <= 5 and name not in names:
                names.append(name)
    return names


_TITLE_BOX_MARKERS = ("AUTOMATIC ROOFTOP CURTAINS USING TEMPERATURE SENSOR",)
_FACULTY_KEYWORDS = ("prof", "dr", "guide", "head", "principal", "department", "hod", "ekature", "ekkatpure")


def _is_signature_line(visible: str) -> bool:
    """True if a text-box paragraph looks like a bare student signature name.

    Signature boxes list group members as short, alphabetic, 2-4 word lines with
    no seat numbers or faculty titles.  This avoids relying on the reference's
    candidate names (which may not cover every signature, e.g. extra members).
    """
    text = visible.strip()
    if not text or len(text) > 40 or any(ch.isdigit() for ch in text):
        return False
    tokens = [t for t in re.split(r"[\s.]+", text) if t]
    if not (2 <= len(tokens) <= 4):
        return False
    if not all(re.fullmatch(r"[A-Za-z]+", t) for t in tokens):
        return False
    lowered = text.lower()
    return not any(kw in lowered for kw in _FACULTY_KEYWORDS)


def _sync_textboxes_in_saved_docx(path: str, topic: str, students: List[Dict], old_names: List[str]):
    """Update cover-page text boxes, which python-docx deliberately omits.

    College reports often place their title, candidate list and signatures in Word
    drawing text boxes.  Word stores each drawing twice (an mc:Choice and an
    mc:Fallback copy), so counters are tracked *per text-box block* rather than
    globally; a global counter would drift across the duplicated blocks and leave
    the friend's topic/names visible or blank the wrong lines.
    """
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with zipfile.ZipFile(path, "r") as source:
        files = {name: source.read(name) for name in source.namelist()}
    xml_name = "word/document.xml"
    root = etree.fromstring(files[xml_name])

    def _set_single(text_nodes, value):
        text_nodes[0].text = value
        text_nodes[0].set(qn("xml:space"), "preserve")
        for node in text_nodes[1:]:
            node.text = ""

    def _blank(text_nodes):
        for node in text_nodes:
            node.text = ""

    for box in root.xpath(".//w:txbxContent", namespaces=namespace):
        candidate_index = 0
        signature_index = 0
        for para in box.xpath(".//w:p", namespaces=namespace):
            text_nodes = para.xpath(".//w:t", namespaces=namespace)
            if not text_nodes:
                continue
            visible = "".join(node.text or "" for node in text_nodes)
            upper = visible.upper()

            if any(marker in upper for marker in _TITLE_BOX_MARKERS):
                _set_single(text_nodes, topic.upper())
                continue

            if students and re.search(r"exam\s*seat\s*no", visible, re.I):
                if candidate_index < len(students):
                    s = students[candidate_index]
                    _set_single(text_nodes, f"{s['name'].upper():<48}Exam Seat No:{s['seat']}")
                else:
                    _blank(text_nodes)
                candidate_index += 1
                continue

            if students and _is_signature_line(visible):
                if signature_index < len(students):
                    name = students[signature_index]["name"].strip()
                    _set_single(text_nodes, name.title() if name.isupper() else name)
                else:
                    _blank(text_nodes)
                signature_index += 1
                continue

    files[xml_name] = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    fd, temp_path = tempfile.mkstemp(suffix=".docx", dir=os.path.dirname(path))
    os.close(fd)
    try:
        with zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as target:
            for name, data in files.items():
                target.writestr(name, data)
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def _remove_body_between(start_para, end_para=None):
    """Remove all old body blocks (paragraphs, tables and images) in a section."""
    node = start_para._element.getnext()
    stop = end_para._element if end_para is not None else None
    while node is not None and node is not stop:
        if node.tag.endswith("}sectPr"):
            break
        next_node = node.getnext()
        parent = node.getparent()
        if parent is not None:
            parent.remove(node)
        node = next_node


def _add_content_after(doc: Document, anchor_para, content: str, reference_para=None):
    anchor = anchor_para
    chunks = [chunk.strip() for chunk in re.split(r"\n\s*\n", content or "") if chunk.strip()]
    if not chunks:
        chunks = ["[AI content to be generated for this section]"]
    for chunk in chunks:
        new_para = doc.add_paragraph()
        if reference_para is not None:
            new_para.style = reference_para.style
            new_para.paragraph_format.alignment = reference_para.paragraph_format.alignment
            new_para.paragraph_format.line_spacing = reference_para.paragraph_format.line_spacing
            new_para.paragraph_format.space_after = reference_para.paragraph_format.space_after
        else:
            new_para.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            new_para.paragraph_format.line_spacing = 1.5
        run = new_para.add_run(chunk)
        if reference_para is not None and reference_para.runs:
            _copy_run_format(reference_para.runs[0], run)
        else:
            run.font.name = "Times New Roman"
            run.font.size = Pt(12)
        anchor._element.addnext(new_para._element)
        anchor = new_para


def _norm_heading_text(s: str) -> str:
    """Normalize a heading for tolerant matching.

    Uppercases, drops legacy Word form-field artifacts ("Bottom of Form"),
    collapses runs of whitespace (spaces/tabs) to one space, and strips trailing
    colons/periods, so headings that differ only by formatting still match.
    """
    s = (s or "").upper()
    s = re.sub(r"BOTTOM OF FORM|TOP OF FORM", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s.rstrip(":.").strip()


def _heading_number(title: str):
    m = re.match(r"^(\d+(?:\.\d+)*)", (title or "").strip())
    return m.group(1) if m else None


def _replace_report_sections(doc: Document, doc_map: Dict[str, Any], ai_sections: Dict[str, str]):
    """Keep the source headings/layout but replace every old editable body block.

    Headings are located by TEXT at edit time rather than by the paragraph indices
    captured during analysis.  Earlier sync steps (abstract, title page) insert and
    remove paragraphs, which shifts those indices and would otherwise cause the
    wrong regions to be replaced—leaving stale reference content in the body.
    """
    section_specs = doc_map.get("sections") or []
    if not section_specs:
        return
    paras = doc.paragraphs
    norm_paras = [_norm_heading_text(p.text) for p in paras]

    # Resolve every spec heading to a live paragraph index, searching forward so
    # repeated/short titles stay in document order.  Matching is normalized
    # (whitespace collapsed, trailing colons and legacy "Bottom of Form" form-field
    # artifacts removed) and falls back to the heading number, so headings that
    # differ only by a tab, a double space, a colon, or a split number/text pair
    # are still found instead of being silently deleted by a neighbouring section.
    resolved: List[Any] = []
    cursor = 0
    unresolved: List[str] = []
    for spec in section_specs:
        title = (spec.get("title") or "").strip()
        ntitle = _norm_heading_text(title)
        num = _heading_number(title)
        title_text = ntitle[len(num):].strip() if (num and ntitle.startswith(num)) else ntitle
        idx = None
        for i in range(cursor, len(paras)):
            if norm_paras[i] == ntitle:
                idx = i
                break
        if idx is None and num:
            for i in range(cursor, len(paras)):
                pt = norm_paras[i]
                if pt == num or pt.startswith(num + " "):
                    rest = pt[len(num):].strip(" .:")
                    # A form-field heading can split as "1.6 <artifact>" + "OBJECTIVES";
                    # anchor on the text paragraph so the heading is preserved.
                    if rest == "" and title_text and i + 1 < len(paras) and norm_paras[i + 1] == title_text:
                        idx = i + 1
                    else:
                        idx = i
                    break
        resolved.append((idx, title))
        if idx is None:
            unresolved.append(title)
        else:
            cursor = idx + 1
    if unresolved:
        print(f"[docx_writer] unresolved section headings (left as-is): {unresolved}")

    captured = []
    for k, (idx, title) in enumerate(resolved):
        if idx is None:
            continue
        tl = title.lower()
        if any(kw in tl for kw in ["title", "cover", "certificate", "acknowledgement", "table of contents", "list of figures"]):
            continue
        if title.upper() == "ABSTRACT":
            continue  # handled by _sync_abstract_page
        content = ai_sections.get(title)
        if content is None:
            continue
        heading = paras[idx]
        next_idx = None
        for j in range(k + 1, len(resolved)):
            if resolved[j][0] is not None:
                next_idx = resolved[j][0]
                break
        next_heading = paras[next_idx] if next_idx is not None else None
        reference = paras[idx + 1] if idx + 1 < len(paras) and (next_idx is None or idx + 1 < next_idx) else None
        captured.append((heading, next_heading, reference, content))

    # Work backwards so each saved XML boundary remains valid.
    for heading, next_heading, reference, content in reversed(captured):
        _remove_body_between(heading, next_heading)
        _add_content_after(doc, heading, content, reference)


def _normalize_guide_name(guide: str) -> str:
    cleaned = re.sub(r"^(Prof\.|Dr\.)\s*", "", guide.strip())
    if guide.strip().startswith("Dr."):
        return f"Dr. {cleaned}"
    return f"Prof. {cleaned}"


def _enforce_times_new_roman(doc: Document):
    """Enforces Times New Roman font universally across paragraphs, tables, headers and footers."""
    for style in doc.styles:
        if hasattr(style, "font") and style.font:
            style.font.name = "Times New Roman"

    for p in doc.paragraphs:
        for r in p.runs:
            r.font.name = "Times New Roman"
            try:
                r._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
                r._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
                r._element.rPr.rFonts.set(qn("w:cs"), "Times New Roman")
            except Exception:
                pass

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    for r in p.runs:
                        r.font.name = "Times New Roman"
                        try:
                            r._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
                            r._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
                            r._element.rPr.rFonts.set(qn("w:cs"), "Times New Roman")
                        except Exception:
                            pass

    for sec in doc.sections:
        # Only touch header/footer parts that already exist.  Accessing the
        # paragraphs of a *linked* header lazily creates a brand-new part (and a
        # matching sectPr reference), which would change the reference's page
        # setup—e.g. adding a default header the source document never had.
        for hf in [sec.header, sec.footer,
                   sec.first_page_header, sec.first_page_footer,
                   sec.even_page_header, sec.even_page_footer]:
            if hf.is_linked_to_previous:
                continue
            for p in hf.paragraphs:
                for r in p.runs:
                    r.font.name = "Times New Roman"


def _sync_certificate_page(doc: Document, students: List[Dict], topic: str, guide: str, hod: str, principal: str, year: str):
    guide_title = _normalize_guide_name(guide)
    cert_start = None
    cert_end = None
    for i, p in enumerate(doc.paragraphs):
        if "CERTIFICATE" in p.text.upper():
            cert_start = i
        if cert_start is not None and i > cert_start and "ACKNOWLEDGEMENT" in p.text.upper():
            cert_end = i
            break

    if cert_start is None:
        return

    if cert_end is None:
        cert_end = min(len(doc.paragraphs), cert_start + 35)

    cert_candidates = []
    for i in range(cert_start, cert_end):
        p = doc.paragraphs[i]
        txt = p.text.strip()
        if not txt:
            continue

        # Topic title in Certificate
        if i > cert_start and i <= cert_start + 5:
            if "entitled" in doc.paragraphs[i - 1].text.lower() or ("“" in txt or '"' in txt or "TALKAR" in txt.upper()):
                p.text = f'“{topic}”'
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                continue

        # Candidate names with PRN
        if "PRN:" in txt or "Exam Seat No" in txt:
            cert_candidates.append(p)
            continue

        # Bonafide work paragraph
        if "is a bonafide work" in txt.lower():
            pronoun = "them" if len(students) > 1 else "him/her"
            p.text = (
                f"is a bonafide work carried out by {pronoun} under the supervision of {guide_title} "
                f"and it is approved for the partial fulfillment of the requirements of Savitribai Phule Pune University, "
                f"Pune for the award of the degree of Bachelor of Engineering (Computer Engineering) during the year {year}."
            )
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            continue

        # Faculty signatures
        next_txt = doc.paragraphs[i + 1].text if i + 1 < len(doc.paragraphs) else ""
        if "Guide" in next_txt and "Head" in next_txt:
            p.text = f"\t{guide_title}\t\t\t\t\t\t{hod}"
            continue
        elif next_txt.strip() == "Principal":
            p.text = principal
            continue

    # Fill candidate names with PRN
    for idx, p in enumerate(cert_candidates):
        if idx < len(students):
            p.text = f"                                 {students[idx]['name']:<35}\t\t\tPRN: {students[idx]['seat']}"
        else:
            p.text = ""


def _sync_acknowledgement(doc: Document, students: List[Dict], guide: str, hod: str, principal: str):
    guide_title = _normalize_guide_name(guide)
    ack_start = None
    ack_end = None
    for i, p in enumerate(doc.paragraphs):
        if "acknowledgement" in p.text.lower():
            ack_start = i
        if ack_start is not None and i > ack_start and "ABSTRACT" in p.text.upper():
            ack_end = i
            break

    if ack_start is None:
        return

    if ack_end is None:
        ack_end = min(len(doc.paragraphs), ack_start + 30)

    for i in range(ack_start, ack_end):
        p = doc.paragraphs[i]
        txt = p.text
        if not txt.strip():
            continue
        if "project guide" in txt.lower() or "guide" in txt.lower():
            txt = re.sub(r"(project guide,\s*)(?:Prof\.|Dr\.)\s+[A-Z]\.\s*[A-Z]\.\s*[A-Za-z]+", rf"\g<1>{guide_title}", txt, flags=re.I)
            txt = re.sub(r"(guide\s+)(?:Prof\.|Dr\.)\s+[A-Z]\.\s*[A-Z]\.\s*[A-Za-z]+", rf"\g<1>{guide_title}", txt, flags=re.I)
            p.text = txt
        if "Head of Department" in txt or "HOD" in txt:
            if hod:
                txt = re.sub(r"(Head of Department\s*)(?:Dr\.|Prof\.)\s+[A-Z]\.\s*[A-Z]\.\s*[A-Za-z]+", rf"\g<1>{hod}", txt)
                p.text = txt
        if "Principal" in txt:
            if principal:
                txt = re.sub(r"(Principal\s*)(?:Dr\.|Prof\.)\s+[A-Z]\.\s*[A-Z]\.\s*[A-Za-z]+", rf"\g<1>{principal}", txt)
                p.text = txt

    # Find candidate signature paragraphs at bottom of Acknowledgement
    ack_cand_paras = []
    for i in range(ack_start, ack_end):
        p = doc.paragraphs[i]
        txt = p.text.strip()
        if not txt:
            continue
        words = txt.split()
        if 1 <= len(words) <= 4 and not any(kw in txt.lower() for kw in ["acknowledgement", "project", "guide", "department", "principal", "college", "savitribai", "pune", "we", "furthermore", "finally"]):
            ack_cand_paras.append(p)

    for idx, p in enumerate(ack_cand_paras):
        if idx < len(students):
            p.text = students[idx]["name"]
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        else:
            p.text = ""


def _sync_abstract_page(doc: Document, ai_sections: Dict[str, str], topic: str):
    abs_start = None
    abs_end = None
    for i, p in enumerate(doc.paragraphs):
        if p.text.strip().upper() == "ABSTRACT":
            abs_start = i
        if abs_start is not None and i > abs_start and ("LIST OF FIGURES" in p.text.upper() or "TABLE OF CONTENTS" in p.text.upper() or "ABBREVIATIONS" in p.text.upper()):
            abs_end = i
            break

    if abs_start is None:
        return

    if abs_end is None:
        # No explicit front-matter marker after the abstract: stop at the next
        # numbered heading (e.g. "1.1 INTRODUCTION") so the whole abstract body is
        # captured, instead of an arbitrary fixed window that truncates it.
        for i in range(abs_start + 1, len(doc.paragraphs)):
            txt = doc.paragraphs[i].text.strip()
            if re.match(r"^\d+\.\d+", txt) or txt.upper() in {
                "LIST OF FIGURES", "TABLE OF CONTENTS", "REFERENCES",
                "ACKNOWLEDGEMENT", "CERTIFICATE", "ABBREVIATIONS",
            }:
                abs_end = i
                break
        if abs_end is None:
            abs_end = min(len(doc.paragraphs), abs_start + 25)

    abstract_content = ai_sections.get("Abstract") or ai_sections.get("abstract") or ""
    if not abstract_content:
        for k, v in ai_sections.items():
            if "abstract" in k.lower():
                abstract_content = v
                break

    if not abstract_content:
        from core.gemini_engine import _synthesize_distinct_section
        abstract_content = _synthesize_distinct_section(topic, "Abstract")

    paragraphs_text = [blk.strip() for blk in abstract_content.split("\n\n") if blk.strip()] or [""]
    # Capture the ORIGINAL abstract body paragraphs as objects before mutating:
    # inserting new blocks shifts paragraph indices, so index-based clearing
    # would blank the wrong paragraphs and leave stale reference text behind.
    body_paras = doc.paragraphs[abs_start + 1:abs_end]
    if not body_paras:
        return
    anchor = body_paras[0]
    anchor.text = paragraphs_text[0]
    anchor.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    anchor.paragraph_format.line_spacing = 1.5

    for old_p in body_paras[1:]:
        old_p._element.getparent().remove(old_p._element)

    curr_p = anchor
    for extra_blk in paragraphs_text[1:]:
        new_p = doc.add_paragraph()
        new_p.text = extra_blk
        new_p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        new_p.paragraph_format.line_spacing = 1.5
        curr_p._element.addnext(new_p._element)
        curr_p = new_p


def _enforce_chapter_page_breaks(doc: Document):
    """
    Enforces page_break_before = True for every main chapter and front-matter heading
    so every chapter strictly starts on a fresh page.
    """
    PAGE_BREAK_HEADINGS = [
        "CERTIFICATE", "ACKNOWLEDGEMENT", "ABSTRACT", "TABLE OF CONTENTS",
        "LIST OF FIGURES", "ABBREVIATIONS", "REFERENCES", "BIBLIOGRAPHY", "ANNEXURE"
    ]
    for p in doc.paragraphs:
        txt = p.text.strip().upper()
        if not txt:
            continue
        is_chap = bool(re.match(r"^CHAPTER\s+\d+(\s*[:\-\u2013\u2014]\s*[A-Z\s]+|\s+[A-Z\s]+)?$", txt)) and len(txt) < 60
        is_front = any(txt == h for h in PAGE_BREAK_HEADINGS)
        if is_chap or is_front:
            p.paragraph_format.page_break_before = True


def _clean_index_tables(doc: Document):
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    cleaned = clean_instruction_text(para.text)
                    if cleaned != para.text:
                        para.text = cleaned


_GENERIC_FIGURE_CAPTIONS = [
    "System Architecture",
    "Block Diagram",
    "System Flowchart",
    "Module / Component Diagram",
    "Implementation Snapshot",
    "Result / Output View",
    "Use Case Diagram",
    "Testing Screenshot",
]


def _lof_caption_column(table):
    """Return the caption-column index if `table` is a List of Figures, else None.

    College reports vary: some use a 3-column "Sr.No. | Figure Name | Pg.No."
    table with a header row, others a bare 2-column numeric/caption table with no
    header.  Detect both without touching the Table of Contents (whose first
    column is mostly non-numeric chapter titles).
    """
    if not table.rows or len(table.columns) < 2:
        return None
    header = [c.text.strip().lower() for c in table.rows[0].cells]
    for i, h in enumerate(header):
        if "figure" in h and "name" in h:
            return i
    if re.match(r"sr\.?\s*no", header[0] or ""):
        return 1
    rows = table.rows
    numeric = sum(1 for r in rows if re.match(r"^\d+\.?$", r.cells[0].text.strip()))
    if numeric >= max(2, len(rows) - 1):
        return 1
    return None


def _sync_list_of_figures(doc: Document, images: List[Dict[str, Any]]):
    """Rewrite the List of Figures captions so the reference's own hardware/figure
    names (e.g. "Temperature Sensor", "DC Motor") never leak into the new report.

    The table's shape, numbering column, page-number column and formatting are
    preserved; only the caption text is replaced—by the user's uploaded image
    captions when present, otherwise by generic topic-agnostic diagram names.
    """
    captions = [(img.get("caption") or "").strip() for img in (images or [])]
    captions = [c for c in captions if c]

    for table in doc.tables:
        cap_idx = _lof_caption_column(table)
        if cap_idx is None:
            continue
        data_rows = [r for r in table.rows if re.match(r"^\d+\.?$", r.cells[0].text.strip())]
        if not data_rows:
            continue

        final = list(captions)
        for generic in _GENERIC_FIGURE_CAPTIONS:
            if len(final) >= len(data_rows):
                break
            if generic not in final:
                final.append(generic)
        while len(final) < len(data_rows):
            final.append(f"Figure {len(final) + 1}")

        for i, row in enumerate(data_rows):
            cell = row.cells[cap_idx]
            if not cell.paragraphs:
                continue
            first = cell.paragraphs[0]
            if first.runs:
                first.runs[0].text = final[i]
                for extra in first.runs[1:]:
                    extra.text = ""
            else:
                first.text = final[i]
            for extra_p in cell.paragraphs[1:]:
                extra_p.text = ""
        break



def _sync_section_page_numbering(doc: Document):
    """Enforce Upper Roman (I, II, III...) for Section 1 (Front Matter) and Decimal (1, 2, 3...) starting at 1 for Section 2 (Chapters)."""
    if len(doc.sections) >= 1:
        s1 = doc.sections[0]
        sectPr1 = s1._sectPr
        for el in list(sectPr1.findall(qn("w:pgNumType"))):
            sectPr1.remove(el)
        pg1 = OxmlElement("w:pgNumType")
        pg1.set(qn("w:fmt"), "upperRoman")
        pg1.set(qn("w:start"), "1")
        sectPr1.append(pg1)
    if len(doc.sections) >= 2:
        for s2 in doc.sections[1:]:
            sectPr2 = s2._sectPr
            for el in list(sectPr2.findall(qn("w:pgNumType"))):
                sectPr2.remove(el)
            pg2 = OxmlElement("w:pgNumType")
            pg2.set(qn("w:fmt"), "decimal")
            pg2.set(qn("w:start"), "1")
            sectPr2.append(pg2)


def fill_template(
    source_docx_path: str,
    doc_map: Dict[str, Any],
    student_info: Dict[str, Any],
    ai_sections: Dict[str, str],
    images: List[Dict[str, Any]],
    output_filename: Optional[str] = None,
) -> str:
    old_candidate_names = _source_candidate_names(source_docx_path)
    doc = Document(source_docx_path)

    topic = student_info.get("topic", "Report").strip()
    group_no = student_info.get("group_no", "Group No. 50").strip()
    guide = student_info.get("guide_name", DEFAULT_FACULTY["guide_name"]).strip()
    hod = student_info.get("hod_name", DEFAULT_FACULTY["hod_name"]).strip()
    principal = student_info.get("principal_name", DEFAULT_FACULTY["principal_name"]).strip()
    year = student_info.get("academic_year", DEFAULT_FACULTY["academic_year"]).strip()

    students = []
    # PBL teams are not capped at four members; accept every indexed student
    # supplied by the conversational workflow.
    for i in range(1, 21):
        s_name = student_info.get(f"student_name_{i}", "").strip()
        s_roll = student_info.get(f"roll_no_{i}", "").strip() or "xxxx"
        if s_name:
            students.append({"name": s_name, "seat": s_roll})
    if not students:
        s1_name = student_info.get("student_name", "Student Name").strip()
        s1_roll = student_info.get("roll_no", "").strip() or "xxxx"
        students.append({"name": s1_name, "seat": s1_roll})

    _sync_title_page(doc, students, topic, guide, year)
    _sync_student_identity_rows(doc, students, len(old_candidate_names))
    _sync_certificate_page(doc, students, topic, guide, hod, principal, year)
    _sync_acknowledgement(doc, students, guide, hod, principal)
    _sync_abstract_page(doc, ai_sections, topic)
    _clean_index_tables(doc)
    _sync_list_of_figures(doc, images)

    replacements = _build_replacements(doc_map, student_info)
    for para in _iter_document_paragraphs(doc):
        _replace_in_paragraph(para, replacements)
    _replace_report_sections(doc, doc_map, ai_sections)
    _insert_uml_diagrams(doc, images)
    _enforce_chapter_page_breaks(doc)
    _enforce_times_new_roman(doc)
    _sync_section_page_numbering(doc)

    if not output_filename:
        topic_clean = "".join(c for c in topic if c.isalnum() or c == "_")[:20]
        output_filename = f"Report_{topic_clean}_{uuid.uuid4().hex[:6]}.docx"
    output_path = os.path.join(OUTPUTS_DIR, output_filename)
    doc.save(output_path)
    _sync_textboxes_in_saved_docx(output_path, topic, students, old_candidate_names)
    _sync_headers_in_saved_docx(output_path, topic, group_no)
    return output_path


def swap_report(
    source_docx_path: str,
    doc_map: Dict[str, Any],
    student_info: Dict[str, Any],
    ai_sections: Dict[str, str],
    images: List[Dict[str, Any]],
    output_filename: Optional[str] = None,
) -> str:
    return fill_template(
        source_docx_path=source_docx_path,
        doc_map=doc_map,
        student_info=student_info,
        ai_sections=ai_sections,
        images=images,
        output_filename=output_filename,
    )


def _sync_headers_in_saved_docx(path: str, topic: str, group_no: str):
    """Refresh header text in the saved file without altering page setup.

    The reference's header/footer part structure (which parts exist, whether the
    first page differs, and the college footer wording) is part of its format and
    must be preserved exactly.  Rebuilding headers through python-docx would force
    ``titlePg``, add a brand-new default header part, and rewrite the displayed
    footer—none of which match the source.  Instead we only rewrite the visible
    text of the header parts that already exist, so a stale topic from the
    reference never leaks while the layout stays identical.  Footers are left
    untouched because they already carry the correct college identity.
    """
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with zipfile.ZipFile(path, "r") as source:
        files = {name: source.read(name) for name in source.namelist()}

    changed = False
    for name in list(files):
        if not re.match(r"word/header\d+\.xml", name):
            continue
        root = etree.fromstring(files[name])
        first_filled = False
        for para in root.xpath(".//w:p", namespaces=namespace):
            text_nodes = para.xpath(".//w:t", namespaces=namespace)
            visible = "".join(node.text or "" for node in text_nodes)
            if not visible.strip():
                continue
            if not first_filled:
                text_nodes[0].text = f"{topic}\t\t{group_no}"
                text_nodes[0].set(qn("xml:space"), "preserve")
                for node in text_nodes[1:]:
                    node.text = ""
                first_filled = True
            else:
                for node in text_nodes:
                    node.text = ""
            changed = True
        files[name] = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)

    if not changed:
        return
    fd, temp_path = tempfile.mkstemp(suffix=".docx", dir=os.path.dirname(path))
    os.close(fd)
    try:
        with zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as target:
            for name, data in files.items():
                target.writestr(name, data)
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def _inject_comprehensive_chapters(doc: Document, ai_sections: Dict[str, str], topic: str):
    if not ai_sections:
        return

    doc.add_page_break()

    current_chapter = None
    for sec_name, content in ai_sections.items():
        sec_lower = sec_name.lower().strip()

        # Detect chapter transitions
        m_chap = re.search(r"chapter\s*(\d+)", sec_lower)
        if m_chap:
            chap_num = int(m_chap.group(1))
            if chap_num != current_chapter:
                if current_chapter is not None:
                    doc.add_page_break()
                current_chapter = chap_num
                
                ch_p = doc.add_paragraph()
                ch_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                ch_run = ch_p.add_run(f"CHAPTER {chap_num}")
                ch_run.font.name = "Times New Roman"
                ch_run.font.size = Pt(14)
                ch_run.bold = True

        h_p = doc.add_paragraph()
        h_p.paragraph_format.space_before = Pt(12)
        h_p.paragraph_format.space_after = Pt(6)
        h_run = h_p.add_run(sec_name)
        h_run.font.name = "Times New Roman"
        h_run.font.size = Pt(12)
        h_run.bold = True

        for p_text in content.split("\n\n"):
            if not p_text.strip():
                continue
            body_p = doc.add_paragraph()
            body_p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            body_p.paragraph_format.line_spacing = 1.5
            body_p.paragraph_format.space_after = Pt(6)

            body_run = body_p.add_run(p_text.strip())
            body_run.font.name = "Times New Roman"
            body_run.font.size = Pt(12)


def _insert_uml_diagrams(doc: Document, images: List[Dict[str, Any]]):
    if not images:
        return

    doc_paras = doc.paragraphs
    for img in images:
        img_path = img.get("path")
        slot_key = img.get("slot_key") or img.get("target_section", "")
        caption = img.get("caption", "Architecture / UML Diagram")

        if not img_path or not os.path.exists(img_path):
            continue

        insert_idx = None
        for idx, p in enumerate(doc_paras):
            if slot_key.lower() in p.text.lower():
                insert_idx = idx + 1
                break

        if insert_idx is None:
            insert_idx = max(0, len(doc_paras) - 2)

        try:
            ref_para = doc_paras[insert_idx]
            img_p = OxmlElement("w:p")
            ref_para._element.addnext(img_p)
            new_para = doc.paragraphs[insert_idx + 1]
            new_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = new_para.add_run()
            run.add_picture(img_path, width=Inches(5.0))

            cap_p = OxmlElement("w:p")
            new_para._element.addnext(cap_p)
            cap_para = doc.paragraphs[insert_idx + 2]
            cap_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            cap_run = cap_para.add_run(f"Figure: {caption}")
            cap_run.font.name = "Times New Roman"
            cap_run.font.size = Pt(10)
            cap_run.italic = True
        except Exception as e:
            print(f"[DocxWriter] UML image insert warning: {e}")


def _set_cell_background(cell, fill_hex: str):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill_hex)
    tcPr.append(shd)


def _set_cell_margins(cell, top=120, bottom=120, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement("w:tcMar")
    for m_name, val in [("top", top), ("bottom", bottom), ("left", left), ("right", right)]:
        node = OxmlElement(f"w:{m_name}")
        node.set(qn("w:w"), str(val))
        node.set(qn("w:type"), "dxa")
        tcMar.append(node)
    tcPr.append(tcMar)


def generate_internship_docx(
    student_info: Dict[str, Any],
    ai_sections: Dict[str, str],
    images: List[Dict[str, Any]],
    output_filename: Optional[str] = None,
) -> str:
    """
    Builds a standalone, 100% formatted SPPU Internship Report DOCX document
    following the exact standards from 'Internship_Report_-_Rameshwar[1].docx'
    and 'Internship_Report_Ajit.pdf'.
    """
    doc = Document()

    # Configure Margins: 1.0 inch all around
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)
        section.different_first_page_header_footer = True

    topic = student_info.get("topic", "Industrial Training").strip()
    company = student_info.get("company_name", "NeuAI Labs LLP").strip()
    mentor = student_info.get("company_mentor_name", "Mr. Subham Asbe").strip()
    mentor_desig = student_info.get("company_mentor_designation", "Technical Lead").strip()
    guide = student_info.get("guide_name") or student_info.get("college_guide_name", "Prof. N. G. Bhojne").strip()
    hod = student_info.get("hod_name", "Dr. M. P. Wankhade").strip()
    principal = student_info.get("principal_name", "Dr. S. D. Lokhande").strip()
    year = student_info.get("academic_year", "2024-25").strip()
    start_date = student_info.get("internship_start_date", "2025-01-01").strip()
    try:
        weeks_count = int(student_info.get("internship_duration_weeks", 4))
    except Exception:
        weeks_count = 4

    student_name = student_info.get("student_name") or student_info.get("student_name_1", "Student Name").strip()
    student_roll = student_info.get("roll_no") or student_info.get("roll_no_1", "xxxx").strip()
    student_prn = student_info.get("prn_no", "").strip()

    # Apply Header & Footer to standard section
    for sec in doc.sections:
        header = sec.header
        header.is_linked_to_previous = False
        p_hdr = header.paragraphs[0] if header.paragraphs else header.add_paragraph()
        p_hdr.text = ""
        r1 = p_hdr.add_run(f"{topic}\t\tInternship Report\nSinhgad College of Engineering, Dept. of Computer Engineering\t\tYear {year}")
        r1.font.name = "Times New Roman"
        r1.font.size = Pt(8.5)
        r1.font.color.rgb = RGBColor(100, 100, 100)

        footer = sec.footer
        p_ftr = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
        p_ftr.text = ""
        r2 = p_ftr.add_run(f"TE (Computer), SCOE Pune\t\tDepartment of Computer Engineering")
        r2.font.name = "Times New Roman"
        r2.font.size = Pt(8.5)
        r2.font.color.rgb = RGBColor(100, 100, 100)

    # ── PAGE 1: TITLE PAGE ───────────────────────────────────────────────────
    p_inst = doc.add_paragraph()
    p_inst.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_inst = p_inst.add_run("SAVITRIBAI PHULE PUNE UNIVERSITY\nSINHGAD COLLEGE OF ENGINEERING, PUNE-41\nDEPARTMENT OF COMPUTER ENGINEERING")
    r_inst.font.name = "Times New Roman"
    r_inst.font.size = Pt(13)
    r_inst.bold = True
    p_inst.paragraph_format.space_after = Pt(28)

    p_rep = doc.add_paragraph()
    p_rep.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_rep = p_rep.add_run("A REPORT ON\nINDUSTRIAL TRAINING / INTERNSHIP")
    r_rep.font.name = "Times New Roman"
    r_rep.font.size = Pt(15)
    r_rep.bold = True
    p_rep.paragraph_format.space_after = Pt(18)

    p_at = doc.add_paragraph()
    p_at.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_at = p_at.add_run(f"Undertaken at\n{company}")
    r_at.font.name = "Times New Roman"
    r_at.font.size = Pt(13)
    r_at.bold = True
    p_at.paragraph_format.space_after = Pt(20)

    p_deg = doc.add_paragraph()
    p_deg.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_deg = p_deg.add_run("SUBMITTED IN PARTIAL FULFILLMENT OF THE REQUIREMENTS\nFOR THE DEGREE OF\nBACHELOR OF ENGINEERING (COMPUTER ENGINEERING)")
    r_deg.font.name = "Times New Roman"
    r_deg.font.size = Pt(11)
    p_deg.paragraph_format.space_after = Pt(24)

    p_by = doc.add_paragraph()
    p_by.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_by = p_by.add_run(f"SUBMITTED BY\n{student_name.upper()}\nRoll / Seat No: {student_roll}" + (f" | PRN: {student_prn}" if student_prn else ""))
    r_by.font.name = "Times New Roman"
    r_by.font.size = Pt(12)
    r_by.bold = True
    p_by.paragraph_format.space_after = Pt(24)

    p_guid = doc.add_paragraph()
    p_guid.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_guid = p_guid.add_run(f"UNDER THE GUIDANCE OF\n{guide} (Internal College Guide)\n&\n{mentor} ({mentor_desig}, {company})")
    r_guid.font.name = "Times New Roman"
    r_guid.font.size = Pt(11.5)
    p_guid.paragraph_format.space_after = Pt(28)

    p_yr = doc.add_paragraph()
    p_yr.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_yr = p_yr.add_run(f"DEPARTMENT OF COMPUTER ENGINEERING\nACADEMIC YEAR {year}")
    r_yr.font.name = "Times New Roman"
    r_yr.font.size = Pt(12)
    r_yr.bold = True

    # ── PAGE 2: CERTIFICATE ──────────────────────────────────────────────────
    doc.add_page_break()

    p_cert_title = doc.add_paragraph()
    p_cert_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_ct = p_cert_title.add_run("CERTIFICATE")
    r_ct.font.name = "Times New Roman"
    r_ct.font.size = Pt(16)
    r_ct.bold = True
    r_ct.underline = True
    p_cert_title.paragraph_format.space_after = Pt(18)

    p_cert_body = doc.add_paragraph()
    p_cert_body.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_cert_body.paragraph_format.line_spacing = 1.5
    p_cert_body.paragraph_format.space_after = Pt(16)
    r_cb = p_cert_body.add_run(
        f"This is to certify that the Industrial Training / Internship report entitled \"{topic}\" submitted by "
        f"{student_name} (Roll No: {student_roll}) is a bonafide work carried out by him/her under our supervision and guidance at {company}, "
        f"in partial fulfillment of the requirements for the award of the Degree of Bachelor of Engineering (Computer Engineering) "
        f"of Savitribai Phule Pune University during the academic year {year}."
    )
    r_cb.font.name = "Times New Roman"
    r_cb.font.size = Pt(12)

    p_cert_body2 = doc.add_paragraph()
    p_cert_body2.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_cert_body2.paragraph_format.line_spacing = 1.5
    p_cert_body2.paragraph_format.space_after = Pt(32)
    r_cb2 = p_cert_body2.add_run(
        "It is certified that all corrections and suggestions indicated during internal review have been incorporated into this report. "
        "The report has been approved as it satisfies the academic requirements prescribed by the university."
    )
    r_cb2.font.name = "Times New Roman"
    r_cb2.font.size = Pt(12)

    # 4 Signatures Table (2x2 Grid)
    sig_table = doc.add_table(rows=2, cols=2)
    sig_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    sig_table.autofit = False

    sig_data = [
        [(f"{guide}\nInternal Faculty Guide\nSCOE, Pune", WD_ALIGN_PARAGRAPH.LEFT),
         (f"{mentor}\n{mentor_desig}\n{company}", WD_ALIGN_PARAGRAPH.RIGHT)],
        [(f"{hod}\nHead of Department\nDept. of Computer Engineering", WD_ALIGN_PARAGRAPH.LEFT),
         (f"{principal}\nPrincipal\nSinhgad College of Engineering", WD_ALIGN_PARAGRAPH.RIGHT)],
    ]

    for r_idx, row_items in enumerate(sig_data):
        row = sig_table.rows[r_idx]
        for c_idx, (text, align) in enumerate(row_items):
            cell = row.cells[c_idx]
            cell.width = Inches(3.2)
            _set_cell_margins(cell, top=160, bottom=160, left=100, right=100)
            p = cell.paragraphs[0]
            p.alignment = align
            p.paragraph_format.line_spacing = 1.2
            r = p.add_run(text)
            r.font.name = "Times New Roman"
            r.font.size = Pt(11)
            r.bold = True

    # ── PAGE 3: ACKNOWLEDGEMENT ──────────────────────────────────────────────
    doc.add_page_break()

    p_ack_title = doc.add_paragraph()
    p_ack_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_at = p_ack_title.add_run("ACKNOWLEDGEMENT")
    r_at.font.name = "Times New Roman"
    r_at.font.size = Pt(14)
    r_at.bold = True
    r_at.underline = True
    p_ack_title.paragraph_format.space_after = Pt(18)

    ack_text = (
        f"I take immense pleasure in expressing my heartfelt gratitude to my industry mentor, {mentor} ({mentor_desig}, {company}), "
        f"for providing the invaluable opportunity to undergo industrial internship training at {company}. His constant guidance, constructive feedback, "
        f"and technical insights were instrumental in completing the industrial project modules successfully.\n\n"
        f"I also express deep gratitude to my internal college guide, {guide}, for continuous encouragement, valuable suggestions, and academic supervision "
        f"throughout the preparation of this report.\n\n"
        f"I convey sincere thanks to {hod}, Head of the Department of Computer Engineering, and {principal}, Principal of Sinhgad College of Engineering, "
        f"for their institutional support and providing excellent facilities.\n\n"
        f"Finally, I express my sincere appreciation to all faculty members, technical staff, and team colleagues at {company} who contributed directly or "
        f"indirectly to this endeavor.\n\n"
        f"Name: {student_name}\nRoll / Seat No: {student_roll}"
    )

    for p_blk in ack_text.split("\n\n"):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.line_spacing = 1.5
        p.paragraph_format.space_after = Pt(10)
        r = p.add_run(p_blk.strip())
        r.font.name = "Times New Roman"
        r.font.size = Pt(12)

    # ── PAGE 4: TABLE OF CONTENTS / INDEX ────────────────────────────────────
    doc.add_page_break()

    p_toc_title = doc.add_paragraph()
    p_toc_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_tt = p_toc_title.add_run("TABLE OF CONTENTS")
    r_tt.font.name = "Times New Roman"
    r_tt.font.size = Pt(14)
    r_tt.bold = True
    p_toc_title.paragraph_format.space_after = Pt(14)

    toc_table = doc.add_table(rows=1, cols=3)
    toc_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr_cells = toc_table.rows[0].cells
    hdr_cells[0].text = "Chapter No."
    hdr_cells[1].text = "Title"
    hdr_cells[2].text = "Page No."

    for idx, c in enumerate(hdr_cells):
        _set_cell_background(c, "EFEFEF")
        _set_cell_margins(c, top=100, bottom=100, left=100, right=100)
        p = c.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER if idx != 1 else WD_ALIGN_PARAGRAPH.LEFT
        for run in p.runs:
            run.font.name = "Times New Roman"
            run.font.size = Pt(11)
            run.bold = True

    toc_items = [
        ("1", "INTRODUCTION & INDUSTRY PROFILE", "1"),
        ("1.1", "Overview of the Industry", "1"),
        ("1.2", "Company Profile & Vision", "2"),
        ("1.3", "Company History & Culture", "3"),
        ("2", "PROBLEM STATEMENT & OBJECTIVES", "4"),
        ("2.1", "Problem Statement & Work Scope", "4"),
        ("3", "MOTIVATION & INDUSTRY TRENDS", "6"),
        ("3.1", "Need for the Project", "6"),
        ("3.2", "Industry Trends & Skill Development", "7"),
        ("4", "METHODOLOGY & ARCHITECTURE", "8"),
        ("4.1", "Development Workflow", "8"),
        ("4.2", "Tech Stack & Tools Utilized", "9"),
        ("5", "RESULTS AND DISCUSSION", "11"),
        ("5.1", "Implementation Outcomes & Interface", "11"),
        ("6", "ATTENDANCE RECORD & WEEKLY LOG", "13"),
        ("6.1", "Weekly Activity & Attendance Schedule", "13"),
        ("7", "CONCLUSION & FUTURE SCOPE", "15"),
        ("—", "REFERENCES", "16"),
        ("—", "ANNEXURE 1: OFFER LETTER", "17"),
        ("—", "ANNEXURE 2: COMPLETION CERTIFICATE", "18"),
    ]

    for ch_no, ch_name, page_no in toc_items:
        row = toc_table.add_row()
        cells = row.cells
        cells[0].text = ch_no
        cells[1].text = ch_name
        cells[2].text = page_no
        for idx, cell in enumerate(cells):
            _set_cell_margins(cell, top=60, bottom=60, left=80, right=80)
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if idx != 1 else WD_ALIGN_PARAGRAPH.LEFT
            for run in p.runs:
                run.font.name = "Times New Roman"
                run.font.size = Pt(10.5)
                if ch_no in ["1", "2", "3", "4", "5", "6", "7", "—"]:
                    run.bold = True

    # ── CHAPTERS 1 TO 7 ──────────────────────────────────────────────────────
    doc.add_page_break()

    for chap in STANDARD_INTERNSHIP_CHAPTERS:
        chap_num = chap["chapter_num"]
        chap_title = chap["title"]

        p_ch = doc.add_paragraph()
        p_ch.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_ch.paragraph_format.space_before = Pt(14)
        p_ch.paragraph_format.space_after = Pt(4)
        r_ch = p_ch.add_run(f"CHAPTER {chap_num}")
        r_ch.font.name = "Times New Roman"
        r_ch.font.size = Pt(14)
        r_ch.bold = True

        p_ct = doc.add_paragraph()
        p_ct.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_ct.paragraph_format.space_after = Pt(16)
        r_ct = p_ct.add_run(chap_title)
        r_ct.font.name = "Times New Roman"
        r_ct.font.size = Pt(13)
        r_ct.bold = True

        # Handle Subsections
        for subsec in chap["subsections"]:
            p_sub = doc.add_paragraph()
            p_sub.paragraph_format.space_before = Pt(12)
            p_sub.paragraph_format.space_after = Pt(6)
            r_sub = p_sub.add_run(subsec)
            r_sub.font.name = "Times New Roman"
            r_sub.font.size = Pt(12)
            r_sub.bold = True

            # If Chapter 6.1 -> Render Weekly Attendance Table
            if chap_num == 6 and "6.1" in subsec:
                diary_weeks = generate_weekly_attendance_diary(topic, company, start_date, weeks_count)
                
                table = doc.add_table(rows=1, cols=5)
                table.alignment = WD_TABLE_ALIGNMENT.CENTER
                h_cells = table.rows[0].cells
                headers = ["Week / Day", "Date", "Daily Work & Modules Completed", "Hours", "Status"]
                for i, h_text in enumerate(headers):
                    h_cells[i].text = h_text
                    _set_cell_background(h_cells[i], "EFEFEF")
                    _set_cell_margins(h_cells[i], top=80, bottom=80, left=80, right=80)
                    p = h_cells[i].paragraphs[0]
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i in [0, 1, 3, 4] else WD_ALIGN_PARAGRAPH.LEFT
                    for r in p.runs:
                        r.font.name = "Times New Roman"
                        r.font.size = Pt(10)
                        r.bold = True

                for week in diary_weeks:
                    w_num = week.get("week_num", 1)
                    for entry in week.get("entries", []):
                        row = table.add_row()
                        c = row.cells
                        c[0].text = f"W{w_num}-{entry.get('day', '')[:3]}"
                        c[1].text = entry.get("date", "")
                        c[2].text = entry.get("topic", "")
                        c[3].text = "8"
                        c[4].text = entry.get("status", "Completed")
                        for idx, cell in enumerate(c):
                            _set_cell_margins(cell, top=60, bottom=60, left=80, right=80)
                            p = cell.paragraphs[0]
                            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if idx in [0, 1, 3, 4] else WD_ALIGN_PARAGRAPH.LEFT
                            for r in p.runs:
                                r.font.name = "Times New Roman"
                                r.font.size = Pt(9.5)

                p_sp = doc.add_paragraph()
                p_sp.paragraph_format.space_after = Pt(12)
                continue


            # Lookup AI Generated Content for this subsection
            content = ai_sections.get(subsec, "")
            if not content:
                for k, v in ai_sections.items():
                    if subsec.lower() in k.lower() or k.lower() in subsec.lower():
                        content = v
                        break

            if not content:
                from core.gemini_engine import _synthesize_distinct_section
                content = _synthesize_distinct_section(topic, subsec, f"Company: {company}, Mentor: {mentor}")

            for p_txt in content.split("\n\n"):
                if not p_txt.strip():
                    continue
                p_b = doc.add_paragraph()
                p_b.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                p_b.paragraph_format.line_spacing = 1.5
                p_b.paragraph_format.space_after = Pt(6)
                r_b = p_b.add_run(p_txt.strip())
                r_b.font.name = "Times New Roman"
                r_b.font.size = Pt(12)

        doc.add_page_break()

    # ── ANNEXURES ────────────────────────────────────────────────────────────
    annexure_slots = [
        ("ANNEXURE 1: COMPANY OFFER LETTER", "offer_letter", "Official Offer Letter Issued by " + company),
        ("ANNEXURE 2: INTERNSHIP COMPLETION CERTIFICATE", "completion_certificate", "Internship Completion Certificate Issued by " + company),
    ]

    for ann_title, slot_key, desc in annexure_slots:
        p_ann = doc.add_paragraph()
        p_ann.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_ann.paragraph_format.space_before = Pt(20)
        p_ann.paragraph_format.space_after = Pt(14)
        r_ann = p_ann.add_run(ann_title)
        r_ann.font.name = "Times New Roman"
        r_ann.font.size = Pt(14)
        r_ann.bold = True

        p_desc = doc.add_paragraph()
        p_desc.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_desc.paragraph_format.space_after = Pt(24)
        r_desc = p_desc.add_run(f"({desc})")
        r_desc.font.name = "Times New Roman"
        r_desc.font.size = Pt(11)
        r_desc.italic = True

        # Check if an image is provided for this slot
        ann_img = None
        for img in images:
            if img.get("slot_key") == slot_key:
                ann_img = img.get("path")
                break

        if ann_img and os.path.exists(ann_img):
            p_img = doc.add_paragraph()
            p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run_img = p_img.add_run()
            try:
                run_img.add_picture(ann_img, width=Inches(5.5))
            except Exception:
                pass
        else:
            p_box = doc.add_paragraph()
            p_box.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r_box = p_box.add_run("[ Official Document Scanned Copy Attached Here ]")
            r_box.font.name = "Times New Roman"
            r_box.font.size = Pt(12)
            r_box.bold = True

        doc.add_page_break()

    _enforce_times_new_roman(doc)

    if not output_filename:
        topic_clean = "".join(c for c in topic if c.isalnum() or c == "_")[:20]
        output_filename = f"Internship_Report_{topic_clean}_{uuid.uuid4().hex[:6]}.docx"
    output_path = os.path.join(OUTPUTS_DIR, output_filename)
    doc.save(output_path)
    return output_path


def convert_docx_to_pdf(docx_path: str) -> Optional[str]:
    import subprocess
    pdf_path = docx_path.replace(".docx", ".pdf")

    for soffice_cmd in ["soffice", "/Applications/LibreOffice.app/Contents/MacOS/soffice"]:
        try:
            result = subprocess.run(
                [soffice_cmd, "--headless", "--convert-to", "pdf", "--outdir",
                 os.path.dirname(docx_path), docx_path],
                capture_output=True, timeout=60
            )
            if result.returncode == 0 and os.path.exists(pdf_path):
                return pdf_path
        except Exception:
            continue

    try:
        from docx2pdf import convert
        convert(docx_path, pdf_path)
        if os.path.exists(pdf_path):
            return pdf_path
    except Exception:
        pass

    return None
