from bson import ObjectId
from app.infrastructure.external.cloudflare_ai_service import CloudflareAIService
from app.service.label_service import LabelApplicationService
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
    
    async def update_text_description(self, text_id: str, text_description: TextDescriptionModel):
        await self.text_dao.update_text_description(text_id, text_description)
    
    async def update_text_is_processed(self, text_id: str, is_processed: bool):
        await self.text_dao.update_text_is_processed(text_id, is_processed)
    
    async def upload_text(self, text: str, user_id: str, source: str):
        logger.info(f"Uploading text: {text} for user: {user_id} with source: {source}")
        
        # 提取文本中的URL
        urls = extract_urls_from_text(text)
        
        # 检查是否为纯URL（文本去除URL后为空）
        is_pure_url = False
        if urls:
            # 从原文本中移除所有URL，检查剩余内容是否为空
            remaining_text = text
            for url in urls:
                remaining_text = remaining_text.replace(url, "").strip()
            is_pure_url = len(remaining_text) == 0
        
        text_id = None
        # 如果不是纯URL，则创建文本记录
        if not is_pure_url:
            try:
                text_model = TextModel(content=text, 
                                      user_id=ObjectId(user_id), 
                                      metadata=MetadataModel(source=source),
                                      description=TextDescriptionModel())
                text_id = await self.text_dao.insert_one(text_model)
            except Exception as e:
                logger.error(f"Error uploading text: {e}")
                raise e
        
        # 处理URL
        if urls:
            try:
                url_models = []
                for url in urls:
                    url_model = UrlModel(url=url, 
                                        user_id=ObjectId(user_id), 
                                        metadata=MetadataModel(source=source),
                                        description=UrlDescriptionModel(),
                                        parent_text=text_id)  # 如果是纯URL，parent_text为None
                    url_models.append(url_model)
                url_ids = await self.url_dao.insert_many(url_models)
                
                # 只有在创建了文本记录的情况下才更新子URL
                if text_id:
                    await self.text_dao.update_child_urls(text_id, url_ids)
            except Exception as e:
                logger.error(f"Error uploading urls: {e}")
                raise e
        
        return text_id  # 返回文本ID，如果是纯URL则为None

class TextAnalysisService:
    def __init__(self):
        self.text_management_service = TextManagementService()
        self.llm_service = CloudflareAIService()
        self.label_application_service = LabelApplicationService()
        
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
            text_id = text_doc["_id"]
            text_description = await self._get_text_description(text_doc, language, summary_min_length)
            await self.text_management_service.update_text_description(text_id, text_description)  
            await self.text_management_service.update_text_is_processed(text_id, True)
        
        except Exception as e:
            logger.error(f"Error processing text: {e}")
    
    async def _get_text_description(self, text_doc: dict, language: str, summary_min_length: int):
        user_id = text_doc["user_id"]
        content = text_doc["content"]

        summary = ''
        auto_title = ''
        summary_vector = []
        keywords = []

        word_count = count_words(content)
        if word_count >= summary_min_length:
            if language == "zh-TW":
                prompt = """請以繁體中文分析本段文字，用100字撰寫內容摘要，捕捉核心觀點，並取一個濃縮文字重點的標題，以及提取5個關鍵詞，返回JSON格式，
                包含3個鍵：summary、title和keywords（keywords為包含5個關鍵詞的數組）"""
            else:
                prompt = """Please analyze this text in English, write a 100-word summary capturing the core points, 
                give a concise title, and extract 5 keywords, return JSON format with 3 keys: summary, 
                title, and keywords (keywords should be an array of 5 keywords)"""
            
            llm_result = await self.llm_service.analyze_text(content, prompt, json_response=True)
            
            summary = llm_result.get("summary", "")
            auto_title = llm_result.get("title", "")
            keywords = llm_result.get("keywords", [])
            logger.info(f"keywords: {keywords}")
            summary_vector = await self.llm_service.get_embedding(summary)

        # 如果文本字數不足100字，則使用文本內容進行向量化（且沒有keyword）
        else:
            summary_vector = await self.llm_service.get_embedding(content)
        
        # 匹配用户标签
        labels = await self.label_application_service.match_user_labels(user_id, summary_vector)
        labels_ids = [label['_id'] for label in labels]
        
        # 打印匹配的标签(debug)
        for label in labels:
            logger.info(f"Label Matched: {label['name']}")
        
        return TextDescriptionModel(
            auto_title=auto_title,
            summary=summary,
            summary_vector=summary_vector,
            labels=labels_ids,
            keywords=keywords
        )