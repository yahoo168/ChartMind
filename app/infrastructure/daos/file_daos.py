from app.infrastructure.daos.content_dao import ContentDAO, ensure_initialized
from app.infrastructure.daos.text_daos import TextDAO
from app.infrastructure.models.file_models import FileModel, FileDescriptionModel
from bson import ObjectId
from typing import List

class FileDAO(ContentDAO[FileModel]):
    def __init__(self):
        super().__init__(model_class=FileModel)
        self.collection_name = "Files"
        self.text_dao = TextDAO()
    
    @ensure_initialized
    async def get_child_texts(self, file_id: ObjectId):
        """获取文件关联的文本内容"""
        query = {"parent_file": file_id}
        text_docs = await self.text_dao.find(
            query, 
            projection={"content": 1, "_id": 1}, 
            sort=[("file_page_num", 1)]
        )
        child_texts = [text.get("content", "") for text in text_docs]
        return child_texts
    
    @ensure_initialized
    async def update_description(self, document_id: str, description: FileDescriptionModel):
        """更新文件描述信息"""
        result = await self.collection.update_one(
            {"_id": ObjectId(document_id)},
            {"$set": {"description": description.model_dump()}}
        )
        return result.modified_count
    
    @ensure_initialized
    async def update_child_texts(self, document_id: str, text_ids: List[ObjectId]):
        """更新文件关联的文本ID列表"""
        result = await self.collection.update_one(
            {"_id": ObjectId(document_id)},
            {"$set": {"child_texts": text_ids}}
        )
        return result.modified_count