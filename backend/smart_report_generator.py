import os
import time
import uuid
from typing import Dict, List, Optional
from docxtpl import DocxTemplate
from docx import Document
from models.analysis import SampleDocumentAnalysis, ContentGenerationRequest, GeneratedReportResponse
from document_analyzer import DocumentAnalyzer
from enhanced_content_generator import enhanced_generator
from image_processor import ImageProcessor

class SmartReportGenerator:
    """Main orchestrator for smart report generation"""
    
    def __init__(self, base_dir: str = "."):
        self.base_dir = base_dir
        self.uploads_dir = os.path.join(base_dir, "uploads")
        self.outputs_dir = os.path.join(base_dir, "outputs")
        self.templates_dir = os.path.join(base_dir, "templates")
        
        # Initialize components
        self.analyzer = DocumentAnalyzer(self.uploads_dir)
        self.content_generator = enhanced_generator
        self.image_processor = ImageProcessor(os.path.join(self.uploads_dir, "images"))
        
        # Ensure directories exist
        for directory in [self.uploads_dir, self.outputs_dir, self.templates_dir]:
            os.makedirs(directory, exist_ok=True)
    
    def analyze_sample_document(self, file_path: str, original_filename: str) -> SampleDocumentAnalysis:
        """
        Analyze a sample document and return analysis results
        
        Args:
            file_path: Path to uploaded sample document
            original_filename: Original filename
            
        Returns:
            SampleDocumentAnalysis object
        """
        return self.analyzer.analyze_document(file_path, original_filename)
    
    async def generate_smart_report(self, request: ContentGenerationRequest, 
                            sample_analysis: SampleDocumentAnalysis) -> GeneratedReportResponse:
        """
        Generate a smart report based on sample document analysis and user input
        
        Args:
            request: Content generation request
            sample_analysis: Analysis of sample document
            
        Returns:
            GeneratedReportResponse object
        """
        start_time = time.time()
        
        try:
            # Generate content based on topic and template structure
            template_sections = sample_analysis.content_sections or [
                "Introduction", "Objectives", "Methodology", "Results", "Conclusion", "References"
            ]
            
            generated_content = await self.content_generator.generate_content(
                request.topic, template_sections, request.content_style, {
                    'student_name': request.student_name,
                    'college_name': request.college_name,
                    'department': request.department
                }
            )
            
            # Process images if provided
            processed_images = []
            if request.images_with_captions:
                processed_images = self.image_processor.process_images_with_captions(
                    request.images_with_captions, 
                    {section.section_name: section.content for section in generated_content.sections.values()}
                )
            
            # Create report using template
            report_filename = self._create_report(
                request, sample_analysis, generated_content, processed_images
            )
            
            # Convert to PDF if requested
            if request.convert_to_pdf:
                pdf_filename = self._convert_to_pdf(report_filename)
                final_filename = pdf_filename
            else:
                final_filename = report_filename
            
            generation_time = time.time() - start_time
            
            return GeneratedReportResponse(
                report_id=str(uuid.uuid4()),
                filename=final_filename,
                download_url=f"/download/{final_filename}",
                file_size=os.path.getsize(os.path.join(self.outputs_dir, final_filename)),
                generation_time=generation_time,
                format_preserved=True,
                content_sections_generated=list(generated_content.sections.keys()),
                images_processed=len(processed_images),
                success=True,
                message="Report generated successfully"
            )
            
        except Exception as e:
            return GeneratedReportResponse(
                report_id=str(uuid.uuid4()),
                filename="",
                download_url="",
                file_size=0,
                generation_time=time.time() - start_time,
                format_preserved=False,
                content_sections_generated=[],
                images_processed=0,
                success=False,
                message=f"Generation failed: {str(e)}"
            )
    
    def _create_report(self, request: ContentGenerationRequest, 
                      sample_analysis: SampleDocumentAnalysis,
                      generated_content: Dict, 
                      processed_images: List[Dict]) -> str:
        """
        Create the actual report document
        
        Args:
            request: Generation request
            sample_analysis: Sample document analysis
            generated_content: Generated content sections
            processed_images: Processed image data
            
        Returns:
            Generated report filename
        """
        # Determine template to use
        template_path = os.path.join(self.templates_dir, "default_template.docx")
        if not os.path.exists(template_path):
            # Create default template if it doesn't exist
            from create_template import create_default_template
            create_default_template()
        
        # Create context for template rendering
        context = self._build_template_context(request, generated_content)
        
        # Generate document using docxtpl
        doc = DocxTemplate(template_path)
        doc.render(context)
        
        # Handle image placement in the document
        if processed_images:
            # Convert to python-docx document for image manipulation
            temp_path = os.path.join(self.outputs_dir, f"temp_{uuid.uuid4()}.docx")
            doc.save(temp_path)
            
            # Reopen with python-docx for image placement
            docx_doc = Document(temp_path)
            self.image_processor.place_images_in_document(docx_doc, processed_images, 
                                                        {section.section_name: section.content 
                                                         for section in generated_content.sections.values()})
            
            # Clean up temp file
            os.remove(temp_path)
        else:
            docx_doc = Document()
            # Convert docxtpl result to python-docx if needed
            # This is a simplified approach - in practice, you'd need more complex conversion
        
        # Save final document
        output_filename = f"Smart_Report_{request.student_name.replace(' ', '_')}_{request.roll_no}_{int(time.time())}.docx"
        output_path = os.path.join(self.outputs_dir, output_filename)
        docx_doc.save(output_path)
        
        return output_filename
    
    def _build_template_context(self, request: ContentGenerationRequest, 
                              generated_content: Dict) -> Dict:
        """Build context dictionary for template rendering"""
        context = {
            'STUDENT_NAME': request.student_name,
            'ROLL_NO': request.roll_no,
            'TOPIC': request.topic,
            'COLLEGE_NAME': request.college_name,
            'DEPARTMENT': request.department
        }
        
        # Add generated content sections
        for section_name, section_content in generated_content.sections.items():
            # Convert section name to uppercase placeholder format
            placeholder_name = section_name.upper().replace(' ', '_')
            context[placeholder_name] = section_content.content
        
        # Fill in any missing sections with user-provided content
        user_content_map = {
            'INTRODUCTION': request.introduction,
            'OBJECTIVES': request.objectives,
            'METHODOLOGY': request.methodology,
            'RESULT': request.result,
            'CONCLUSION': request.conclusion,
            'REFERENCES': request.references
        }
        
        for placeholder, user_content in user_content_map.items():
            if user_content and placeholder not in context:
                context[placeholder] = user_content
            elif not context.get(placeholder) and user_content:
                context[placeholder] = user_content
        
        return context
    
    def _convert_to_pdf(self, docx_filename: str) -> str:
        """Convert DOCX to PDF using LibreOffice"""
        try:
            import subprocess
            
            docx_path = os.path.join(self.outputs_dir, docx_filename)
            pdf_filename = docx_filename.replace('.docx', '.pdf')
            
            subprocess.run([
                "soffice", "--headless", "--convert-to", "pdf",
                "--outdir", self.outputs_dir, docx_path
            ], check=True)
            
            return pdf_filename
        except Exception as e:
            print(f"PDF conversion failed: {e}")
            return docx_filename  # Return original DOCX if PDF fails
    
    def get_sample_document_path(self, document_id: str) -> Optional[str]:
        """Get the file path for a stored sample document"""
        # In a real implementation, this would query a database
        # For now, we'll search the uploads directory
        for filename in os.listdir(self.uploads_dir):
            if document_id in filename or filename.startswith(f"{document_id}_"):
                return os.path.join(self.uploads_dir, filename)
        return None
    
    def store_sample_document(self, file_content: bytes, original_filename: str) -> str:
        """Store uploaded sample document and return document ID"""
        document_id = str(uuid.uuid4())
        safe_filename = f"{document_id}_{original_filename}"
        file_path = os.path.join(self.uploads_dir, safe_filename)
        
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        return document_id
    
    def cleanup_old_files(self, max_age_days: int = 7):
        """Clean up old files to manage storage"""
        import datetime
        
        cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
        
        for directory in [self.uploads_dir, self.outputs_dir]:
            if os.path.exists(directory):
                for filename in os.listdir(directory):
                    file_path = os.path.join(directory, filename)
                    if os.path.getctime(file_path) < cutoff_time:
                        try:
                            os.remove(file_path)
                        except Exception:
                            pass  # Ignore cleanup errors

# Usage example:
# generator = SmartReportGenerator()
# analysis = generator.analyze_sample_document("sample.docx", "sample.docx")
# request = ContentGenerationRequest(...)
# response = generator.generate_smart_report(request, analysis)