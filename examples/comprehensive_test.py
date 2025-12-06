#!/usr/bin/env python3
"""
Comprehensive end-to-end test demonstrating all AnswerFlow features.
"""

from answerflow import AnswerFlow, Question, CustomerInput
from pathlib import Path
import json


def test_complete_workflow():
    """Test the complete AnswerFlow workflow."""
    
    print("=" * 80)
    print("AnswerFlow - Comprehensive End-to-End Test")
    print("=" * 80)
    
    # Test 1: Basic question with attributes
    print("\n[Test 1] Basic Question with Attributes")
    print("-" * 80)
    
    question1 = Question(
        text="What are the specifications of this laptop?",
        category="technical_specs"
    )
    
    input1 = CustomerInput(
        attributes={
            "product": "Gaming Laptop",
            "cpu": "Intel i7",
            "ram": "16GB",
            "storage": "512GB SSD",
            "price": 1299.99
        }
    )
    
    with AnswerFlow(headless=True) as flow:
        answer1 = flow.answer_question(question1, input1)
        print(f"Q: {answer1.question.text}")
        print(f"A: {answer1.text}")
        print(f"Confidence: {answer1.confidence:.2%}")
    
    # Test 2: Multiple questions
    print("\n[Test 2] Multiple Questions")
    print("-" * 80)
    
    questions = [
        Question(text="What is the price?"),
        Question(text="What are the key features?"),
        Question(text="Is it in stock?")
    ]
    
    input2 = CustomerInput(
        attributes={
            "product_name": "Smart Watch Pro",
            "price": 399.99,
            "features": ["Heart Rate", "GPS", "Water Resistant"],
            "in_stock": True
        }
    )
    
    with AnswerFlow(headless=True) as flow:
        answers = flow.answer_multiple_questions(questions, input2)
        for idx, answer in enumerate(answers, 1):
            print(f"\nQ{idx}: {answer.question.text}")
            print(f"A{idx}: {answer.text[:150]}...")
    
    # Test 3: With images
    print("\n[Test 3] Question with Images")
    print("-" * 80)
    
    question3 = Question(text="Analyze this product image")
    
    input3 = CustomerInput(
        attributes={
            "category": "Electronics",
            "brand": "TechCorp"
        }
    )
    
    # Add test image if it exists
    test_image = Path("examples/sample_product.png")
    if test_image.exists():
        input3.add_image(str(test_image))
        print(f"Added image: {test_image}")
    
    with AnswerFlow(headless=True) as flow:
        answer3 = flow.answer_question(question3, input3)
        print(f"Q: {answer3.question.text}")
        print(f"A: {answer3.text[:200]}...")
        print(f"Images processed: {len(input3.image_paths)}")
    
    # Test 4: Save to JSON
    print("\n[Test 4] Save Answer to JSON")
    print("-" * 80)
    
    output_file = "/tmp/test_answers.json"
    question4 = Question(text="Test JSON output")
    input4 = CustomerInput(attributes={"test": "value"})
    
    with AnswerFlow(headless=True) as flow:
        answer4 = flow.answer_question(question4, input4)
        
        # Save answer
        output_data = {
            "question": answer4.question.text,
            "answer": answer4.text,
            "confidence": answer4.confidence,
            "timestamp": answer4.timestamp.isoformat()
        }
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"Answer saved to: {output_file}")
        
        # Verify saved file
        with open(output_file, 'r') as f:
            loaded_data = json.load(f)
            print(f"Loaded question: {loaded_data['question']}")
            print(f"Confidence: {loaded_data['confidence']:.2%}")
    
    # Test 5: Browser interaction (screenshots only - network may be limited)
    print("\n[Test 5] Screenshot Capability")
    print("-" * 80)
    
    with AnswerFlow(headless=True) as flow:
        # Take a screenshot of blank page
        screenshot_path = flow.take_screenshot("/tmp/test_screenshot.png")
        print(f"Screenshot saved: {screenshot_path}")
        print(f"Screenshot exists: {Path(screenshot_path).exists()}")
    
    print("\n" + "=" * 80)
    print("All tests completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    test_complete_workflow()
