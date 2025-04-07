import os, logging
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional

class MongodbClient:
    client: Optional[AsyncIOMotorClient] = None 
    db = None

    @classmethod
    async def connect_client(cls):
        if cls.client is None:
            mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
            cls.client = AsyncIOMotorClient(mongodb_uri)
            logging.info("MongoDB client connected")

    @classmethod
    async def connect_db(cls, db_name: str):
        await cls.connect_client()
        cls.db = cls.client[db_name]
        return cls.db

    @classmethod
    async def get_client(cls):
        """獲取MongoDB客戶端，如果未初始化則先連接"""
        if cls.client is None:
            await cls.connect_client()
        return cls.client

    @classmethod
    async def get_db(cls, db_name: str):
        """異步獲取指定的數據庫實例"""
        if cls.client is None:
            await cls.connect_db(db_name)
        return cls.client[db_name]

    @classmethod
    async def close_db(cls):
        if cls.client:
            cls.client.close()
            cls.client = None
            cls.db = None
            logging.info("MongoDB connection closed")

    @classmethod
    async def close_client(cls):
        if cls.client:
            cls.client.close()
            cls.client = None
            logging.info("MongoDB client closed")

        # @classmethod
        # async def connect_db(cls, db_name: str = "default_db"):
        #     try:
        #         if cls.client is None:
        #             mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        #             # 根據環境決定是否啟用TLS
        #             use_tls = os.getenv("MONGODB_USE_TLS", "False").lower() == "true"
                    
        #             if use_tls:
        #                 cls.client = AsyncIOMotorClient(
        #                     mongodb_uri,
        #                     tls=True,
        #                     tlsAllowInvalidCertificates=True  # 生產環境應移除此選項
        #                 )
        #             else:
        #                 cls.client = AsyncIOMotorClient(mongodb_uri)
                    
        #             logging.info(f"MongoDB connected to {mongodb_uri}")
                
        #         cls.db = cls.client[db_name] #成功連線後記錄訊息
        #         return cls.db
        #     except Exception as e:
        #         logging.error(f"MongoDB connection error: {str(e)}")
        #         raise