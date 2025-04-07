from pydantic import BaseModel
from datetime import datetime, timezone
from typing import List
from bson import ObjectId

class ImageLabelModel(BaseModel):
    name: str
    user_id: ObjectId
    vector: List[float]
    created_timestamp: datetime = datetime.now(timezone.utc)
    updated_timestamp: datetime = None
    is_deleted: bool = False

    model_config = {
        "arbitrary_types_allowed": True,
        "json_encoders": {
            ObjectId: str # 在序列化模型為 JSON 時生效，例如當你調用 model.json() 或 model.dict() 方法時
        }
    }

    model_config = {
        "arbitrary_types_allowed": True,
        "json_encoders": {
            ObjectId: str # 在序列化模型為 JSON 時生效，例如當你調用 model.json() 或 model.dict() 方法時
        }
    }