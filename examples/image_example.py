#!/usr/bin/env python3
"""
Example script demonstrating AnswerFlow usage with images.
"""

from pathlib import Path
from answerflow import AnswerFlow, Question, CustomerInput


def main():
    """Run AnswerFlow example with images."""
    
    # Create questions
    questions = [
        Question(text="What can you tell me about this product based on the image?"),
        Question(text="What are the main colors visible?"),
        Question(text="Is this suitable for professional use?")
    ]
    
    # Create customer input with attributes and images
    customer_input = CustomerInput(
        attributes={
            "product_category": "Office Supplies",
            "brand": "Premium Brands",
            "price_range": "mid-range"
        }
    )
    
    # Add images if they exist (example paths)
    example_images = [
        "examples/product_image_1.png",
        "examples/product_image_2.jpg"
    ]
    
    for img_path in example_images:
        if Path(img_path).exists():
            customer_input.add_image(img_path)
            print(f"Added image: {img_path}")
        else:
            print(f"Skipping non-existent image: {img_path}")
    
    # Initialize and use AnswerFlow
    with AnswerFlow(headless=False) as flow:
        # Answer all questions
        answers = flow.answer_multiple_questions(questions, customer_input)
        
        # Display answers
        print("\n" + "=" * 70)
        print("QUESTION & ANSWER SESSION")
        print("=" * 70)
        
        for idx, answer in enumerate(answers, 1):
            print(f"\n[Q{idx}] {answer.question.text}")
            print("-" * 70)
            print(f"[A{idx}] {answer.text}")
            print(f"Confidence: {answer.confidence:.2%}")
            print("-" * 70)
        
        # Take a screenshot
        screenshot_path = flow.take_screenshot()
        print(f"\nScreenshot saved: {screenshot_path}")


if __name__ == "__main__":
    main()
