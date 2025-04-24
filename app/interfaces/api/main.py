from fastapi import APIRouter, Request, HTTPException, Body
from app.service.application_service import UserContentRetrievalService
from app.utils.logging_utils import logger
from pydantic import BaseModel
from app.utils.format_utils import convert_objectid_to_str
from bson import ObjectId

router = APIRouter()

class UsersContentRequest(BaseModel):
    user_id: str
    content_type: str
    label_id: str = None
    query_text: str = None

@router.post("/user_content")
async def get_user_content(request: UsersContentRequest):
    try:
        user_id = ObjectId(request.user_id)
        labels = [ObjectId(request.label_id)] if request.label_id else []
        query_text = request.query_text
        user_content_service = UserContentRetrievalService()
        
        content_type_handlers = {
            "label": lambda: user_content_service.get_user_labels(user_id),
            "image": lambda: user_content_service.get_user_images(user_id, labels, query_text),
            "text": lambda: user_content_service.get_user_texts(user_id, labels, query_text),
            "file": lambda: user_content_service.get_user_files(user_id, labels, query_text),
            "url": lambda: user_content_service.get_user_urls(user_id, labels, query_text)
        }
        
        if request.content_type not in content_type_handlers:
            raise HTTPException(status_code=400, detail="Invalid content type")
            
        content = await content_type_handlers[request.content_type]()
        
        logger.info(f"成功獲取{request.content_type}，數量: {len(content)}")
        
        return convert_objectid_to_str(content)
        
    except Exception as e:
        logger.error(f"處理請求時發生錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail=f"處理請求時發生錯誤: {str(e)}")

