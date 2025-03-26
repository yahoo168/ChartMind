# app/api/api_v1.py
from fastapi import APIRouter
from app.api.routes import auth, linebot

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(linebot.router, prefix="/linebot", tags=["LINE Bot"])  # ← 加這行
