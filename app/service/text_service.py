from bson import ObjectId
from typing import Dict, Any

from app.infrastructure.models.text_models import TextModel, TextDescriptionModel
from app.infrastructure.models.base_models import MetadataModel
from app.infrastructure.daos.text_daos import TextDAO

from app.utils.logging_utils import logger
from app.utils.url_utils import extract_urls_from_text, check_is_pure_url, remove_urls_from_text
from app.utils.format_utils import count_words

from app.service.url_services import UrlService
from app.service.content_service import ContentService
from app.service.user_service import UserContentMetaService


class TextService(ContentService):
    """文本服务，处理文本的创建、存储和分析"""
    
    def __init__(self):
        super().__init__()
        self.content_type = "text"
        self.content_dao = TextDAO()
        self.url_service = UrlService()
        self.user_content_meta_service = UserContentMetaService()

    async def create_content(self, text: str, uploader_id: ObjectId, authorized_users: list[ObjectId], upload_metadata: Dict[str, Any] = None, 
                             parent_file: ObjectId = None, file_page_num: int = None) -> Dict[str, Any]:
        """创建文本内容，如果包含URL则也创建URL内容
        
        Args:
            text: 文本内容
            uploader_id: 上传者ID
            authorized_users: 授权用户ID列表
            upload_metadata: 上传元数据字典，可包含来源特定的信息
        """
        logger.info(f"创建文本: {text} 上传者: {uploader_id} 来源: {upload_metadata.get('upload_source')}")
        
        # 提取文本中的URL
        urls = extract_urls_from_text(text)
        text_id = None
        url_ids = []
        
        try:
            # 检查是否为纯URL
            is_pure_url = check_is_pure_url(text)
            # 如果不是纯URL，则创建文本记录
            if not is_pure_url:
                text_model = TextModel(
                    content=text, 
                    authorized_users=authorized_users,
                    uploader=uploader_id,
                    metadata=MetadataModel(**upload_metadata),
                    parent_file=parent_file,
                    file_page_num=file_page_num
                )
                text_id = await self.content_dao.insert_one(text_model)
                

                # 创建User Content Metadata
                await self.user_content_meta_service.create_content_meta(
                    content_type="text",
                    content_ids=[text_id],
                    user_ids=authorized_users
                )
            
            # 创建URL
            if urls:
                url_ids = await self.url_service.create_content(
                    urls=urls,
                    uploader_id=uploader_id,
                    authorized_users=authorized_users,
                    parent_text_id=text_id,
                    upload_metadata=upload_metadata,
                )
                
                # 创建 User URL Metadata
                if url_ids:
                    await self.user_content_meta_service.create_content_meta(
                        content_type="url",
                        content_ids=url_ids,
                        user_ids=authorized_users
                    )
                    
            # 只有在创建了文本记录和URL的情况下才更新子URL
            if text_id and url_ids:
                await self.content_dao.update_child_urls(text_id, url_ids)
            
            return {"text_id": text_id, "url_ids": url_ids}
        
        except Exception as e:
            # 全局异常处理，确保所有资源都被清理
            if url_ids:
                await self.url_service.delete_content(url_ids)
            if text_id:
                await self.content_dao.delete_one(text_id)
            logger.error(f"创建内容过程中发生未处理的异常: {e}")
            raise e
    
    async def get_content_description(self, content: Dict, language: str = "zh-TW") -> TextDescriptionModel:
        """获取文本描述"""
        text = content["content"]
        
        summary = ''
        auto_title = ''
        summary_vector = []
        keywords = []
        
        # 去除URL後計算字數，確認是否需要LLM摘要
        text = remove_urls_from_text(text)
        word_count = count_words(text)
        summary_min_length = 200  # 可配置的最小长度
        
        if word_count >= summary_min_length:
            # 获取通用分析结果
            analysis_result = await self.get_content_analysis(text=text, language=language)
            
            summary = analysis_result["summary"]
            auto_title = analysis_result["title"]
            summary_vector = analysis_result["summary_vector"]
            keywords = analysis_result["keywords"]
            
        else:
            # 文本过短，直接使用文本内容向量化
            summary_vector = await self.llm_service.get_embedding(text)
        
        return TextDescriptionModel(
            auto_title=auto_title,
            summary=summary,
            summary_vector=summary_vector,
            keywords=keywords
        )