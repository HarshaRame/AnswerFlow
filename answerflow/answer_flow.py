"""
Core AnswerFlow automation class using Playwright.
"""

import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext

from answerflow.config import Config
from answerflow.models import Question, Answer, CustomerInput
from answerflow.image_processor import ImageProcessor
from answerflow.logger import logger


class AnswerFlow:
    """
    Main class for AnswerFlow automation.
    Handles browser automation to answer customer questions based on images and attributes.
    """
    
    def __init__(
        self,
        headless: Optional[bool] = None,
        browser_type: Optional[str] = None,
        timeout: Optional[int] = None
    ):
        """
        Initialize AnswerFlow.
        
        Args:
            headless: Run browser in headless mode
            browser_type: Browser type (chromium, firefox, webkit)
            timeout: Default timeout in milliseconds
        """
        self.headless = headless if headless is not None else Config.HEADLESS
        self.browser_type = browser_type or Config.BROWSER_TYPE
        self.timeout = timeout or Config.TIMEOUT
        
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        self.image_processor = ImageProcessor()
        
        logger.info(f"AnswerFlow initialized (browser: {self.browser_type}, headless: {self.headless})")
    
    def start(self) -> None:
        """Start the browser and create a new page."""
        try:
            self.playwright = sync_playwright().start()
            
            # Get browser based on type
            if self.browser_type == "firefox":
                self.browser = self.playwright.firefox.launch(headless=self.headless)
            elif self.browser_type == "webkit":
                self.browser = self.playwright.webkit.launch(headless=self.headless)
            else:
                self.browser = self.playwright.chromium.launch(headless=self.headless)
            
            self.context = self.browser.new_context()
            self.context.set_default_timeout(self.timeout)
            self.page = self.context.new_page()
            
            logger.info("Browser started successfully")
        except Exception as e:
            logger.error(f"Error starting browser: {e}")
            raise
    
    def stop(self) -> None:
        """Stop the browser and cleanup resources."""
        try:
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            
            logger.info("Browser stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping browser: {e}")
            raise
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
    
    def process_customer_input(self, customer_input: CustomerInput) -> Dict[str, Any]:
        """
        Process customer input (images and attributes).
        
        Args:
            customer_input: CustomerInput object containing images and attributes
        
        Returns:
            Processed input data
        """
        processed_data = {
            "attributes": customer_input.attributes.copy(),
            "images": [],
            "metadata": customer_input.metadata.copy()
        }
        
        # Process images
        for image_path in customer_input.image_paths:
            try:
                if self.image_processor.validate_image(image_path):
                    image_info = self.image_processor.get_image_info(image_path)
                    image_data = {
                        "path": image_path,
                        "info": image_info,
                        "base64": self.image_processor.encode_image_to_base64(image_path)
                    }
                    processed_data["images"].append(image_data)
                    logger.info(f"Processed image: {image_path}")
            except Exception as e:
                logger.warning(f"Failed to process image {image_path}: {e}")
        
        return processed_data
    
    def answer_question(
        self,
        question: Question,
        customer_input: CustomerInput,
        context_url: Optional[str] = None
    ) -> Answer:
        """
        Answer a customer question based on provided input.
        
        Args:
            question: Question object containing the customer's question
            customer_input: CustomerInput with images and attributes
            context_url: Optional URL to navigate to for context
        
        Returns:
            Answer object containing the response
        """
        logger.info(f"Processing question: {question.text}")
        
        # Ensure browser is started
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first or use context manager.")
        
        # Process customer input
        processed_input = self.process_customer_input(customer_input)
        
        # Navigate to context URL if provided
        if context_url:
            try:
                self.page.goto(context_url)
                logger.info(f"Navigated to: {context_url}")
            except Exception as e:
                logger.warning(f"Failed to navigate to {context_url}: {e}")
        
        # Build answer based on question and input
        answer_text = self._generate_answer(question, processed_input)
        
        # Create answer object
        answer = Answer(
            question=question,
            text=answer_text,
            confidence=0.85,  # Default confidence
            metadata={
                "processed_input": processed_input,
                "context_url": context_url
            }
        )
        
        logger.info(f"Generated answer: {answer.text[:100]}...")
        return answer
    
    def _generate_answer(self, question: Question, processed_input: Dict[str, Any]) -> str:
        """
        Generate an answer based on the question and processed input.
        
        Args:
            question: The customer question
            processed_input: Processed customer input data
        
        Returns:
            Generated answer text
        """
        # This is a basic implementation that can be extended with AI/ML models
        attributes = processed_input.get("attributes", {})
        images = processed_input.get("images", [])
        
        answer_parts = []
        
        # Include information about attributes
        if attributes:
            answer_parts.append(f"Based on the provided attributes:")
            for key, value in attributes.items():
                answer_parts.append(f"- {key}: {value}")
        
        # Include information about images
        if images:
            answer_parts.append(f"\nAnalyzed {len(images)} image(s):")
            for idx, img in enumerate(images, 1):
                info = img.get("info", {})
                answer_parts.append(
                    f"- Image {idx}: {info.get('format', 'Unknown')} "
                    f"({info.get('width', 0)}x{info.get('height', 0)})"
                )
        
        # Generate response based on question
        answer_parts.append(f"\nRegarding your question: '{question.text}'")
        answer_parts.append(
            "The answer has been generated based on the provided information. "
            "This automation system processes your images and attributes to provide relevant responses."
        )
        
        return "\n".join(answer_parts)
    
    def answer_multiple_questions(
        self,
        questions: List[Question],
        customer_input: CustomerInput,
        context_url: Optional[str] = None
    ) -> List[Answer]:
        """
        Answer multiple customer questions.
        
        Args:
            questions: List of Question objects
            customer_input: CustomerInput with images and attributes
            context_url: Optional URL for context
        
        Returns:
            List of Answer objects
        """
        answers = []
        
        for question in questions:
            try:
                answer = self.answer_question(question, customer_input, context_url)
                answers.append(answer)
            except Exception as e:
                logger.error(f"Error answering question '{question.text}': {e}")
                # Create error answer
                error_answer = Answer(
                    question=question,
                    text=f"Error processing question: {str(e)}",
                    confidence=0.0
                )
                answers.append(error_answer)
        
        return answers
    
    def take_screenshot(self, path: Optional[str] = None) -> str:
        """
        Take a screenshot of the current page.
        
        Args:
            path: Optional path to save the screenshot
        
        Returns:
            Path to the saved screenshot
        """
        if not self.page:
            raise RuntimeError("Browser not started")
        
        # Create screenshots directory if it doesn't exist
        screenshot_dir = Path(Config.SCREENSHOT_DIR)
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        
        if path is None:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = str(screenshot_dir / f"screenshot_{timestamp}.png")
        
        self.page.screenshot(path=path)
        logger.info(f"Screenshot saved: {path}")
        return path
    
    def navigate(self, url: str) -> None:
        """
        Navigate to a URL.
        
        Args:
            url: URL to navigate to
        """
        if not self.page:
            raise RuntimeError("Browser not started")
        
        self.page.goto(url)
        logger.info(f"Navigated to: {url}")
    
    def execute_script(self, script: str) -> Any:
        """
        Execute JavaScript on the page.
        
        Args:
            script: JavaScript code to execute
        
        Returns:
            Result of the script execution
        """
        if not self.page:
            raise RuntimeError("Browser not started")
        
        result = self.page.evaluate(script)
        logger.debug(f"Executed script: {script[:50]}...")
        return result
