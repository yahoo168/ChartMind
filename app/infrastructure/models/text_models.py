from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId
from app.infrastructure.models.base_models import MetadataModel

class TextDescriptionModel(BaseModel):
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

class TextModel(BaseModel):
    user_id: ObjectId
    content: str
    description: TextDescriptionModel = TextDescriptionModel()
    metadata: MetadataModel = MetadataModel()
    # Link
    parent_document: Optional[ObjectId] = None
    parent_file: Optional[ObjectId] = None
    file_page_num: Optional[int] = None
    child_urls: List[ObjectId] = []
    model_config = {
        "arbitrary_types_allowed": True,
        "json_encoders": {
            ObjectId: str
        }
    }
    