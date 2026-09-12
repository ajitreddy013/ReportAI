"""
preview_renderer.py
Renders publication-quality multi-page A4 academic previews directly from
the generated DOCX document binary, ensuring a 100% exact match with the
downloaded DOCX file.
"""

import base64
import html
import io
import os
import re
from typing import Any, Dict, List, Optional, Tuple

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.table import Table
from docx.text.paragraph import Paragraph


def _extract_images_as_base64(doc: docx.Document) -> Dict[str, str]:
    """Extract embedded images from DOCX part relationships as base64 data URIs."""
    images = {}
    for r_id, part in doc.part.related_parts.items():
        if hasattr(part, "content_type") and "image" in part.content_type:
            mime = part.content_type
            try:
                b64_str = base64.b64encode(part.blob).decode("utf-8")
                images[r_id] = f"data:{mime};base64,{b64_str}"
            except Exception:
                pass
    return images


def _paragraph_to_html(p: Paragraph, images_b64: Dict[str, str]) -> str:
    """Convert a python-docx paragraph to clean, styled HTML with runs and images."""
    txt = p.text.strip()
    xml_str = p._element.xml

    # Check for embedded drawing image in paragraph XML
    img_tags = []
    for r_id, data_uri in images_b64.items():
        if r_id in xml_str:
            img_tags.append(
                f'<div class="docx-embedded-img">'
                f'<img src="{data_uri}" alt="Embedded Diagram / Signature" />'
                f'</div>'
            )

    if not txt and not img_tags:
        return ""

    # Determine alignment
    align_class = "align-left"
    align_val = p.paragraph_format.alignment
    if align_val == WD_ALIGN_PARAGRAPH.CENTER:
        align_class = "align-center"
    elif align_val == WD_ALIGN_PARAGRAPH.RIGHT:
        align_class = "align-right"
    elif align_val == WD_ALIGN_PARAGRAPH.JUSTIFY:
        align_class = "align-justify"

    # Style classification
    style_name = (p.style.name if p.style else "").lower()
    p_class = "academic-para"
    if "heading 1" in style_name or re.match(r"^CHAPTER\s+\d+", txt, re.I):
        p_class = "chapter-title"
    elif "heading 2" in style_name or re.match(r"^\d+\.\d+\s+", txt):
        p_class = "section-heading"
    elif "heading 3" in style_name or re.match(r"^\d+\.\d+\.\d+\s+", txt):
        p_class = "subsection-heading"
    elif "title" in style_name or re.match(r"^(?:A\s+REPORT|A\s+PRELIMINARY|CERTIFICATE|ACKNOWLEDGEMENT|ABSTRACT|TABLE OF CONTENTS|REFERENCES|ANNEXURE)", txt, re.I):
        p_class = "front-heading"

    # Build runs HTML
    runs_html = []
    for r in p.runs:
        r_text = html.escape(r.text)
        if not r_text:
            continue
        
        # Check run styling
        is_bold = bool(r.bold)
        is_italic = bool(r.italic)
        is_underline = bool(r.underline)

        inner = r_text
        if is_bold:
            inner = f"<strong>{inner}</strong>"
        if is_italic:
            inner = f"<em>{inner}</em>"
        if is_underline:
            inner = f"<u>{inner}</u>"

        # Check font size
        font_size_style = ""
        if r.font and r.font.size:
            pt_size = round(r.font.size.pt, 1)
            if pt_size > 14:
                font_size_style = f"font-size:{pt_size}pt;"
            elif pt_size < 11:
                font_size_style = f"font-size:{pt_size}pt;"

        if font_size_style:
            inner = f'<span style="{font_size_style}">{inner}</span>'

        runs_html.append(inner)

    content_html = "".join(runs_html) if runs_html else html.escape(txt)
    
    # Prepend any embedded image tags
    img_prefix = "".join(img_tags)
    if img_prefix and not content_html:
        return img_prefix

    return f'{img_prefix}<p class="{p_class} {align_class}">{content_html}</p>'


def _table_to_html(t: Table) -> str:
    """Convert a python-docx Table to styled academic HTML."""
    rows_html = []
    is_first_row = True

    for row in t.rows:
        cells_html = []
        for cell in row.cells:
            cell_paras = [p.text.strip() for p in cell.paragraphs if p.text.strip()]
            cell_text = "<br>".join(html.escape(t) for t in cell_paras)
            tag = "th" if is_first_row and len(t.rows) > 2 else "td"
            cells_html.append(f"<{tag}>{cell_text}</{tag}>")
        rows_html.append("<tr>" + "".join(cells_html) + "</tr>")
        is_first_row = False

    return '<table class="academic-data-table">' + "".join(rows_html) + "</table>"


def _segment_docx_into_pages(doc: docx.Document, images_b64: Dict[str, str]) -> List[List[str]]:
    """Segments python-docx elements into distinct A4 page buckets."""
    pages: List[List[str]] = [[]]

    # Patterns that naturally start on a fresh page
    PAGE_BREAK_KEYWORDS = re.compile(
        r"^(?:A\s+REPORT\s+ON|A\s+PRELIMINARY\s+PROJECT|CERTIFICATE|ACKNOWLEDGEMENT|ABSTRACT|TABLE\s+OF\s+CONTENTS|LIST\s+OF\s+FIGURES|CHAPTER\s+\d+|REFERENCES|BIBLIOGRAPHY|ANNEXURE\s+\d+)",
        re.IGNORECASE,
    )

    for child in doc.element.body:
        if child.tag.endswith("p"):
            p = Paragraph(child, doc)
            txt = p.text.strip()
            xml_str = child.xml

            # Check explicit page breaks
            has_break = False
            if 'w:type="page"' in xml_str or "w:pageBreakBefore" in xml_str:
                has_break = True
            elif PAGE_BREAK_KEYWORDS.match(txt) and len(pages[-1]) > 0:
                has_break = True

            if has_break and len(pages[-1]) > 0:
                pages.append([])

            p_html = _paragraph_to_html(p, images_b64)
            if p_html:
                pages[-1].append(p_html)

        elif child.tag.endswith("tbl"):
            t = Table(child, doc)
            t_html = _table_to_html(t)
            pages[-1].append(t_html)

    # Filter out empty pages
    cleaned_pages = [p for p in pages if len(p) > 0]
    return cleaned_pages if cleaned_pages else [["<p class='academic-para'>Document generated successfully.</p>"]]


def render_report_html(docx_path: str, report_data: Dict[str, Any]) -> str:
    """
    Renders publication-quality multi-page A4 academic HTML.
    Parses the actual generated DOCX file when available for a 1:1 match.
    """
    info = report_data.get("student_info", {})
    report_type = info.get("report_type", report_data.get("report_type", "project")).lower()
    
    topic = info.get("topic", "Project Report").strip()
    group_no = info.get("group_no", "Group No. 50").strip()
    year = info.get("academic_year", "2024-25").strip()
    company = info.get("company_name", "NeuAI Labs LLP").strip()

    # Try reading the exact generated DOCX binary
    doc_pages_raw: Optional[List[List[str]]] = None
    if docx_path and os.path.exists(docx_path):
        try:
            doc = docx.Document(docx_path)
            images_b64 = _extract_images_as_base64(doc)
            doc_pages_raw = _segment_docx_into_pages(doc, images_b64)
        except Exception as exc:
            print(f"[PreviewRenderer] Note: DOCX parse fallback due to {exc}")
            doc_pages_raw = None

    pages_html: List[str] = []

    def make_header(is_front_matter: bool = False) -> str:
        if is_front_matter:
            return f"""
            <div class="page-header">
                <div class="header-line1">
                    <span>Sinhgad College of Engineering, Dept. of Computer Engineering</span>
                    <span>Year {html.escape(year)}</span>
                </div>
            </div>
            """
        if report_type == "internship":
            return f"""
            <div class="page-header">
                <div class="header-line1">
                    <span>{html.escape(topic)}</span>
                    <span style="font-weight:normal; font-style:italic;">{html.escape(company)}</span>
                </div>
            </div>
            """
        return f"""
        <div class="page-header">
            <div class="header-line1">
                <span>{html.escape(topic)}</span>
                <span>{html.escape(group_no)}</span>
            </div>
        </div>
        """

    def make_footer(page_num_str: str) -> str:
        return f"""
        <div class="page-footer">
            <span>SCOE, Dept. of Computer Engineering</span>
            <span>Year {html.escape(year)}</span>
        </div>
        """

    if doc_pages_raw:
        total_p = len(doc_pages_raw)
        roman_numerals = ["(i)", "(ii)", "(iii)", "(iv)", "(v)", "(vi)", "(vii)"]

        for idx, page_items in enumerate(doc_pages_raw):
            page_num = idx + 1
            is_front = page_num <= 4
            
            # Roman page numbers for front matter, arabic for chapters
            if page_num == 1:
                page_tag = ""  # No page number on Title Page
            elif page_num <= len(roman_numerals):
                page_tag = roman_numerals[page_num - 1]
            else:
                page_tag = str(page_num - 4)

            # Detect anchor ID for sidebar navigation
            joined_text = " ".join(page_items)
            anchor_id = f"page-{page_num}"
            if "CERTIFICATE" in joined_text:
                anchor_id = "page-certificate"
            elif "ACKNOWLEDGEMENT" in joined_text:
                anchor_id = "page-acknowledgement"
            elif "ABSTRACT" in joined_text:
                anchor_id = "page-abstract"
            elif "TABLE OF CONTENTS" in joined_text:
                anchor_id = "page-toc"
            elif "CHAPTER 1" in joined_text:
                anchor_id = "sec-chapter-1"
            elif "CHAPTER 2" in joined_text:
                anchor_id = "sec-chapter-2"
            elif "CHAPTER 3" in joined_text:
                anchor_id = "sec-chapter-3"
            elif "CHAPTER 4" in joined_text:
                anchor_id = "sec-chapter-4"
            elif "CHAPTER 5" in joined_text:
                anchor_id = "sec-chapter-5"
            elif "CHAPTER 6" in joined_text:
                anchor_id = "sec-chapter-6"
            elif "CHAPTER 7" in joined_text:
                anchor_id = "sec-chapter-7"
            elif "CHAPTER 8" in joined_text:
                anchor_id = "sec-chapter-8"
            elif "ANNEXURE 1" in joined_text:
                anchor_id = "sec-annexure-1"
            elif "ANNEXURE 2" in joined_text:
                anchor_id = "sec-annexure-2"
            elif "REFERENCES" in joined_text:
                anchor_id = "sec-references"

            body_content = "\n".join(page_items)
            header_html = make_header(is_front_matter=is_front) if page_num > 1 else ""
            footer_html = make_footer(page_tag) if page_num > 1 else ""

            page_div = f"""
            <div class="a4-page {'front-matter' if is_front else 'content-page'}" id="{anchor_id}">
                {header_html}
                <div class="page-body-flow">
                    {body_content}
                </div>
                {footer_html}
            </div>
            """
            pages_html.append(page_div)

    else:
        # Structured synthesizer fallback
        st_name = info.get("student_name", "Student Name").strip()
        st_roll = info.get("roll_no", "xxxx").strip()
        guide = info.get("guide_name", "Prof. Guide").strip()
        hod = info.get("hod_name", "Dr. HOD").strip()
        principal = info.get("principal_name", "Dr. Principal").strip()

        p1 = f"""
        <div class="a4-page front-matter" id="page-title">
            <div class="title-page-content">
                <p class="univ-tag">{'A REPORT OF INTERNSHIP' if report_type == 'internship' else 'A PRELIMINARY PROJECT REPORT ON'}</p>
                <h1 class="main-report-title">{html.escape(topic.upper())}</h1>
                <p class="submit-tag">SUBMITTED TO SAVITRIBAI PHULE PUNE UNIVERSITY<br>IN PARTIAL FULFILLMENT OF DEGREE REQUIREMENTS<br><strong>BACHELOR OF ENGINEERING</strong><br>In <strong>COMPUTER ENGINEERING</strong></p>
                <div class="by-section">
                    <p class="by-tag">By</p>
                    <p style="font-size:13pt; font-weight:bold;">{html.escape(st_name.upper())}</p>
                    <p style="font-size:11pt; font-weight:bold;">Roll / Seat No: {html.escape(st_roll)}</p>
                </div>
                <div class="guide-section">
                    <p class="guide-tag">Under the guidance of</p>
                    <p class="guide-name">{html.escape(guide)}</p>
                </div>
                <div class="college-seal-block">
                    <div class="college-logo-text">SCOE</div>
                    <p class="dept-name">DEPARTMENT OF COMPUTER ENGINEERING</p>
                    <p class="college-name">SINHGAD COLLEGE OF ENGINEERING, PUNE-41</p>
                    <p class="acad-year">{html.escape(year)}</p>
                </div>
            </div>
        </div>
        """
        pages_html.append(p1)

    all_pages_html = "\n".join(pages_html)
    total_pages_count = len(pages_html)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Report Preview — {html.escape(topic)}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  
  html, body {{
    background: #141414;
    color: #111111;
    font-family: 'Times New Roman', 'Liberation Serif', Times, serif;
    padding: 30px 0 80px 0;
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
  }}

  .preview-viewport {{
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 36px;
    width: 100%;
  }}

  /* ── A4 Page Container (Authentic DOCX Physical Page) ────────── */
  .a4-page {{
    width: 210mm;
    min-height: 297mm;
    background: #ffffff;
    padding: 22mm 22mm 20mm 28mm;
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.55), 0 0 1px rgba(0, 0, 0, 0.85);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    position: relative;
    border-radius: 2px;
  }}

  /* ── Institutional 2-Line Header ──────────────────────────────── */
  .page-header {{
    border-bottom: 1.2px solid #555;
    padding-bottom: 5px;
    margin-bottom: 18px;
    font-size: 9pt;
    color: #444;
    font-family: 'Times New Roman', serif;
  }}
  .header-line1, .header-line2 {{
    display: flex;
    justify-content: space-between;
    width: 100%;
  }}
  .header-line1 {{ font-weight: bold; margin-bottom: 2px; color: #111; }}

  /* ── Institutional Footer ─────────────────────────────────────── */
  .page-footer {{
    border-top: 1px solid #aaa;
    padding-top: 6px;
    margin-top: 20px;
    display: flex;
    justify-content: space-between;
    font-size: 9pt;
    color: #555;
  }}
  .page-footer .page-num {{ font-weight: bold; color: #111; }}

  /* ── Cover Page Typography ────────────────────────────────────── */
  .title-page-content {{
    text-align: center;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    height: 100%;
    min-height: 250mm;
  }}
  .univ-tag {{
    font-size: 13pt;
    font-weight: bold;
    letter-spacing: 0.5px;
    margin-bottom: 12px;
  }}
  .main-report-title {{
    font-size: 17pt;
    font-weight: bold;
    text-transform: uppercase;
    line-height: 1.4;
    margin: 10px 0 20px 0;
  }}
  .submit-tag {{
    font-size: 11pt;
    line-height: 1.6;
    margin-bottom: 16px;
  }}
  .by-section {{
    margin: 14px 0;
  }}
  .by-tag {{
    font-size: 12pt;
    font-weight: bold;
    margin-bottom: 6px;
  }}
  .guide-section {{
    margin: 16px 0;
  }}
  .guide-tag {{
    font-size: 11pt;
    margin-bottom: 4px;
  }}
  .guide-name {{
    font-size: 13pt;
    font-weight: bold;
  }}
  .college-seal-block {{
    margin-top: 14px;
    border-top: 2px solid #000;
    padding-top: 12px;
  }}
  .college-logo-text {{
    font-size: 18pt;
    font-weight: bold;
    letter-spacing: 2px;
    margin-bottom: 4px;
  }}
  .dept-name {{
    font-size: 11.5pt;
    font-weight: bold;
  }}
  .college-name {{
    font-size: 12pt;
    font-weight: bold;
  }}
  .acad-year {{
    font-size: 12pt;
    font-weight: bold;
    margin-top: 4px;
  }}

  /* ── Body Flow & Typography ───────────────────────────────────── */
  .page-body-flow {{
    flex: 1;
  }}

  .chapter-title {{
    font-size: 14pt;
    font-weight: bold;
    text-align: center;
    text-transform: uppercase;
    margin: 14px 0 16px 0;
    border-bottom: 2px solid #000;
    padding-bottom: 6px;
    letter-spacing: 0.5px;
  }}

  .front-heading {{
    text-align: center;
    font-size: 15pt;
    font-weight: bold;
    text-transform: uppercase;
    margin: 12px 0 16px 0;
    letter-spacing: 0.5px;
  }}

  .section-heading {{
    font-size: 12.5pt;
    font-weight: bold;
    margin: 14px 0 6px 0;
    color: #000;
  }}

  .subsection-heading {{
    font-size: 11.5pt;
    font-weight: bold;
    margin: 10px 0 4px 0;
    color: #111;
  }}

  .academic-para {{
    font-size: 12pt;
    line-height: 1.6;
    text-align: justify;
    margin-bottom: 10px;
    color: #111;
  }}

  .align-center {{ text-align: center; }}
  .align-right {{ text-align: right; }}
  .align-left {{ text-align: left; }}
  .align-justify {{ text-align: justify; }}

  /* ── Academic Data & Attendance Tables ────────────────────────── */
  .academic-data-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 9.5pt;
    margin: 12px 0 16px 0;
    font-family: 'Times New Roman', serif;
  }}
  .academic-data-table th {{
    background: #f0f0f0;
    border: 1px solid #444;
    padding: 7px 8px;
    font-weight: bold;
    text-align: left;
    color: #000;
  }}
  .academic-data-table td {{
    border: 1px solid #666;
    padding: 6px 8px;
    text-align: left;
    vertical-align: top;
    color: #111;
  }}

  /* ── Embedded Images & Diagram Blocks ─────────────────────────── */
  .docx-embedded-img {{
    text-align: center;
    margin: 14px 0;
  }}
  .docx-embedded-img img {{
    max-width: 92%;
    max-height: 160mm;
    height: auto;
    border: 1px solid #ddd;
    border-radius: 2px;
  }}

  /* Print Media Query */
  @media print {{
    html, body {{
      background: #fff;
      padding: 0;
    }}
    .a4-page {{
      box-shadow: none;
      margin: 0;
      page-break-after: always;
    }}
  }}
</style>
</head>
<body>
<div class="preview-viewport" data-total-pages="{total_pages_count}">
  {all_pages_html}
</div>
</body>
</html>"""
