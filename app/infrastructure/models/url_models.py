from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId
from app.infrastructure.models.base_models import MetadataModel

class UrlDescriptionModel(BaseModel):
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
    title: str = ''
    thumbnail_url: str = ''
    user_id: ObjectId
    description: UrlDescriptionModel = UrlDescriptionModel()
    metadata: MetadataModel = MetadataModel()
    # Link
    parent_text: Optional[ObjectId] = None
    model_config = {
        "arbitrary_types_allowed": True,
        "json_encoders": {
            ObjectId: str
        }
    }