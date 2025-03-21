from fastapi import FastAPI, Request
from line_handler import handle_line_webhook

app = FastAPI()

@app.post("/callback")
async def callback(request: Request):
    return await handle_line_webhook(request)
