from fastapi import APIRouter
from . import user
from . import server
from . import config
from . import shop

api_v1_router = APIRouter()

api_v1_router.include_router(user.router, prefix='/users', tags=['API - Users'])
api_v1_router.include_router(server.router, prefix='/server', tags=['API - Server'])
api_v1_router.include_router(config.router, prefix='/config')
api_v1_router.include_router(shop.router, tags=['API - Shop'])