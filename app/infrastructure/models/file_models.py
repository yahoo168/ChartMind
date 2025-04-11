from pydantic import BaseModel
from datetime import datetime, timezone
from typing import List, Optional
from bson import ObjectId
from app.infrastructure.models.base_models import MetadataModel

class FileDescriptionModel(BaseModel):
    auto_title: str = ''
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
    user_id: ObjectId
    # File
    title: str = ''
    file_url: str = ''
    file_type: str
    file_size: int
    
    description: FileDescriptionModel = FileDescriptionModel()
    metadata: MetadataModel = MetadataModel()
    # Link
    child_texts: List[ObjectId] = []
    child_images: List[ObjectId] = []
    
    model_config = {
        "arbitrary_types_allowed": True,
        "json_encoders": {
            ObjectId: str
        }
    }