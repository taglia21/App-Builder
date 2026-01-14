"""CRUD operations for Lead."""

from app.crud.base import CRUDBase
from app.models.lead import Lead
from app.schemas.lead import LeadCreate, LeadUpdate


class CRUDLead(CRUDBase[Lead, LeadCreate, LeadUpdate]):
    pass


crud_lead = CRUDLead(Lead)
