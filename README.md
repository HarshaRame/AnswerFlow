# AnswerFlow

A Python Playwright-based automation tool that answers customer questions based on both image and text attribute inputs.

## Features

- 🤖 **Automated Question Answering**: Process customer questions intelligently using Playwright automation
- 🖼️ **Image Processing**: Support for multiple image formats with built-in validation and processing
- 📊 **Attribute Handling**: Accept and process structured customer data attributes
- 🌐 **Browser Automation**: Leverages Playwright for robust web automation (Chromium, Firefox, WebKit)
- 📝 **Flexible Input**: Support for both CLI arguments and JSON configuration files
- 🔄 **Batch Processing**: Answer multiple questions in a single run
- 💾 **Output Management**: Save answers in JSON format for further processing
- 📸 **Screenshot Capability**: Capture browser screenshots during automation
- 🎯 **Interactive Mode**: Run in interactive mode for real-time question answering

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Install from source

```bash
# Clone the repository
git clone https://github.com/HarshaRame/AnswerFlow.git
cd AnswerFlow

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### Install as a package

```bash
pip install -e .
```

## Quick Start

### Basic Usage

```python
from answerflow import AnswerFlow, Question, CustomerInput

# Create a question
question = Question(text="What are the key features of this product?")

# Create customer input with attributes
customer_input = CustomerInput(
    attributes={
        "product_name": "Smart Watch",
        "color": "Silver",
        "price": 299.99
    }
)

# Use AnswerFlow
with AnswerFlow(headless=True) as flow:
    answer = flow.answer_question(question, customer_input)
    print(answer.text)
```

### Command Line Interface

#### Answer a single question with attributes

```bash
python -m answerflow.main \
  --question "What is this product?" \
  --attributes color=red size=large price=49.99 \
  --headless
```

#### Answer question with images

```bash
python -m answerflow.main \
  --question "What's in this image?" \
  --images product1.png product2.jpg \
  --attributes brand=TechCo category=Electronics
```

#### Use configuration files

```bash
python -m answerflow.main \
  --questions-file examples/questions.json \
  --input-file examples/customer_input.json \
  --output answers.json
```

#### Interactive Mode

```bash
python -m answerflow.main --interactive
```

## Configuration

### Environment Variables

Create a `.env` file in the project root (see `.env.example`):

```env
# Browser Settings
HEADLESS=false
BROWSER_TYPE=chromium
TIMEOUT=30000

# Logging
LOG_LEVEL=INFO
LOG_FILE=answerflow.log

# Screenshots
SCREENSHOT_ON_FAILURE=true
SCREENSHOT_DIR=screenshots
```

### Configuration File Formats

#### Questions File (JSON)

```json
[
  {
    "text": "What are the features of this product?",
    "category": "product_info",
    "priority": "high"
  },
  {
    "text": "What is the size and color?",
    "category": "specifications",
    "priority": "normal"
  }
]
```

#### Customer Input File (JSON)

```json
{
  "attributes": {
    "product_name": "Wireless Headphones",
    "color": "Black",
    "size": "Medium",
    "price": 99.99,
    "brand": "TechAudio"
  },
  "images": [
    "path/to/image1.png",
    "path/to/image2.jpg"
  ],
  "metadata": {
    "customer_id": "CUST-12345"
  }
}
```

## API Reference

### AnswerFlow Class

Main automation class for processing questions.

```python
flow = AnswerFlow(
    headless=True,          # Run browser in headless mode
    browser_type="chromium", # Browser type: chromium, firefox, webkit
    timeout=30000           # Timeout in milliseconds
)
```

**Methods:**

- `start()`: Start the browser
- `stop()`: Stop the browser and cleanup
- `answer_question(question, customer_input, context_url=None)`: Answer a single question
- `answer_multiple_questions(questions, customer_input, context_url=None)`: Answer multiple questions
- `take_screenshot(path=None)`: Take a screenshot
- `navigate(url)`: Navigate to a URL
- `execute_script(script)`: Execute JavaScript on the page

### Question Class

Represents a customer question.

```python
question = Question(
    text="What is this product?",
    category="product_info",
    priority="high",
    metadata={"source": "web"}
)
```

### CustomerInput Class

Represents customer input including attributes and images.

```python
customer_input = CustomerInput(
    attributes={"color": "red", "size": "large"},
    metadata={"session_id": "123"}
)

# Add attributes
customer_input.add_attribute("price", 99.99)

# Add images
customer_input.add_image("product.png")
```

### Answer Class

Represents an answer to a question.

```python
answer = Answer(
    question=question,
    text="This product is...",
    confidence=0.95,
    sources=["product_db", "image_analysis"]
)
```

## Examples

See the `examples/` directory for complete examples:

- `basic_example.py`: Basic usage with attributes
- `image_example.py`: Using images with questions
- `questions.json`: Sample questions file
- `customer_input.json`: Sample input file

## Advanced Usage

### Using with Context URL

```python
with AnswerFlow() as flow:
    answer = flow.answer_question(
        question,
        customer_input,
        context_url="https://example.com/product"
    )
```

### Custom Image Processing

```python
from answerflow.image_processor import ImageProcessor

processor = ImageProcessor()

# Get image information
info = processor.get_image_info("product.png")

# Resize image
resized_path = processor.resize_image("large_image.png", max_width=1920)

# Validate image
is_valid = processor.validate_image("image.png")

# Encode to base64
base64_str = processor.encode_image_to_base64("image.png")
```

### Batch Processing

```python
questions = [
    Question(text="Question 1"),
    Question(text="Question 2"),
    Question(text="Question 3")
]

with AnswerFlow() as flow:
    answers = flow.answer_multiple_questions(questions, customer_input)
    
    for answer in answers:
        print(f"Q: {answer.question.text}")
        print(f"A: {answer.text}\n")
```

## Architecture

```
AnswerFlow/
├── answerflow/
│   ├── __init__.py           # Package initialization
│   ├── answer_flow.py        # Main AnswerFlow class
│   ├── models.py             # Data models (Question, Answer, CustomerInput)
│   ├── config.py             # Configuration management
│   ├── logger.py             # Logging utilities
│   ├── image_processor.py    # Image processing utilities
│   └── main.py               # CLI entry point
├── examples/                 # Example scripts and files
├── requirements.txt          # Python dependencies
├── setup.py                  # Package setup
├── .env.example              # Example environment variables
└── README.md                 # This file
```

## Development

### Running Tests

```bash
# Install development dependencies
pip install -r requirements.txt

# Run examples
python examples/basic_example.py
python examples/image_example.py
```

### Code Structure

- **AnswerFlow**: Main automation engine using Playwright
- **Models**: Data structures for questions, answers, and customer input
- **ImageProcessor**: Handles image validation, resizing, and encoding
- **Config**: Centralized configuration management
- **Logger**: Structured logging throughout the application

## Troubleshooting

### Playwright Installation Issues

```bash
# Install Playwright browsers manually
playwright install chromium

# Or install all browsers
playwright install
```

### Image Processing Errors

Ensure images exist and are valid formats (PNG, JPG, JPEG, etc.). Use the `validate_image()` method to check.

### Browser Not Starting

- Check if Playwright browsers are installed
- Try running with `headless=False` to see browser window
- Check logs for detailed error messages

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues and questions:
- Open an issue on [GitHub](https://github.com/HarshaRame/AnswerFlow/issues)
- Check the examples directory for usage patterns

## Roadmap

- [ ] Integration with AI/ML models for smarter answers
- [ ] Support for video inputs
- [ ] REST API interface
- [ ] Docker containerization
- [ ] Enhanced image analysis with computer vision
- [ ] Multi-language support
- [ ] Database integration for answer caching

## Acknowledgments

- Built with [Playwright](https://playwright.dev/) for browser automation
- Uses [Pillow](https://python-pillow.org/) for image processing