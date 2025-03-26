from app.utils.mongodb_utils import MongoDB
from app.models.user_models import UserRegistrationModel
import random
import string

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
            
        # 处理其他可能的查询参数
        for key, value in kwargs.items():
            if key.startswith('external_ids.'):
                query[key] = value
            else:
                query[f'external_ids.{key}'] = value
        
        user_data = await self.collection.find_one(query)
        return user_data
    
    async def check_user_exist(self, username: str = None, user_id: str = None, line_id: str = None, google_id: str = None, **kwargs):
        user_data = await self.find_user(username, user_id, line_id, google_id, **kwargs)
        return user_data is not None

    async def create_user(self, user_data: UserRegistrationModel):
        await self.collection.insert_one(user_data)

    async def create_user_from_line(self, line_id):
        # 生成随机用户名和密码（10码以内）
        # 生成不重复的随机用户名
        random_username = ''.join(random.choices(string.ascii_letters + string.digits, k=random.randint(6, 10)))
        while await self.check_user_exist(username=random_username):
            random_username = ''.join(random.choices(string.ascii_letters + string.digits, k=random.randint(6, 10)))
        random_password = ''.join(random.choices(string.ascii_letters + string.digits, k=random.randint(6, 10)))
        
        user_data = {
            "username": random_username,
            "password": random_password,
            "external_ids":{
                "line_id": line_id,
            },

        }
        await self.create_user(user_data)
        return user_data