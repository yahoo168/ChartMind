import os
from fastapi import Request
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, ImageMessage, TextSendMessage
from utils.line_utils import download_image
from dotenv import load_dotenv

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
    image_path = download_image(line_bot_api, message_id, save_dir="images")

    # 回覆訊息
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=f"已收到圖表，儲存於：{image_path}")
    )
