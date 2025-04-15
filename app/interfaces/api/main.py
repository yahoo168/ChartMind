from fastapi import APIRouter, Request, HTTPException, Body
from app.service.application_service import UserContentRetrievalService
from app.utils.logging_utils import logger
from pydantic import BaseModel
from app.utils.format_utils import convert_objectid_to_str
router = APIRouter()

class UserImageRequest(BaseModel):
    user_id: str

@router.post("/user_images")
async def get_user_images(request: UserImageRequest):
    user_id = request.user_id
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID is required")
    
    logger.info(f"Received request for user ID: {user_id}")

    images = await UserContentRetrievalService().get_user_images(user_id)  # 返回實際的圖片列表
    logger.info(f"Fetched images, Num: {len(images)}")
    # images = [convert_objectid_to_str(image) for image in images]
    return convert_objectid_to_str(images)  # 确保返回正确的数据

