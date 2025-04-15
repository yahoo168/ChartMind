import os
from fastapi import Request, APIRouter
from linebot import WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, ImageMessage, TextMessage, FileMessage
from app.service.linebot_service import handle_text_message, handle_image_message, handle_file_message
import asyncio

router = APIRouter()

handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# 獲取事件循環
loop = asyncio.get_event_loop()

@router.post("/callback")
async def line_webhook(request: Request):
    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()

    try:
        handler.handle(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        return {"message": "Invalid signature."}

    return {"message": "OK"}

# 處理圖片訊息
@handler.add(MessageEvent, message=ImageMessage)
def _handle_image_message(event):
    # 从event中提取图片内容和reply_token
    message_id = event.message.id
    reply_token = event.reply_token
    line_id = event.source.user_id
    line_group_id = event.source.group_id if hasattr(event.source, 'group_id') else '' #若是官方帳號，則不會有group_id
    
    # 使用已定義的事件循環運行異步函數
    loop.create_task(handle_image_message(message_id, line_id, reply_token, line_group_id))

# 處理文字訊息
@handler.add(MessageEvent, message=TextMessage)
def _handle_text_message(event):
    # 从event中提取文本内容和reply_token
    text = event.message.text
    reply_token = event.reply_token
    line_id = event.source.user_id
    line_group_id = event.source.group_id if hasattr(event.source, 'group_id') else '' #若是官方帳號，則不會有group_id
    # 使用已定義的事件循環運行異步函數
    loop.create_task(handle_text_message(text, line_id, reply_token, line_group_id))

# 處理檔案訊息
@handler.add(MessageEvent, message=FileMessage)
def _handle_file_message(event):
    # 從event中提取檔案內容和reply_token
    message_id = event.message.id
    reply_token = event.reply_token
    line_id = event.source.user_id
    line_group_id = event.source.group_id if hasattr(event.source, 'group_id') else '' #若是官方帳號，則不會有group_id
    file_name = event.message.file_name
    
    # 使用已定義的事件循環運行異步函數
    loop.create_task(handle_file_message(message_id, line_id, reply_token, file_name, line_group_id))
