from typing import List
from bson import ObjectId
import os
import asyncio
from app.utils.logging_utils import logger
from app.utils.format_utils import extract_pdf_content
from app.infrastructure.external.cloudflare_ai_service import CloudflareAIService

from app.infrastructure.daos.file_daos import FileDAO
from app.infrastructure.models.file_models import FileModel, FileDescriptionModel
from app.infrastructure.models.text_models import TextModel, TextDescriptionModel
from app.infrastructure.models.base_models import MetadataModel
from app.infrastructure.daos.text_daos import TextDAO
from app.infrastructure.db.r2 import R2Storage

class FileManagementService:
    def __init__(self):
        self.file_dao = FileDAO()
        self.text_dao = TextDAO()
        self.r2_storage = R2Storage()

    async def create_document(self, document: FileModel):
        return await self.file_dao.insert_one(document)

    async def find_unprocessed_files(self):
        return await self.file_dao.find_unprocessed_files()
    
    async def update_document_description(self, document_id: str, description: FileDescriptionModel):
        return await self.file_dao.update_description(document_id, description)
    
    async def update_document_child_texts(self, document_id: str, text_ids: List[ObjectId]):
        return await self.file_dao.update_child_texts(document_id, text_ids)

    async def upload_file(self, file_name: str, file_path: str, user_id: str, source: str, file_type: str):
        """上传文件的通用方法"""
        if file_type == "pdf":
            return await self._upload_pdf(file_name, file_path, user_id, source)
        else:
            raise ValueError(f"不支持的文件类型: {file_type}")
    
    async def _upload_pdf(self, file_name: str, file_path: str, user_id: str, source: str):
        """处理PDF文件上传的内部方法"""
        upload_result = self.r2_storage.upload(file_path, user_id)
        file_url = upload_result["url"]
        object_key = upload_result["object_key"]
        document_id = None
        text_ids = []

        try:
            file_size = os.path.getsize(file_path)
            document_model = FileModel(file_type="pdf", title=file_name, file_url=file_url, user_id=ObjectId(user_id), file_size=file_size,
                                       metadata=MetadataModel(source=source),
                                       description=FileDescriptionModel())
            document_id = await self.create_document(document_model)
            
            text_ids = await self._process_pdf(file_path, user_id, source, document_id)
            await self.update_document_child_texts(document_id, text_ids)
            return document_id
        
        except Exception as e:
            await self._cleanup_orphan_resources(text_ids, document_id, object_key, e)
            raise e
    
    async def _process_pdf(self, file_path: str, user_id: str, source: str, file_id: ObjectId):
        text_models = []
        pages_text = extract_pdf_content(file_path)
        # 逐頁生成Text物件，並保存到資料庫
        for i in range(len(pages_text)):
            text_model = TextModel(content=pages_text[i], user_id=ObjectId(user_id), 
                                   metadata=MetadataModel(source=source),
                                   parent_file=file_id, file_page_num=i+1)
            text_models.append(text_model)
        return await self.text_dao.insert_many(text_models)
    
    async def _cleanup_orphan_resources(self, text_ids, document_id, object_key, error):
        # 上傳失敗時，清理已創建的資源
        if text_ids:
            logger.error(f"刪除已創建的text記錄: {text_ids}")
            await self.text_dao.delete_many(text_ids)
        
        if document_id:
            logger.error(f"刪除已創建的document記錄: {document_id}")
            await self.file_dao.delete_one(document_id)
        
        # 删除已上传到R2的文件
        logger.error(f"Mongodb 数据插入失败，删除R2文件: {object_key}, 错误: {str(error)}")
        self.r2_storage.delete(object_key)
    
    async def update_file_description(self, file_id: ObjectId, description: FileDescriptionModel):
        return await self.file_dao.update_description(file_id, description)
    
    async def get_file_texts(self, file_id: ObjectId):
        return await self.file_dao.get_child_texts(file_id)
    
    async def update_file_is_processed(self, file_id: ObjectId, is_processed: bool):
        return await self.file_dao.update_is_processed(file_id, is_processed)

class FileAnalysisService:
    def __init__(self):
        self.file_dao = FileDAO()
        self.file_management_service = FileManagementService()
        self.llm_service = CloudflareAIService()

    async def process_files(self, language: str = "zh-TW"):
        """处理所有未处理的文件"""
        try:
            logger.info("开始处理文件")
            unprocessed_files = await self.file_management_service.find_unprocessed_files()
            logger.info(f"未处理的文件数量: {len(unprocessed_files)}")

            if not unprocessed_files:
                logger.info("没有未处理的文件")
                return []
            
            tasks = []
            processed_file_ids = []
            for file in unprocessed_files:
                task = self._process_single_file(file, language)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 收集成功处理的文件ID
            for i, result in enumerate(results):
                if not isinstance(result, Exception):
                    processed_file_ids.append(unprocessed_files[i]["_id"])
            
            logger.info(f"已成功处理文件: {len(processed_file_ids)}/{len(unprocessed_files)}")
            return processed_file_ids
        except Exception as e:
            logger.error(f"处理文件时出错: {e}")
            return []
        
    async def _process_single_file(self, file_doc: dict, language: str = "zh-TW"):
        """处理单个文件"""
        try:
            file_id = file_doc["_id"]
            logger.info(f"开始处理文件 ID: {file_id}")
            
            # 获取文件内容（從預先存入的text中獲取）
            file_texts = await self.file_management_service.get_file_texts(file_id)
            file_text = '\n'.join(file_texts)[:10000] # 限制文件內容不超過10000字，避免Token過多
            
            if language == "zh-TW":
                prompt = """請分析這個文件，並以JSON格式提供以下資訊：
                    {
                        "title": "簡短的標題",
                        "summary": "詳細的文件描述，約150字", 
                        "labels": ["標籤1", "標籤2", "標籤3", "標籤4", "標籤5"]
                    }
                    請確保回應是有效的JSON格式。"""
            else:
                prompt = """Please analyze this file and provide the following information in JSON format:
                    {
                        "title": "a concise title",
                        "summary": "detailed file description, about 150 words",
                        "labels": ["label1", "label2", "label3", "label4", "label5"]
                    }
                    Please ensure the response is in valid JSON format."""
                
            llm_result = await self.llm_service.analyze_text(file_text, prompt, json_response=True)
            title = llm_result.get("title", '')
            summary = llm_result.get("summary", '')
            labels = llm_result.get("labels", [])
            summary_vector = await self.llm_service.get_embedding(summary)
            
            description = FileDescriptionModel(
                auto_title=title,
                summary=summary,
                summary_vector=summary_vector
            )
            await self.file_management_service.update_file_description(file_id, description)
            await self.file_management_service.update_file_is_processed(file_id, True)
            
            return file_id  # 返回成功处理的文件ID
        except Exception as e:
            logger.error(f"处理文件 {file_doc.get('_id', '未知')} 时出错: {e}")
            raise  # 重新抛出异常，让调用者知道处理失败