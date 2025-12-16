#!/bin/bash
echo "🚀 Starting AI Startup Generator UI..."
echo "Open http://localhost:8501 in your browser"
echo ""
echo "In Codespaces/dev containers:"
echo "1. Click 'PORTS' tab at bottom"
echo "2. Find port 8501"
echo "3. Click the globe icon to open"
echo ""
streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0
