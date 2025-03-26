import os
from fastapi import FastAPI, Request, HTTPException, APIRouter
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from pydantic import BaseModel

from app.models.user_models import UserModel, UserRegistrationModel
from app.services.linebot_services import handle_line_webhook
from app.utils.logging_config import logger
from app.utils.mongodb_utils import MongoDB

router = APIRouter()

@router.get("/test")
async def test():
    logger.info("測試 API 呼叫")
    return JSONResponse(status_code=200, content={"message": "API 測試成功"})

@router.post("/register")
async def register(user: UserRegistrationModel):
    db = MongoDB.get_db()
    existing_user = await db.users.find_one({"username": user.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    await db.users.insert_one(user.model_dump())
    return JSONResponse(status_code=201, content={"message": "User registered"})

@router.post("/login")
async def login(user: UserModel):
    db = MongoDB.get_db()
    db_user = await db.users.find_one({"email": user.email, "password": user.password})
    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return JSONResponse(status_code=200, content={"message": "Login successful"})

# @app.get("/images")
# async def get_images():
#     images = await db.images.find().to_list(100)
#     return JSONResponse(status_code=200, content=images)