#!/bin/bash
# Setup script for Multi-LLM Startup Generation Engine

set -e

echo "🚀 Setting up Multi-LLM Startup Generation Engine..."

# Check Python version
echo "📋 Checking Python version..."
python3 --version

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "🔨 Creating virtual environment..."
    python3 -m venv venv
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo "⚡ Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Create .env from example if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your API keys!"
else
    echo "✓ .env file already exists"
fi

# Create output directories
echo "📁 Creating output directories..."
mkdir -p output/intelligence
mkdir -p output/ideas
mkdir -p output/prompts
mkdir -p output/generated

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Activate the virtual environment: source venv/bin/activate"
echo "2. Edit .env and add your API keys"
echo "3. Run: python src/cli.py generate --help"
echo ""
