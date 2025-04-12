from app.infrastructure.models.url_models import UrlModel
from app.infrastructure.daos.mongodb_base import MongodbBaseDAO, ensure_initialized
from bson import ObjectId

class UrlDAO(MongodbBaseDAO):
    def __init__(self):
        super().__init__()
        self.database_name = "Materials"
        self.collection_name = "Urls"
        
    @ensure_initialized
    async def insert_one(self, url_data: UrlModel):
        result = await self.collection.insert_one(url_data.model_dump())
        return result.inserted_id
    
    @ensure_initialized
    async def insert_many(self, urls: list[UrlModel]):
        url_dicts = [url.model_dump() for url in urls]
        result = await self.collection.insert_many(url_dicts)
        return result.inserted_ids
    
    @ensure_initialized
    async def find_urls_by_user_id(self, user_id: str):
        return await self.collection.find({"user_id": ObjectId(user_id)}).to_list(length=None)
    
    @ensure_initialized
    async def count_urls_by_user_id(self, user_id: str):
        return await self.collection.count_documents({"user_id": ObjectId(user_id)})

    @ensure_initialized
    async def delete_one(self, url_id: str):
        result = await self.collection.delete_one({"_id": ObjectId(url_id)})
        return result.deleted_count
    
    @ensure_initialized
    async def delete_many(self, url_ids: list[ObjectId]):
        result = await self.collection.delete_many({"_id": {"$in": url_ids}})
        return result.deleted_count
    
    @ensure_initialized
    async def find_unprocessed_urls(self):
        return await self.collection.find({"metadata.is_processed": False}).to_list(length=None)

    @ensure_initialized
    async def update_url_preview(self, url_id, title, thumbnail_url, description_summary, summary_vector, label_ids):
        await self.collection.update_one({"_id": ObjectId(url_id)}, {"$set": {"title": title, 
                                                                              "thumbnail_url": thumbnail_url, 
                                                                              "description.summary": description_summary, 
                                                                              "description.summary_vector": summary_vector,
                                                                              "description.labels": label_ids}})
    
    @ensure_initialized
    async def update_url_is_processed(self, url_id, is_processed):
        await self.collection.update_one({"_id": ObjectId(url_id)}, {"$set": {"metadata.is_processed": is_processed}})
    
    @ensure_initialized
    async def full_text_search(self, query_text, limit=10):
        return await super().full_text_search(query_text, limit)
    
    @ensure_initialized
    async def vector_search(self, query_vector, limit=10, num_candidates=100):
        return await super().vector_search(query_vector, limit, num_candidates)