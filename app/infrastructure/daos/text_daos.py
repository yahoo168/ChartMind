from app.infrastructure.daos.content_dao import ContentDAO, ensure_initialized
from app.infrastructure.models.text_models import TextModel, TextDescriptionModel
from bson import ObjectId
from typing import List

class TextDAO(ContentDAO[TextModel]):
    def __init__(self):
        super().__init__(model_class=TextModel)
        self.collection_name = "Texts"
    
    @ensure_initialized
    async def update_child_urls(self, text_id: str, url_ids: List[ObjectId]):
        """更新文本关联的 URL IDs"""
        result = await self.collection.update_one(
            {"_id": ObjectId(text_id)}, 
            {"$set": {"child_urls": url_ids}}
        )
        return result.modified_count
    
    @ensure_initialized
    async def update_text_description(self, text_id: str, text_description: TextDescriptionModel):
        """更新文本描述信息"""
        result = await self.collection.update_one(
            {"_id": ObjectId(text_id)}, 
            {"$set": {"description": text_description.model_dump()}}
        )
        return result.modified_count