from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class ContentSection(BaseModel):
    """Individual content section"""
    section_name: str
    content: str
    word_count: int
    key_points: List[str]
    academic_keywords: List[str]

class GeneratedContent(BaseModel):
    """Complete generated content for a report"""
    topic: str
    sections: Dict[str, ContentSection]
    overall_word_count: int
    academic_level: str
    content_quality_score: float

class ContentStyleTemplate(BaseModel):
    """Template for content generation style"""
    style_name: str
    tone: str  # formal, semi-formal, technical
    complexity_level: str  # basic, intermediate, advanced
    section_templates: Dict[str, str]
    academic_phrases: List[str]
    transition_words: List[str]

class TopicAnalysis(BaseModel):
    """Analysis of the input topic"""
    topic: str
    domain: str
    complexity_level: str
    related_keywords: List[str]
    suggested_sections: List[str]
    content_length_recommendation: str