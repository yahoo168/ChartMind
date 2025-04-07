from pydantic import BaseModel
from bson import ObjectId
from datetime import datetime, timezone
from typing import List, Dict, Optional
from app.infrastructure.models.base_models import PyObjectId

class ImageCommentModel(BaseModel):
    text: str
    timestamp: datetime
    source: str  # 'user' / 'gpt'
    is_deleted: bool

class ImageDescriptionModel(PyObjectId):
    title: str = ''
    summary: str = ''
    summary_vector: List[float] = []
    labels: List[ObjectId] = []
    label_names: List[str] = []
    ocr_text: str = ''
    is_processed: bool = False
    processed_timestamp: Optional[datetime] = None
    updated_timestamp: Optional[datetime] = None

class ImageModel(PyObjectId):
    user_id: ObjectId
    file_name: str
    file_url: str
    source: str
    file_size: int
    content_type: str

    thumbnail_url: str = ''
    created_timestamp: datetime= datetime.now(timezone.utc),
    is_deleted: bool = False
    description: ImageDescriptionModel
    comments: List[ImageCommentModel] = []
    metadata: Dict = {}