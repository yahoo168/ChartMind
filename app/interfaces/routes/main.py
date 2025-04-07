from fastapi import APIRouter, Request, HTTPException, Body
from backend.app.infrastructure.external.linebot_services import handle_line_webhook
from backend.app.domain.entities.user import UserImageService
from app.utils.logging_utils import logger
from pydantic import BaseModel

router = APIRouter()

class UserImageRequest(BaseModel):
    user_id: str

@router.post("/user_images")
async def get_user_images(request: UserImageRequest):
    user_id = request.user_id
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID is required")
    
    logger.info(f"Received request for user ID: {user_id}")

    user_image_service= UserImageService()

    images = await user_image_service.get_user_images(user_id)  # 返回實際的圖片列表
    logger.info(f"Fetched images:")
    
    return images  # 确保返回正确的数据