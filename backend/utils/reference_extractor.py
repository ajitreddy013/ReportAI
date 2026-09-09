import os
import re
import urllib.request
import urllib.parse
import json
from typing import Dict, List, Optional, Tuple
from docx import Document

class ReferenceExtractor:
    """Extracts text content and context from uploaded files, web URLs, and AI chat links."""

    def __init__(self, upload_dir: Optional[str] = None):
        if upload_dir is None:
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.upload_dir = os.path.join(backend_dir, "uploads")
        else:
            self.upload_dir = upload_dir
        os.makedirs(self.upload_dir, exist_ok=True)

    def extract_from_file(self, file_path: str, filename: str) -> Dict[str, any]:
        """Extract text from various document formats (.docx, .txt, .md, .pdf)"""
        ext = os.path.splitext(filename)[1].lower()
        content = ""
        summary = ""

        try:
            if ext in [".docx", ".doc"]:
                content = self._extract_docx(file_path)
            elif ext in [".txt", ".md", ".markdown", ".rst", ".json"]:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            elif ext == ".pdf":
                content = self._extract_pdf(file_path)
            else:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

            summary = self._create_snippet(content, max_length=250)
            return {
                "filename": filename,
                "type": ext.replace(".", "").upper(),
                "content": content,
                "summary": summary,
                "char_count": len(content),
                "word_count": len(content.split())
            }
        except Exception as e:
            print(f"Error extracting text from {filename}: {e}")
            return {
                "filename": filename,
                "type": ext.replace(".", "").upper(),
                "content": f"[Error reading file: {str(e)}]",
                "summary": "Failed to extract content",
                "char_count": 0,
                "word_count": 0
            }

    def _extract_docx(self, file_path: str) -> str:
        """Extract all paragraphs and tables from a Word document"""
        doc = Document(file_path)
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        
        # Also extract table text
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join([cell.text.strip() for cell in row.cells if cell.text.strip()])
                if row_text:
                    paragraphs.append(row_text)
                    
        return "\n\n".join(paragraphs)

    def _extract_pdf(self, file_path: str) -> str:
        """Extract text from PDF using basic stream parsing or fallback"""
        text_parts = []
        try:
            import pypdf
            reader = pypdf.PdfReader(file_path)
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
            if text_parts:
                return "\n\n".join(text_parts)
        except ImportError:
            pass
        except Exception as e:
            print(f"pypdf extraction error: {e}")

        # Fallback: simple text scanner for uncompressed streams in PDF
        try:
            with open(file_path, "rb") as f:
                raw_bytes = f.read()
                matches = re.findall(rb"\(([\w\s\.,;:!\?\-\'\"]+)\)\s*Tj", raw_bytes)
                if matches:
                    text = " ".join([m.decode("latin1", errors="ignore") for m in matches])
                    if len(text.strip()) > 50:
                        return text
        except Exception as e:
            print(f"PDF raw fallback error: {e}")

        return "[PDF content extraction requires text-based PDF]"

    def extract_from_url(self, url: str) -> Dict[str, any]:
        """
        Fetch and extract readable text from a URL (including ChatGPT/Claude share links or articles)
        """
        url = url.strip()
        if not url:
            return {"url": url, "title": "Empty URL", "content": "", "summary": ""}

        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url

        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
                }
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode("utf-8", errors="ignore")

            title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
            title = title_match.group(1).strip() if title_match else url

            clean_text = self._html_to_clean_text(html)
            summary = self._create_snippet(clean_text, max_length=250)

            return {
                "url": url,
                "title": title,
                "content": clean_text[:12000],
                "summary": summary,
                "word_count": len(clean_text.split())
            }
        except Exception as e:
            print(f"Failed to fetch URL {url}: {e}")
            return {
                "url": url,
                "title": url,
                "content": f"[Could not auto-fetch link: {str(e)}. Link registered as citation reference.]",
                "summary": f"Referenced link: {url}",
                "word_count": 0
            }

    def _html_to_clean_text(self, html: str) -> str:
        """Strip HTML tags, JavaScript, styles and return clean text paragraphs"""
        html = re.sub(r"<(script|style|nav|header|footer|aside)[^>]*>.*?</\1>", " ", html, flags=re.IGNORECASE | re.DOTALL)
        html = re.sub(r"<(p|br|div|h1|h2|h3|h4|h5|h6|li|tr)[^>]*>", "\n", html, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", html)
        text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", "\"").replace("&#39;", "'")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n+", "\n\n", text)
        return text.strip()

    def _create_snippet(self, text: str, max_length: int = 250) -> str:
        """Create a clean representative snippet of text"""
        clean = re.sub(r"\s+", " ", text).strip()
        if len(clean) <= max_length:
            return clean
        return clean[:max_length].rstrip() + "..."

    def compile_all_references(
        self,
        extracted_files: List[Dict],
        extracted_links: List[Dict],
        raw_notes: str
    ) -> Dict[str, any]:
        """
        Synthesize all reference sources into unified context text for report generation
        """
        combined_text_blocks = []
        sources_list = []

        if raw_notes and raw_notes.strip():
            combined_text_blocks.append(f"### USER REFERENCE NOTES & INSTRUCTIONS:\n{raw_notes.strip()}")
            sources_list.append("Custom User Notes")

        for f in extracted_files:
            if f.get("content") and len(f["content"].strip()) > 0:
                combined_text_blocks.append(f"### REFERENCE DOCUMENT [{f.get('filename')}]:\n{f['content'][:8000]}")
                sources_list.append(f"Document: {f.get('filename')}")

        for l in extracted_links:
            if l.get("content") and len(l["content"].strip()) > 0:
                combined_text_blocks.append(f"### REFERENCE LINK [{l.get('title', l.get('url'))}]:\n{l['content'][:6000]}")
                sources_list.append(f"Link: {l.get('url')}")

        full_context = "\n\n" + ("\n\n".join(combined_text_blocks)) if combined_text_blocks else ""

        return {
            "full_context_text": full_context,
            "sources": sources_list,
            "total_sources_count": len(sources_list),
            "has_references": bool(sources_list)
        }

reference_extractor = ReferenceExtractor()
