from datetime import datetime, timezone
from typing import TypeVar, Generic, Type, List, Optional, Any, Dict, Union
from bson import ObjectId

from app.infrastructure.daos.mongodb_base import MongodbBaseDAO, ensure_initialized
from app.infrastructure.models.base_models import BaseModel

T = TypeVar('T', bound=BaseModel)

class ContentDAO(MongodbBaseDAO, Generic[T]):
    """
    内容 DAO 的基类，提供所有内容类型共享的基本操作
    """
    def __init__(self, model_class: Type[T]):
        super().__init__()
        self.model_class = model_class
        self.database_name = "Content"  # 默认数据库名称

    @ensure_initialized
    async def insert_one(self, document_data: T):
        """插入单个文档"""
        result = await self.collection.insert_one(document_data.model_dump())
        return result.inserted_id
    
    @ensure_initialized
    async def insert_many(self, documents: List[T]):
        """批量插入多个文档"""
        docs_dicts = [doc.model_dump() for doc in documents]
        result = await self.collection.insert_many(docs_dicts)
        return result.inserted_ids
    
    @ensure_initialized
    async def update_content_description(self, document_id: str, description: Any):
        """更新文档的描述"""
        result = await self.collection.update_one(
            {"_id": ObjectId(document_id)},
            {"$set": {"description": description.model_dump()}}
        )
        return result.modified_count
    
    @ensure_initialized
    async def update_is_processed(self, document_id: str, is_processed: bool):
        """更新文档的处理状态"""
        result = await self.collection.update_one(
            {"_id": ObjectId(document_id)},
            {"$set": {"metadata.is_processed": is_processed,
                      "metadata.processed_timestamp": datetime.now(timezone.utc),
                      "metadata.updated_timestamp": datetime.now(timezone.utc)}}
        )
        return result.modified_count
    
    @ensure_initialized
    async def find_unprocessed_documents(self):
        """查找未处理的文档"""
        result = await self.collection.find({"metadata.is_processed": False}).to_list(length=None)
        return result
    
    @ensure_initialized
    async def find_documents_by_user_id(self, user_id: str):
        """根据用户 ID 查找文档"""
        result = await self.collection.find({"user_id": ObjectId(user_id)}).to_list(length=None)
        return result
    
    @ensure_initialized
    async def count_documents_by_user_id(self, user_id: str):
        """统计用户拥有的文档数量"""
        return await self.collection.count_documents({"user_id": ObjectId(user_id)})
    
    @ensure_initialized
    async def delete_one(self, document_id: str):
        """删除单个文档"""
        result = await self.collection.delete_one({"_id": ObjectId(document_id)})
        return result.deleted_count
    
    @ensure_initialized
    async def delete_many(self, document_ids: List[ObjectId]):
        """批量删除多个文档"""
        result = await self.collection.delete_many({"_id": {"$in": document_ids}})
        return result.deleted_count
    
    @ensure_initialized
    async def find(self, query: Dict, projection: Dict = None, sort: List = None):
        """通用查询方法"""
        cursor = self.collection.find(query, projection=projection)
        if sort:
            cursor = cursor.sort(sort)
        result = await cursor.to_list(length=None)
        return result
    
    @ensure_initialized
    async def full_text_search(self, query_text, user_id=None, limit=10, min_score=0.5):
        """全文搜索方法"""
        return await super().full_text_search(query_text, limit, user_id, min_score)
    
    @ensure_initialized
    async def vector_search(self, query_vector, user_id=None, limit=10, num_candidates=100, min_score=0):
        """向量搜索方法"""
        return await super().vector_search(query_vector, limit, user_id, num_candidates, min_score)
