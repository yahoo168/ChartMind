from app.infrastructure.daos.mongodb_base import MongodbBaseDAO, ensure_initialized
from app.infrastructure.models.user_models import UserRegistrationModel
from bson import ObjectId

class UserDAO(MongodbBaseDAO):
    def __init__(self):
        super().__init__()
        self.database_name = "Account"
        self.collection_name = "Users"

    @ensure_initialized
    async def create_user(self, user_data: dict):
        result = await self.collection.insert_one(user_data)
        return result.inserted_id
    
    @ensure_initialized
    async def find_user(self, username: str = None, user_id: str = None, line_id: str = None, google_id: str = None):
        query = {}
        if username:
            query['username'] = username
        if user_id:
            query['_id'] = ObjectId(user_id)
        if line_id:
            query['external_ids.line_id'] = line_id
        if google_id:
            query['external_ids.google_id'] = google_id
        
        data = await self.collection.find_one(query)
        return data