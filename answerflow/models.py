"""
Data models for AnswerFlow.
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class Question:
    """Represents a customer question."""
    
    text: str
    category: Optional[str] = None
    priority: Optional[str] = "normal"
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __str__(self) -> str:
        return f"Question: {self.text}"


@dataclass
class CustomerInput:
    """Represents customer input including attributes and images."""
    
    attributes: Dict[str, Any] = field(default_factory=dict)
    image_paths: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_attribute(self, key: str, value: Any) -> None:
        """Add an attribute to the input."""
        self.attributes[key] = value
    
    def add_image(self, image_path: str) -> None:
        """Add an image path to the input."""
        if Path(image_path).exists():
            self.image_paths.append(image_path)
        else:
            raise FileNotFoundError(f"Image not found: {image_path}")
    
    def get_attribute(self, key: str, default: Any = None) -> Any:
        """Get an attribute value."""
        return self.attributes.get(key, default)
    
    def has_images(self) -> bool:
        """Check if input has images."""
        return len(self.image_paths) > 0


@dataclass
class Answer:
    """Represents an answer to a customer question."""
    
    question: Question
    text: str
    confidence: float = 0.0
    sources: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __str__(self) -> str:
        return f"Answer: {self.text} (confidence: {self.confidence:.2f})"
    
    def add_source(self, source: str) -> None:
        """Add a source to the answer."""
        if source not in self.sources:
            self.sources.append(source)
