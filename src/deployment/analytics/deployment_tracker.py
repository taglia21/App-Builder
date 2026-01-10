
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from ..models import DeploymentResult

logger = logging.getLogger(__name__)

class DeploymentTracker:
    """
    Tracks deployment history.
    Currently uses a JSON file, but designed to swap for SQL.
    """
    
    def __init__(self, storage_path: str = ".deployments.json"):
        self.storage_path = Path(storage_path)

    async def record_deployment(self, result: DeploymentResult):
        """
        Save the deployment result.
        """
        history = self._load_history()
        history.append(result.model_dump(mode='json'))
        self._save_history(history)
        logger.info(f"Recorded deployment {result.deployment_id}")

    def get_history(self) -> List[dict]:
        return self._load_history()

    def get_deployment(self, deployment_id: str) -> Optional[dict]:
        history = self._load_history()
        for d in history:
            if d.get("deployment_id") == deployment_id:
                return d
        return None

    def _load_history(self) -> List[dict]:
        if not self.storage_path.exists():
            return []
        try:
            with open(self.storage_path, "r") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_history(self, history: List[dict]):
        with open(self.storage_path, "w") as f:
            json.dump(history, f, indent=2)
