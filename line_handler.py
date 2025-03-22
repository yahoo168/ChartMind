import os
from fastapi import Request
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, ImageMessage, TextMessage, TextSendMessage
from utils.line_utils import download_image
from utils.upload_and_store_utils import upload_and_store
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
    image_path = download_image(line_bot_api, message_id, save_dir="temp")

    # 上傳到 Cloudflare R2
    try:
        image_url = upload_and_store(image_path, user_id)
        reply_text = f"✅ 已收到圖表！\n\n📁 儲存位置：{image_path}\n🌐 圖片連結：{image_url}"
    except Exception as e:
        reply_text = f"❌ 圖片上傳失敗：{str(e)}"

    # 回覆使用者
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    user_id = event.source.user_id
    text = event.message.text

    # 回覆訊息
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=f"用戶{user_id}: {text}")
    )