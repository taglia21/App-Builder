"""CRUD operations for AutomationWorkflow."""

from app.crud.base import CRUDBase
from app.models.automationworkflow import AutomationWorkflow
from app.schemas.automationworkflow import AutomationWorkflowCreate, AutomationWorkflowUpdate


class CRUDAutomationWorkflow(
    CRUDBase[AutomationWorkflow, AutomationWorkflowCreate, AutomationWorkflowUpdate]
):
    pass


crud_automationworkflow = CRUDAutomationWorkflow(AutomationWorkflow)
