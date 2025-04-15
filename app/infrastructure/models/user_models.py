from pydantic import BaseModel, Field, EmailStr
from bson import ObjectId
from datetime import datetime, timezone
from typing import List, Dict, Optional, Literal

class UserLoginModel(BaseModel):
    username: str
    password: str

class UserRegistrationModel(BaseModel):
    username: str = Field(min_length=5, max_length=10)
    password: str = Field(min_length=5, max_length=10)
    external_ids: Dict[str, Optional[str]] = {
        "line_id": None,
        "google_id": None
    }
    line_group_ids: List[str] = []

class UserContentMetadataModel(BaseModel):
    user_id: ObjectId
    content_id: ObjectId  # 可以是文本、文档或文件的ID
    content_type: str
    labels: List[ObjectId] = []
    
    # 添加最近读取时间戳
    last_read_timestamp: Optional[datetime] = None
    read_count: int = 0  # 可选：记录阅读次数
    
    created_timestamp: datetime = datetime.now(timezone.utc)
    updated_timestamp: datetime = datetime.now(timezone.utc)
    
    model_config = {
        "arbitrary_types_allowed": True,
        "json_encoders": {
            ObjectId: str
        }
    }
    
    def update_timestamp(self):
        self.updated_timestamp = datetime.now(timezone.utc)
        
    def update_read_timestamp(self):
        """更新阅读时间戳并增加阅读计数"""
        self.last_read_timestamp = datetime.now(timezone.utc)
        self.read_count += 1
