from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId
from app.infrastructure.models.base_models import MetadataModel, BaseDescriptionModel

class TextDescriptionModel(BaseDescriptionModel):
    # 文本特有的描述字段可以在这里添加
    pass

class TextModel(BaseModel):
    authorized_users: List[ObjectId] = []
    uploader: ObjectId
    
    content: str
    description: TextDescriptionModel = TextDescriptionModel()
    metadata: MetadataModel = MetadataModel()
    # Link
    parent_file: Optional[ObjectId] = None
    file_page_num: Optional[int] = None
    child_urls: List[ObjectId] = []
    
    model_config = {
        "arbitrary_types_allowed": True,
        "json_encoders": {
            ObjectId: str
        }
    }
    