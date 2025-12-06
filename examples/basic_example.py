#!/usr/bin/env python3
"""
Example script demonstrating basic AnswerFlow usage.
"""

from answerflow import AnswerFlow, Question, CustomerInput


def main():
    """Run basic AnswerFlow example."""
    
    # Create a question
    question = Question(
        text="What are the key features of this product?",
        category="product_info"
    )
    
    # Create customer input with attributes
    customer_input = CustomerInput(
        attributes={
            "product_name": "Smart Watch",
            "color": "Silver",
            "price": 299.99,
            "brand": "TechWear",
            "features": ["Heart Rate Monitor", "GPS", "Water Resistant"]
        }
    )
    
    # Initialize and use AnswerFlow
    with AnswerFlow(headless=True) as flow:
        # Answer the question
        answer = flow.answer_question(question, customer_input)
        
        # Display the answer
        print("=" * 70)
        print(f"Question: {answer.question.text}")
        print("=" * 70)
        print(f"Answer:\n{answer.text}")
        print("=" * 70)
        print(f"Confidence: {answer.confidence:.2%}")
        print("=" * 70)


if __name__ == "__main__":
    main()
