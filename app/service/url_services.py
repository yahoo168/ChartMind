from app.infrastructure.daos.url_daos import UrlDAO
from app.utils.logging_utils import logger
from app.utils.url_utils import get_url_preview
from app.infrastructure.models.url_models import UrlModel, UrlDescriptionModel
from app.infrastructure.models.base_models import MetadataModel
from bson import ObjectId
from typing import Dict, Any
from app.service.content_service import ContentService
from app.infrastructure.external.cloudflare_ai_service import CloudflareAIService

class UrlService(ContentService):
    """URL服务，处理URL的创建、存储和分析"""
    
    def __init__(self):
        super().__init__()
        self.content_type = "url"
        self.content_dao = UrlDAO()
        self.llm_service = CloudflareAIService()
    
    async def create_content(self, urls: list[str], uploader_id: ObjectId, authorized_users: list[ObjectId], parent_text_id: ObjectId = None,
                            upload_metadata: Dict[str, Any] = None) -> ObjectId:
        """创建URL内容，UserContentMeta在Text Service中實現"""
        url_models = []
        for url in urls:
            url_model = UrlModel(
                url=url, 
                authorized_users=authorized_users,
                uploader=uploader_id,
                metadata=MetadataModel(**upload_metadata),  
                description=UrlDescriptionModel(),
                parent_text=parent_text_id
            )
            url_models.append(url_model)
        return await self.content_dao.insert_many(url_models)
    
    async def get_content_description(self, content: Dict) -> Dict:
        """获取URL描述信息"""
        try:
            # 获取URL预览信息
            url_preview = await get_url_preview(content["url"])
            logger.info(f"获取URL预览: {content['url']}")
            
            # 获取基本信息
            title = url_preview.get("title", '')
            thumbnail_url = url_preview.get("thumbnail_url", '')
            description = url_preview.get("description", '')
            
            # 即使没有描述，也使用标题或URL本身进行向量化，确保返回正确维度的向量
            if description or title:
                text_to_embed = title + description  # 将title和description合并向量化
            else:
                # 如果没有标题和描述，使用URL本身
                text_to_embed = content["url"]
                
            summary_vector = await self.llm_service.get_embedding(text_to_embed)
            
            return UrlDescriptionModel(
                auto_title=title,
                thumbnail_url=thumbnail_url,
                summary=description,
                summary_vector=summary_vector
            ) 
            
        except Exception as e:
            logger.error(f"获取URL描述时出错: {e}")
            # 创建一个空向量，确保维度正确（3072维）
            empty_vector = [0.0] * 3072  # 创建一个全零向量，维度与模型输出匹配
            return UrlDescriptionModel(summary_vector=empty_vector)