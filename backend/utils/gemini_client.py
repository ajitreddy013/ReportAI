import google.generativeai as genai
from typing import Dict, List, Optional
import asyncio
import time
from config.gemini_config import gemini_config

class GeminiContentGenerator:
    """Primary content generation engine using Google Gemini API"""
    
    def __init__(self):
        self.model = None
        self.is_initialized = False
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize Gemini model if API key is available"""
        if gemini_config.is_configured():
            try:
                genai.configure(api_key=gemini_config.api_key)
                self.model = genai.GenerativeModel(
                    gemini_config.model_name,
                    generation_config={
                        "temperature": gemini_config.temperature,
                        "max_output_tokens": gemini_config.max_tokens,
                        "top_p": gemini_config.top_p,
                        "top_k": gemini_config.top_k
                    },
                    safety_settings=gemini_config.get_safety_settings()
                )
                self.is_initialized = True
                print("✅ Gemini API initialized successfully")
            except Exception as e:
                print(f"❌ Failed to initialize Gemini API: {e}")
                self.is_initialized = False
        else:
            print("⚠️  Gemini API not configured - using rule-based fallback")
            self.is_initialized = False
    
    async def generate_section_content(self, section: str, topic: str, 
                                     domain: str, context: Dict) -> str:
        """Generate content for a specific section using Gemini"""
        if not self.is_initialized:
            raise Exception("Gemini API not available")
        
        try:
            prompt = self._build_academic_prompt(section, topic, domain, context)
            response = await asyncio.get_event_loop().run_in_executor(
                None, self._generate_content_sync, prompt
            )
            return response
        except Exception as e:
            raise Exception(f"Gemini content generation failed: {str(e)}")
    
    def _generate_content_sync(self, prompt: str) -> str:
        """Synchronous content generation (for async wrapper)"""
        response = self.model.generate_content(prompt)
        return response.text.strip()
    
    def _build_academic_prompt(self, section: str, topic: str, 
                              domain: str, context: Dict) -> str:
        """Build comprehensive academic prompt for Gemini"""
        
        base_prompt = f"""You are an expert academic writer specializing in {domain} fields. 
Generate high-quality, original academic content for a student report.

TOPIC: {topic}
SECTION: {section}
DOMAIN: {domain}

REQUIREMENTS:
- Write in formal academic English
- Maintain proper academic tone and structure
- Include relevant technical terminology for {domain}
- Ensure content is plagiarism-free and original
- Follow standard academic writing conventions
- Keep content focused and well-organized

"""
        
        # Add section-specific guidance
        section_guidance = self._get_section_guidance(section, domain)
        base_prompt += section_guidance
        
        # Add context information
        if context.get('student_name'):
            base_prompt += f"\nStudent Name: {context['student_name']}"
        if context.get('college_name'):
            base_prompt += f"\nInstitution: {context['college_name']}"
        if context.get('department'):
            base_prompt += f"\nDepartment: {context['department']}"
        
        # Add length guidance
        word_count = context.get('word_count', 300)
        base_prompt += f"\n\nTarget length: approximately {word_count} words"
        
        base_prompt += "\n\nGenerate the content now:"
        
        return base_prompt
    
    def _get_section_guidance(self, section: str, domain: str) -> str:
        """Get section-specific writing guidance"""
        guidance_map = {
            "introduction": f"""Write an engaging introduction that:
- Provides context for {topic} in {domain}
- States the importance and relevance of this topic
- Outlines what the report will cover
- Includes a clear thesis or purpose statement
- Uses {domain}-appropriate terminology""",
            
            "objectives": f"""List 4-6 specific, measurable objectives that:
- Are directly related to {topic}
- Use action verbs (analyze, evaluate, demonstrate, etc.)
- Are achievable within the report scope
- Follow SMART criteria (Specific, Measurable, Achievable, Relevant, Time-bound)
- Reflect {domain} standards and practices""",
            
            "methodology": f"""Describe the research/approach methodology:
- Explain the research design or approach
- Detail methods, tools, and procedures
- Justify methodology choices for {domain}
- Include technical specifications relevant to {topic}
- Address limitations and considerations""",
            
            "results": f"""Present findings and analysis:
- Report key findings related to {topic}
- Use {domain}-appropriate data presentation
- Include relevant metrics and measurements
- Analyze patterns and significance
- Connect findings to methodology""",
            
            "conclusion": f"""Provide comprehensive conclusion that:
- Summarizes key findings about {topic}
- Discusses implications for {domain}
- Identifies limitations and future research
- Makes recommendations based on findings
- Emphasizes the significance of the work""",
            
            "references": f"""List academic sources in appropriate format:
- Include relevant {domain} literature
- Use proper citation style
- Ensure sources are credible and recent
- Cover theoretical and practical aspects
- Include diverse source types"""
        }
        
        return guidance_map.get(section.lower(), 
                               f"Write a comprehensive {section} section about {topic} in {domain} field.")
    
    def is_available(self) -> bool:
        """Check if Gemini API is available for content generation"""
        return self.is_initialized
    
    async def test_connection(self) -> Dict:
        """Test Gemini API connection and return status"""
        if not self.is_initialized:
            return {
                "status": "unavailable",
                "message": "API key not configured",
                "model": None
            }
        
        try:
            # Simple test prompt
            test_prompt = "Write one sentence about academic writing."
            response = await self.generate_section_content(
                "test", "academic writing", "general", {"word_count": 20}
            )
            
            return {
                "status": "available",
                "message": "Gemini API connected successfully",
                "model": gemini_config.model_name,
                "test_response": response[:100] + "..." if len(response) > 100 else response
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Connection test failed: {str(e)}",
                "model": gemini_config.model_name
            }

# Global instance
gemini_generator = GeminiContentGenerator()