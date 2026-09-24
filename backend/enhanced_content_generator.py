import asyncio
import re
from typing import Dict, List, Optional, Any
from utils.gemini_client import gemini_generator
from models.content import GeneratedContent, ContentSection, TopicAnalysis
from config.gemini_config import gemini_config

REPORT_FORMAT_PRESETS = {
    "project_report": {
        "id": "project_report",
        "title": "Project / Mini-Project Report",
        "badge": "Standard Academic",
        "description": "Comprehensive engineering project report with architecture, implementation, and results.",
        "sections": [
            "Introduction",
            "Literature Survey",
            "System Architecture & Methodology",
            "Implementation & Experimental Setup",
            "Results & Performance Evaluation",
            "Conclusion & Future Scope",
            "References"
        ]
    },
    "seminar_report": {
        "id": "seminar_report",
        "title": "Technical Seminar Report",
        "badge": "Research Overview",
        "description": "State-of-the-art literature review, technical comparison, and emerging trends.",
        "sections": [
            "Abstract",
            "Introduction & Background",
            "Current State of Technology",
            "Key Applications & Industrial Case Studies",
            "Challenges & Open Issues",
            "Future Trends & Discussion",
            "Conclusion",
            "References"
        ]
    },
    "internship_report": {
        "id": "internship_report",
        "title": "Internship / Industrial Training Report",
        "badge": "Industry & Applied",
        "description": "Industry project report highlighting company profile, tools used, and deliverables.",
        "sections": [
            "Executive Summary",
            "Company Profile & Department Overview",
            "Objectives & Scope of Internship",
            "Tools, Frameworks & Technologies Used",
            "Projects Undertaken & Implementation",
            "Key Learnings & Professional Competencies",
            "Conclusion & Recommendations"
        ]
    },
    "ieee_paper": {
        "id": "ieee_paper",
        "title": "IEEE Research Paper Format",
        "badge": "Conference / Journal",
        "description": "Formal research paper structure with abstract, methodology, and empirical analysis.",
        "sections": [
            "Abstract",
            "Introduction",
            "Related Work",
            "Proposed System Architecture",
            "Performance Analysis & Discussion",
            "Conclusion",
            "References"
        ]
    }
}

class EnhancedContentGenerator:
    """Enhanced content generator with Gemini as primary engine and rich academic synthesis fallback"""
    
    def __init__(self):
        self.gemini_available = gemini_generator.is_available()
        self.rule_based_generator = self._initialize_rule_based_generator()
        print(f"Gemini API Status: {'✅ Available' if self.gemini_available else '⚠️ Unavailable (using intelligent rule-based engine)'}")
    
    def _initialize_rule_based_generator(self):
        """Initialize the original rule-based generator as fallback"""
        try:
            from content_generator import ContentGenerator
            return ContentGenerator()
        except ImportError:
            return None

    def get_sections_for_format(self, format_type: str, custom_sections: Optional[List[str]] = None) -> List[str]:
        """Resolve section list for the requested format preset"""
        if custom_sections and len(custom_sections) > 0:
            return custom_sections
        preset = REPORT_FORMAT_PRESETS.get(format_type)
        if preset:
            return preset["sections"]
        return REPORT_FORMAT_PRESETS["project_report"]["sections"]

    async def generate_report_preview(
        self,
        topic: str,
        format_type: str = "project_report",
        academic_info: Optional[Dict[str, str]] = None,
        reference_context: str = "",
        reference_sources: Optional[List[str]] = None,
        custom_sections: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate complete preview report payload with structured sections and metadata
        """
        academic_info = academic_info or {}
        reference_sources = reference_sources or []
        sections_list = self.get_sections_for_format(format_type, custom_sections)
        format_meta = REPORT_FORMAT_PRESETS.get(format_type, REPORT_FORMAT_PRESETS["project_report"])

        context = {
            'student_name': academic_info.get('student_name', 'Student Name'),
            'roll_no': academic_info.get('roll_no', 'N/A'),
            'college_name': academic_info.get('college_name', 'Sinhgad College of Engineering, Pune'),
            'department': academic_info.get('department', 'Computer Engineering'),
            'academic_year': academic_info.get('academic_year', '2025 - 2026'),
            'guide_name': academic_info.get('guide_name', 'Faculty Guide'),
            'reference_context': reference_context,
            'reference_sources': reference_sources,
            'format_type': format_type
        }

        generated_sections: Dict[str, str] = {}
        generation_engine = "Rule-based Academic Engine"

        # Try Gemini first if available
        if gemini_generator.is_available():
            try:
                print(f"🤖 Generating full report preview using Gemini for topic: {topic}")
                generated_sections = await gemini_generator.generate_full_report_structure(
                    topic, format_meta["title"], sections_list, context
                )
                generation_engine = f"Google Gemini ({gemini_config.model_name})"
            except Exception as e:
                print(f"⚠️ Gemini generation failed: {e}. Falling back to intelligent synthesizer.")

        # If Gemini didn't fill all sections or unavailable, use rich synthesizer
        if not generated_sections or len(generated_sections) < len(sections_list):
            fallback_sections = self._synthesize_rich_sections(topic, format_type, sections_list, context)
            for s in sections_list:
                if s not in generated_sections or not generated_sections[s]:
                    generated_sections[s] = fallback_sections.get(s, f"Detailed academic coverage for {s}.")

        # Calculate word counts and stats
        section_items = []
        total_words = 0
        for idx, s_name in enumerate(sections_list, start=1):
            content = generated_sections.get(s_name, "").strip()
            w_count = len(content.split())
            total_words += w_count
            section_items.append({
                "number": idx,
                "title": s_name,
                "key": s_name.lower().replace(" ", "_").replace("&", "and"),
                "content": content,
                "word_count": w_count
            })

        estimated_pages = max(1, round(total_words / 280, 1))

        return {
            "success": True,
            "topic": topic,
            "format_type": format_type,
            "format_title": format_meta["title"],
            "academic_info": {
                "student_name": context["student_name"],
                "roll_no": context["roll_no"],
                "college_name": context["college_name"],
                "department": context["department"],
                "academic_year": context["academic_year"],
                "guide_name": context["guide_name"]
            },
            "reference_sources": reference_sources,
            "has_references": bool(reference_sources or reference_context),
            "generation_engine": generation_engine,
            "total_words": total_words,
            "estimated_pages": estimated_pages,
            "sections": section_items
        }

    def _synthesize_rich_sections(
        self, topic: str, format_type: str, sections_list: List[str], context: Dict
    ) -> Dict[str, str]:
        """Synthesize rich, high-quality domain content incorporating references and topic analysis"""
        ref_text = context.get("reference_context", "")
        student_name = context.get("student_name", "Student")
        dept = context.get("department", "Computer Engineering")
        college = context.get("college_name", "Engineering College")

        # Extract snippet from references if available
        ref_highlight = ""
        if ref_text:
            clean_ref = re.sub(r"#+", "", ref_text)[:400].strip()
            ref_highlight = f" Drawing upon primary research notes and ingested background material: \"{clean_ref}...\""

        output = {}
        for s in sections_list:
            s_lower = s.lower()
            if "abstract" in s_lower:
                output[s] = (
                    f"This report presents a thorough investigation into {topic}, emphasizing key technical architectures, "
                    f"operational methodologies, and performance characteristics. Rapid developments in {dept} domains "
                    f"have necessitated systematic frameworks capable of handling scalability, resilience, and automation. "
                    f"In this work, we analyze core theoretical underpinnings, synthesize empirical observations, and present "
                    f"a validated structural model.{ref_highlight} The results indicate notable enhancements over legacy baselines, "
                    f"offering actionable insights for contemporary research and production deployment."
                )
            elif "intro" in s_lower:
                output[s] = (
                    f"1.1 Background & Motivation\n"
                    f"In recent years, {topic} has emerged as a transformative area of interest within {dept}. "
                    f"As modern computing and engineering paradigms transition toward distributed intelligence and data-driven systems, "
                    f"establishing robust methodologies for {topic} has become increasingly critical for academic and industrial progress.\n\n"
                    f"1.2 Problem Formulation & Scope\n"
                    f"Traditional approaches often suffer from bottlenecks such as computational overhead, architectural rigidity, "
                    f"and sub-optimal latency. To address these limitations, this project undertakes a rigorous analysis of the design "
                    f"patterns, algorithmic strategies, and engineering trade-offs required to build dependable solutions.\n\n"
                    f"1.3 Key Objectives\n"
                    f"• Formulate a comprehensive foundational framework for {topic}.\n"
                    f"• Evaluate system workflows, performance bottlenecks, and comparative advantages.\n"
                    f"• Validate the proposed implementation using empirical testing metrics and standardized benchmarks.\n"
                    f"• Document deployment strategies, limitations, and future technological trajectories."
                )
            elif "survey" in s_lower or "related" in s_lower or "literature" in s_lower:
                output[s] = (
                    f"A review of contemporary literature demonstrates extensive exploration in the domain of {topic}. "
                    f"Early research primarily focused on foundational algorithmic heuristics and standalone models. However, recent "
                    f"breakthroughs have introduced end-to-end modular architectures that significantly enhance reliability and throughput.\n\n"
                    f"Comparative Literature Synthesis:\n"
                    f"1. Classical Baseline Models: Demonstrated baseline viability but exhibited scalability constraints under dense workloads.\n"
                    f"2. Hybrid Machine-Assisted Systems: Improved inference speed and classification precision through pipeline parallelism.\n"
                    f"3. Distributed & Modular Frameworks: Addressed fault-tolerance while minimizing parameter synchronization overhead.\n\n"
                    f"{ref_highlight}\n\n"
                    f"By synthesizing these research paradigms, our methodology bridges the gap between theoretical modeling and scalable practical implementation."
                )
            elif "method" in s_lower or "architecture" in s_lower or "system" in s_lower or "framework" in s_lower:
                output[s] = (
                    f"The architectural design of {topic} is structured into three cohesive tiers:\n\n"
                    f"1. Data Ingestion & Preprocessing Pipeline: Responsible for acquiring heterogeneous input streams, normalizing telemetry, "
                    f"and applying noise filtering and tokenization routines to maintain uniform data distribution.\n\n"
                    f"2. Core Computational & Execution Engine: Implements the primary algorithmic routines, optimizing memory allocation "
                    f"and vectorized matrix operations. The module maintains high concurrency through asynchronous thread management.\n\n"
                    f"3. Validation & Telemetry Layer: Captures system performance metrics, validates schema integrity, and generates structured analytical summaries.\n\n"
                    f"Mathematical Formulation:\n"
                    f"Let S represent the overall system state and X the input vector. The objective optimization function is formulated as:\n"
                    f"    min J(θ) = E[ L(f(X; θ), Y) ] + λ ||θ||²\n"
                    f"where L denotes the loss metric, θ denotes the model parameter tensor, and λ controls regularization to prevent overfitting."
                )
            elif "implement" in s_lower or "tool" in s_lower or "task" in s_lower or "experi" in s_lower:
                output[s] = (
                    f"The implementation was executed using modern engineering toolchains, high-performance runtime libraries, "
                    f"and containerized execution environments. The software pipeline was evaluated on standard benchmarking hardware with the following configuration:\n\n"
                    f"• Primary Language & Frameworks: Python 3.10+, PyTorch / FastAPI / Scientific Compute Stack\n"
                    f"• Hardware Specifications: Multicore CPU with CUDA-enabled accelerator support\n"
                    f"• Dataset & Benchmarks: Standardized synthetic and empirical test suites\n\n"
                    f"Execution Workflow:\n"
                    f"1. Environment Setup & Dependency Isolation\n"
                    f"2. Pipeline Integration & Unit Verification\n"
                    f"3. Load Simulation & Stress Testing under variable concurrency thresholds\n"
                    f"4. Output validation and logging verification."
                )
            elif "result" in s_lower or "learn" in s_lower or "evalua" in s_lower:
                output[s] = (
                    f"The empirical evaluation of {topic} demonstrates substantial performance gains across key evaluation metrics:\n\n"
                    f"Key Performance Indicators:\n"
                    f"• Latency & Processing Speed: Reduced average execution time by 28.4% compared to standard baselines.\n"
                    f"• Accuracy / Precision: Achieved a composite score of 94.7% across extensive test splits.\n"
                    f"• Resource Utilization: Memory footprint was minimized by 22% through dynamic buffer reuse.\n\n"
                    f"Discussion & Analysis:\n"
                    f"The observed metrics confirm that the structured architecture effectively minimizes computational overhead while maintaining "
                    f"high fidelity. Sensitivity analysis reveals that the system retains stability across fluctuating input distributions without performance degradation."
                )
            elif "challenge" in s_lower or "company" in s_lower or "trend" in s_lower or "scope" in s_lower:
                output[s] = (
                    f"Throughout the execution and analysis of {topic}, several technical challenges and practical considerations were addressed:\n\n"
                    f"• Data Sparsity & High Dimensionality: Mitigated by applying dimensionality reduction and robust feature extraction techniques.\n"
                    f"• Hardware & Memory Constraints: Addressed via batch-wise processing and quantized representations.\n"
                    f"• Emerging Trends: Future systems are poised to leverage edge computing accelerators, automated neural architecture search, "
                    f"and federated learning for privacy-preserving distributed deployments."
                )
            elif "conclusion" in s_lower or "summary" in s_lower:
                output[s] = (
                    f"In this report, we presented a comprehensive study and implementation of {topic}. "
                    f"By integrating rigorous theoretical analysis with modern software engineering practices, we demonstrated "
                    f"a scalable, dependable, and efficient framework.\n\n"
                    f"Summary of Contributions:\n"
                    f"1. Designed an end-to-end architectural workflow tailored for academic and industrial application.\n"
                    f"2. Conducted rigorous comparative benchmarking against established standard paradigms.\n"
                    f"3. Identified practical avenues for future enhancement, including distributed edge integration and self-supervised adaptation.\n\n"
                    f"The findings underscore the viability and importance of {topic} in advancing modern {dept} practices."
                )
            elif "ref" in s_lower:
                output[s] = (
                    f"[1] A. Vaswani et al., \"Attention Is All You Need,\" in Advances in Neural Information Processing Systems (NeurIPS), 2017, pp. 5998–6008.\n"
                    f"[2] Y. LeCun, Y. Bengio, and G. Hinton, \"Deep Learning,\" Nature, vol. 521, no. 7553, pp. 436–444, 2015.\n"
                    f"[3] M. Zaharia et al., \"Apache Spark: A Unified Engine for Big Data Processing,\" Communications of the ACM, vol. 59, no. 11, pp. 56–65, 2016.\n"
                    f"[4] IEEE Standard Glossary of Software Engineering Terminology, IEEE Std 610.12-1990, 1990.\n"
                    f"[5] Academic Reference Repository & IEEE Xplore Digital Library on {topic}, 2024."
                )
            else:
                output[s] = (
                    f"This section provides detailed technical examination for {s} regarding {topic}. "
                    f"The conceptual formulation and execution parameters have been structured to ensure consistency with {dept} standards."
                )
        return output

    def get_generation_status(self) -> Dict:
        """Get current generation engine status"""
        return {
            "gemini_available": gemini_generator.is_available(),
            "rule_based_available": True,
            "primary_engine": "Gemini AI" if gemini_generator.is_available() else "Rule-based Academic Synthesizer",
            "api_key_configured": gemini_config.is_configured(),
            "model_name": gemini_config.model_name if gemini_config.is_configured() else None,
            "available_presets": list(REPORT_FORMAT_PRESETS.keys())
        }

enhanced_generator = EnhancedContentGenerator()