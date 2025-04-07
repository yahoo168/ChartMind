from pydantic import BaseModel
from bson import ObjectId

# 创建自定义基础模型
class PyObjectId(BaseModel):
    model_config = {
        "arbitrary_types_allowed": True,
        "json_encoders": {
            ObjectId: str  # 在序列化模型為 JSON 時生效，例如當你調用 model.json() 或 model.dict() 方法時
        }
    }