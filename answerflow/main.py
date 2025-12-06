"""
Main entry point for AnswerFlow CLI.
"""

import argparse
import sys
import json
from pathlib import Path
from typing import List, Dict, Any

from answerflow import AnswerFlow
from answerflow.models import Question, CustomerInput, Answer
from answerflow.logger import logger, setup_logger
from answerflow.config import Config


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="AnswerFlow - Automated customer question answering using Playwright",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Answer a single question with attributes
  python -m answerflow.main -q "What is this product?" -a color=red size=large
  
  # Answer question with images
  python -m answerflow.main -q "What's in this image?" -i image1.png image2.jpg
  
  # Answer multiple questions from a file
  python -m answerflow.main --questions-file questions.json --input-file input.json
  
  # Interactive mode
  python -m answerflow.main --interactive
        """
    )
    
    # Question input
    question_group = parser.add_argument_group('Question Input')
    question_group.add_argument(
        '-q', '--question',
        help='Single question to answer'
    )
    question_group.add_argument(
        '--questions-file',
        help='JSON file containing multiple questions'
    )
    
    # Customer input
    input_group = parser.add_argument_group('Customer Input')
    input_group.add_argument(
        '-a', '--attributes',
        nargs='+',
        help='Customer attributes in key=value format'
    )
    input_group.add_argument(
        '-i', '--images',
        nargs='+',
        help='Paths to customer images'
    )
    input_group.add_argument(
        '--input-file',
        help='JSON file containing customer input (attributes and images)'
    )
    
    # Browser options
    browser_group = parser.add_argument_group('Browser Options')
    browser_group.add_argument(
        '--headless',
        action='store_true',
        help='Run browser in headless mode'
    )
    browser_group.add_argument(
        '--browser',
        choices=['chromium', 'firefox', 'webkit'],
        default='chromium',
        help='Browser type to use (default: chromium)'
    )
    browser_group.add_argument(
        '--timeout',
        type=int,
        default=30000,
        help='Browser timeout in milliseconds (default: 30000)'
    )
    
    # Other options
    parser.add_argument(
        '--url',
        help='Context URL to navigate to'
    )
    parser.add_argument(
        '--output',
        help='Output file for answers (JSON format)'
    )
    parser.add_argument(
        '--screenshot',
        help='Take a screenshot and save to this path'
    )
    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Run in interactive mode'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    return parser.parse_args()


def parse_attributes(attr_list: List[str]) -> Dict[str, Any]:
    """
    Parse attributes from key=value format.
    
    Args:
        attr_list: List of strings in key=value format
    
    Returns:
        Dictionary of attributes
    """
    attributes = {}
    for attr in attr_list:
        if '=' in attr:
            key, value = attr.split('=', 1)
            # Try to parse as number or boolean
            if value.lower() == 'true':
                value = True
            elif value.lower() == 'false':
                value = False
            elif value.isdigit():
                value = int(value)
            else:
                try:
                    value = float(value)
                except ValueError:
                    pass  # Keep as string
            
            attributes[key.strip()] = value
        else:
            logger.warning(f"Ignoring invalid attribute format: {attr}")
    
    return attributes


def load_questions_from_file(file_path: str) -> List[Question]:
    """
    Load questions from a JSON file.
    
    Args:
        file_path: Path to JSON file
    
    Returns:
        List of Question objects
    """
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    questions = []
    for q_data in data if isinstance(data, list) else [data]:
        question = Question(
            text=q_data['text'],
            category=q_data.get('category'),
            priority=q_data.get('priority', 'normal'),
            metadata=q_data.get('metadata', {})
        )
        questions.append(question)
    
    return questions


def load_input_from_file(file_path: str) -> CustomerInput:
    """
    Load customer input from a JSON file.
    
    Args:
        file_path: Path to JSON file
    
    Returns:
        CustomerInput object
    """
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    customer_input = CustomerInput(
        attributes=data.get('attributes', {}),
        metadata=data.get('metadata', {})
    )
    
    # Add images
    for image_path in data.get('images', []):
        try:
            customer_input.add_image(image_path)
        except FileNotFoundError as e:
            logger.warning(str(e))
    
    return customer_input


def save_answers(answers: List[Answer], output_path: str) -> None:
    """
    Save answers to a JSON file.
    
    Args:
        answers: List of Answer objects
        output_path: Path to output file
    """
    output_data = []
    for answer in answers:
        output_data.append({
            'question': {
                'text': answer.question.text,
                'category': answer.question.category,
                'priority': answer.question.priority,
                'timestamp': answer.question.timestamp.isoformat()
            },
            'answer': answer.text,
            'confidence': answer.confidence,
            'sources': answer.sources,
            'timestamp': answer.timestamp.isoformat()
        })
    
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    logger.info(f"Answers saved to: {output_path}")


def interactive_mode():
    """Run AnswerFlow in interactive mode."""
    print("=" * 70)
    print("AnswerFlow - Interactive Mode")
    print("=" * 70)
    print("Type 'quit' or 'exit' to stop\n")
    
    # Initialize AnswerFlow
    with AnswerFlow(headless=False) as flow:
        while True:
            try:
                # Get question
                question_text = input("\nEnter your question: ").strip()
                if question_text.lower() in ['quit', 'exit']:
                    print("Goodbye!")
                    break
                
                if not question_text:
                    continue
                
                question = Question(text=question_text)
                
                # Get attributes
                print("\nEnter attributes (key=value format, press Enter when done):")
                attributes = {}
                while True:
                    attr = input("  Attribute (or press Enter to continue): ").strip()
                    if not attr:
                        break
                    if '=' in attr:
                        key, value = attr.split('=', 1)
                        attributes[key.strip()] = value.strip()
                
                # Get images
                print("\nEnter image paths (press Enter when done):")
                images = []
                while True:
                    img_path = input("  Image path (or press Enter to continue): ").strip()
                    if not img_path:
                        break
                    if Path(img_path).exists():
                        images.append(img_path)
                    else:
                        print(f"  Warning: Image not found: {img_path}")
                
                # Create customer input
                customer_input = CustomerInput(attributes=attributes)
                for img in images:
                    customer_input.add_image(img)
                
                # Get answer
                print("\n" + "=" * 70)
                print("Processing your question...")
                print("=" * 70)
                
                answer = flow.answer_question(question, customer_input)
                
                print(f"\nAnswer:\n{answer.text}")
                print(f"\nConfidence: {answer.confidence:.2%}")
                
            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                logger.error(f"Error in interactive mode: {e}")
                print(f"Error: {e}")


def main():
    """Main entry point for AnswerFlow CLI."""
    args = parse_arguments()
    
    # Setup logging
    if args.verbose:
        setup_logger(level="DEBUG")
    
    # Interactive mode
    if args.interactive:
        interactive_mode()
        return 0
    
    # Validate input
    if not args.question and not args.questions_file:
        print("Error: Either --question or --questions-file must be provided")
        print("Use --help for usage information")
        return 1
    
    # Load questions
    questions = []
    if args.questions_file:
        questions = load_questions_from_file(args.questions_file)
    elif args.question:
        questions = [Question(text=args.question)]
    
    # Load customer input
    if args.input_file:
        customer_input = load_input_from_file(args.input_file)
    else:
        customer_input = CustomerInput()
        
        # Add attributes
        if args.attributes:
            customer_input.attributes = parse_attributes(args.attributes)
        
        # Add images
        if args.images:
            for img_path in args.images:
                try:
                    customer_input.add_image(img_path)
                except FileNotFoundError as e:
                    logger.warning(str(e))
    
    # Process questions
    try:
        with AnswerFlow(
            headless=args.headless,
            browser_type=args.browser,
            timeout=args.timeout
        ) as flow:
            # Navigate to URL if provided
            if args.url:
                flow.navigate(args.url)
            
            # Answer questions
            answers = flow.answer_multiple_questions(questions, customer_input, args.url)
            
            # Take screenshot if requested
            if args.screenshot:
                flow.take_screenshot(args.screenshot)
            
            # Display answers
            print("\n" + "=" * 70)
            print("ANSWERS")
            print("=" * 70)
            
            for idx, answer in enumerate(answers, 1):
                print(f"\nQuestion {idx}: {answer.question.text}")
                print("-" * 70)
                print(answer.text)
                print(f"Confidence: {answer.confidence:.2%}")
                print("-" * 70)
            
            # Save to file if requested
            if args.output:
                save_answers(answers, args.output)
            
            return 0
    
    except Exception as e:
        logger.error(f"Error in main execution: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
