from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from bson import ObjectId
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.utils.logging_utils import logger
from app.infrastructure.external.cloudflare_ai_service import CloudflareAIService
from app.service.label_service import LabelApplicationService
from app.infrastructure.db.r2 import R2Storage
from app.infrastructure.daos.content_dao import ContentDAO

# 内容处理基类
class ContentService(ABC):
    """所有内容类型（文件、图片、文本、URL）的抽象基类"""
    
    def __init__(self):
        self.content_type = None # 子类需要重写
        self.content_dao = None # 子类需要重写
        self.llm_service = CloudflareAIService()
        self.label_application_service = LabelApplicationService()
        self.r2_storage = R2Storage()    
    
    @abstractmethod
    async def create_content(self, **kwargs) -> ObjectId:
        """创建内容记录"""
        pass

    async def delete_content(self, content_id: ObjectId):
        """删除内容"""
        return await self.content_dao.delete_one(content_id)
    
    async def delete_contents(self, content_ids: list[ObjectId]):
        """删除内容"""
        return await self.content_dao.delete_many(content_ids)
    
    async def find_unprocessed_content(self) -> List[Dict]:
        """查找未处理的内容"""
        return await self.content_dao.find_unprocessed_documents()
    
    async def update_content_description(self, content_id: ObjectId, description: Any) -> bool:
        """更新内容描述"""
        return await self.content_dao.update_content_description(content_id, description)
    
    async def update_is_processed(self, content_id: ObjectId, is_processed: bool) -> bool:
        """更新处理状态"""
        return await self.content_dao.update_is_processed(content_id, is_processed)
        
    @abstractmethod
    async def get_content_description(self, content: Dict, language: str = "zh-TW") -> Any:
        """生成内容描述信息，由子类实现，返回對應的 DescriptionModel"""
        pass

    async def get_content_analysis(self, text: str=None, image_url: str=None, language: str = "zh-TW") -> Dict:
        """获取通用内容分析结果"""
        if not text and not image_url:
            raise ValueError("text 或 image_url 必須提供其中一個")
        
        if language == "zh-TW":
            prompt = """請分析以下內容，並以JSON格式提供以下資訊：
                {
                    "title": "簡短的標題",
                    "summary": "詳細的內容描述，約100字", 
                    "keywords": ["關鍵詞1", "關鍵詞2", "關鍵詞3", "關鍵詞4", "關鍵詞5"]
                }
                請確保回應是有效的JSON格式。"""
        else:
            prompt = """Please analyze this content and provide the following information in JSON format:
                {
                    "title": "a concise title",
                    "summary": "detailed content description, about 100 words",
                    "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"]
                }
                Please ensure the response is in valid JSON format."""
        
        if image_url:
            llm_result = await self.llm_service.analyze_image(image_url, prompt, json_response=True)
        else:
            llm_result = await self.llm_service.analyze_text(text, prompt, json_response=True)
        
        title = llm_result.get("title", '')
        summary = llm_result.get("summary", '')
        keywords = llm_result.get("keywords", [])
        
        if summary:
            summary_vector = await self.llm_service.get_embedding(summary)
        else:
            summary_vector = []
        
        return {
            "title": title,
            "summary": summary,
            "summary_vector": summary_vector,
            "keywords": keywords
        }

    async def process_batch_content(self, max_concurrency: int = 5) -> List[ObjectId]:
        """批量处理未处理的内容
        
        Args:
            max_concurrency: 最大并发处理数量
        """
        try:
            logger.info(f"开始处理{self.content_type}内容")
            unprocessed_contents = await self.find_unprocessed_content()
            logger.info(f"未处理的{self.content_type}数量: {len(unprocessed_contents)}")
            
            if not unprocessed_contents:
                logger.info(f"没有未处理的{self.content_type}")
                return []
            
            processed_ids = []
            # 使用信号量控制并发数量
            semaphore = asyncio.Semaphore(max_concurrency)
            
            async def process_with_semaphore(content):
                async with semaphore:
                    return await self._process_single_content(content)
            
            # 创建所有任务
            tasks = [process_with_semaphore(content) for content in unprocessed_contents]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 过滤有效的结果
            processed_ids = [result for result in results 
                             if result and not isinstance(result, Exception)]
            
            logger.info(f"已处理{self.content_type}: {len(processed_ids)}/{len(unprocessed_contents)}")
            return processed_ids
            
        except Exception as e:
            logger.error(f"批量处理{self.content_type}时出错: {e}")
            return []
    
    async def _process_single_content(self, content: Dict) -> Union[ObjectId, None]:
        """处理单个内容项"""
        try:
            content_id = content["_id"]
            logger.info(f"开始处理{self.content_type} ID: {content_id}")
            
            description = await self.get_content_description(content)
            await self.update_content_description(content_id, description)
            await self.update_is_processed(content_id, True)
            
            logger.info(f"已完成{self.content_type}处理 ID: {content_id}")
            return content_id
        
        except Exception as e:
            logger.error(f"处理{self.content_type} {content.get('_id', '未知')} 时出错: {e}")
            return None