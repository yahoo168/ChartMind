from app.utils.mongodb_utils import MongoDB
from app.models.user_models import UserRegistrationModel

class UserDAO:
    def __init__(self):
        db = MongoDB.get_db("Account")
        self.collection = db["Users"]

    async def find_user(self, username: str = None, user_id: str = None, line_id: str = None, google_id: str = None, **kwargs):
        query = {}
        if username:
            query['username'] = username
        if user_id:
            query['user_id'] = user_id
        if line_id:
            query['external_ids.line_id'] = line_id
        if google_id:
            query['external_ids.google_id'] = google_id
        for key, value in kwargs.items():
            if key.startswith('external_ids.'):
                query[key] = value
            else:
                query[f'external_ids.{key}'] = value
        return await self.collection.find_one(query)

    async def create_user(self, user_data: UserRegistrationModel):
        if isinstance(user_data, UserRegistrationModel):
            user_data = user_data.model_dump()
        await self.collection.insert_one(user_data)