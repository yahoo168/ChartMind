from bson import ObjectId
from app.infrastructure.daos.mongodb_base import MongodbBaseDAO, ensure_initialized
from app.infrastructure.models.label_models import ImageLabelModel

class ImageLabelDAO(MongodbBaseDAO):
    def __init__(self):
        super().__init__()
        self.database_name = "Materials"
        self.collection_name = "Labels"
    
    @ensure_initialized
    async def insert_one(self, label_data: ImageLabelModel):
        inserted_id = await self.collection.insert_one(label_data.model_dump())
        return inserted_id
    
    @ensure_initialized
    async def find_labels_by_user_id(self, user_id: str):
        data = await self.collection.find({"user_id": ObjectId(user_id)}).to_list(length=None)
        return self.convert_objectid_to_str(data)
    
    @ensure_initialized
    async def count_labels_by_user_id(self, user_id: str):
        return await self.collection.count_documents({"user_id": ObjectId(user_id)})
    
    # @ensure_initialized
    # async def find_label_by_id(self, label_id: str):
    #     label = await self.collection.find_one({"_id": ObjectId(label_id)})
    #     return label