from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class SampleDocumentAnalysis(BaseModel):
    """Analysis results from a sample document"""
    document_id: str
    original_filename: str
    file_size: int
    upload_timestamp: datetime
    
    # Formatting information
    font_styles: Dict[str, Any]
    paragraph_styles: Dict[str, Any]
    section_structure: List[Dict[str, Any]]
    header_footer_info: Dict[str, Any]
    page_setup: Dict[str, Any]
    
    # Content structure
    identified_placeholders: List[str]
    content_sections: List[str]
    formatting_preservation_score: float
    
    # Template information
    is_valid_template: bool
    template_compatibility: str
    recommended_placeholders: List[str]

class ContentGenerationRequest(BaseModel):
    """Request for smart content generation"""
    document_id: str
    student_name: str
    roll_no: str
    topic: str
    college_name: str = "Sinhgad College of Engineering, Pune"
    department: str = "Computer Engineering"
    
    # Content sections
    introduction: Optional[str] = None
    objectives: Optional[str] = None
    methodology: Optional[str] = None
    result: Optional[str] = None
    conclusion: Optional[str] = None
    references: Optional[str] = None
    
    # Image information
    images_with_captions: List[Dict[str, str]] = []
    
    # Generation options
    preserve_formatting: bool = True
    generate_full_content: bool = True
    content_style: str = "academic"
    convert_to_pdf: bool = False

class GeneratedReportResponse(BaseModel):
    """Response for generated report"""
    report_id: str
    filename: str
    download_url: str
    file_size: int
    generation_time: float
    format_preserved: bool
    content_sections_generated: List[str]
    images_processed: int
    success: bool
    message: str

class ImageCaption(BaseModel):
    """Image with caption information"""
    filename: str
    caption: str
    content_relevance: str  # e.g., "introduction", "methodology", "results"
    placement_preference: str = "auto"  # auto, top, bottom, inline
    file_size: Optional[int] = None

class AnalysisProgress(BaseModel):
    """Progress tracking for document analysis"""
    step: str
    progress: int  # 0-100
    message: str
    completed: bool = False