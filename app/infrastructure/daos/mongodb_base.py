import functools
import asyncio
import logging

from bson import ObjectId
from app.infrastructure.db.mongodb import MongodbClient

def ensure_initialized(func):
    """裝飾器：確保DAO已初始化後再執行方法"""
    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs):
        await self.ensure_initialized()
        return await func(self, *args, **kwargs)
    return wrapper

class MongodbBaseDAO:
    _instances = {}  # 用於存儲不同子類的實例
    _init_lock = asyncio.Lock()  # 用於初始化的鎖

    def __new__(cls, *args, **kwargs): # 確保只有一個實例
        if cls not in cls._instances:
            cls._instances[cls] = super().__new__(cls)
        return cls._instances[cls]
    
    def __init__(self):
        """同步初始化方法，設置基本屬性"""
        # 確保這些屬性在子類初始化前已經存在
        self.database_name = "default_db"  # 默認值，確保是字符串
        self.collection_name = "default_collection"  # 默認值，確保是字符串
        self.collection = None
        self.initialized = False
        
    async def ensure_initialized(self): 
        """確保 DAO 已初始化，所有子類都可以使用此方法（外部檢查調用）"""
        if not hasattr(self, 'initialized') or not self.initialized:
            await self.__init_async__()
            
    async def __init_async__(self):
        """異步初始化方法，確保數據庫連接已建立"""
        if not hasattr(self, 'initialized') or not self.initialized:
            async with self._init_lock: # 確保只有一個執行緒可以進行初始化，防止高併發時多個協程同時初始化
                if not hasattr(self, 'initialized') or not self.initialized:
                    try:
                        # 檢查數據庫名稱和集合名稱是否為字符串
                        if not isinstance(self.database_name, str):
                            raise TypeError(f"database_name must be a string, got {type(self.database_name)}")
                        if not isinstance(self.collection_name, str):
                            raise TypeError(f"collection_name must be a string, got {type(self.collection_name)}")
                        
                        # 獲取數據庫連接
                        client = await MongodbClient.get_client()
                        db = client[self.database_name]
                        self.collection = db[self.collection_name]
                        
                        self.initialized = True
                        logging.info(f"{self.__class__.__name__} initialized with database: {self.database_name}, collection: {self.collection_name}")
                    except Exception as e:
                        logging.error(f"Failed to initialize {self.__class__.__name__}: {str(e)}")
                        raise
    
    def convert_objectid_to_str(self, data):
        """將文檔中的ObjectId轉換為字符串"""
        if isinstance(data, dict):
            # 處理字典
            result = {}
            for key, value in data.items():
                if key == '_id' and isinstance(value, ObjectId):
                    result[key] = str(value)
                elif isinstance(value, ObjectId):
                    result[key] = str(value)
                elif isinstance(value, (dict, list)):
                    result[key] = self.convert_objectid_to_str(value)
                else:
                    result[key] = value
            return result
        elif isinstance(data, list):
            # 處理列表
            return [self.convert_objectid_to_str(item) for item in data]
        else:
            # 其他類型直接返回
            return data