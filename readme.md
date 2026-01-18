# 📄 ReportAI - Automated Academic Report Generator

> **Transform your academic report writing workflow with AI-powered automation**

A modern web application that automatically generates professionally formatted academic reports (semester reports, mini projects, internships) using customizable Word templates. Say goodbye to manual formatting and hello to instant, perfectly formatted documents.

![Status](https://img.shields.io/badge/status-active-success.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)

---

## 🎯 Problem Statement

Academic report writing is time-consuming and frustrating:
- **Manual formatting** takes hours of repetitive work
- **Template compliance** requires constant adjustments
- **Revision cycles** mean reformatting everything again
- **Inconsistent styling** leads to rejected submissions

Students waste valuable time on formatting instead of focusing on content quality.

---

## ✨ Solution

**ReportAI** automates the entire report generation process:

1. 📤 Upload your institution's Word template (or use the default)
2. ✍️ Fill in your content through an intuitive web interface
3. 🤖 AI processes and formats everything automatically
4. 📥 Download your perfectly formatted DOCX or PDF report

**Result:** What used to take hours now takes minutes!

---

## 🚀 Key Features

### ✅ Core Capabilities
- **Template-Based Generation** - Use any Word template with placeholder support
- **Smart Formatting** - Preserves fonts, spacing, margins, headers, and footers
- **Dual Output** - Generate both DOCX and PDF formats
- **Custom Templates** - Upload your own institutional templates
- **Modern UI** - Beautiful, responsive interface with real-time feedback
- **Zero Configuration** - Works out of the box with sensible defaults

### 🎨 Preserved Formatting
- Font styles and sizes
- Line spacing and paragraph alignment
- Page margins and orientation
- Headers and footers
- Page numbering
- Section styles and headings

---

## 🛠️ Tech Stack

### Frontend
- **HTML5** - Semantic structure
- **CSS3** - Modern styling with glassmorphism effects
- **Vanilla JavaScript** - No framework overhead
- **Google Fonts** - Inter & Outfit typography

### Backend
- **Python 3.8+** - Core language
- **FastAPI** - High-performance async web framework
- **docxtpl** - Template rendering engine
- **python-docx** - Advanced document manipulation

### Document Processing
- **LibreOffice** - Headless PDF conversion
- **python-multipart** - File upload handling

### Deployment Ready
- **Backend**: Render, Railway, PythonAnywhere
- **Frontend**: Vercel, Netlify, GitHub Pages
- **Storage**: Local filesystem (upgradeable to cloud)

---

## 📁 Project Structure

```
ReportAI/
├── backend/
│   ├── main.py                 # FastAPI application
│   ├── create_template.py      # Template creation utility
│   ├── requirements.txt        # Python dependencies
│   ├── templates/              # Default templates
│   │   └── default_template.docx
│   ├── uploads/                # User-uploaded templates
│   └── outputs/                # Generated reports
├── frontend/
│   ├── index.html              # Main UI
│   ├── style.css               # Styling
│   └── script.js               # Client-side logic
└── readme.md                   # This file
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- LibreOffice (for PDF conversion)
- Modern web browser

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/yourusername/ReportAI.git
cd ReportAI
```

### 2️⃣ Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3️⃣ Start the Backend Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Server will be available at: `http://localhost:8000`

### 4️⃣ Launch the Frontend

```bash
# Open in a new terminal
cd frontend

# Option 1: Open directly in browser
open index.html  # macOS
# or just double-click index.html

# Option 2: Use Python's built-in server
python -m http.server 3000
# Then visit http://localhost:3000
```

---

## 📝 Creating Templates

### Template Placeholder Syntax

Use double curly braces for placeholders in your Word template:

```
{{COLLEGE_NAME}}
{{DEPARTMENT}}
{{STUDENT_NAME}}
{{ROLL_NO}}
{{TOPIC}}
{{INTRODUCTION}}
{{OBJECTIVES}}
{{METHODOLOGY}}
{{RESULT}}
{{CONCLUSION}}
{{REFERENCES}}
```

### Creating a Custom Template

1. Open Microsoft Word or LibreOffice Writer
2. Design your report format (fonts, margins, headers, etc.)
3. Insert placeholders where content should appear
4. Save as `.docx` format
5. Place in `backend/templates/` or upload via the web interface

**Pro Tip:** Use the included `create_template.py` script to generate a starter template!

```bash
cd backend
python create_template.py
```

---

## 🔌 API Documentation

### Generate Report Endpoint

**POST** `/generate-report`

**Form Data:**
```
student_name: string (required)
roll_no: string (required)
topic: string (required)
college_name: string (default: "Sinhgad College of Engineering, Pune")
department: string (default: "Computer Engineering")
introduction: string (required)
objectives: string (optional)
methodology: string (optional)
result: string (optional)
conclusion: string (optional)
references: string (optional)
template_file: file (optional, .docx)
convertToPdf: boolean (default: false)
```

**Response:**
- Success: File download (DOCX or PDF)
- Error: JSON with error details

**Example using cURL:**
```bash
curl -X POST "http://localhost:8000/generate-report" \
  -F "student_name=John Doe" \
  -F "roll_no=12345" \
  -F "topic=AI in Healthcare" \
  -F "introduction=This report explores..." \
  -F "convertToPdf=true"
```

---

## 🎨 Usage Workflow

1. **Open the Application** - Navigate to the frontend in your browser
2. **Fill Academic Details** - Enter college, department, name, and roll number
3. **Add Report Content** - Fill in topic, introduction, objectives, methodology, etc.
4. **Choose Template** - Upload custom template or use default
5. **Select Output Format** - Check "Convert to PDF" if needed
6. **Generate** - Click "Generate Report" button
7. **Download** - Your formatted report downloads automatically

---

## 🔧 Configuration

### PDF Conversion Setup

Install LibreOffice for PDF generation:

**macOS:**
```bash
brew install --cask libreoffice
```

**Ubuntu/Debian:**
```bash
sudo apt-get install libreoffice
```

**Windows:**
Download from [LibreOffice.org](https://www.libreoffice.org/download/download/)

Verify installation:
```bash
soffice --version
```

---

## 🐛 Troubleshooting

### Issue: Template placeholders not replaced

**Solution:**
- Verify placeholder names match exactly (case-sensitive)
- Ensure placeholders are in regular paragraphs, not text boxes
- Check for extra spaces: `{{ NAME }}` won't work, use `{{NAME}}`

### Issue: PDF conversion fails

**Solution:**
- Confirm LibreOffice is installed: `soffice --version`
- Check PATH includes LibreOffice binary
- On Windows, add to PATH: `C:\Program Files\LibreOffice\program\`

### Issue: CORS errors in browser console

**Solution:**
Already configured! CORS middleware is enabled in `main.py`. If issues persist:
- Ensure backend is running on port 8000
- Check browser console for specific error
- Try accessing from `http://localhost` instead of `file://`

### Issue: Module not found errors

**Solution:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Reinstall dependencies
pip install -r requirements.txt
```

---

## 🗺️ Roadmap

### 🎯 Phase 2: AI-Powered Feedback (Planned)
- Paste teacher feedback
- Auto-detect required changes
- One-click regeneration with fixes

### 📚 Phase 3: Template Library (Planned)
- Pre-built templates for different departments
- Community-shared templates
- Template versioning

### 💬 Phase 4: Natural Language Editing (Planned)
- "Make all headings bold"
- "Set line spacing to 1.5"
- "Add page numbers at bottom center"

### 👤 Phase 5: User Accounts (Planned)
- Save report history
- Cloud storage integration
- Collaborative editing

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed for **educational use**. Feel free to modify and extend for academic purposes.

---

## 👨‍💻 Author

**Ajit Reddy**  
Computer Engineering Student  
Sinhgad College of Engineering, Pune

---

## 🙏 Acknowledgments

- FastAPI for the excellent web framework
- docxtpl for template rendering
- LibreOffice for PDF conversion
- The open-source community

---

## 📞 Support

Having issues? Found a bug? Have a feature request?

- 🐛 [Open an Issue](https://github.com/yourusername/ReportAI/issues)
- 💡 [Request a Feature](https://github.com/yourusername/ReportAI/issues/new)
- 📧 Contact: your.email@example.com

---

<div align="center">

**Made with ❤️ for students, by a student**

⭐ Star this repo if it helped you!

</div>
