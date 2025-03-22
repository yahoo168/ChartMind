from fastapi import FastAPI, Request
from line_handler import handle_line_webhook
import logging

app = FastAPI()
logger = logging.getLogger("uvicorn.error")  # 使用 uvicorn 的 log 管道

@app.post("/callback")
async def callback(request: Request):
    logger.info("[log] Received request from LINE webhook.")
    return await handle_line_webhook(request)
