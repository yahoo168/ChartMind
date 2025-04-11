from bson import ObjectId
from app.infrastructure.external.cloudflare_ai_service import CloudflareAIService

from app.infrastructure.models.text_models import TextModel, TextDescriptionModel
from app.infrastructure.models.url_models import UrlModel, UrlDescriptionModel
from app.infrastructure.models.base_models import MetadataModel
from app.infrastructure.daos.text_daos import TextDAO
from app.infrastructure.daos.url_daos import UrlDAO

from app.utils.logging_utils import logger
from app.utils.url_utils import extract_urls_from_text
from app.utils.format_utils import count_words

import asyncio

class TextManagementService:
    def __init__(self):
        self.text_dao = TextDAO()
        self.url_dao = UrlDAO()
    
    async def get_unprocessed_texts(self):
        return await self.text_dao.find_unprocessed_texts()
    
    async def update_text_description(self, text_id: str, text_summary: str, text_summary_vector: list, text_title: str):
        await self.text_dao.update_text_description(text_id, text_summary, text_summary_vector, text_title)
    
    async def update_text_is_processed(self, text_id: str, is_processed: bool):
        await self.text_dao.update_text_is_processed(text_id, is_processed)
    
    async def upload_text(self, text: str, user_id: str, source: str):
        logger.info(f"Uploading text: {text} for user: {user_id} with source: {source}")
        try:
            text_model = TextModel(content=text, 
                                   user_id=ObjectId(user_id), 
                                   metadata=MetadataModel(source=source),
                                   description=TextDescriptionModel())
            text_id = await self.text_dao.insert_one(text_model)
        except Exception as e:
            logger.error(f"Error uploading text: {e}")
            raise e
            
        try:
            # 提取文本中的URL，并保存到数据库
            urls = extract_urls_from_text(text)
            if urls:
                url_models = []
                for url in urls:
                    url_model = UrlModel(url=url, 
                                         user_id=ObjectId(user_id), 
                                         metadata=MetadataModel(source=source),
                                         description=UrlDescriptionModel(),
                                         parent_text=text_id)
                    url_models.append(url_model)
                url_ids = await self.url_dao.insert_many(url_models)
                # 更新文本的子URL
                await self.text_dao.update_child_urls(text_id, url_ids)
        except Exception as e:
            logger.error(f"Error uploading urls: {e}")
            raise e

class TextAnalysisService:
    def __init__(self):
        self.text_management_service = TextManagementService()
        self.llm_service = CloudflareAIService()
        self.text_dao = TextDAO()
        self.url_dao = UrlDAO()
        
    async def process_text(self):
        """处理未处理的文本"""
        try:
            unprocessed_texts = await self.text_management_service.get_unprocessed_texts()
            logger.info(f"Found {len(unprocessed_texts)} unprocessed texts.")
            if not unprocessed_texts:
                logger.info(f"Found no unprocessed texts.")
                return
            
            # 创建任务列表
            tasks = []
            for text_doc in unprocessed_texts:
                task = self._process_single_text(text_doc)
                tasks.append(task)
            await asyncio.gather(*tasks)
            logger.info(f"Completed processing {len(tasks)} texts")
        except Exception as e:
            logger.error(f"Error processing texts: {e}")
    
    async def _process_single_text(self, text_doc: dict, language: str = "zh-TW", summary_min_length: int = 200):
        """处理单个文本"""
        try:
            text = text_doc["content"]
            text_id = text_doc["_id"]

            text_summary = ''
            text_title = ''
            text_summary_vector = []

            word_count = count_words(text)
            if word_count >= summary_min_length:
                if language == "zh-TW":
                    prompt = "請以繁體中文分析本段文字，用100字左右撰寫內容摘要，捕捉核心觀點，並取一個濃縮文字重點的標題，返回JSON格式，包含2個鍵：summary和title"
                else:
                    prompt = "Please analyze this text in English, write a 100-word summary capturing the core points, and give a concise title, return JSON format with 2 keys: summary and title"
                
                llm_result = await self.llm_service.analyze_text(text, prompt, json_response=True)
                text_summary, text_title = llm_result.get("summary", ""), llm_result.get("title", "")
                text_summary_vector = await self.llm_service.get_embedding(text_summary)
            
            else:
                text_summary_vector = await self.llm_service.get_embedding(text)
            
            await self.text_management_service.update_text_description(text_id, text_summary, text_summary_vector, text_title)  
            await self.text_management_service.update_text_is_processed(text_id, True)
        
        except Exception as e:
            logger.error(f"Error processing text: {e}")