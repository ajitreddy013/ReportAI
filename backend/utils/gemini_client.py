try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    genai = None
    GENAI_AVAILABLE = False

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
        if not GENAI_AVAILABLE:
            print("⚠️  google-generativeai package not installed - using rule-based fallback")
            self.is_initialized = False
            return
            
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
                print("✅ Gemini API initialized successfully with model:", gemini_config.model_name)
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

    async def generate_full_report_structure(self, topic: str, format_type: str, 
                                            sections_list: List[str], context: Dict) -> Dict[str, str]:
        """Generate entire structured report in a single coherent Gemini call"""
        if not self.is_initialized:
            raise Exception("Gemini API not available")

        sections_formatted = "\n".join([f"- {s}" for s in sections_list])
        ref_context = context.get("reference_context", "")

        prompt = f"""You are an elite academic professor and technical researcher. 
Generate a comprehensive, professionally written academic report on the topic: "{topic}".

REPORT TYPE / FORMAT: {format_type}
STUDENT NAME: {context.get('student_name', 'Student')}
INSTITUTION: {context.get('college_name', 'University Department')}
DEPARTMENT: {context.get('department', 'Computer Science & Engineering')}

SECTIONS TO GENERATE:
{sections_formatted}

ADDITIONAL REFERENCE MATERIAL & SOURCE NOTES:
{ref_context if ref_context else "No extra reference notes provided. Synthesize complete state-of-the-art knowledge on this topic."}

CRITICAL INSTRUCTIONS:
1. Provide rich, detailed academic paragraphs for EACH section with deep technical depth, methodologies, algorithms/equations if applicable, analysis, and formal academic tone.
2. If reference material/links are provided above, explicitly cite, integrate, and synthesize their key points into the corresponding sections.
3. For References / Bibliography section, provide realistic standard IEEE / APA academic citations with authors, titles, journals/conferences, and years.
4. Output your response as valid JSON matching this format:
{{
  "sections": {{
    "Section Name": "Full detailed multi-paragraph content for this section...",
    ...
  }}
}}
Return ONLY the JSON object. Do not include markdown code block backticks if possible, or wrap strictly in ```json.
"""
        try:
            response_text = await asyncio.get_event_loop().run_in_executor(
                None, self._generate_content_sync, prompt
            )
            # Clean JSON
            cleaned = response_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            import json
            data = json.loads(cleaned)
            if "sections" in data and isinstance(data["sections"], dict):
                return data["sections"]
            return {s: "Content generated." for s in sections_list}
        except Exception as e:
            print(f"Full report generation JSON parse fallback: {e}")
            # Fallback to generating section by section
            results = {}
            for s in sections_list:
                try:
                    results[s] = await self.generate_section_content(s, topic, "Computer Science & Engineering", context)
                except Exception as inner_err:
                    results[s] = f"Error generating section {s}: {inner_err}"
            return results

    def _generate_content_sync(self, prompt: str) -> str:
        """Synchronous content generation (for async wrapper)"""
        response = self.model.generate_content(prompt)
        return response.text.strip()
    
    def _build_academic_prompt(self, section: str, topic: str, 
                              domain: str, context: Dict) -> str:
        """Build comprehensive academic prompt for Gemini"""
        base_prompt = f"""You are an expert academic writer specializing in {domain}. 
Generate high-quality, original academic content for a student report.

TOPIC: {topic}
SECTION: {section}
DOMAIN: {domain}

REQUIREMENTS:
- Write in formal academic English with proper paragraph structure.
- Include relevant technical terminology, theories, and methodologies for {domain}.
- Ensure content is plagiarism-free and original.
- Follow standard academic report conventions.
"""
        ref_context = context.get("reference_context", "")
        if ref_context:
            base_prompt += f"\nREFERENCE MATERIALS & NOTES TO INCORPORATE:\n{ref_context}\n"

        # Add section-specific guidance
        section_guidance = self._get_section_guidance(section, topic, domain)
        base_prompt += "\n" + section_guidance
        
        if context.get('student_name'):
            base_prompt += f"\nStudent Name: {context['student_name']}"
        if context.get('college_name'):
            base_prompt += f"\nInstitution: {context['college_name']}"
        if context.get('department'):
            base_prompt += f"\nDepartment: {context['department']}"
        
        word_count = context.get('word_count', 400)
        base_prompt += f"\n\nTarget length: approximately {word_count} words.\n\nGenerate the content now:"
        return base_prompt
    
    def _get_section_guidance(self, section: str, topic: str, domain: str) -> str:
        """Get section-specific writing guidance"""
        s = section.lower()
        if "intro" in s or "abstract" in s:
            return f"Write a comprehensive introduction for {topic}, establishing background, problem context, significance, and report overview."
        elif "literature" in s or "related" in s or "survey" in s:
            return f"Provide an in-depth literature review and state-of-the-art analysis comparing existing works and approaches for {topic}."
        elif "method" in s or "architecture" in s or "design" in s:
            return f"Describe the detailed architecture, system design, algorithm flow, and methodology for {topic}."
        elif "result" in s or "experiment" in s or "evaluation" in s or "implementation" in s:
            return f"Detail implementation details, experimental setup, key findings, metrics, and quantitative/qualitative analysis for {topic}."
        elif "conclusion" in s or "summary" in s or "future" in s:
            return f"Provide an insightful conclusion summarizing key contributions, limitations, and future research directions for {topic}."
        elif "ref" in s or "biblio" in s:
            return f"List standard academic IEEE / APA citations and references for {topic}."
        else:
            return f"Write a rigorous, detailed academic section '{section}' specifically focused on {topic}."

    def is_available(self) -> bool:
        """Check if Gemini API is available for content generation"""
        return self.is_initialized
    
    async def test_connection(self) -> Dict:
        """Test Gemini API connection and return status"""
        if not self.is_initialized:
            return {
                "status": "unavailable",
                "message": "API key not configured (using intelligent rule-based engine)",
                "model": None
            }
        
        try:
            test_prompt = "Respond with 'Connected' if you can read this."
            response = await asyncio.get_event_loop().run_in_executor(
                None, self._generate_content_sync, test_prompt
            )
            return {
                "status": "available",
                "message": "Gemini AI active",
                "model": gemini_config.model_name,
                "test_response": response[:60]
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Connection test failed: {str(e)}",
                "model": gemini_config.model_name
            }

# Global instance
gemini_generator = GeminiContentGenerator()