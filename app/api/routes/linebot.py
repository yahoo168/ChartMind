# app/api/routes/linebot.py
from fastapi import APIRouter, Request
from app.services.linebot_services import handle_line_webhook

router = APIRouter()

@router.post("/callback")
async def callback(request: Request):
    # 交給 service 層處理
    return await handle_line_webhook(request)
