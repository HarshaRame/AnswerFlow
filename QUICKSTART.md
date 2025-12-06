# AnswerFlow Quick Start Guide

## Installation (2 minutes)

```bash
# Clone the repository
git clone https://github.com/HarshaRame/AnswerFlow.git
cd AnswerFlow

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
python -m playwright install chromium

# Install the package
pip install -e .
```

## Run Your First Question (30 seconds)

```bash
# Simple question with attributes
python -m answerflow.main \
  --question "What is this product?" \
  --attributes color=blue size=large price=49.99 \
  --headless
```

## Try the Examples (1 minute)

```bash
# Run basic example
python examples/basic_example.py

# Run comprehensive test
python examples/comprehensive_test.py

# Use example JSON files
python -m answerflow.main \
  --questions-file examples/questions.json \
  --input-file examples/customer_input.json \
  --output my_answers.json
```

## Interactive Mode

```bash
python -m answerflow.main --interactive
```

Then follow the prompts to:
1. Enter your question
2. Add attributes (optional)
3. Add image paths (optional)
4. Get your answer!

## Python API

```python
from answerflow import AnswerFlow, Question, CustomerInput

# Create question and input
question = Question(text="What are the key features?")
customer_input = CustomerInput(
    attributes={"product": "Smart Watch", "price": 299.99}
)

# Get answer
with AnswerFlow(headless=True) as flow:
    answer = flow.answer_question(question, customer_input)
    print(answer.text)
```

## Common Use Cases

### E-commerce Product Questions
```bash
python -m answerflow.main \
  -q "Is this suitable for outdoor use?" \
  -a product="Wireless Headphones" waterproof=true \
  -i product_photo.jpg
```

### Technical Support
```bash
python -m answerflow.main \
  -q "What are the system requirements?" \
  -a software="Video Editor Pro" version=2.0
```

### Batch Processing
```bash
python -m answerflow.main \
  --questions-file support_questions.json \
  --input-file customer_data.json \
  --output support_answers.json
```

## Next Steps

- Read the [full documentation](README.md)
- Explore [TEST_RESULTS.md](TEST_RESULTS.md) for detailed test outputs
- Check [examples/](examples/) for more code samples
- Customize `.env` file for your needs (copy from `.env.example`)

## Need Help?

- Check the help: `python -m answerflow.main --help`
- Open an issue on GitHub
- Review the examples in the `examples/` directory
