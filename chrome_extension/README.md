# ReportAI — Academic Google Docs Copilot (Chrome Extension)

Turn Google Docs into an intelligent university-standard project report generator and editor. Open your friend's report or a blank document, and ReportAI adapts all chapters, student details, formulas, test cases, and citations to your project topic.

---

## 🚀 Quick Setup (Takes 1 minute)

1. Open **Google Chrome** and navigate to:
   ```
   chrome://extensions/
   ```
2. Enable **Developer mode** (toggle in the top-right corner).
3. Click **Load unpacked** (top-left button).
4. Select the directory:
   ```
   /Users/ajitreddy/Engineering/Projets/ReportAI/chrome_extension
   ```
5. Ensure the backend server is running:
   ```bash
   cd /Users/ajitreddy/Engineering/Projets/ReportAI/backend
   ./venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
   ```

---

## 📖 How to Use on Google Docs

1. Open any report in [Google Docs](https://docs.google.com).
2. Click the **ReportAI extension icon** or open the **Chrome Side Panel** and select **ReportAI**.
3. **Configure Project Details**:
   - Enter your **Project Topic** (e.g. *Smart IoT Hydroponics Monitoring System*).
   - Enter Group No, Guide Name, and 4 Student Names/Roll Numbers.
   - Enter your hardware/software notes.
4. **Execute Actions**:
   - 🔄 **Rewrite for Topic**: Highlight any old section from your friend's report and click *Rewrite for Topic* to adapt it instantly.
   - 🔍 **Expand with Depth**: Adds rigorous engineering explanations, circuits, or state machines.
   - 📐 **Set Theory Model**: Injects $S = \{I, A, P, R, O\}$ formal models.
   - 🧪 **Test Case Matrix**: Injects structured Unit / Integration test tables.
   - 📚 **IEEE References**: Inserts verified research citations.
   - 📖 **Chapter Generator**: Select any subsection (1.1 to 6.1) or click **Generate Entire Report** to copy/paste the whole document.
   - 💬 **Interactive AI Chat**: Ask questions, request edits, and click **Copy to Document** to paste with `Cmd+V`.
