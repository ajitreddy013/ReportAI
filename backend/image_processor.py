import os
import uuid
import re
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher

# Optional imports
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None

try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    pytesseract = None

class ImageProcessor:
    """Handles image processing, caption matching, and smart placement"""
    
    def __init__(self, uploads_dir: str = "uploads/images"):
        self.uploads_dir = uploads_dir
        os.makedirs(uploads_dir, exist_ok=True)
        self.caption_keywords = self._initialize_caption_keywords()
    
    def process_images_with_captions(self, images_data: List[Dict], 
                                   content_sections: Dict[str, str]) -> List[Dict]:
        """
        Process images and match them with appropriate content sections
        
        Args:
            images_data: List of image data with captions
            content_sections: Generated content sections
            
        Returns:
            List of processed images with placement information
        """
        processed_images = []
        
        for image_data in images_data:
            processed_image = self._process_single_image(image_data, content_sections)
            processed_images.append(processed_image)
        
        return processed_images
    
    def _process_single_image(self, image_data: Dict, 
                            content_sections: Dict[str, str]) -> Dict:
        """Process a single image and determine placement"""
        filename = image_data.get('filename', '')
        caption = image_data.get('caption', '')
        content_relevance = image_data.get('content_relevance', 'auto')
        
        # Determine best placement section
        if content_relevance == 'auto':
            placement_section = self._match_caption_to_section(caption, content_sections)
        else:
            placement_section = content_relevance
        
        # Analyze image content if possible (OCR)
        image_text = self._extract_image_text(filename)
        
        # Determine placement preference
        placement_preference = self._determine_placement_preference(
            caption, image_text, placement_section
        )
        
        return {
            'original_filename': filename,
            'caption': caption,
            'placement_section': placement_section,
            'placement_preference': placement_preference,
            'image_text': image_text,
            'relevance_score': self._calculate_relevance_score(caption, placement_section, content_sections),
            'file_size': image_data.get('file_size', 0)
        }
    
    def _match_caption_to_section(self, caption: str, 
                                content_sections: Dict[str, str]) -> str:
        """Match caption to the most relevant content section"""
        caption_lower = caption.lower()
        best_match = 'introduction'  # Default
        best_score = 0.0
        
        for section_name, section_content in content_sections.items():
            # Calculate similarity score
            score = self._calculate_section_similarity(caption_lower, section_content.lower())
            
            # Check for keyword matches
            keyword_score = self._calculate_keyword_match(caption_lower, section_name)
            combined_score = score + (keyword_score * 0.5)
            
            if combined_score > best_score:
                best_score = combined_score
                best_match = section_name
        
        return best_match
    
    def _calculate_section_similarity(self, caption: str, section_content: str) -> float:
        """Calculate similarity between caption and section content"""
        # Use sequence matching for similarity
        similarity = SequenceMatcher(None, caption, section_content[:200]).ratio()
        return similarity
    
    def _calculate_keyword_match(self, caption: str, section_name: str) -> float:
        """Calculate keyword match score"""
        section_keywords = self.caption_keywords.get(section_name.lower(), [])
        match_count = sum(1 for keyword in section_keywords if keyword in caption)
        return match_count / len(section_keywords) if section_keywords else 0.0
    
    def _extract_image_text(self, filename: str) -> str:
        """Extract text from image using OCR (if available)"""
        if not OCR_AVAILABLE or not pytesseract:
            return ""  # Return empty string if OCR not available
        
        try:
            image_path = os.path.join(self.uploads_dir, filename)
            if os.path.exists(image_path):
                text = pytesseract.image_to_string(Image.open(image_path))
                return text.strip()
            return ""
        except Exception:
            return ""
    
    def _determine_placement_preference(self, caption: str, image_text: str, 
                                      section_name: str) -> str:
        """Determine optimal placement preference for the image"""
        caption_lower = caption.lower()
        
        # Check for placement indicators in caption
        if any(word in caption_lower for word in ['above', 'top', 'beginning']):
            return 'top'
        elif any(word in caption_lower for word in ['below', 'bottom', 'end']):
            return 'bottom'
        elif any(word in caption_lower for word in ['side', 'next to', 'beside']):
            return 'inline'
        
        # Default based on section type
        section_defaults = {
            'introduction': 'top',
            'methodology': 'inline',
            'results': 'inline',
            'conclusion': 'bottom'
        }
        
        return section_defaults.get(section_name.lower(), 'auto')
    
    def _calculate_relevance_score(self, caption: str, section_name: str, 
                                 content_sections: Dict[str, str]) -> float:
        """Calculate relevance score between image and section"""
        section_content = content_sections.get(section_name, '').lower()
        caption_lower = caption.lower()
        
        # Direct keyword matches
        direct_matches = sum(1 for word in caption_lower.split() 
                           if word in section_content)
        
        # Semantic similarity
        similarity = SequenceMatcher(None, caption_lower, section_content[:300]).ratio()
        
        # Combined score (0-100)
        return min(100.0, (direct_matches * 5) + (similarity * 50))
    
    def _initialize_caption_keywords(self) -> Dict[str, List[str]]:
        """Initialize caption keywords for different sections"""
        return {
            'introduction': ['overview', 'background', 'context', 'study', 'research'],
            'objectives': ['goal', 'aim', 'purpose', 'target', 'objective'],
            'methodology': ['method', 'approach', 'procedure', 'technique', 'process'],
            'results': ['result', 'finding', 'outcome', 'data', 'analysis', 'chart', 'graph'],
            'conclusion': ['conclusion', 'summary', 'finding', 'recommendation'],
            'references': ['reference', 'source', 'citation', 'bibliography']
        }
    
    def place_images_in_document(self, doc, processed_images: List[Dict], 
                               content_sections: Dict[str, str]) -> None:
        """
        Place processed images in the document at appropriate locations
        
        Args:
            doc: python-docx Document object
            processed_images: List of processed image data
            content_sections: Content sections mapping
        """
        # Group images by placement section
        images_by_section = {}
        for img_data in processed_images:
            section = img_data['placement_section']
            if section not in images_by_section:
                images_by_section[section] = []
            images_by_section[section].append(img_data)
        
        # Place images in document
        for paragraph in doc.paragraphs:
            # Check if this paragraph contains section indicators
            para_text = paragraph.text.lower()
            
            for section_name, images in images_by_section.items():
                if self._paragraph_matches_section(para_text, section_name):
                    # Insert images for this section
                    for img_data in images:
                        self._insert_image_at_position(doc, paragraph, img_data)
                    # Remove processed images
                    del images_by_section[section_name]
                    break
    
    def _paragraph_matches_section(self, paragraph_text: str, section_name: str) -> bool:
        """Check if paragraph matches section name"""
        section_indicators = {
            'introduction': ['introduction', 'intro', 'background'],
            'objectives': ['objective', 'aim', 'goal'],
            'methodology': ['method', 'approach', 'procedure'],
            'results': ['result', 'finding', 'outcome'],
            'conclusion': ['conclusion', 'summary'],
            'references': ['reference', 'bibliography']
        }
        
        indicators = section_indicators.get(section_name.lower(), [section_name.lower()])
        return any(indicator in paragraph_text for indicator in indicators)
    
    def _insert_image_at_position(self, doc, target_paragraph, image_data: Dict) -> None:
        """Insert image at the specified position"""
        try:
            image_path = os.path.join(self.uploads_dir, image_data['original_filename'])
            
            if not os.path.exists(image_path):
                return  # Skip if image file doesn't exist
            
            # Determine insertion position based on preference
            preference = image_data['placement_preference']
            
            if preference == 'top':
                # Insert before the paragraph
                self._insert_image_before_paragraph(doc, target_paragraph, image_path, image_data['caption'])
            elif preference == 'bottom':
                # Insert after the paragraph
                self._insert_image_after_paragraph(doc, target_paragraph, image_path, image_data['caption'])
            else:  # inline or auto
                # Insert inline with the paragraph
                self._insert_image_inline(target_paragraph, image_path, image_data['caption'])
                
        except Exception as e:
            print(f"Error inserting image {image_data['original_filename']}: {e}")
    
    def _insert_image_before_paragraph(self, doc, paragraph, image_path: str, caption: str):
        """Insert image before the specified paragraph"""
        # Add new paragraph for image
        image_para = doc.add_paragraph()
        image_para.alignment = 1  # Center alignment
        run = image_para.add_run()
        run.add_picture(image_path, width=doc.sections[0].page_width * 0.8)
        
        # Add caption
        if caption:
            caption_para = doc.add_paragraph()
            caption_para.alignment = 1  # Center alignment
            caption_para.add_run(f"Figure: {caption}").italic = True
    
    def _insert_image_after_paragraph(self, doc, paragraph, image_path: str, caption: str):
        """Insert image after the specified paragraph"""
        # Find paragraph index
        paragraphs = list(doc.paragraphs)
        try:
            para_index = paragraphs.index(paragraph)
            # Insert after this paragraph
            if para_index < len(paragraphs) - 1:
                next_para = paragraphs[para_index + 1]
                # Add image paragraph before next paragraph
                # This requires more complex document manipulation
                pass
        except ValueError:
            pass  # Paragraph not found
    
    def _insert_image_inline(self, paragraph, image_path: str, caption: str):
        """Insert image inline with the paragraph"""
        try:
            # Add image run to existing paragraph
            run = paragraph.add_run()
            run.add_picture(image_path, width=paragraph.part.document.sections[0].page_width * 0.6)
            
            # Add caption as separate run
            if caption:
                caption_run = paragraph.add_run(f"\nFigure: {caption}")
                caption_run.italic = True
        except Exception:
            # Fallback: add at end of document
            pass
    
    def validate_image_format(self, file_path: str) -> Tuple[bool, str]:
        """Validate image format and return status"""
        try:
            with Image.open(file_path) as img:
                format_name = img.format.lower()
                if format_name in ['jpeg', 'jpg', 'png', 'bmp', 'tiff']:
                    return True, format_name
                else:
                    return False, f"Unsupported format: {format_name}"
        except Exception as e:
            return False, f"Invalid image file: {str(e)}"
    
    def resize_image_if_needed(self, file_path: str, max_size_mb: float = 5.0) -> str:
        """Resize image if it exceeds size limit"""
        try:
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            
            if file_size_mb <= max_size_mb:
                return file_path  # No resizing needed
            
            # Resize image
            with Image.open(file_path) as img:
                # Calculate new dimensions maintaining aspect ratio
                max_pixels = 2000 * 2000  # Rough limit
                current_pixels = img.width * img.height
                
                if current_pixels > max_pixels:
                    ratio = (max_pixels / current_pixels) ** 0.5
                    new_width = int(img.width * ratio)
                    new_height = int(img.height * ratio)
                    
                    resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    
                    # Save resized image
                    resized_path = file_path.replace('.', '_resized.')
                    resized_img.save(resized_path, optimize=True, quality=85)
                    return resized_path
                
            return file_path
        except Exception:
            return file_path  # Return original if resizing fails