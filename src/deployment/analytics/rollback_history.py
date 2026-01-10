
import logging
from .deployment_tracker import DeploymentTracker

logger = logging.getLogger(__name__)

class RollbackManager:
    """
    Manages rollback history and logic validation.
    """
    
    def __init__(self, tracker: DeploymentTracker):
        self.tracker = tracker

    async def can_rollback(self, deployment_id: str) -> bool:
        """
        Check if a deployment is valid to rollback TO.
        """
        deploy = self.tracker.get_deployment(deployment_id)
        if not deploy:
            return False
            
        return deploy.get("success", False)

    async def record_rollback(self, from_id: str, to_id: str):
        """
        Log a rollback event.
        """
        # In a real system, we'd log this as a special deployment type or separate table
        logger.info(f"ROLLBACK RECORDED: {from_id} -> {to_id}")
