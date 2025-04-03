from pydantic import BaseModel, Field, EmailStr
from bson import ObjectId
from datetime import datetime
from typing import List, Dict, Optional


class UserLoginModel(BaseModel):
    username: str
    password: str

class UserRegistrationModel(BaseModel):
    username: str = Field(min_length=5, max_length=10)
    password: str = Field(min_length=5, max_length=10)

# class UserModel(BaseModel):
#     # id: Optional[ObjectId] = Field(alias='_id')
#     username: str
#     password: str
#     email: EmailStr
#     external_ids: Dict[str, Optional[str]] = {
#         "line_id": None,
#         "google_id": None
#     }
#     joined_timestamp: datetime
#     last_login: datetime
#     is_active: bool
#     role: str
#     quota: Dict
#     language: str
#     user_setting: Dict
#     notification_setting: Dict
#     tag_history: List[str]

# class Config:
#     arbitrary_types_allowed = True
#     json_encoders = {
#         ObjectId: str
#     }

# # 示例用法
# user = UserModel(
#     username="example_user",
#     password="secure_password",
#     email="user@example.com",
#     joined_timestamp=datetime.now(),
#     last_login=datetime.now(),
#     is_active=True,
#     role="user",
#     quota={},
#     language="en",
#     user_setting={},
#     notification_setting={},
#     tag_history=[]
# )

# print(user.json())