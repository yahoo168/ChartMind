from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import List, Optional
from bson import ObjectId

from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone
from typing import List, Optional, Union
from bson import ObjectId

class LabelModel(BaseModel):
    # id: Optional[str] = Field(None, alias="_id")
    name: str
    user_id: Union[str, ObjectId]  # 接受字符串或ObjectId
    vector: List[float]
    created_timestamp: datetime = datetime.now(timezone.utc)
    updated_timestamp: datetime = None
    is_deleted: bool = False

    @field_validator('user_id')
    def validate_object_id(cls, v):
        if isinstance(v, str):
            return ObjectId(v)
        return v

    model_config = {
        "arbitrary_types_allowed": True,
        "json_encoders": {
            ObjectId: str
        }
    }