"""
report_rules.py
Unified Engineering & Internship Academic Report Knowledge Engine.

Standards Ingested From:
  1. 'Internship_Report_Ajit( final).docx' (Benchmark typography & formatting)
  2. 'Report format.docx' (Template rules)
  3. 'TalkAR_Preliminary_Report (2)--.pdf' (Preliminary project specifications)
  4. '1234567678.pdf' (Final report & Header/Footer rules)

Typography & Page Layout Standards:
  - Page Size: A4 (210mm x 297mm)
  - Margins: 1.0 inch (72pt) Top, Bottom, Left, Right
  - Primary Font: Times New Roman
  - Title Page:
      * Document Type Title: 14pt Bold Uppercase Centered
      * Degree & Branch: 16pt Bold Uppercase Centered
      * Candidate & Guide Names: 14pt Bold Centered
      * College & NAAC Tag: 14pt Bold Centered
  - Certificate Page:
      * Heading: 16pt Bold Uppercase Centered (14pt space before/after)
      * Body: 12pt Times New Roman, 1.5 line spacing, Justified
      * Signatures: 12pt Bold (Guide Left, HOD Right, Principal Centered)
  - Chapter Headings:
      * Line 1: 'Chapter X' (14pt Bold, Right-aligned or Centered)
      * Line 2: '[CHAPTER NAME]' (14pt Bold Uppercase)
      * Subsections: 12pt Bold, 1.5 line spacing, 6pt space before & after
  - Body Paragraphs:
      * 12pt Times New Roman Regular, 1.5 line spacing, Justified alignment, 6pt space after
  - Header & Footer:
      * Header: [Topic Title] (Left) | [Group No. XX] (Right)
      * Footer: 'SCOE, Dept. of Computer Engineering' / 'TE (Computer), SCOE Pune' | Page No.
"""

from typing import Any, Dict, List, Optional


# ── UML Diagram Slots (Project Reports) ───────────────────────────────────────
UML_DIAGRAM_SLOTS = [
    {"key": "architecture", "title": "Figure 3.1: System Architecture", "section": "3.5 System Architecture"},
    {"key": "use_case", "title": "Figure 3.2: Use Case Diagram", "section": "3.6.1 Use-Case Diagrams"},
    {"key": "activity_user", "title": "Figure 3.3: Main Activity Diagram", "section": "3.6.2 Activity Diagram"},
    {"key": "activity_backend", "title": "Figure 3.4: Backend API Activity Diagram", "section": "3.6.2 Activity Diagram"},
    {"key": "class_diagram", "title": "Figure 3.5: Class Diagram", "section": "3.6.3 Class Diagrams"},
    {"key": "er_diagram", "title": "Figure 3.6: ER Diagram", "section": "3.6.4 ER Diagrams"},
    {"key": "sequence_diagram", "title": "Figure 3.7: Main System Sequence Diagram", "section": "3.6.5 Sequence Diagrams"},
    {"key": "component_diagram", "title": "Figure 3.8: Complete System Component Diagram", "section": "3.6.6 Component/Interface diagram"},
    {"key": "deployment_diagram", "title": "Figure 3.9: Deployment Diagram", "section": "3.6.8 Deployment Diagrams"},
]

# ── SPPU / Sinhgad Default Institutional Metadata ─────────────────────────────
DEFAULT_FACULTY = {
    "group_no": "Group No. 50",
    "hod_name": "Dr. M. P. Wankhade",
    "hod_designation": "Head, Department of Computer Engineering",
    "vice_principal_hod": "Dr. R. H. Borhade",
    "principal_name": "Dr. S. D. Lokhande",
    "principal_designation": "Principal, Sinhgad College of Engineering",
    "academic_year": "2024-25",
    "college_name": "Sinhgad College of Engineering, Pune-41",
    "department_name": "DEPARTMENT OF COMPUTER ENGINEERING",
    "university_name": "SAVITRIBAI PHULE PUNE UNIVERSITY",
    "footer_class_tag": "TE (Computer), SCOE Pune",
}

# ── Standard Project Report Chapter Outline (8 Chapters) ───────────────────────
STANDARD_PROJECT_CHAPTERS = [
    {
        "chapter_num": 1,
        "title": "INTRODUCTION",
        "subsections": [
            "1.1 Background and Basics",
            "1.2 Literature Survey",
            "1.3 Project Undertaken",
            "1.3.1 Problem Definition",
            "1.3.2 Scope Statement",
            "1.4 Organization Of Project Report",
        ]
    },
    {
        "chapter_num": 2,
        "title": "PROJECT PLANNING AND MANAGEMENT",
        "subsections": [
            "2.1 Introduction",
            "2.2 System Requirement Specification (SRS)",
            "2.2.1 System Overview",
            "2.2.2 Functional Requirements",
            "2.2.3 Non-Functional Requirements",
            "2.2.4 Deployment Environment",
            "2.2.5 External Interface Requirements",
            "2.2.6 Other Requirements",
            "2.3 Project Process Modeling",
            "2.4 Cost & Efforts Estimates",
            "2.5 Project Scheduling",
        ]
    },
    {
        "chapter_num": 3,
        "title": "ANALYSIS & DESIGN",
        "subsections": [
            "3.1 Introduction",
            "3.2 IDEA matrix",
            "3.3 Mathematical Model",
            "3.4 Feasibility Analysis",
            "3.5 System Architecture",
            "3.6 UML diagrams",
            "3.6.1 Use-Case Diagrams",
            "3.6.2 Activity Diagram",
            "3.6.3 Class Diagrams",
            "3.6.4 ER Diagrams",
            "3.6.5 Sequence Diagrams",
            "3.6.6 Component/Interface diagram",
            "3.6.7 State Machine Diagrams",
            "3.6.8 Deployment Diagrams",
        ]
    },
    {
        "chapter_num": 4,
        "title": "IMPLEMENTATION DETAILS",
        "subsections": [
            "4.1 Implementation Environment",
            "4.2 Key Algorithms & Execution Workflow",
        ]
    },
    {
        "chapter_num": 5,
        "title": "TESTING",
        "subsections": [
            "5.1 Unit Testing",
            "5.2 Integration Testing",
            "5.3 Acceptance Testing",
        ]
    },
    {
        "chapter_num": 6,
        "title": "RESULTS & DISCUSSION",
        "subsections": [
            "6.1 Experimental Results & Interface Outputs",
            "6.2 Comparative Performance Evaluation",
        ]
    },
    {
        "chapter_num": 7,
        "title": "CONCLUSION",
        "subsections": [
            "7.1 Conclusion",
        ]
    },
    {
        "chapter_num": 8,
        "title": "FUTURE SCOPE",
        "subsections": [
            "8.1 Future Scope",
            "References",
        ]
    }
]

# ── Standard Second-Year PBL Report Outline (topic-agnostic) ─────────────────
# Mirrors the college PBL/preliminary format (4 body chapters + References) with
# generic section titles only.  A friend's completed report supplies the college
# identity, cover, logo and fonts; this outline supplies the body structure so
# every section title fits the *user's* topic.  Topic-specific subsections (e.g.
# literature-survey entries named after a reference's papers) are intentionally
# absent — the Literature Survey is a single section regenerated per topic.
STANDARD_PBL_CHAPTERS = [
    {
        "chapter_num": 1,
        "title": "INTRODUCTION",
        "subsections": [
            "1.1 Background and Basics",
            "1.2 Literature Survey",
            "1.3 Project Undertaken",
            "1.3.1 Problem Definition",
            "1.3.2 Scope Statement",
            "1.4 Organization of the Project Report",
        ]
    },
    {
        "chapter_num": 2,
        "title": "PROJECT PLANNING AND MANAGEMENT",
        "subsections": [
            "2.1 Introduction",
            "2.2 System Requirement Specification (SRS)",
            "2.2.1 System Overview",
            "2.2.2 Functional Requirements",
            "2.2.3 Non-Functional Requirements",
            "2.2.4 Deployment Environment",
            "2.2.5 External Interface Requirements",
            "2.2.6 Other Requirements",
            "2.3 Project Process Modeling",
            "2.4 Cost & Effort Estimates",
            "2.5 Project Scheduling",
        ]
    },
    {
        "chapter_num": 3,
        "title": "ANALYSIS & DESIGN",
        "subsections": [
            "3.1 Introduction",
            "3.2 IDEA Matrix",
            "3.3 Mathematical Model, Algorithm and Methodology",
            "3.4 Feasibility Analysis",
            "3.5 System Architecture",
            "3.6 UML Diagrams",
            "3.6.1 Use Case Diagram",
            "3.6.2 Activity Diagram",
            "3.6.3 Class Diagrams",
            "3.6.4 ER Diagrams",
            "3.6.5 Sequence Diagrams",
            "3.6.6 Component/Interface Diagram",
            "3.6.7 State Machine Diagrams",
            "3.6.8 Deployment Diagrams",
        ]
    },
    {
        "chapter_num": 4,
        "title": "TESTING",
        "subsections": [
            "4.1 Introduction",
            "4.2 Unit Testing",
            "4.3 Integration Testing",
            "4.4 Acceptance Testing",
        ]
    },
    {
        "chapter_num": 5,
        "title": "CONCLUSION AND FUTURE SCOPE",
        "subsections": [
            "5.1 Conclusion",
            "5.2 Future Scope",
            "References",
        ]
    },
]


def pbl_section_list() -> List[str]:
    """Flat, topic-agnostic PBL body section list used for both AI generation
    and deterministic rendering so the two stay in lock-step."""
    return [sub for chapter in STANDARD_PBL_CHAPTERS for sub in chapter["subsections"]]


# ── Standard Internship Report Chapter Outline (7 Chapters) ────────────────────
STANDARD_INTERNSHIP_CHAPTERS = [
    {
        "chapter_num": 1,
        "title": "INTRODUCTION",
        "subsections": [
            "1.1 Overview of the Industry",
            "1.2 Company Profile",
            "1.2.1 About the Company",
            "1.2.2 Corporate Overview",
            "1.2.3 Vision and Strategy",
            "1.2.4 Work Culture",
            "1.3 Company History",
        ]
    },
    {
        "chapter_num": 2,
        "title": "PROBLEM STATEMENT",
        "subsections": [
            "2.1 Problem Statement & Objectives",
        ]
    },
    {
        "chapter_num": 3,
        "title": "MOTIVATION",
        "subsections": [
            "3.1 Need for the Project",
            "3.2 Industry Trends and Market Demand",
            "3.3 Contribution to Innovation and Skill Development",
            "3.4 Commitment to Quality and Compliance",
            "3.5 Long-term Vision and Growth",
        ]
    },
    {
        "chapter_num": 4,
        "title": "METHODOLOGY",
        "subsections": [
            "4.1 Development Workflow & Architecture",
            "4.2 Tech Stack & Tools Utilized",
        ]
    },
    {
        "chapter_num": 5,
        "title": "RESULTS AND DISCUSSION",
        "subsections": [
            "5.1 Implementation Outcomes",
            "5.2 Key Features & Performance",
        ]
    },
    {
        "chapter_num": 6,
        "title": "ATTENDANCE RECORD",
        "subsections": [
            "6.1 Weekly Activity & Attendance Log",
        ]
    },
    {
        "chapter_num": 7,
        "title": "CONCLUSION",
        "subsections": [
            "7.1 Conclusion",
            "Reference",
        ]
    }
]


# ── Standard Internship Report Annexures ──────────────────────────────────────
INTERNSHIP_ANNEXURES = [
    {"key": "offer_letter", "title": "Annexure 1: Company Offer Letter", "description": "Official offer / appointment letter on company letterhead"},
    {"key": "completion_certificate", "title": "Annexure 2: Internship Completion Certificate", "description": "Official completion certificate signed by company mentor"},
]

DEFAULT_FACULTY = {
    "guide_name": "Prof. P. M. Kamde",
    "hod_name": "Dr. R. H. Borhade",
    "principal_name": "Dr. S. D. Lokhande",
    "academic_year": "2025-26",
    "group_no": "Group No. 50",
    "college_name": "Sinhgad College of Engineering, Pune-41",
    "department_name": "DEPARTMENT OF COMPUTER ENGINEERING",
    "university_name": "SAVITRIBAI PHULE PUNE UNIVERSITY",
}

DEFAULT_INTERNSHIP_FACULTY = {
    "company_name": "NeuAI Labs LLP",
    "company_mentor_name": "Mr. Subham Asbe",
    "company_mentor_designation": "Technical Lead",
    "college_guide_name": "Prof. N. G. Bhojne",
    "guide_name": "Prof. N. G. Bhojne",
    "hod_name": "Dr. M. P. Wankhade",
    "principal_name": "Dr. S. D. Lokhande",
    "academic_year": "2024-25",
    "college_name": "Sinhgad College of Engineering, Pune-41",
    "department_name": "DEPARTMENT OF COMPUTER ENGINEERING",
    "university_name": "SAVITRIBAI PHULE PUNE UNIVERSITY",
    "footer_class_tag": "TE (Computer), SCOE Pune",
}


def generate_weekly_attendance_diary(topic: str, company: str, start_date_str: str = "2025-01-01", weeks_count: int = 4) -> List[Dict[str, Any]]:
    """Generates realistic Monday-Friday daily engineering logs for Chapter 6."""
    from datetime import datetime, timedelta
    try:
        cur_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    except Exception:
        cur_date = datetime(2025, 1, 1)

    milestones_4w = [
        [
            f"Company orientation, security compliance & development environment setup at {company}",
            f"Understanding system architecture, API schemas & repository structure for {topic}",
            "Environment configuration: Node.js, Python, Docker, Git version control tooling",
            f"Reviewing software requirements, user stories & database schema draft for {topic}",
            "Setting up local databases, seed data & executing baseline service tests",
        ],
        [
            f"Designing responsive frontend layout & core UI components for {topic}",
            "Implementing styling, CSS grid, dark mode & interactive user controls",
            "Developing client-side form validations & state management stores",
            "Writing asynchronous fetch handlers & REST API service connectors",
            "Frontend unit testing & cross-browser responsiveness audit across devices",
        ],
        [
            f"Implementing backend REST API endpoints & route controllers for {topic}",
            "Integrating PostgreSQL / MongoDB database with ORM data models",
            "Implementing JWT authentication, role-based middleware & input sanitization",
            "Configuring asynchronous queue workers & background job processing",
            "Testing backend CRUD operations & API response latency under concurrent load",
        ],
        [
            f"End-to-end integration: Connecting frontend UI with backend APIs for {topic}",
            "Implementing caching layers, index tuning & database query optimization",
            "Conducting comprehensive unit testing, integration testing & security checks",
            "Staging deployment on cloud container infrastructure (Docker / AWS / Vercel)",
            f"Final code review with industry mentor, project documentation & report submission",
        ]
    ]

    weeks = []
    for w_idx in range(weeks_count):
        w_num = w_idx + 1
        w_tasks = milestones_4w[min(w_idx, len(milestones_4w) - 1)]
        day_entries = []
        
        days_added = 0
        while days_added < 5:
            if cur_date.weekday() < 5:
                task_desc = w_tasks[days_added]
                day_entries.append({
                    "date": cur_date.strftime("%d/%m/%y"),
                    "day": cur_date.strftime("%A"),
                    "topic": task_desc,
                    "status": "Completed"
                })
                days_added += 1
            cur_date += timedelta(days=1)
            
        w_suffix = "st" if w_num == 1 else ("nd" if w_num == 2 else ("rd" if w_num == 3 else "th"))
        weeks.append({
            "week_num": w_num,
            "week_label": f"{w_num}{w_suffix} WEEK",
            "entries": day_entries
        })
    return weeks


def clean_instruction_text(text: str) -> str:
    import re
    cleaned = re.sub(r"<<[^<>]*>>", "", text)
    cleaned = re.sub(r"\(\s*\d+\s*,\s*bold[^()]*\)", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"/\*+[\s\S]*?\*+/", "", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned).strip()
    return cleaned
