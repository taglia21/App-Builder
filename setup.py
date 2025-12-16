"""
Setup script for the Startup Generator package.
"""

from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="startup-generator",
    version="1.0.0",
    author="Startup Generator Team",
    description="Multi-LLM Automated Startup-Generation Engine",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/startup-generator",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Code Generators",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.11",
    install_requires=[
        "fastapi>=0.109.0",
        "uvicorn>=0.27.0",
        "pydantic>=2.5.3",
        "pydantic-settings>=2.1.0",
        "httpx>=0.26.0",
        "requests>=2.31.0",
        "aiohttp>=3.9.1",
        "pandas>=2.1.4",
        "numpy>=1.26.3",
        "scikit-learn>=1.3.2",
        "transformers>=4.36.2",
        "sentence-transformers>=2.2.2",
        "bertopic>=0.16.0",
        "nltk>=3.8.1",
        "textblob>=0.17.1",
        "sqlalchemy>=2.0.25",
        "praw>=7.7.1",
        "tweepy>=4.14.0",
        "google-api-python-client>=2.111.0",
        "PyGithub>=2.1.1",
        "newsapi-python>=0.2.7",
        "openai>=1.7.2",
        "anthropic>=0.8.1",
        "click>=8.1.7",
        "rich>=13.7.0",
        "loguru>=0.7.2",
        "pyyaml>=6.0.1",
        "jinja2>=3.1.3",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1",
            "pytest-cov>=4.1.0",
            "black>=23.12.1",
            "isort>=5.13.2",
            "flake8>=7.0.0",
            "mypy>=1.8.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "startup-generator=src.cli:cli",
        ],
    },
)
