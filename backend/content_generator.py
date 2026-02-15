import re
import sys
import os
sys.path.append(os.path.dirname(__file__))
from typing import Dict, List, Optional
from models.content import GeneratedContent, ContentSection, ContentStyleTemplate, TopicAnalysis

class ContentGenerator:
    """Generates academic content based on topic and template structure"""
    
    def __init__(self):
        self.style_templates = self._initialize_style_templates()
        self.academic_keywords = self._initialize_academic_keywords()
        self.transition_phrases = self._initialize_transition_phrases()
    
    def generate_content(self, topic: str, template_structure: List[str], 
                        style: str = "academic") -> GeneratedContent:
        """
        Generate complete content for a report based on topic and template structure
        
        Args:
            topic: The main topic of the report
            template_structure: List of sections from the template
            style: Content style (academic, technical, formal)
            
        Returns:
            GeneratedContent object with all sections
        """
        topic_analysis = self._analyze_topic(topic)
        style_template = self.style_templates.get(style, self.style_templates["academic"])
        
        sections = {}
        total_word_count = 0
        
        # Generate content for each section
        for section_name in template_structure:
            section_content = self._generate_section_content(
                section_name, topic, topic_analysis, style_template
            )
            sections[section_name.lower().replace(' ', '_')] = section_content
            total_word_count += section_content.word_count
        
        return GeneratedContent(
            topic=topic,
            sections=sections,
            overall_word_count=total_word_count,
            academic_level=topic_analysis.complexity_level,
            content_quality_score=self._calculate_quality_score(sections)
        )
    
    def _analyze_topic(self, topic: str) -> TopicAnalysis:
        """Analyze the topic to determine domain and complexity"""
        topic_lower = topic.lower()
        
        # Domain detection
        domains = {
            "computer_science": ["algorithm", "programming", "software", "database", "ai", "machine learning", "web development"],
            "engineering": ["mechanical", "electrical", "civil", "chemical", "design", "manufacturing"],
            "business": ["marketing", "finance", "management", "economics", "entrepreneurship"],
            "science": ["biology", "chemistry", "physics", "mathematics", "research"],
            "general": []  # fallback
        }
        
        domain = "general"
        for domain_name, keywords in domains.items():
            if any(keyword in topic_lower for keyword in keywords):
                domain = domain_name
                break
        
        # Complexity level based on topic length and technical terms
        word_count = len(topic.split())
        technical_indicators = len(re.findall(r'\b(?:algorithm|methodology|implementation|analysis|framework)\b', topic_lower))
        
        if word_count > 10 or technical_indicators > 2:
            complexity = "advanced"
        elif word_count > 5 or technical_indicators > 0:
            complexity = "intermediate"
        else:
            complexity = "basic"
        
        # Generate related keywords
        base_keywords = topic.split()
        related_keywords = self._expand_keywords(base_keywords, domain)
        
        # Suggest sections based on topic
        suggested_sections = self._suggest_sections(topic_lower, domain)
        
        return TopicAnalysis(
            topic=topic,
            domain=domain,
            complexity_level=complexity,
            related_keywords=related_keywords,
            suggested_sections=suggested_sections,
            content_length_recommendation=self._recommend_content_length(complexity)
        )
    
    def _generate_section_content(self, section_name: str, topic: str, 
                                topic_analysis: TopicAnalysis, 
                                style_template: ContentStyleTemplate) -> ContentSection:
        """Generate content for a specific section"""
        
        section_name_lower = section_name.lower()
        
        if "intro" in section_name_lower:
            content = self._generate_introduction(topic, topic_analysis, style_template)
        elif "object" in section_name_lower:
            content = self._generate_objectives(topic, topic_analysis, style_template)
        elif "method" in section_name_lower:
            content = self._generate_methodology(topic, topic_analysis, style_template)
        elif "result" in section_name_lower:
            content = self._generate_results(topic, topic_analysis, style_template)
        elif "concl" in section_name_lower:
            content = self._generate_conclusion(topic, topic_analysis, style_template)
        elif "refer" in section_name_lower:
            content = self._generate_references(topic, topic_analysis, style_template)
        else:
            content = self._generate_generic_section(section_name, topic, topic_analysis, style_template)
        
        # Extract key points and keywords
        key_points = self._extract_key_points(content)
        academic_keywords = self._extract_academic_keywords(content, topic_analysis.domain)
        
        return ContentSection(
            section_name=section_name,
            content=content,
            word_count=len(content.split()),
            key_points=key_points,
            academic_keywords=academic_keywords
        )
    
    def _generate_introduction(self, topic: str, analysis: TopicAnalysis, template: ContentStyleTemplate) -> str:
        """Generate introduction content"""
        domain_intro = {
            "computer_science": "In the rapidly evolving field of computer science",
            "engineering": "Modern engineering practices continue to advance",
            "business": "Contemporary business environments require",
            "science": "Scientific research in this area has shown",
            "general": "This study focuses on"
        }
        
        intro_template = template.section_templates.get("introduction", 
            "{domain_intro}, {topic} represents a significant area of study. " +
            "This report examines various aspects of {topic_lower} and provides " +
            "comprehensive analysis of current developments and future prospects."
        )
        
        content = intro_template.format(
            domain_intro=domain_intro.get(analysis.domain, domain_intro["general"]),
            topic=topic,
            topic_lower=topic.lower()
        )
        
        # Add academic phrases
        if template.academic_phrases:
            content += f" {template.academic_phrases[0]} {topic.lower()} has gained considerable attention "
            content += "in recent academic literature."
        
        return content
    
    def _generate_objectives(self, topic: str, analysis: TopicAnalysis, template: ContentStyleTemplate) -> str:
        """Generate objectives content"""
        objectives = [
            f"To analyze and understand the fundamental concepts of {topic.lower()}",
            f"To examine current practices and methodologies in {topic.lower()}",
            f"To identify key challenges and opportunities in {topic.lower()}",
            f"To provide recommendations for future development in {topic.lower()}"
        ]
        
        if analysis.complexity_level == "advanced":
            objectives.extend([
                f"To evaluate advanced theoretical frameworks related to {topic.lower()}",
                f"To propose innovative solutions for complex problems in {topic.lower()}"
            ])
        
        content = "The primary objectives of this study are:\n\n"
        for i, obj in enumerate(objectives, 1):
            content += f"{i}. {obj}\n"
        
        return content.strip()
    
    def _generate_methodology(self, topic: str, analysis: TopicAnalysis, template: ContentStyleTemplate) -> str:
        """Generate methodology content"""
        methodologies = {
            "computer_science": ["literature review", "algorithm analysis", "experimental evaluation", "case studies"],
            "engineering": ["design analysis", "testing procedures", "simulation modeling", "experimental validation"],
            "business": ["market research", "data analysis", "case study methodology", "statistical evaluation"],
            "science": ["experimental research", "data collection", "statistical analysis", "literature synthesis"],
            "general": ["research methodology", "data collection", "analysis techniques", "evaluation methods"]
        }
        
        methods = methodologies.get(analysis.domain, methodologies["general"])
        
        content = f"This study employs a comprehensive {analysis.complexity_level} approach to investigate {topic.lower()}. "
        content += "The methodology includes:\n\n"
        
        for method in methods:
            content += f"• {method.title()}: Detailed analysis and evaluation of relevant aspects\n"
        
        content += f"\nThe research follows {template.tone} standards and incorporates "
        content += "established academic protocols for ensuring reliability and validity."
        
        return content
    
    def _generate_results(self, topic: str, analysis: TopicAnalysis, template: ContentStyleTemplate) -> str:
        """Generate results content"""
        content = f"The analysis of {topic.lower()} reveals several important findings:\n\n"
        
        # Domain-specific findings
        findings = {
            "computer_science": [
                "Performance evaluation shows significant improvements",
                "Algorithm efficiency has been enhanced by optimization techniques",
                "User experience metrics demonstrate positive outcomes"
            ],
            "engineering": [
                "Design parameters meet specified requirements",
                "Testing results validate theoretical predictions",
                "Performance benchmarks exceed industry standards"
            ],
            "business": [
                "Market analysis reveals emerging trends",
                "Financial metrics indicate positive performance",
                "Customer feedback shows high satisfaction levels"
            ],
            "science": [
                "Experimental data supports theoretical hypotheses",
                "Statistical analysis confirms significant correlations",
                "Observations align with established scientific principles"
            ],
            "general": [
                "Analysis results demonstrate key findings",
                "Data evaluation reveals important insights",
                "Research outcomes contribute to understanding"
            ]
        }
        
        domain_findings = findings.get(analysis.domain, findings["general"])
        
        for finding in domain_findings:
            content += f"• {finding}\n"
        
        content += f"\nThese results contribute to the {analysis.complexity_level} understanding "
        content += f"of {topic.lower()} and provide valuable insights for future research."
        
        return content
    
    def _generate_conclusion(self, topic: str, analysis: TopicAnalysis, template: ContentStyleTemplate) -> str:
        """Generate conclusion content"""
        content = f"In conclusion, this study on {topic.lower()} has demonstrated "
        content += f"significant {analysis.complexity_level} insights into the field. "
        
        # Add key takeaways based on complexity
        takeaways = {
            "basic": "The fundamental concepts have been clearly established",
            "intermediate": "Practical applications and theoretical frameworks have been explored",
            "advanced": "Sophisticated methodologies and cutting-edge developments have been analyzed"
        }
        
        content += f"{takeaways.get(analysis.complexity_level, takeaways['basic'])}. "
        
        content += "The research findings suggest promising directions for future investigation "
        content += "and highlight the importance of continued study in this area."
        
        return content
    
    def _generate_references(self, topic: str, analysis: TopicAnalysis, template: ContentStyleTemplate) -> str:
        """Generate references content"""
        content = "The following sources were consulted during this research:\n\n"
        
        # Domain-specific reference types
        reference_types = {
            "computer_science": ["academic journals", "conference proceedings", "technical documentation"],
            "engineering": ["technical standards", "industry reports", "research publications"],
            "business": ["market reports", "academic journals", "industry publications"],
            "science": ["peer-reviewed journals", "scientific publications", "research databases"]
        }
        
        refs = reference_types.get(analysis.domain, ["academic sources", "research publications"])
        
        for ref_type in refs:
            content += f"• Relevant {ref_type.title()} on {topic.lower()}\n"
        
        content += "\nAll sources follow appropriate academic citation standards."
        
        return content
    
    def _generate_generic_section(self, section_name: str, topic: str, 
                                analysis: TopicAnalysis, template: ContentStyleTemplate) -> str:
        """Generate content for generic sections"""
        content = f"This section examines {section_name.lower()} in the context of {topic.lower()}. "
        content += f"The analysis incorporates {analysis.complexity_level} approaches and "
        content += f"follows {template.tone} academic standards. "
        content += f"Key considerations include relevant theoretical frameworks, "
        content += f"practical applications, and future development opportunities."
        
        return content
    
    def _initialize_style_templates(self) -> Dict[str, ContentStyleTemplate]:
        """Initialize content style templates"""
        return {
            "academic": ContentStyleTemplate(
                style_name="academic",
                tone="formal",
                complexity_level="intermediate",
                section_templates={
                    "introduction": "This study examines {topic} within the broader context of {topic_lower}. "
                                  "The research aims to provide comprehensive analysis and insights.",
                    "conclusion": "The investigation demonstrates significant findings regarding {topic}. "
                                "These results contribute to ongoing academic discourse in this field."
                },
                academic_phrases=[
                    "contemporary research indicates", "empirical evidence suggests", 
                    "theoretical frameworks propose", "methodological approaches reveal"
                ],
                transition_words=["furthermore", "additionally", "consequently", "however", "moreover"]
            ),
            "technical": ContentStyleTemplate(
                style_name="technical",
                tone="technical",
                complexity_level="advanced",
                section_templates={},
                academic_phrases=[
                    "experimental validation confirms", "performance analysis demonstrates",
                    "technical specifications require", "implementation considerations include"
                ],
                transition_words=["specifically", "alternatively", "likewise", "nevertheless", "therefore"]
            )
        }
    
    def _initialize_academic_keywords(self) -> Dict[str, List[str]]:
        """Initialize academic keywords by domain"""
        return {
            "computer_science": ["algorithm", "framework", "implementation", "optimization", "architecture"],
            "engineering": ["design", "analysis", "specification", "validation", "prototype"],
            "business": ["strategy", "marketing", "finance", "operations", "management"],
            "science": ["hypothesis", "experimentation", "analysis", "theory", "empirical"]
        }
    
    def _initialize_transition_phrases(self) -> List[str]:
        """Initialize transition phrases for content flow"""
        return [
            "In order to", "Furthermore", "As a result", "It should be noted that",
            "Taking into consideration", "With regard to", "In addition to",
            "On the other hand", "For instance", "In conclusion"
        ]
    
    def _expand_keywords(self, base_keywords: List[str], domain: str) -> List[str]:
        """Expand keywords based on domain"""
        domain_keywords = self.academic_keywords.get(domain, [])
        expanded = base_keywords.copy()
        expanded.extend(domain_keywords[:3])  # Add top 3 domain keywords
        return list(set(expanded))  # Remove duplicates
    
    def _suggest_sections(self, topic: str, domain: str) -> List[str]:
        """Suggest appropriate sections based on topic and domain"""
        base_sections = ["Introduction", "Objectives", "Methodology", "Results", "Conclusion", "References"]
        
        # Add domain-specific sections
        domain_sections = {
            "computer_science": ["Literature Review", "System Design", "Implementation"],
            "engineering": ["Design Specifications", "Testing Results", "Performance Analysis"],
            "business": ["Market Analysis", "Financial Evaluation", "Strategic Recommendations"],
            "science": ["Theoretical Background", "Experimental Setup", "Data Analysis"]
        }
        
        additional_sections = domain_sections.get(domain, [])
        return base_sections + additional_sections[:2]  # Add max 2 additional sections
    
    def _recommend_content_length(self, complexity: str) -> str:
        """Recommend content length based on complexity"""
        recommendations = {
            "basic": "1000-1500 words",
            "intermediate": "1500-2500 words",
            "advanced": "2500-4000 words"
        }
        return recommendations.get(complexity, "1500-2500 words")
    
    def _extract_key_points(self, content: str) -> List[str]:
        """Extract key points from content"""
        sentences = content.split('. ')
        # Return first 3 sentences as key points (simplified approach)
        return [sent.strip() + '.' for sent in sentences[:3] if sent.strip()]
    
    def _extract_academic_keywords(self, content: str, domain: str) -> List[str]:
        """Extract academic keywords from content"""
        domain_keywords = self.academic_keywords.get(domain, [])
        content_lower = content.lower()
        found_keywords = [kw for kw in domain_keywords if kw.lower() in content_lower]
        return found_keywords[:5]  # Return top 5 keywords
    
    def _calculate_quality_score(self, sections: Dict[str, ContentSection]) -> float:
        """Calculate content quality score"""
        if not sections:
            return 0.0
        
        total_words = sum(section.word_count for section in sections.values())
        avg_words = total_words / len(sections)
        
        # Score based on adequate content length (300-800 words per section ideal)
        if 300 <= avg_words <= 800:
            length_score = 100.0
        elif avg_words > 800:
            length_score = 80.0
        else:
            length_score = avg_words / 300 * 100
        
        # Score based on section completeness
        completeness_score = (len(sections) / 6) * 100  # Assuming 6 standard sections
        
        # Combined score
        return (length_score * 0.7 + completeness_score * 0.3)