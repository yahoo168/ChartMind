from pydantic import BaseModel
from datetime import datetime, timezone
from typing import List, Optional
from bson import ObjectId

class UrlDescriptionModel(BaseModel):
    title: str = ''
    summary: str = ''
    summary_vector: List[float] = []
    labels: List[ObjectId] = []
    model_config = {
        "arbitrary_types_allowed": True,
        "json_encoders": {
            ObjectId: str
        }
    }

class UrlModel(BaseModel):
    url: str
    user_id: ObjectId
    source: str
    description: UrlDescriptionModel = UrlDescriptionModel()
    created_timestamp: datetime = datetime.now(timezone.utc)
    updated_timestamp: Optional[datetime] = None
    is_deleted: bool = False
    is_processed: bool = False
    processed_timestamp: Optional[datetime] = None
    # Link
    parent_text: Optional[ObjectId] = None
    model_config = {
        "arbitrary_types_allowed": True,
        "json_encoders": {
            ObjectId: str
        }
    }

class TextDescriptionModel(BaseModel):
    title: str = ''
    summary: str = ''
    summary_vector: List[float] = []
    labels: List[ObjectId] = []
    model_config = {
        "arbitrary_types_allowed": True,
        "json_encoders": {
            ObjectId: str
        }
    }

class TextModel(BaseModel):
    content: str
    user_id: ObjectId
    source: str
    description: TextDescriptionModel = TextDescriptionModel()
    created_timestamp: datetime = datetime.now(timezone.utc)
    updated_timestamp: datetime = datetime.now(timezone.utc)
    is_deleted: bool = False
    is_processed: bool = False
    processed_timestamp: Optional[datetime] = None
    # Link
    parent_document: Optional[ObjectId] = None
    document_page_num: Optional[int] = None
    child_urls: List[ObjectId] = []
    model_config = {
        "arbitrary_types_allowed": True,
        "json_encoders": {
            ObjectId: str
        }
    }
    