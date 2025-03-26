from motor.motor_asyncio import AsyncIOMotorClient
import os
from typing import Optional

class MongoDB:
    client: Optional[AsyncIOMotorClient] = None 
    db = None

    @classmethod
    async def connect_db(cls, db_name: str = "default_db"):
        if cls.client is None:
            cls.client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
        cls.db = cls.client[db_name]  # 动态选择数据库

    @classmethod
    async def close_db(cls):
        if cls.client:
            cls.client.close()

    @classmethod
    def get_db(cls, db_name: str):
        if cls.client is None:
            raise Exception("Database client is not initialized. Call connect_db first.")
        return cls.client[db_name]  # 返回指定的数据库实例