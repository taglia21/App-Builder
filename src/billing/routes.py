"""Billing routes for subscription management."""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from ..auth.dependencies import get_current_user
from ..templates import templates

def create_billing_router():
    router = APIRouter(prefix="/billing", tags=["billing"])
    
    @router.get("/", response_class=HTMLResponse)
    async def billing_page(request: Request, user = Depends(get_current_user)):
        """Billing dashboard page."""
        return templates.TemplateResponse(
            "billing/billing.html",
            {"request": request, "user": user}
        )
    
    @router.get("/plans", response_class=HTMLResponse)
    async def plans_page(request: Request):
        """Pricing plans page."""
        return templates.TemplateResponse(
            "billing/plans.html",
            {"request": request}
        )
    
    return router
