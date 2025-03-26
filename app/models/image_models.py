from pydantic import BaseModel, Field
from bson import ObjectId
from datetime import datetime, timezone
from typing import List, Dict, Optional

class ImageCommentModel(BaseModel):
    text: str
    timestamp: datetime
    source: str  # 'user' / 'gpt'
    is_deleted: bool

class ImageDescriptionModel(BaseModel):
    tags: List[str] = []
    ocr_text: str = ''
    gpt_summary: str = ''
    comments: List[ImageCommentModel] = []

class ImageModel(BaseModel):
    user_id: str
    file_name: str
    file_url: str
    source: str
    file_size: int
    content_type: str

    thumbnail_url: str = ''
    created_timestamp: datetime= datetime.now(timezone.utc),
    status: str = 'active'
    description: ImageDescriptionModel
    metadata: Dict = {}

# class Config:
#     arbitrary_types_allowed = True
#     json_encoders = {
#         ObjectId: str
#     }

# 示例用法
# image = ImageModel(
#     user_id="user123",
#     file_name="example.jpg",
#     file_url="http://example.com/image.jpg",
#     thumbnail_url="http://example.com/thumbnail.jpg",
#     file_size=1024,
#     content_type="image/jpeg",
#     created_timestamp=datetime.now(),
#     status="active",
#     source="upload",
#     description=DescriptionModel(
#         tags=["example", "test"],
#         ocr_text="Sample OCR text",
#         gpt_summary="Sample GPT summary",
#         comments=[
#             CommentModel(
#                 text="Nice image!",
#                 timestamp=datetime.now(),
#                 source="user",
#                 is_deleted=False
#             )
#         ]
#     ),
#     metadata={}
# )

# print(image.json())