from app.infrastructure.daos.content_dao import ContentDAO, ensure_initialized
from app.infrastructure.models.url_models import UrlModel
from bson import ObjectId
from typing import List

class UrlDAO(ContentDAO[UrlModel]):
    def __init__(self):
        super().__init__(model_class=UrlModel)
        self.collection_name = "Urls"
    
    @ensure_initialized
    async def update_url_preview(self, url_id: str, title: str, thumbnail_url: str, 
                                description_summary: str, summary_vector: List[float], 
                                label_ids: List[ObjectId]):
        """更新URL预览信息"""
        result = await self.collection.update_one(
            {"_id": ObjectId(url_id)}, 
            {"$set": {
                "title": title, 
                "thumbnail_url": thumbnail_url, 
                "description.summary": description_summary, 
                "description.summary_vector": summary_vector,
                "description.labels": label_ids
            }}
        )
        return result.modified_count