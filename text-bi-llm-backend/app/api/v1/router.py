# app/api/v1/router.py

from fastapi import APIRouter
from .endpoints import ask, po

api_router = APIRouter(prefix="/api/v1")

# POST /api/v1/ask
api_router.include_router(ask.router, tags=["ask"])
api_router.include_router(po.router,  prefix="/po",  tags=["po"]) 