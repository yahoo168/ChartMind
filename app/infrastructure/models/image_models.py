from pydantic import BaseModel
from bson import ObjectId
from datetime import datetime, timezone
from typing import List, Dict, Optional, Union
from app.infrastructure.models.base_models import PyObjectId

class ImageDescriptionModel(BaseModel):
    title: str = ''
    summary: str = ''
    summary_vector: List[float] = []
    labels: List[ObjectId] = []
    ocr_text: str = ''
    is_processed: bool = False
    processed_timestamp: Optional[datetime] = None
    updated_timestamp: Optional[datetime] = None
    
    model_config = {
        "arbitrary_types_allowed": True,
        "json_encoders": {
            ObjectId: str
        }
    }

class ImageModel(BaseModel):
    user_id: ObjectId
    file_name: str
    file_url: str
    source: str
    file_size: int
    content_type: str
    thumbnail_url: str = ''
    created_timestamp: datetime= datetime.now(timezone.utc),
    is_deleted: bool = False
    description: ImageDescriptionModel = ImageDescriptionModel()
    # Link
    parent_document: Optional[ObjectId] = None

    model_config = {
        "arbitrary_types_allowed": True,
        "json_encoders": {
            ObjectId: str
        }
    }