import asyncio
from typing import Dict, List, Optional
from utils.gemini_client import gemini_generator
from models.content import GeneratedContent, ContentSection, TopicAnalysis
from config.gemini_config import gemini_config

class EnhancedContentGenerator:
    """Enhanced content generator with Gemini as primary engine and rule-based fallback"""
    
    def __init__(self):
        self.gemini_available = gemini_generator.is_available()
        self.rule_based_generator = self._initialize_rule_based_generator()
        print(f"Gemini API Status: {'✅ Available' if self.gemini_available else '❌ Unavailable (using fallback)'}")
    
    def _initialize_rule_based_generator(self):
        """Initialize the original rule-based generator as fallback"""
        try:
            from content_generator import ContentGenerator
            return ContentGenerator()
        except ImportError:
            return None
    
    async def generate_content(self, topic: str, template_structure: List[str], 
                             style: str = "academic", context: Dict = None) -> GeneratedContent:
        """
        Generate content using Gemini as primary with rule-based fallback
        
        Args:
            topic: Report topic
            template_structure: List of sections
            style: Content style
            context: Additional context (student info, etc.)
            
        Returns:
            GeneratedContent object
        """
        if context is None:
            context = {}
        
        # Try Gemini first if available
        if self.gemini_available:
            try:
                return await self._generate_with_gemini(topic, template_structure, style, context)
            except Exception as e:
                print(f"⚠️  Gemini generation failed: {e}")
                print("🔄 Falling back to rule-based generation...")
        
        # Fallback to rule-based generation
        return self._generate_rule_based(topic, template_structure, style, context)
    
    async def _generate_with_gemini(self, topic: str, template_structure: List[str], 
                                  style: str, context: Dict) -> GeneratedContent:
        """Generate content using Gemini API"""
        print("🤖 Generating content with Google Gemini...")
        
        topic_analysis = self._analyze_topic(topic)
        sections = {}
        total_word_count = 0
        
        # Generate each section with Gemini
        for section_name in template_structure:
            print(f"  📝 Generating {section_name}...")
            
            section_content = await gemini_generator.generate_section_content(
                section=section_name,
                topic=topic,
                domain=topic_analysis.domain,
                context={
                    **context,
                    'word_count': self._get_section_word_count(section_name, topic_analysis.complexity_level),
                    'student_name': context.get('student_name', 'Student'),
                    'college_name': context.get('college_name', 'University'),
                    'department': context.get('department', 'Department')
                }
            )
            
            # Create content section
            content_section = ContentSection(
                section_name=section_name,
                content=section_content,
                word_count=len(section_content.split()),
                key_points=self._extract_key_points(section_content),
                academic_keywords=self._extract_academic_keywords(section_content, topic_analysis.domain)
            )
            
            sections[section_name.lower().replace(' ', '_')] = content_section
            total_word_count += content_section.word_count
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.1)
        
        return GeneratedContent(
            topic=topic,
            sections=sections,
            overall_word_count=total_word_count,
            academic_level=topic_analysis.complexity_level,
            content_quality_score=self._calculate_gemini_quality_score(sections)
        )
    
    def _generate_rule_based(self, topic: str, template_structure: List[str], 
                           style: str, context: Dict) -> GeneratedContent:
        """Fallback to original rule-based generation"""
        print("📋 Generating content with rule-based engine...")
        
        if self.rule_based_generator:
            return self.rule_based_generator.generate_content(topic, template_structure, style)
        else:
            # Create minimal fallback content
            return self._create_minimal_content(topic, template_structure)
    
    def _analyze_topic(self, topic: str) -> TopicAnalysis:
        """Analyze topic to determine domain and complexity (simplified version)"""
        topic_lower = topic.lower()
        
        # Domain detection
        domains = {
            "computer_science": ["algorithm", "programming", "software", "database", "ai", "machine learning", "web development"],
            "engineering": ["mechanical", "electrical", "civil", "chemical", "design", "manufacturing"],
            "business": ["marketing", "finance", "management", "economics", "entrepreneurship"],
            "science": ["biology", "chemistry", "physics", "mathematics", "research"],
        }
        
        domain = "general"
        for domain_name, keywords in domains.items():
            if any(keyword in topic_lower for keyword in keywords):
                domain = domain_name
                break
        
        # Complexity level
        word_count = len(topic.split())
        technical_indicators = len([w for w in ["algorithm", "methodology", "implementation", "analysis", "framework"] if w in topic_lower])
        
        if word_count > 10 or technical_indicators > 2:
            complexity = "advanced"
        elif word_count > 5 or technical_indicators > 0:
            complexity = "intermediate"
        else:
            complexity = "basic"
        
        return TopicAnalysis(
            topic=topic,
            domain=domain,
            complexity_level=complexity,
            related_keywords=topic.split()[:5],
            suggested_sections=["Introduction", "Objectives", "Methodology", "Results", "Conclusion", "References"],
            content_length_recommendation="1500-2500 words"
        )
    
    def _get_section_word_count(self, section: str, complexity: str) -> int:
        """Determine appropriate word count for section"""
        base_counts = {
            "introduction": {"basic": 200, "intermediate": 300, "advanced": 400},
            "objectives": {"basic": 150, "intermediate": 200, "advanced": 250},
            "methodology": {"basic": 250, "intermediate": 350, "advanced": 500},
            "results": {"basic": 200, "intermediate": 300, "advanced": 400},
            "conclusion": {"basic": 150, "intermediate": 200, "advanced": 250},
            "references": {"basic": 100, "intermediate": 150, "advanced": 200}
        }
        
        section_key = section.lower().replace(' ', '_')
        return base_counts.get(section_key, {}).get(complexity, 250)
    
    def _extract_key_points(self, content: str) -> List[str]:
        """Extract key points from content"""
        sentences = content.split('. ')
        return [sent.strip() + '.' for sent in sentences[:3] if sent.strip()]
    
    def _extract_academic_keywords(self, content: str, domain: str) -> List[str]:
        """Extract academic keywords (simplified)"""
        domain_keywords = {
            "computer_science": ["algorithm", "system", "data", "implementation", "performance"],
            "engineering": ["design", "analysis", "testing", "specification", "validation"],
            "business": ["market", "strategy", "financial", "management", "operational"],
            "science": ["experiment", "hypothesis", "data", "analysis", "research"]
        }
        
        keywords = domain_keywords.get(domain, ["study", "analysis", "research", "findings"])
        content_lower = content.lower()
        return [kw for kw in keywords if kw in content_lower][:3]
    
    def _calculate_gemini_quality_score(self, sections: Dict) -> float:
        """Calculate quality score for Gemini-generated content"""
        if not sections:
            return 0.0
        
        total_words = sum(section.word_count for section in sections.values())
        avg_words = total_words / len(sections)
        
        # Score based on adequate content length (200-600 words per section ideal for Gemini)
        if 200 <= avg_words <= 600:
            length_score = 100.0
        elif avg_words > 600:
            length_score = 85.0
        else:
            length_score = (avg_words / 200) * 100
        
        # Score based on section completeness
        completeness_score = min(100.0, (len(sections) / 6) * 100)
        
        return (length_score * 0.7 + completeness_score * 0.3)
    
    def _create_minimal_content(self, topic: str, template_structure: List[str]) -> GeneratedContent:
        """Create minimal fallback content when no generators available"""
        sections = {}
        total_words = 0
        
        for section_name in template_structure:
            content = f"This is a placeholder {section_name.lower()} section for the topic: {topic}. In a complete implementation, this would contain detailed academic content generated by Google Gemini AI."
            word_count = len(content.split())
            
            sections[section_name.lower().replace(' ', '_')] = ContentSection(
                section_name=section_name,
                content=content,
                word_count=word_count,
                key_points=[f"Placeholder content for {section_name}"],
                academic_keywords=["placeholder", "content"]
            )
            total_words += word_count
        
        return GeneratedContent(
            topic=topic,
            sections=sections,
            overall_word_count=total_words,
            academic_level="basic",
            content_quality_score=30.0
        )
    
    def get_generation_status(self) -> Dict:
        """Get current generation engine status"""
        return {
            "gemini_available": self.gemini_available,
            "rule_based_available": self.rule_based_generator is not None,
            "primary_engine": "Gemini" if self.gemini_available else "Rule-based",
            "api_key_configured": gemini_config.is_configured(),
            "model_name": gemini_config.model_name if gemini_config.is_configured() else None
        }

# Global instance
enhanced_generator = EnhancedContentGenerator()