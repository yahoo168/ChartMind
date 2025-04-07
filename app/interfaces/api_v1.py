# app/api/api_v1.py
from fastapi import APIRouter
from app.interfaces.api import auth, linebot, main

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(main.router, prefix="/main", tags=["Main"])
api_router.include_router(linebot.router, prefix="/linebot", tags=["LINE Bot"])
