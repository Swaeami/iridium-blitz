"""
Shop Page Router - Renders the shop management page
"""

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from dependency import get_templates

router = APIRouter()


@router.get('/')
async def shop_page(request: Request, templates: Jinja2Templates = Depends(get_templates)):
    """Render shop management page"""
    return templates.TemplateResponse('shop.html', {'request': request})

