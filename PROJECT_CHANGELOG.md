# ReportAI — System Changelog & Architecture Documentation

This document records the complete architecture, formatting rules, test suites, and extensions built for **ReportAI**.

---

## 📌 Executive Summary

ReportAI is an end-to-end academic technical report generation and editing engine. It transforms existing reference reports (e.g., [`PBL Report Rooftop Curtains.docx`](file:///Users/ajitreddy/Downloads/Test%20Reports/PBL%20Report%20Rooftop%20Curtains.docx)) into publication-quality university engineering reports tailored to new project topics, with zero leftover markers, verified IEEE citations, formal Set Theory models, test matrices, and exact page-numbering compliance.

---

## 🏛️ Key Capabilities & Implementations

### 1. Document Formatting & Page Numbering Standard
- **Front Matter (Section 1)**: Formatted strictly with **Uppercase Roman Numerals** (`w:fmt="upperRoman"` & `w:start="1"`), numbering pages `I, II, III, IV, V...` on Title, Certificate, Acknowledgement, Abstract, List of Figures, and Table of Contents.
- **Section Break**: Placed immediately following the Table of Contents.
- **Main Chapters (Section 2)**: Restarts numbering at **`1`** in **Arabic Decimal format** (`w:fmt="decimal"` & `w:start="1"`), continuing consecutively through Chapter 6 (References).
- **Footer Structure**: 3-tab layout preserving `Sinhgad College of Engineering.` (Left), Page Number (Center), and `Department of Computer Engineering` (Right).
- **Typography**: Times New Roman 12pt body text, 1.5 line spacing, Justified alignment, standard margins.

---

### 2. 6-Chapter Academic Structure (PBL Standard)
Every generated report strictly preserves the university 6-chapter sequence:
- **Chapter 1: Introduction** (1.1 Background, 1.2 Problem Statement, 1.3 Motivation & Scope, 1.4 Methodology, 1.5 System Architecture, 1.6 Objectives, 1.7 Scope)
- **Chapter 2: Literature Survey** (2.1 Literature Review citing 4 verified IEEE/ACM/Springer papers with Seed Idea, Limitations, and Relevance)
- **Chapter 3: Proposed Methodology** (3.1 System Overview, 3.2 Hardware/Software Specs, 3.3 Implementation Details, 3.4 Design & Analysis, 3.4.1 Core Code & Pipeline)
- **Chapter 4: Result and Discussion** (4.1 How it Works, 4.2 Quantitative Test Results & Latency Benchmarks, 4.3 Comparative Evaluation, 4.4 Purpose & Significance)
- **Chapter 5: Conclusion & Future Work** (5.1 Conclusion, 5.2 Future Scope & Scalability)
- **Chapter 6: References** (6.1 Verified IEEE Reference List)

---

### 3. Multi-Topic Generation & Testing Suite
- **Test Harness**: [`test_multi_topic_reports.py`](file:///Users/ajitreddy/Engineering/Projets/ReportAI/test_multi_topic_reports.py)
- **Validated Topics**:
  1. **Smart IoT Hydroponics Monitoring & Automated Dosing**: ~3,503 words, 182 paragraphs.
  2. **Real-Time Driver Drowsiness Detection & Accident Prevention**: ~3,278 words, 179 paragraphs.
  3. **CampusConnect - Decentralized Academic Peer Platform**: ~2,877 words, 176 paragraphs.
- **Zero Leakage Guarantee**: 100% elimination of reference names (`KOLPE`, `PRATIKSHA`, `VEDANT`, etc.) and hardware markers (`ROOFTOP CURTAINS`, `DS18B20`, `L23D`, `OPEN-AIR CAFE`).

---

### 4. Web Studio: Google Docs-Style Online Editor + AI Copilot
- **Frontend**: Running on `http://localhost:3000` (`frontend/index.html`, `frontend/style.css`, `frontend/app.js`, `frontend/server.py`).
- **Backend API**: Running on `http://localhost:8000` (`backend/main.py`, `backend/core/gemini_engine.py`).
- **Features**:
  - A4 editable canvas with real-time margins and headers/footers.
  - Rich formatting toolbar (undo/redo, font sizes, heading styles, bold/italic/underline, alignments, lists, tables).
  - Document outline navigation for instant chapter jumping.
  - Side-by-side AI Copilot chat with live section updates and instant DOCX/PDF downloads.

---

### 5. Google Docs Chrome Extension (Manifest V3)
- **Directory**: [`chrome_extension/`](file:///Users/ajitreddy/Engineering/Projets/ReportAI/chrome_extension)
- **Core Files**:
  - `manifest.json`: Manifest V3 configuration with SidePanel and Google Docs scripting.
  - `background.js`: Manages side panel opening.
  - `content.js`: Autonomous in-page AI agent with visual cursor, selection highlighter, and typing animation.
  - `content.css`: Styling for virtual cursor, deletion/insertion diff chips, and top status banner.
  - `sidepanel.html` & `sidepanel.js`: Conversational chat assistant with document verification (`🔍 Verify Doc`) and one-click chapter generation.
- **How to Load in Chrome**:
  1. Open `chrome://extensions/` in Google Chrome.
  2. Enable **Developer mode**.
  3. Click **Load unpacked** and select `/Users/ajitreddy/Engineering/Projets/ReportAI/chrome_extension`.
  4. Open any document on [Google Docs](https://docs.google.com) and click the ReportAI icon.

---

## 🛠️ Verification Commands

```bash
# 1. Run full multi-topic test suite (checks page numbering, word counts, and zero leakage)
PYTHONPATH=backend backend/venv/bin/python test_multi_topic_reports.py

# 2. Run Chrome extension workflow test
PYTHONPATH=backend backend/venv/bin/python test_extension_workflow.py

# 3. Start Backend Server (FastAPI on port 8000)
cd backend && ./venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000

# 4. Start Frontend Web Studio (Port 3000)
backend/venv/bin/python frontend/server.py
```
