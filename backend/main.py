import os
import shutil
import json
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from docxtpl import DocxTemplate
import subprocess
from models.analysis import SampleDocumentAnalysis, ContentGenerationRequest, GeneratedReportResponse
from smart_report_generator import SmartReportGenerator

app = FastAPI(title="Auto Report Generator")

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "http://localhost:3000", "http://127.0.0.1:3000"],
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

# Initialize smart report generator
generator = SmartReportGenerator(BASE_DIR)

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

# New endpoints for smart content generation

@app.post("/analyze-sample")
async def analyze_sample_document(
    sample_file: UploadFile = File(...)
):
    """Analyze a sample document and return formatting information"""
    try:
        # Save uploaded file
        sample_path = os.path.join(UPLOADS_DIR, f"sample_{sample_file.filename}")
        with open(sample_path, "wb") as buffer:
            shutil.copyfileobj(sample_file.file, buffer)
        
        # Analyze document
        analysis = generator.analyze_sample_document(sample_path, sample_file.filename)
        
        # Convert datetime objects to strings for JSON serialization
        analysis_dict = analysis.dict()
        if 'upload_timestamp' in analysis_dict and hasattr(analysis_dict['upload_timestamp'], 'isoformat'):
            analysis_dict['upload_timestamp'] = analysis_dict['upload_timestamp'].isoformat()
        
        return JSONResponse(content=analysis_dict)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.post("/generate-smart-report")
async def generate_smart_report(
    document_id: str = Form(...),
    student_name: str = Form(...),
    roll_no: str = Form(...),
    topic: str = Form(...),
    college_name: str = Form("Sinhgad College of Engineering, Pune"),
    department: str = Form("Computer Engineering"),
    introduction: str = Form(""),
    objectives: str = Form(""),
    methodology: str = Form(""),
    result: str = Form(""),
    conclusion: str = Form(""),
    references: str = Form(""),
    images_json: str = Form("[]"),
    convert_to_pdf: bool = Form(False),
    content_style: str = Form("academic")
):
    """Generate a smart report based on sample document analysis"""
    try:
        # Parse images JSON
        images_data = json.loads(images_json) if images_json else []
        
        # Create content generation request
        request = ContentGenerationRequest(
            document_id=document_id,
            student_name=student_name,
            roll_no=roll_no,
            topic=topic,
            college_name=college_name,
            department=department,
            introduction=introduction,
            objectives=objectives,
            methodology=methodology,
            result=result,
            conclusion=conclusion,
            references=references,
            images_with_captions=images_data,
            convert_to_pdf=convert_to_pdf,
            content_style=content_style
        )
        
        # In a real implementation, retrieve actual analysis from storage
        # For now, create a basic analysis structure
        import datetime
        sample_analysis = SampleDocumentAnalysis(
            document_id=document_id,
            original_filename="sample.docx",
            file_size=1024,
            upload_timestamp=datetime.datetime.now(),
            font_styles={},
            paragraph_styles={},
            section_structure=[],
            header_footer_info={},
            page_setup={},
            identified_placeholders=[],
            content_sections=["Introduction", "Objectives", "Methodology", "Results", "Conclusion", "References"],
            formatting_preservation_score=95.0,
            is_valid_template=True,
            template_compatibility="high",
            recommended_placeholders=[]
        )
        
        # Generate smart report
        response = await generator.generate_smart_report(request, sample_analysis)
        
        if response.success:
            file_path = os.path.join(OUTPUTS_DIR, response.filename)
            return FileResponse(
                file_path, 
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document" if response.filename.endswith('.docx') else "application/pdf",
                filename=response.filename
            )
        else:
            raise HTTPException(status_code=500, detail=response.message)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Smart report generation failed: {str(e)}")

@app.post("/upload-images")
async def upload_images(
    images: List[UploadFile] = File(...)
):
    """Upload images for report generation"""
    try:
        uploaded_images = []
        images_dir = os.path.join(UPLOADS_DIR, "images")
        os.makedirs(images_dir, exist_ok=True)
        
        for image in images:
            # Save image
            image_path = os.path.join(images_dir, image.filename)
            with open(image_path, "wb") as buffer:
                shutil.copyfileobj(image.file, buffer)
            
            uploaded_images.append({
                "filename": image.filename,
                "file_size": os.path.getsize(image_path)
            })
        
        return JSONResponse(content={"uploaded_images": uploaded_images})
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image upload failed: {str(e)}")

@app.post("/configure-gemini")
async def configure_gemini(api_key: str = Form(...)):
    """Configure Google Gemini API integration"""
    try:
        # Update configuration
        from config.gemini_config import gemini_config
        gemini_config.api_key = api_key
        
        # Reinitialize generator
        from utils.gemini_client import GeminiContentGenerator
        global gemini_generator
        gemini_generator = GeminiContentGenerator()
        
        # Update enhanced generator
        from enhanced_content_generator import EnhancedContentGenerator
        global enhanced_generator
        enhanced_generator = EnhancedContentGenerator()
        
        return JSONResponse(content={
            "status": "success",
            "message": "Gemini API configured successfully",
            "api_key_set": bool(api_key and api_key != "YOUR_API_KEY_HERE")
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Configuration failed: {str(e)}")

@app.get("/gemini-status")
async def get_gemini_status():
    """Get current Gemini API status"""
    try:
        from utils.gemini_client import gemini_generator
        from config.gemini_config import gemini_config
        from enhanced_content_generator import enhanced_generator
        
        status = await gemini_generator.test_connection()
        generation_status = enhanced_generator.get_generation_status()
        
        return JSONResponse(content={
            "api_status": status,
            "generation_status": generation_status,
            "configured": gemini_config.is_configured()
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
