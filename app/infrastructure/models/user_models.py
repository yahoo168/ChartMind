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
    external_ids: Dict[str, Optional[str]] = {
        "line_id": None,
        "google_id": None
    }