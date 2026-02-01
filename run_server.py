#!/usr/bin/env python3
"""Server runner that bypasses middleware issues."""
import uvicorn
import os

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

if __name__ == "__main__":
    # Import and create app
    from src.dashboard.app import create_app
    app = create_app()
    
    # Run the server
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
