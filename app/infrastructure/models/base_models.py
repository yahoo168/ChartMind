from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Optional, List
from bson import ObjectId
from pydantic import field_validator

# 所有模型繼承自BaseModel，並使用field_validator來驗證ObjectId
# model=before，表示验证器会在 Pydantic 对字段进行任何类型转换之前运行。这对于 ObjectId 验证特别有用
# check_fields=False，表示  不要检查这些字段是否存在于当前模型中，因为它们可能存在于子类中。
class BaseModel(BaseModel):
    @field_validator('user_id', 'parent_file', 'parent_document', 'parent_text', mode='before', check_fields=False)
    def validate_object_id(cls, v):
        if isinstance(v, str) and v:
            return ObjectId(v)
        return v
    
class BaseDescriptionModel(BaseModel):
    auto_title: str = ''
    summary: str = ''
    summary_vector: List[float] = []
    labels: List[ObjectId] = []
    keywords: List[str] = []
    
    model_config = {
        "arbitrary_types_allowed": True,
        "json_encoders": {
            ObjectId: str
        }
    }

class MetadataModel(BaseModel):
    # Status
    is_deleted: bool = False
    is_processed: bool = False
    # Timestamp
    created_timestamp: datetime = datetime.now(timezone.utc)
    updated_timestamp: datetime = datetime.now(timezone.utc)
    processed_timestamp: Optional[datetime] = None
    last_viewed_timestamp: Optional[datetime] = None
    
    # Upload Source
    upload_source: str = ''
    
    model_config = {
        "arbitrary_types_allowed": True
    }

    def update_timestamp(self):
        self.updated_timestamp = datetime.now(timezone.utc)
        
    def mark_processed(self):
        self.is_processed = True
        self.processed_timestamp = datetime.now(timezone.utc)
        self.update_timestamp()

    def mark_opened(self):
        self.last_opened_timestamp = datetime.now(timezone.utc)