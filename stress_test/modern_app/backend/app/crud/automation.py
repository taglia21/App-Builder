"""CRUD operations for Automation."""

from app.crud.base import CRUDBase
from app.models.automation import Automation
from app.schemas.automation import AutomationCreate, AutomationUpdate


class CRUDAutomation(CRUDBase[Automation, AutomationCreate, AutomationUpdate]):
    pass


crud_automation = CRUDAutomation(Automation)
