from app.infrastructure.daos.mongodb_base import MongodbBaseDAO, ensure_initialized
from app.infrastructure.models.text_models import TextModel, UrlModel
from bson import ObjectId

class TextDAO(MongodbBaseDAO):
    def __init__(self):
        super().__init__()
        self.database_name = "Materials"
        self.collection_name = "Texts"
    
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
    async def find_texts_by_user_id(self, user_id: str):
        return await self.collection.find({"user_id": ObjectId(user_id)}).to_list(length=None)
    
    @ensure_initialized
    async def count_texts_by_user_id(self, user_id: str):
        return await self.collection.count_documents({"user_id": ObjectId(user_id)})

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
