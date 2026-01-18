import os
import shutil
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from docxtpl import DocxTemplate
import subprocess

app = FastAPI(title="Auto Report Generator")

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")

# Ensure directories exist
for d in [TEMPLATES_DIR, UPLOADS_DIR, OUTPUTS_DIR]:
    os.makedirs(d, exist_ok=True)

@app.post("/generate-report")
async def generate_report(
    student_name: str = Form(...),
    roll_no: str = Form(...),
    topic: str = Form(...),
    college_name: str = Form("Sinhgad College of Engineering, Pune"),
    department: str = Form("Computer Engineering"),
    introduction: str = Form(...),
    objectives: str = Form(""),
    methodology: str = Form(""),
    result: str = Form(""),
    conclusion: str = Form(""),
    references: str = Form(""),
    template_file: Optional[UploadFile] = File(None),
    convertToPdf: bool = Form(False)
):
    # Determine which template to use
    if template_file:
        template_path = os.path.join(UPLOADS_DIR, template_file.filename)
        with open(template_path, "wb") as buffer:
            shutil.copyfileobj(template_file.file, buffer)
    else:
        template_path = os.path.join(TEMPLATES_DIR, "default_template.docx")
        if not os.path.exists(template_path):
            raise HTTPException(status_code=404, detail="Default template not found.")

    try:
        doc = DocxTemplate(template_path)
        
        context = {
            'STUDENT_NAME': student_name,
            'ROLL_NO': roll_no,
            'TOPIC': topic,
            'COLLEGE_NAME': college_name,
            'DEPARTMENT': department,
            'INTRODUCTION': introduction,
            'OBJECTIVES': objectives,
            'METHODOLOGY': methodology,
            'RESULT': result,
            'CONCLUSION': conclusion,
            'REFERENCES': references
        }
        
        doc.render(context)
        
        output_filename = f"Report_{student_name.replace(' ', '_')}_{roll_no}.docx"
        output_path = os.path.join(OUTPUTS_DIR, output_filename)
        doc.save(output_path)

        if convertToPdf:
            # Attempt PDF conversion using LibreOffice (soffice)
            try:
                subprocess.run([
                    "soffice", "--headless", "--convert-to", "pdf", 
                    "--outdir", OUTPUTS_DIR, output_path
                ], check=True)
                pdf_filename = output_filename.replace(".docx", ".pdf")
                pdf_path = os.path.join(OUTPUTS_DIR, pdf_filename)
                return FileResponse(pdf_path, media_type="application/pdf", filename=pdf_filename)
            except Exception as e:
                # Fallback to DOCX if PDF conversion fails
                print(f"PDF conversion failed: {e}")
                return FileResponse(output_path, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", filename=output_filename)

        return FileResponse(output_path, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", filename=output_filename)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
