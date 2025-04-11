#!/usr/bin/env python
"""
Schwab-AI Portfolio Manager

A Python application that automatically connects to your Schwab account
via the schwab-py library and uses AI/LLM APIs to analyze and manage your
portfolio with a risk-averse approach.
"""

from setuptools import setup, find_packages

setup(
    name="schwab-ai-portfolio-manager",
    version="0.1.0",
    description="AI-powered portfolio management for Charles Schwab accounts",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "schwab-py>=0.2.1",
        "pandas>=2.0.0",
        "numpy>=1.20.0",
        "matplotlib>=3.5.0",
        "seaborn>=0.11.0",
        "requests>=2.25.0",
        "aiohttp>=3.8.0",
        "anthropic>=0.16.0",
        "openai>=1.3.0",
        "yfinance>=0.2.0",
        "ta>=0.10.0",
        "python-dotenv>=0.19.0",
        "pyyaml>=6.0",
        "rich>=12.0.0",
        "schedule>=1.1.0",
        "tqdm>=4.64.0",
    ],
    entry_points={
        "console_scripts": [
            "schwab-ai=src.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)