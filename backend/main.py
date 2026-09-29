"""
main.py — ReportAI FastAPI Backend with Full Academic Report Rules
"""

import os
import sys
import json
import uuid
import shutil
from typing import Any, Dict, List, Optional

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    pass

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

sys.path.insert(0, os.path.dirname(__file__))

from core.docx_reader import analyze_docx, extract_pdf_research_paper, extract_supporting_material
from core.docx_writer import fill_template, swap_report, generate_internship_docx, convert_docx_to_pdf
from core.pbl_renderer import render_pbl_report
from core.gemini_engine import generate_content, GEMINI_MODEL
from core.report_rules import UML_DIAGRAM_SLOTS, STANDARD_INTERNSHIP_CHAPTERS, INTERNSHIP_ANNEXURES, DEFAULT_INTERNSHIP_FACULTY, pbl_section_list
from core.paper_search import find_recent_papers, merge_papers, enrich_paper_by_title
from core.preview_renderer import render_report_html

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
IMAGES_DIR  = os.path.join(BASE_DIR, "uploads", "images")
PAPERS_DIR  = os.path.join(BASE_DIR, "uploads", "papers")
SOURCES_DIR = os.path.join(BASE_DIR, "uploads", "sources")


for d in [UPLOADS_DIR, OUTPUTS_DIR, IMAGES_DIR, PAPERS_DIR, SOURCES_DIR]:
    os.makedirs(d, exist_ok=True)

_report_store: Dict[str, Dict] = {}
_doc_store: Dict[str, Dict]    = {}
_source_store: Dict[str, Dict] = {}

DOC_STORE_FILE = os.path.join(UPLOADS_DIR, "_doc_store.json")
REPORT_STORE_FILE = os.path.join(OUTPUTS_DIR, "_report_store.json")

def _load_stores():
    global _doc_store, _report_store
    if os.path.exists(DOC_STORE_FILE):
        try:
            with open(DOC_STORE_FILE, "r") as f:
                _doc_store.update(json.load(f))
        except Exception:
            pass
    if os.path.exists(REPORT_STORE_FILE):
        try:
            with open(REPORT_STORE_FILE, "r") as f:
                _report_store.update(json.load(f))
        except Exception:
            pass

def _save_doc_store():
    try:
        with open(DOC_STORE_FILE, "w") as f:
            json.dump(_doc_store, f)
    except Exception:
        pass

def _save_report_store():
    try:
        with open(REPORT_STORE_FILE, "w") as f:
            json.dump(_report_store, f)
    except Exception:
        pass

_load_stores()

app = FastAPI(title="ReportAI", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get("/api/status")
def status():
    gemini_key_set = bool(os.environ.get("GEMINI_API_KEY", "").strip())
    try:
        import google.generativeai
        gemini_available = True
    except ImportError:
        gemini_available = False
    return {
        "status": "ok",
        "gemini_available": gemini_available,
        "gemini_key_set": gemini_key_set,
        "gemini_model": GEMINI_MODEL,
        "using_ai": gemini_available and gemini_key_set,
    }


@app.post("/api/upload-doc")
async def upload_doc(file: UploadFile = File(...)):
    """Upload template or friend's report DOCX."""
    if not file.filename.lower().endswith(".docx"):
        raise HTTPException(400, "Only .docx files are supported.")

    doc_id    = str(uuid.uuid4())
    save_path = os.path.join(UPLOADS_DIR, f"{doc_id}_{file.filename}")

    with open(save_path, "wb") as f:
        f.write(await file.read())

    try:
        doc_map = analyze_docx(save_path)
    except Exception as e:
        if os.path.exists(save_path):
            os.remove(save_path)
        raise HTTPException(500, f"Failed to analyze document: {str(e)}")

    _doc_store[doc_id] = {**doc_map, "file_path": save_path}
    _save_doc_store()

    return {
        "doc_id":                 doc_id,
        "filename":               file.filename,
        "is_template":            doc_map["is_template"],
        "default_student_count":  doc_map.get("default_student_count", 4),
        "title_page_fields":      doc_map.get("title_page_fields", []),
        "faculty_fields":         doc_map.get("faculty_fields", []),
        "role_records":           doc_map.get("role_records", []),
        "confirmed_fields":       doc_map.get("confirmed_fields", []),
        "detected_values":        doc_map.get("detected_values", {}),
        "headings":               doc_map.get("headings", []),
        "uml_slots":              UML_DIAGRAM_SLOTS,
        "total_sections":         len(doc_map.get("headings", [])),
        "total_paragraphs":       doc_map["total_paragraphs"],
    }


@app.post("/api/upload-paper")
async def upload_paper(file: UploadFile = File(...)):
    """Upload user research paper PDF for literature survey citation."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only .pdf files are supported for research papers.")

    paper_id = str(uuid.uuid4())
    save_path = os.path.join(PAPERS_DIR, f"{paper_id}_{file.filename}")

    with open(save_path, "wb") as f:
        f.write(await file.read())

    extracted = extract_pdf_research_paper(save_path)
    title = extracted.get("title") or file.filename
    # A user PDF yields only title/abstract; resolve authors/year/venue/DOI from
    # CrossRef so the paper is cited properly in the Literature Survey.
    enrichment = enrich_paper_by_title(title)
    return {
        "paper_id": paper_id,
        "filename": file.filename,
        "title": title,
        "abstract": extracted.get("abstract", "")[:300],
        "authors": enrichment.get("authors", []),
        "year": enrichment.get("year"),
        "venue": enrichment.get("venue", ""),
        "doi": enrichment.get("doi"),
    }


@app.post("/api/upload-image")
async def upload_image(file: UploadFile = File(...)):
    """Upload image/diagram."""
    allowed = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed:
        raise HTTPException(400, f"Image format {ext} not supported.")
    img_id = str(uuid.uuid4())
    save_path = os.path.join(IMAGES_DIR, f"{img_id}{ext}")
    with open(save_path, "wb") as f:
        f.write(await file.read())
    return {"image_id": img_id, "filename": file.filename, "path": save_path}


@app.post("/api/upload-source")
async def upload_source(file: UploadFile = File(...)):
    """Upload factual project material used by AI; templates remain DOCX-only."""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in {".pdf", ".docx", ".pptx", ".txt", ".md"}:
        raise HTTPException(400, "Supporting files must be PDF, DOCX, PPTX, TXT, or Markdown.")
    source_id = str(uuid.uuid4())
    path = os.path.join(SOURCES_DIR, f"{source_id}{ext}")
    with open(path, "wb") as target:
        target.write(await file.read())
    text = extract_supporting_material(path)
    if not text:
        raise HTTPException(422, "No readable text could be extracted from this supporting file.")
    _source_store[source_id] = {"path": path, "filename": file.filename, "text": text}
    return {"source_id": source_id, "filename": file.filename, "characters_extracted": len(text)}


@app.post("/api/generate")
async def generate(request: Request):
    form = await request.form()
    
    doc_id = form.get("doc_id")
    mode = form.get("mode", "template")
    reference_notes = form.get("reference_notes", "")
    images_json = form.get("images_json", "[]")
    papers_json = form.get("papers_json", "[]")
    source_ids_json = form.get("source_ids_json", "[]")

    if not doc_id or doc_id not in _doc_store:
        raise HTTPException(404, "Document not found. Please re-upload.")

    doc_info = _doc_store[doc_id]
    doc_map = {k: v for k, v in doc_info.items() if k != "file_path"}
    source_path = doc_info["file_path"]

    user_inputs: Dict[str, Any] = {}
    for key, value in form.items():
        if key not in ["doc_id", "mode", "images_json", "papers_json", "source_ids_json"]:
            user_inputs[key] = str(value)

    topic = user_inputs.get("topic", "Preliminary Project Report").strip()

    # A reference report already contains institution values.  Preserve these
    # when the conversational UI has asked the user only to confirm them.
    detected = doc_info.get("detected_values", {})
    for key in ("academic_year", "college_name", "department_name"):
        if not user_inputs.get(key):
            values = detected.get(key, [])
            if values:
                user_inputs[key] = values[0]

    # Parse images
    try:
        images_raw = json.loads(images_json)
    except Exception:
        images_raw = []

    images = []
    for img in images_raw:
        img_id = img.get("image_id", "")
        img_path = os.path.join(IMAGES_DIR, img_id)
        found = None
        if os.path.exists(img_path):
            found = img_path
        else:
            for ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"]:
                candidate = img_path + ext
                if os.path.exists(candidate):
                    found = candidate
                    break
        if found:
            images.append({
                "path": found,
                "caption": img.get("caption", "Architecture Diagram"),
                "slot_key": img.get("slot_key", ""),
                "target_section": img.get("target_section", ""),
            })

    # Parse user uploaded research papers
    try:
        research_papers = json.loads(papers_json)
    except Exception:
        research_papers = []

    try:
        source_ids = json.loads(source_ids_json)
    except Exception:
        source_ids = []
    source_material = "\n\n".join(
        _source_store[source_id]["text"] for source_id in source_ids
        if source_id in _source_store
    )

    report_type = user_inputs.get("report_type", "project").lower()

    if report_type == "internship":
        sections_to_gen = [s for chap in STANDARD_INTERNSHIP_CHAPTERS for s in chap["subsections"]]
    elif report_type == "pbl":
        ref_headings = doc_info.get("headings", [])
        if ref_headings:
            # Format-identical path: keep the uploaded reference's own chapter
            # structure and edit that DOCX in place, so the cover, logos, headers,
            # footers and fonts are preserved exactly. Content is generated keyed
            # to the reference's real headings so every body block is replaced.
            sections_to_gen = list(ref_headings)
        else:
            # No usable structure detected: fall back to the clean standard outline.
            sections_to_gen = ["Abstract"] + pbl_section_list()
    else:
        sections = doc_info.get("headings", [])
        if not sections:
            sections = [
                "1.1 Introduction", "1.2 Literature Survey", "1.3 Project Undertaken",
                "2.1 Introduction", "2.2 System Requirement Specification (SRS)",
                "2.3 Project Process Modeling", "2.4 Cost & Efforts Estimates", "2.5 Project Scheduling",
                "3.1 Introduction", "3.2 IDEA matrix", "3.3 Mathematical Model", "3.4 Feasibility Analysis",
                "3.5 Architecture Diagram", "3.6 UML diagrams",
                "4.1 Introduction", "4.2 Unit Testing", "4.3 Integration Testing", "4.4 Acceptance Testing",
                "5.1 Conclusion", "5.2 Future Scope", "References"
            ]
        sections_to_gen = list(sections)
        if not any("abstract" in s.lower() for s in sections_to_gen):
            sections_to_gen.insert(0, "Abstract")

    # Literature Survey sources: user-uploaded papers take priority and are
    # enriched by real recent papers discovered from Semantic Scholar / CrossRef.
    merged_papers = list(research_papers)
    if report_type in ("pbl", "project"):
        try:
            auto_papers = find_recent_papers(topic=topic, notes=str(reference_notes), max_results=5)
        except Exception as exc:
            print(f"[main] Paper discovery failed: {exc}")
            auto_papers = []
        merged_papers = merge_papers(research_papers, auto_papers)

    try:
        ai_content = generate_content(
            topic=topic,
            sections=sections_to_gen,
            student_info=user_inputs,
            reference_notes=str(reference_notes),
            research_papers=merged_papers,
            source_material=source_material,
            target_words_per_section=350,
        )
    except Exception as e:
        raise HTTPException(500, f"Content generation failed: {str(e)}")

    report_id = str(uuid.uuid4())
    output_filename = f"{report_id}.docx"

    try:
        if report_type == "internship":
            out_path = generate_internship_docx(
                student_info=user_inputs,
                ai_sections=ai_content,
                images=images,
                output_filename=output_filename,
            )
        elif report_type == "pbl":
            if doc_info.get("headings"):
                # Edit the uploaded reference in place to keep its exact format.
                out_path = fill_template(
                    source_docx_path=source_path,
                    doc_map=doc_map,
                    student_info=user_inputs,
                    ai_sections=ai_content,
                    images=images,
                    output_filename=output_filename,
                )
            else:
                user_inputs["_reference_docx_path"] = source_path
                out_path = render_pbl_report(
                    student_info=user_inputs,
                    doc_map=doc_map,
                    ai_sections=ai_content,
                    images=images,
                    output_filename=output_filename,
                )
        elif mode == "template":
            out_path = fill_template(
                source_docx_path=source_path,
                doc_map=doc_map,
                student_info=user_inputs,
                ai_sections=ai_content,
                images=images,
                output_filename=output_filename,
            )
        else:
            out_path = swap_report(
                source_docx_path=source_path,
                doc_map=doc_map,
                student_info=user_inputs,
                ai_sections=ai_content,
                images=images,
                output_filename=output_filename,
            )
    except Exception as e:
        raise HTTPException(500, f"Document generation failed: {str(e)}")

    _report_store[report_id] = {
        "docx_path":    out_path,
        "student_info": user_inputs,
        "ai_content":   ai_content,
        "sections":     sections_to_gen,
        "topic":        topic,
        "mode":         mode,
        "report_type":  report_type,
    }
    _save_report_store()

    return {
        "report_id": report_id,
        "sections": list(ai_content.keys()),
        "topic": topic,
        "mode": mode,
        "report_type": report_type,
    }


@app.get("/api/preview/{report_id}", response_class=HTMLResponse)
def preview(report_id: str):
    if report_id not in _report_store:
        raise HTTPException(404, "Report not found.")

    data = _report_store[report_id]
    html_content = render_report_html(data.get("docx_path", ""), data)
    return HTMLResponse(content=html_content)



from core.gemini_engine import generate_content, edit_section_with_ai, GEMINI_MODEL


@app.get("/api/report/{report_id}")
def get_report(report_id: str):
    if report_id not in _report_store:
        raise HTTPException(404, "Report not found.")
    data = _report_store[report_id]
    return {
        "report_id": report_id,
        "topic": data.get("topic", ""),
        "student_info": data.get("student_info", {}),
        "ai_content": data.get("ai_content", {}),
        "sections": data.get("sections", []),
        "mode": data.get("mode", "template"),
        "report_type": data.get("report_type", "pbl"),
        "docx_path": data.get("docx_path", ""),
    }


@app.post("/api/chat-edit")
async def chat_edit(request: Request):
    """Interactive AI chat endpoint for editing, refining, or asking questions about the report."""
    body = await request.json()
    report_id = body.get("report_id", "")
    message = body.get("message", "").strip()
    section_name = body.get("section_name")
    selected_text = body.get("selected_text", "").strip()
    current_content = body.get("current_content", "").strip()

    if not message:
        raise HTTPException(400, "Message cannot be empty.")

    report_data = _report_store.get(report_id, {})
    topic = report_data.get("topic", "Engineering Project Report")
    
    if not current_content and report_id and section_name:
        current_content = report_data.get("ai_content", {}).get(section_name, "")

    result = edit_section_with_ai(
        topic=topic,
        message=message,
        section_name=section_name,
        current_content=current_content,
        selected_text=selected_text,
    )

    # If updated content was produced, auto-update the store
    if report_id in _report_store and result.get("updated_content") and result.get("target_section"):
        sec = result["target_section"]
        _report_store[report_id]["ai_content"][sec] = result["updated_content"]
        _save_report_store()

    return {
        "reply": result.get("reply", "Response processed."),
        "updated_content": result.get("updated_content"),
        "target_section": result.get("target_section", section_name),
        "report_id": report_id,
    }


@app.post("/api/extension/transform-selection")
async def extension_transform_selection(request: Request):
    """Transform or expand selected text in Google Docs according to academic PBL requirements."""
    body = await request.json()
    topic = body.get("topic", "").strip() or "Engineering Project Report"
    action = body.get("action", "rewrite_for_topic")
    selected_text = body.get("selected_text", "").strip()
    section_name = body.get("section_name", "Academic Section")
    notes = body.get("notes", "").strip()

    if action == "expand":
        instruction = f"Expand this section with deep technical details, specifications, and academic rigor for the topic '{topic}'."
    elif action == "formalize":
        instruction = f"Rewrite this text in formal academic style conforming to university engineering guidelines for '{topic}'."
    elif action == "test_cases":
        instruction = f"Generate a structured Unit/Integration Test Case Table for '{topic}'."
    elif action == "math_model":
        instruction = f"Formulate a Set Theory Mathematical Model S = {{I, A, P, R, O}} for '{topic}'."
    elif action == "citations":
        instruction = f"Generate verified IEEE citations and literature references for '{topic}'."
    elif action == "rewrite_for_topic":
        instruction = f"Adapt and rewrite this entire section specifically for the project topic '{topic}' based on the notes: '{notes}'. Ensure all old names/hardware are completely replaced."
    else:
        instruction = f"Refine this section for '{topic}': {action}"

    result = edit_section_with_ai(
        topic=topic,
        message=instruction,
        section_name=section_name,
        current_content=selected_text,
        selected_text=selected_text,
        reference_notes=notes,
    )

    return {
        "action": action,
        "topic": topic,
        "transformed_text": result.get("updated_content") or result.get("reply"),
        "reply": result.get("reply"),
    }


@app.post("/api/extension/generate-section")
async def extension_generate_section(request: Request):
    """Generate a full specific chapter or subsection for the Chrome extension."""
    body = await request.json()
    topic = body.get("topic", "").strip() or "Engineering Project Report"
    section_name = body.get("section_name", "1.1 Introduction").strip()
    notes = body.get("notes", "").strip()
    student_info = body.get("student_info", {})

    content_dict = generate_content(
        topic=topic,
        sections=[section_name],
        student_info=student_info,
        reference_notes=notes,
        research_papers=[],
        source_material="",
        target_words_per_section=300,
    )

    return {
        "topic": topic,
        "section_name": section_name,
        "content": content_dict.get(section_name, ""),
    }


@app.post("/api/extension/generate-all-sections")
async def extension_generate_all_sections(request: Request):
    """Generate the entire 6-chapter PBL report payload for Google Docs."""
    body = await request.json()
    topic = body.get("topic", "").strip() or "Engineering Project Report"
    notes = body.get("notes", "").strip()
    student_info = body.get("student_info", {})

    pbl_headings = [
        "1.1 Introduction",
        "1.2 Problem Statement",
        "1.3 Motivation and Scope",
        "1.4 Methodology",
        "1.5 System Architecture",
        "1.6 Objectives",
        "1.7 Scope",
        "2.1 Literature Survey",
        "3.1 Overview of the Proposed System",
        "3.2 Hardware and Software Specification",
        "3.3 Implementation Details",
        "3.4 Design and Analysis",
        "3.4.1 Core Code & Processing Pipeline",
        "4.1 How it Works",
        "4.2 Result and Discussion",
        "4.3 Comparative Evaluation",
        "4.4 Purpose and Significance",
        "5.1 Conclusion",
        "5.2 Future Scope",
        "6.1 References",
    ]

    content_dict = generate_content(
        topic=topic,
        sections=pbl_headings,
        student_info=student_info,
        reference_notes=notes,
        research_papers=[],
        source_material="",
        target_words_per_section=250,
    )

    return {
        "topic": topic,
        "sections": content_dict,
        "total_sections": len(content_dict),
    }


@app.post("/api/save-report/{report_id}")
async def save_report(report_id: str, request: Request):
    """Save user edits from the online doc editor and regenerate the DOCX file."""
    if report_id not in _report_store:
        raise HTTPException(404, "Report not found.")
    
    body = await request.json()
    updated_content = body.get("ai_content")
    if updated_content and isinstance(updated_content, dict):
        _report_store[report_id]["ai_content"].update(updated_content)

    data = _report_store[report_id]
    user_inputs = data.get("student_info", {})
    ai_content = data.get("ai_content", {})
    mode = data.get("mode", "template")
    report_type = data.get("report_type", "pbl")
    
    # Regenerate docx with the saved edits
    out_path = data.get("docx_path", "")
    output_filename = os.path.basename(out_path) if out_path else f"{report_id}.docx"
    
    doc_id = user_inputs.get("doc_id")
    source_path = _doc_store.get(doc_id, {}).get("file_path") if doc_id else None
    doc_map = {k: v for k, v in _doc_store.get(doc_id, {}).items() if k != "file_path"} if doc_id else {}

    try:
        if source_path and os.path.exists(source_path):
            new_path = fill_template(
                source_docx_path=source_path,
                doc_map=doc_map,
                student_info=user_inputs,
                ai_sections=ai_content,
                images=[],
                output_filename=output_filename,
            )
            _report_store[report_id]["docx_path"] = new_path
        _save_report_store()
    except Exception as e:
        print(f"[save_report] Error regenerating docx: {e}")

    return {"status": "ok", "message": "Report saved and document updated.", "report_id": report_id}


@app.get("/api/download-docx/{report_id}")
def download_docx(report_id: str):
    if report_id not in _report_store:
        raise HTTPException(404, "Report not found.")
    data = _report_store[report_id]
    docx_path = data["docx_path"]
    if not os.path.exists(docx_path):
        raise HTTPException(404, "DOCX file missing.")

    topic_safe = "".join(c for c in data["topic"] if c.isalnum() or c in " _-")[:30]
    dl_name = f"Report_{topic_safe}.docx".replace(" ", "_")

    return FileResponse(
        path=docx_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=dl_name,
    )


@app.get("/api/download-pdf/{report_id}")
def download_pdf(report_id: str):
    if report_id not in _report_store:
        raise HTTPException(404, "Report not found.")
    data = _report_store[report_id]
    docx_path = data["docx_path"]

    pdf_path = convert_docx_to_pdf(docx_path)
    if not pdf_path or not os.path.exists(pdf_path):
        raise HTTPException(
            503,
            "PDF conversion unavailable. Please install LibreOffice or docx2pdf."
        )

    topic_safe = "".join(c for c in data["topic"] if c.isalnum() or c in " _-")[:30]
    dl_name = f"Report_{topic_safe}.pdf".replace(" ", "_")

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=dl_name,
    )

