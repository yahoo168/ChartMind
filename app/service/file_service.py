from typing import List
from bson import ObjectId


from app.utils.logging_utils import logger
from app.utils.format_utils import extract_pdf_content

from app.infrastructure.daos.file import FileDAO
from app.infrastructure.models.file_models import FileModel, FileDescriptionModel
from app.infrastructure.models.text_models import TextModel
from app.infrastructure.daos.text import TextDAO
from app.infrastructure.db.r2 import R2Storage

class FileManagementService:
    def __init__(self):
        self.file_dao = FileDAO()
        self.text_dao = TextDAO()
        self.r2_storage = R2Storage()

    async def create_document(self, document: FileModel):
        return await self.file_dao.insert_one(document)

    async def update_document_description(self, document_id: str, description: FileDescriptionModel):
        return await self.file_dao.update_description(document_id, description)
    
    async def update_document_child_texts(self, document_id: str, text_ids: List[ObjectId]):
        return await self.file_dao.update_child_texts(document_id, text_ids)

    async def upload_pdf(self, file_name: str, file_path: str, user_id: str, source: str):
        upload_result = self.r2_storage.upload(file_path, user_id)
        file_url = upload_result["url"]
        object_key = upload_result["object_key"]

        try:
            document_model = FileModel(file_type="pdf", title=file_name, url=file_url, user_id=ObjectId(user_id), source=source)
            docuemnt_id = await self.create_document(document_model)
            
            text_models = []
            pages_text = extract_pdf_content(file_path)
            # 逐頁生成Text物件，並保存到資料庫
            for i in range(len(pages_text)):
                text_model = TextModel(content=pages_text[i], user_id=ObjectId(user_id), source=source, 
                                    parent_document=docuemnt_id, document_page_num=i+1)
                text_models.append(text_model)
            text_ids = await self.text_dao.insert_many(text_models)
            await self.update_document_child_texts(docuemnt_id, text_ids)
            return docuemnt_id
        
        except Exception as e:
            # 数据库插入失败，删除已上传到R2的文件
            logger.error(f"Mongodb pdf 数据插入失败，删除R2文件: {object_key}, 错误: {str(e)}")
            self.r2_storage.delete(object_key)
            raise e