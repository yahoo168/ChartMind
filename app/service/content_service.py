from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from bson import ObjectId
import asyncio
from app.utils.logging_utils import logger
from app.infrastructure.external.cloudflare_ai_service import CloudflareAIService
from app.service.label_service import LabelApplicationService
from app.infrastructure.db.r2 import R2Storage
from app.service.user_service import UserContentMetaService
from app.utils.format_utils import count_words

# 内容处理基类
class ContentService(ABC):
    """所有内容类型（文件、图片、文本、URL）的抽象基类"""
    
    def __init__(self):
        self.content_type = None # 子类需要重写
        self.content_dao = None # 子类需要重写
        self.llm_service = CloudflareAIService()
        self.label_application_service = LabelApplicationService()
        self.r2_storage = R2Storage()    
        self.user_content_meta_service = UserContentMetaService()
        
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
    
    async def find_content_by_ids(self, content_ids: list[ObjectId]) -> List[Dict]:
        """查找内容"""
        return await self.content_dao.find(query={"_id": {"$in": content_ids}}, 
                                           projection={"description.summary_vector": 0},
                                           sort=[("metadata.created_timestamp", -1)])
    
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
            
            # 在內存中更新 content 對象
            content["description"] = description.model_dump()
            logger.info(f"内容{content_id} 描述: {content['description']}")
            await self.update_content_labels(content)
            await self.update_is_processed(content_id, True)
            logger.info(f"已完成{self.content_type}处理 ID: {content_id}")
            return content_id
        
        except Exception as e:
            logger.error(f"处理{self.content_type} {content.get('_id', '未知')} 时出错: {e}")
            return None
    
    async def update_content_labels(self, content: Dict) -> List[ObjectId]:
        """获取内容标签"""
        def _get_representative_content(content_type, content):
            if content_type == "image":
                return content["description"]["ocr_text"]

            elif content_type == "text":
                return content["content"]
            
            elif (content_type == "file") or (content_type == "url"):
                return content["description"]["summary"]
            else:
                raise ValueError(f"Unsupported content type: {content_type}")
        
        # 取得content meta data
        content_id = content["_id"]
        representative_content = _get_representative_content(self.content_type, content) # 获取内容代表性文本(以使用include_keywords和exclude_keywords)
        logger.info(f"内容{content_id} 代表性文本: {representative_content}")
        content_vector = content["description"]["summary_vector"]
        authorized_users = content["authorized_users"]
        content_type = self.content_type
        
        # 對於每個授權用戶，匹配其標籤
        for user_id in authorized_users:
            logger.info(f"内容{content_id} 类型: {content_type} 授权用户: {user_id}")
            labels = await self.label_application_service.match_user_labels(user_id, representative_content, content_vector)
            label_ids = [label["_id"] for label in labels]
            label_names = [label["name"] for label in labels]
            logger.info(f"用户{user_id} 内容{content_id} 标签: {label_names}")
            await self.user_content_meta_service.update_content_labels(user_id, content_id, content_type, label_ids)
    
    async def full_text_search(self, query_text: str, user_id: ObjectId, limit: int) -> List[Dict]:
        """全文搜索"""
        return await self.content_dao.full_text_search(query_text=query_text, user_id=user_id, limit=limit)
    
    async def vector_search(self, query_vector: List[float], user_id: ObjectId, limit: int) -> List[Dict]:
        """向量搜索"""
        return await self.content_dao.vector_search(query_vector=query_vector, user_id=user_id, limit=limit)

    async def smart_search(self, query_text: str, user_id: ObjectId, limit: int = 10, hybrid_weight: float = 0.7) -> List[Dict]:
        """
        智能搜索函数，根据查询文本长度选择搜索方式并优化结果排序
        - 10字以下：混合搜索策略，结合全文搜索和向量搜索结果
        - 10字以上：直接使用向量搜索
        
        参数:
            query_text: 查询文本
            user_id: 用户ID
            limit: 需要返回的结果数量
            hybrid_weight: 全文搜索结果的权重(0-1)，向量搜索权重为(1-hybrid_weight)
        
        返回:
            搜索结果列表
        """
        # 预先计算向量嵌入，避免重复计算
        query_vector = await self.llm_service.get_embedding(query_text)
        
        if count_words(query_text) > 10:
            # 长查询直接使用向量搜索
            results = await self.vector_search(query_vector, user_id, limit)
        
        else:
            # 短查询使用混合搜索策略
            text_results = await self.full_text_search(query_text, user_id, limit)
            
            # 无论全文搜索结果如何，都进行向量搜索以获得更全面的结果
            vector_results = await self.vector_search(query_vector, user_id, limit)
            
            # 合并并重新排序结果
            results = []
            text_result_ids = {str(item["_id"]): i for i, item in enumerate(text_results)}
            vector_result_ids = {str(item["_id"]): i for i, item in enumerate(vector_results)}
            
            # 所有出现在结果中的文档ID
            all_doc_ids = set(text_result_ids.keys()) | set(vector_result_ids.keys())
            
            # 计算混合分数并排序
            scored_results = []
            for doc_id in all_doc_ids:
                # 初始化分数
                text_score = 0
                vector_score = 0
                
                # 获取文档
                doc = None
                
                # 如果在全文搜索结果中
                if doc_id in text_result_ids:
                    idx = text_result_ids[doc_id]
                    doc = text_results[idx]
                    # 根据排名计算分数 (排名越靠前分数越高)
                    text_score = 1.0 - (idx / len(text_results)) if len(text_results) > 0 else 0
                
                # 如果在向量搜索结果中
                if doc_id in vector_result_ids:
                    idx = vector_result_ids[doc_id]
                    if doc is None:
                        doc = vector_results[idx]
                    # 使用相似度分数
                    vector_score = vector_results[idx].get("similarity_score", 0)
                
                # 计算混合分数
                hybrid_score = (hybrid_weight * text_score) + ((1 - hybrid_weight) * vector_score)
                
                # 添加混合分数到文档
                doc["hybrid_score"] = hybrid_score
                scored_results.append(doc)
            
            # 按混合分数排序
            results = sorted(scored_results, key=lambda x: x.get("hybrid_score", 0), reverse=True)
        
        return results[:limit]  # 返回指定数量的结果