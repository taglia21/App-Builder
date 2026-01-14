"""CRUD operations for CustomerInteraction."""

from app.crud.base import CRUDBase
from app.models.customerinteraction import CustomerInteraction
from app.schemas.customerinteraction import CustomerInteractionCreate, CustomerInteractionUpdate


class CRUDCustomerInteraction(
    CRUDBase[CustomerInteraction, CustomerInteractionCreate, CustomerInteractionUpdate]
):
    pass


crud_customerinteraction = CRUDCustomerInteraction(CustomerInteraction)
