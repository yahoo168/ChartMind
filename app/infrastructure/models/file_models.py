from pydantic import BaseModel
from datetime import datetime, timezone
from typing import List, Optional
from bson import ObjectId

class FileDescriptionModel(BaseModel):
    summary: str = ''
    summary_vector: List[float] = []
    labels: List[ObjectId] = []
    model_config = {
        "arbitrary_types_allowed": True,
        "json_encoders": {
            ObjectId: str
        }
    }

class FileModel(BaseModel):
    title: str = ''
    url: str = ''
    file_type: str
    user_id: ObjectId
    source: str
    description: FileDescriptionModel = FileDescriptionModel()
    created_timestamp: datetime = datetime.now(timezone.utc)
    updated_timestamp: datetime = datetime.now(timezone.utc)
    is_deleted: bool = False
    is_processed: bool = False
    processed_timestamp: Optional[datetime] = None
    # Link
    child_texts: List[ObjectId] = []
    child_images: List[ObjectId] = []
    model_config = {
        "arbitrary_types_allowed": True,
        "json_encoders": {
            ObjectId: str
        }
    }