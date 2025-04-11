from app.infrastructure.daos.mongodb_base import MongodbBaseDAO, ensure_initialized
from app.infrastructure.daos.text_daos import TextDAO
from app.infrastructure.models.file_models import FileModel, FileDescriptionModel
from bson import ObjectId
from typing import List
from datetime import datetime, timezone
class FileDAO(MongodbBaseDAO):
    def __init__(self):
        super().__init__()
        self.database_name = "Materials"
        self.collection_name = "Files"
        self.text_dao = TextDAO()

    @ensure_initialized
    async def insert_one(self, document_data: FileModel):
        result = await self.collection.insert_one(document_data.model_dump())
        return result.inserted_id
    
    @ensure_initialized
    async def get_child_texts(self, file_id: ObjectId):
        query = {"parent_file": file_id}
        text_docs = await self.text_dao.find(
            query, 
            projection={"content": 1, "_id": 1}, 
            sort=[("file_page_num", 1)]
        )
        child_texts = [text.get("content", "") for text in text_docs]
        return child_texts

    @ensure_initialized
    async def find_unprocessed_files(self):
        result = await self.collection.find({"metadata.is_processed": False}).to_list(length=None)
        return result
    
    @ensure_initialized
    async def update_description(self, document_id: str, description: FileDescriptionModel):
        result = await self.collection.update_one(
            {"_id": ObjectId(document_id)},
            {"$set": {"description": description.model_dump()}}
        )
        return result.modified_count
    
    @ensure_initialized
    async def update_is_processed(self, document_id: str, is_processed: bool):
        result = await self.collection.update_one(
            {"_id": ObjectId(document_id)},
            {"$set": {"metadata.is_processed": is_processed,
                      "metadata.processed_timestamp": datetime.now(timezone.utc),
                      "metadata.updated_timestamp": datetime.now(timezone.utc)}}
        )
        return result.modified_count

    @ensure_initialized
    async def update_child_texts(self, document_id: str, text_ids: list[ObjectId]):
        result = await self.collection.update_one(
            {"_id": ObjectId(document_id)},
            {"$set": {"child_texts": text_ids}}
        )
        return result.modified_count
    
    @ensure_initialized
    async def delete_one(self, document_id: str):
        result = await self.collection.delete_one({"_id": ObjectId(document_id)})
        return result.deleted_count
    