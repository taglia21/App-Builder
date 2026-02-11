"""Demo mode manager for Valeric."""
import os
import logging
from typing import Dict, Optional

from .sample_projects import get_sample_project, list_sample_projects

logger = logging.getLogger(__name__)


class DemoManager:
    """Manages demo mode functionality."""

    def __init__(self):
        """Initialize demo manager."""
        self._demo_mode = self._check_demo_mode()

    def _check_demo_mode(self) -> bool:
        """Check if demo mode is enabled via environment variable."""
        demo_value = os.environ.get("DEMO_MODE", "").lower()
        return demo_value in ("true", "1", "yes")

    def is_demo_mode(self) -> bool:
        """Check if demo mode is currently enabled.
        
        Returns:
            True if demo mode is enabled
        """
        return self._demo_mode

    def requires_api_keys(self) -> bool:
        """Check if API keys are required.
        
        In demo mode, API keys are not required.
        
        Returns:
            True if API keys are required
        """
        return not self.is_demo_mode()

    async def load_sample_project(self, project_id: Optional[str] = None) -> Optional[Dict]:
        """Load a sample project for demo mode.
        
        Args:
            project_id: Optional ID of specific sample project
            
        Returns:
            Sample project dictionary or None if not in demo mode
        """
        if not self.is_demo_mode():
            logger.warning("Cannot load sample project outside demo mode")
            return None

        project = get_sample_project(project_id)
        
        if project:
            logger.info(f"Loaded sample project: {project['name']}")
        else:
            logger.warning(f"Sample project not found: {project_id}")
        
        return project

    def get_llm_client(self):
        """Get LLM client for demo mode.
        
        In demo mode, returns a mock client that doesn't require API keys.
        
        Returns:
            Mock LLM client
        """
        from src.llm.client import MockLLMClient
        
        if self.is_demo_mode():
            logger.info("Using mock LLM client in demo mode")
            return MockLLMClient()
        else:
            # In production, use the real client
            from src.llm.client import get_llm_client
            return get_llm_client()

    def get_restrictions(self) -> Dict:
        """Get demo mode restrictions.
        
        Returns:
            Dictionary of restrictions applied in demo mode
        """
        if not self.is_demo_mode():
            return {}

        return {
            "max_projects": 3,
            "max_file_size": 1024 * 100,  # 100KB
            "max_files_per_project": 20,
            "deployment_disabled": True,
            "custom_domains_disabled": True,
        }

    def add_demo_watermark(self, project: Dict) -> Dict:
        """Add demo watermark to project.
        
        Args:
            project: Project dictionary
            
        Returns:
            Project with demo watermark added
        """
        if not self.is_demo_mode():
            return project

        # Add watermark to README if it exists
        if "files" in project and "README.md" in project["files"]:
            project["files"]["README.md"] += "\n\n---\n*This is a demo project from Valeric*\n"

        # Add demo flag to project metadata
        if "metadata" not in project:
            project["metadata"] = {}
        project["metadata"]["demo"] = True
        project["metadata"]["demo_restrictions"] = self.get_restrictions()

        return project

    def list_available_projects(self) -> Dict:
        """List all available sample projects.
        
        Returns:
            Dictionary of available sample projects
        """
        if not self.is_demo_mode():
            return {}

        return list_sample_projects()
