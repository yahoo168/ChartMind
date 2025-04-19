from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone
from typing import List, Optional, Union
from bson import ObjectId

class LabelModel(BaseModel):
    user_id: ObjectId
    name: str
    description: str
    vector: List[float]
    created_timestamp: datetime = datetime.now(timezone.utc)
    updated_timestamp: Optional[datetime] = None
    is_deleted: bool = False

    model_config = {
        "arbitrary_types_allowed": True,
        "json_encoders": {
            ObjectId: str
        }
    }
    @field_validator('user_id')
    def validate_object_id(cls, v):
        if isinstance(v, str):
            return ObjectId(v)
        return v