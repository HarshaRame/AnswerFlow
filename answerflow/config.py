"""
Configuration management for AnswerFlow.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration class for AnswerFlow application."""
    
    # Browser settings
    HEADLESS: bool = os.getenv("HEADLESS", "false").lower() == "true"
    BROWSER_TYPE: str = os.getenv("BROWSER_TYPE", "chromium")
    TIMEOUT: int = int(os.getenv("TIMEOUT", "30000"))
    
    # Logging settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "answerflow.log")
    
    # Screenshot settings
    SCREENSHOT_ON_FAILURE: bool = os.getenv("SCREENSHOT_ON_FAILURE", "true").lower() == "true"
    SCREENSHOT_DIR: str = os.getenv("SCREENSHOT_DIR", "screenshots")
    
    # Answer settings
    DEFAULT_CONFIDENCE: float = float(os.getenv("DEFAULT_CONFIDENCE", "0.85"))
    
    @classmethod
    def get(cls, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get configuration value by key."""
        return os.getenv(key, default)
    
    @classmethod
    def set(cls, key: str, value: str) -> None:
        """Set configuration value."""
        os.environ[key] = value
