from app.infrastructure.daos.mongodb_base import MongodbBaseDAO, ensure_initialized
from app.infrastructure.models.text_models import TextModel
from app.infrastructure.models.url_models import UrlModel

from bson import ObjectId
from datetime import datetime, timezone

class TextDAO(MongodbBaseDAO):
    def __init__(self):
        super().__init__()
        self.database_name = "Materials"
        self.collection_name = "Texts"
    
    @ensure_initialized
    async def find(self, query: dict, projection: dict = None, sort: list = None):
        cursor = self.collection.find(query, projection=projection)
        if sort:
            cursor = cursor.sort(sort)
        result = await cursor.to_list(length=None)
        return result
    
    @ensure_initialized
    async def insert_one(self, text_data: TextModel):
        result = await self.collection.insert_one(text_data.model_dump())
        return result.inserted_id
    
    @ensure_initialized
    async def insert_many(self, texts: list[TextModel]):
        text_dicts = [text.model_dump() for text in texts]
        result = await self.collection.insert_many(text_dicts)
        return result.inserted_ids
    
    @ensure_initialized
    async def update_child_urls(self, text_id: str, url_ids: list[ObjectId]):
        await self.collection.update_one({"_id": ObjectId(text_id)}, {"$set": {"child_urls": url_ids}})
    
    @ensure_initialized
    async def update_text_description(self, text_id: str, text_summary: str, text_summary_vector: list, text_title: str):
        await self.collection.update_one({"_id": ObjectId(text_id)}, {"$set": {"description.summary": text_summary, 
                                                                               "description.summary_vector": text_summary_vector, 
                                                                               "description.auto_title": text_title}})
    
    @ensure_initialized
    async def update_text_is_processed(self, text_id: str, is_processed: bool):
        await self.collection.update_one({"_id": ObjectId(text_id)}, {"$set": {"metadata.is_processed": is_processed,
                                                                               "metadata.processed_timestamp": datetime.now(timezone.utc),
                                                                               "metadata.updated_timestamp": datetime.now(timezone.utc)
                                                                               }})
    
    @ensure_initialized
    async def find_unprocessed_texts(self):
        return await self.collection.find({"metadata.is_processed": False}).to_list(length=None)
    
    @ensure_initialized
    async def find_texts_by_user_id(self, user_id: str):
        return await self.collection.find({"user_id": ObjectId(user_id)}).to_list(length=None)
    
    @ensure_initialized
    async def count_texts_by_user_id(self, user_id: str):
        return await self.collection.count_documents({"user_id": ObjectId(user_id)})
    
    @ensure_initialized
    async def delete_one(self, url_id: str):
        result = await self.collection.delete_one({"_id": ObjectId(url_id)})
        return result.deleted_count
    
    @ensure_initialized
    async def delete_many(self, url_ids: list[ObjectId]):
        result = await self.collection.delete_many({"_id": {"$in": url_ids}})
        return result.deleted_count