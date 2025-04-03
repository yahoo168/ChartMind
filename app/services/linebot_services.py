import os
from dotenv import load_dotenv
import asyncio

from fastapi import Request
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, ImageMessage, TextMessage, TextSendMessage

from app.services.upload_services import upload_image
from app.services.user_services import UserAuthService

from app.utils.line_utils import download_image_message
from app.utils.logging_config import logger

load_dotenv()

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

async def handle_line_webhook(request: Request):
    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()

    try:
        handler.handle(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        return {"message": "Invalid signature."}

    return {"message": "OK"}

@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    message_id = event.message.id
    user_id = event.source.user_id
    # 下載圖片
    image_path = download_image_message(line_bot_api, message_id, save_dir="temp")
    # 使用 asyncio.create_task 來運行異步任務
    asyncio.create_task(process_image_message(image_path, user_id, event.reply_token))

@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    line_id = event.source.user_id
    text = event.message.text
    # 创建异步任务处理用户文字訊息
    asyncio.create_task(process_text_message(line_id, text, event.reply_token))

async def process_text_message(line_id, text, reply_token):
    user_status = await check_and_handle_user(line_id)
    if user_status["is_new_user"]:
        user_data = user_status["user_data"]
        username, password = user_data["username"], user_data["password"]
        # Add auto-registration information to the reply
        reply_text += f"\n\n ✅ 用户初次登入，已自動註冊\n 帳號: {username}\n 帳號: {password} 連結: {None}"
        
        # Reply to the user with the prepared message
        # 回覆使用者
        line_bot_api.reply_message(
            reply_token,
            TextSendMessage(text=reply_text)
        )

async def process_image_message(image_path, line_id, reply_token):
    try:
        # Check if user exists, if not, create a new user
        user_status = await check_and_handle_user(line_id)
        user_id = str(user_status["user_data"]["_id"])
        # Upload image to Cloudflare R2 & MongoDB
        image_url = await upload_image(image_path, user_id)
        # Success message with image URL
        reply_text = f"✅ 已收到圖表！\n\n📁 🌐 圖片連結：{image_url}"
    
    except Exception as e:
        # Log the error and prepare failure message
        logger.warning(e)
        reply_text = "❌ 圖片上傳失敗，請稍後再試。"

    # If this is a new user, add registration info to the reply
    if user_status["is_new_user"]:
        user_data = user_status["user_data"]
        username, password = user_data["username"], user_data["password"]
        # Add auto-registration information to the reply
        reply_text += f"\n\n ✅ 用户初次登入，已自動註冊\n 帳號: {username}\n 帳號: {password} 連結: {None}"
        
    # Reply to the user with the prepared message
    # 回覆使用者
    line_bot_api.reply_message(
        reply_token,
        TextSendMessage(text=reply_text)
    )

async def check_and_handle_user(line_id):
    user_service = UserAuthService()
    user_data = await user_service.get_user(by="line_id", value=line_id) #使用line_id 查找用戶是否存在
    if user_data:
        return {"user_data": user_data, "is_new_user": False}
    else:
        logger.info(f"用户 {line_id} 不存在，进行注册。")
        user_data = await user_service.create_user_from_line(line_id)
        
        return {"user_data": user_data, "is_new_user": True}

    