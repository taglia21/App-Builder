
import shutil
import os
from typing import Dict, List
from ..models import DeploymentProviderType

class ProviderDetector:
    """Detects which providers are available based on environment and tools."""
    
    @staticmethod
    def detect_available_providers() -> Dict[str, bool]:
        # Check CLIs
        vercel_cli = shutil.which("vercel") is not None
        fly_cli = shutil.which("flyctl") is not None
        aws_cli = shutil.which("aws") is not None
        
        # Check Env Vars
        render_key = "RENDER_API_KEY" in os.environ
        railway_token = "RAILWAY_TOKEN" in os.environ
        
        return {
            "vercel": vercel_cli,
            "render": render_key,
            "fly_io": fly_cli,
            "aws": aws_cli,
            "railway": railway_token
        }
