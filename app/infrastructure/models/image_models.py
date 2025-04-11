from pydantic import BaseModel
from bson import ObjectId
from typing import List, Optional
from app.infrastructure.models.base_models import MetadataModel

class ImageDescriptionModel(BaseModel):
    auto_title: str = ''
    summary: str = ''
    summary_vector: List[float] = []
    labels: List[ObjectId] = []
    ocr_text: str = ''    
    model_config = {
        "arbitrary_types_allowed": True,
        "json_encoders": {
            ObjectId: str
        }
    }

class ImageModel(BaseModel):
    user_id: ObjectId
    # File
    file_url: str
    file_size: int
    file_type: str
    
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