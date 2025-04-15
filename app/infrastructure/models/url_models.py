from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId
from app.infrastructure.models.base_models import MetadataModel, BaseDescriptionModel

class UrlDescriptionModel(BaseDescriptionModel):
    # URL特有的描述字段可以在这里添加
    pass

class UrlModel(BaseModel):
    authorized_users: List[ObjectId]=[]
    uploader: ObjectId

    url: str
    title: str = ''
    thumbnail_url: str = ''
    
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