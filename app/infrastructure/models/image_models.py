from pydantic import BaseModel
from bson import ObjectId
from typing import List, Optional
from app.infrastructure.models.base_models import MetadataModel, BaseDescriptionModel

class ImageDescriptionModel(BaseDescriptionModel):
    # 图像特有的描述字段
    ocr_text: str = ''
    model_config = {
        "arbitrary_types_allowed": True,
        "json_encoders": {
            ObjectId: str
        }
    }

class ImageModel(BaseModel):
    authorized_users: List[ObjectId]=[]
    uploader: ObjectId
    # File
    file_url: str
    file_type: str
    file_size: int
    
    description: ImageDescriptionModel = ImageDescriptionModel()
    metadata: MetadataModel = MetadataModel()
    # Link
    parent_file: Optional[ObjectId] = None
    file_page_num: Optional[int] = None

    model_config = {
        "arbitrary_types_allowed": True,
        "json_encoders": {
            ObjectId: str
        }
    }