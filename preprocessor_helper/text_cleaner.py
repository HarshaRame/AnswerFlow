"""
Text Cleaning Utilities
Handles UTF-8 cleaning and text normalization.
"""

import unicodedata
import pandas as pd


class TextCleaner:
    """Handles text cleaning and UTF-8 normalization."""
    
    def __init__(self):
        """Initialize the text cleaner with corruption fixes."""
        self.corruption_fixes = {
            'â€™': "'",      # Right single quotation mark
            'â€œ': '"',      # Left double quotation mark
            'â€': '"',       # Right double quotation mark
            'â€"': '—',      # Em dash
            'â€"': '–',      # En dash
            'â€¦': '...',    # Ellipsis
            'Â': '',         # Non-breaking space corruption
            'Ã©': 'é',       # e with acute accent
            'Ã¨': 'è',       # e with grave accent
            'Ã ': 'à',       # a with grave accent
            'Ã¢': 'â',       # a with circumflex
            'Ã´': 'ô',       # o with circumflex
            'Ã»': 'û',       # u with circumflex
            'Ã§': 'ç',       # c with cedilla
        }
        
        self.replacements = {
            '\x00': '',       # Null character
            '\x0b': ' ',      # Vertical tab
            '\x0c': ' ',      # Form feed
            '\r\n': '\n',     # Windows line endings
            '\r': '\n',       # Mac line endings
            '\u2018': "'",    # Left single quotation mark
            '\u2019': "'",    # Right single quotation mark
            '\u201C': '"',    # Left double quotation mark
            '\u201D': '"',    # Right double quotation mark
            '\u2013': '-',    # En dash
            '\u2014': '-',    # Em dash
            '\u2026': '...',  # Horizontal ellipsis
        }
    
    def clean_text(self, text: str) -> str:
        """
        Clean non-UTF-8 characters from text.
        
        Args:
            text: Input text to clean
            
        Returns:
            Cleaned text with valid UTF-8 encoding
        """
        if not text or pd.isna(text):
            return ""
        
        text = str(text)
        
        # Fix UTF-8 corruption patterns
        for corrupt, fixed in self.corruption_fixes.items():
            text = text.replace(corrupt, fixed)
        
        # Normalize unicode
        try:
            text = unicodedata.normalize('NFKD', text)
        except Exception:
            pass
        
        # Remove non-printable characters except newlines and tabs
        text = ''.join(char for char in text if char.isprintable() or char in '\n\t')
        
        # Replace problematic characters
        for old, new in self.replacements.items():
            text = text.replace(old, new)
        
        # Ensure UTF-8 compliance
        try:
            text = text.encode('utf-8', errors='ignore').decode('utf-8')
        except Exception:
            text = ""
        
        # Clean up extra whitespace
        text = ' '.join(text.split())
        
        return text.strip()
    
    def clean_json_recursive(self, data):
        """
        Clean Non-UTF Characters from JSON data recursively.
        
        Args:
            data: JSON data (dict, list, or primitive)
            
        Returns:
            Cleaned JSON data
        """
        if isinstance(data, dict):
            return {key: self.clean_json_recursive(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self.clean_json_recursive(item) for item in data]
        elif isinstance(data, str):
            return self.clean_text(data)
        else:
            return data
