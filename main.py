#!/usr/bin/env python3
"""
⚡ Valeric - AI-Powered Startup Builder

Generate validated startup ideas and production-ready applications
using AI with real-time market intelligence.

Usage:
    python main.py generate --demo          # Try with sample data
    python main.py generate                 # Use real AI providers
    python main.py providers                # List available providers

For more: python main.py --help
"""

from src.cli import cli

if __name__ == "__main__":
    cli()
