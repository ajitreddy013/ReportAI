import os
from typing import Optional

class GeminiConfig:
    """Configuration for Google Gemini API"""
    
    def __init__(self):
        self.api_key: Optional[str] = None
        self.model_name: str = "gemini-pro"
        self.temperature: float = 0.7
        self.max_tokens: int = 2048
        self.top_p: float = 0.9
        self.top_k: int = 40
        
    def load_from_env(self):
        """Load configuration from environment variables"""
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-pro")
        self.temperature = float(os.getenv("GEMINI_TEMPERATURE", "0.7"))
        self.max_tokens = int(os.getenv("GEMINI_MAX_TOKENS", "2048"))
        self.top_p = float(os.getenv("GEMINI_TOP_P", "0.9"))
        self.top_k = int(os.getenv("GEMINI_TOP_K", "40"))
        
    def is_configured(self) -> bool:
        """Check if Gemini API is properly configured"""
        return bool(self.api_key and self.api_key != "YOUR_API_KEY_HERE")
        
    def get_safety_settings(self):
        """Get safety settings for content generation"""
        return [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
        ]

# Global configuration instance
gemini_config = GeminiConfig()
gemini_config.load_from_env()