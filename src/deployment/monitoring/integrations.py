
from typing import Dict, Any

class MonitoringIntegrations:
    """
    Generates configuration and connection details for monitoring tools.
    """
    
    def generate_sentry_config(self, dsn: str, project_type: str) -> Dict[str, Any]:
        """Generate Sentry config snippet."""
        if project_type == "nextjs":
            return {
                "file": "sentry.client.config.js",
                "content": f"""
import * as Sentry from "@sentry/nextjs";

Sentry.init({{
  dsn: "{dsn}",
  tracesSampleRate: 1.0,
}});
"""
            }
        elif project_type == "python":
             return {
                "file": "sentry_config.py",
                "content": f"""
import sentry_sdk

sentry_sdk.init(
    dsn="{dsn}",
    traces_sample_rate=1.0,
)
"""
            }
        return {}

    def generate_logrocket_config(self, app_id: str) -> Dict[str, Any]:
        """Generate LogRocket setup for frontend."""
        return {
            "file": "monitor.js",
            "content": f"""
import LogRocket from 'logrocket';
LogRocket.init('{app_id}');
"""
        }
