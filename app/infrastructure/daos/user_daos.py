from app.infrastructure.daos.mongodb_base import MongodbBaseDAO, ensure_initialized
from app.infrastructure.models.user_models import UserContentMetadataModel
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
    
    @ensure_initialized
    async def find_users_by_line_group_id(self, line_group_id: str, only_id: bool = False):
        if only_id:
            # 使用 distinct 方法只获取 _id 字段
            return await self.collection.distinct("_id", {"line_group_ids": line_group_id})
        else:
            # 原有逻辑，返回完整文档
            return await self.collection.find({"line_group_ids": line_group_id}).to_list(length=None)

class UserContentMetaDAO(MongodbBaseDAO):
    def __init__(self):
        super().__init__()
        self.database_name = "Content"
        self.collection_name = "UserContentMeta"
        
    @ensure_initialized
    async def find_user_content_meta(self, user_id: ObjectId, content_type: str, labels: list[ObjectId]=None, limit: int = None):
        query = {
            "user_id": user_id,
            "content_type": content_type,
            "is_deleted": {"$ne": True} # 不包含已删除的内容
        }
        # 只有当labels不为None且不为空列表时，才添加标签过滤条件
        if labels is not None and len(labels) > 0:
            query["labels"] = {"$in": labels}
        
        return await self.collection.find(query).to_list(length=limit)
    
    @ensure_initialized
    async def insert_one(self, user_content_meta_data: UserContentMetadataModel):
        result = await self.collection.insert_one(user_content_meta_data.model_dump())
        return result.inserted_id
    
    @ensure_initialized
    async def insert_many(self, user_content_meta_data: list[UserContentMetadataModel]):
        result = await self.collection.insert_many([meta.model_dump() for meta in user_content_meta_data])
        return result.inserted_ids  
    
    @ensure_initialized
    async def update_content_labels(self, user_id: ObjectId, content_id: ObjectId, content_type: str, label_ids: list[ObjectId]):
        return await self.collection.update_one(
            {"user_id": user_id, "content_id": content_id, "content_type": content_type},
            {"$set": {"labels": label_ids}}
        )