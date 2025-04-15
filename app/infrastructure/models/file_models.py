from pydantic import BaseModel
from datetime import datetime, timezone
from typing import List, Optional
from bson import ObjectId
from app.infrastructure.models.base_models import MetadataModel, BaseDescriptionModel

# 使用基础描述模型替代重复的FileDescriptionModel
class FileDescriptionModel(BaseDescriptionModel):
    # 可以在这里添加文件特有的描述字段
    pass

class FileModel(BaseModel):
    authorized_users: List[ObjectId]=[]
    uploader: ObjectId
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