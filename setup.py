from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="answerflow",
    version="0.1.0",
    author="HarshaRame",
    description="A Python Playwright-based automation that answers customer questions based on image and attribute inputs",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/HarshaRame/AnswerFlow",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "playwright>=1.40.0",
        "python-dotenv>=1.0.0",
        "Pillow>=10.0.0",
        "requests>=2.31.0",
        "pydantic>=2.0.0",
    ],
    entry_points={
        "console_scripts": [
            "answerflow=answerflow.main:main",
        ],
    },
)
