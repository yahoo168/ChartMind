from app.infrastructure.daos.mongodb_base import MongodbBaseDAO, ensure_initialized
from app.infrastructure.models.file_models import FileModel, FileDescriptionModel
from bson import ObjectId

class FileDAO(MongodbBaseDAO):
    def __init__(self):
        super().__init__()
        self.database_name = "Materials"
        self.collection_name = "Files"

    @ensure_initialized
    async def insert_one(self, document_data: FileModel):
        result = await self.collection.insert_one(document_data.model_dump())
        return result.inserted_id
    
    @ensure_initialized
    async def update_description(self, document_id: str, description: FileDescriptionModel):
        result = await self.collection.update_one(
            {"_id": ObjectId(document_id)},
            {"$set": {"description": description.model_dump()}}
        )
        return result.modified_count

    @ensure_initialized
    async def update_child_texts(self, document_id: str, text_ids: list[ObjectId]):
        result = await self.collection.update_one(
            {"_id": ObjectId(document_id)},
            {"$set": {"child_texts": text_ids}}
        )
        return result.modified_count