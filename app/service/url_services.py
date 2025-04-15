from app.infrastructure.external.cloudflare_ai_service import CloudflareAIService
from app.service.label_service import LabelApplicationService
from app.infrastructure.daos.url_daos import UrlDAO
from app.utils.logging_utils import logger
from app.utils.url_utils import get_url_preview

from app.infrastructure.models.url_models import UrlModel, UrlDescriptionModel
from app.infrastructure.models.base_models import MetadataModel
import asyncio
from bson import ObjectId

class UrlManagementService:
    def __init__(self):
        self.url_dao = UrlDAO()
    
    async def get_unprocessed_urls(self):
        return await self.url_dao.find_unprocessed_urls()
    
    async def update_url_preview(self, url_id, title, thumbnail_url, description_summary, summary_vector, label_ids):
        await self.url_dao.update_url_preview(url_id, title, thumbnail_url, description_summary, summary_vector, label_ids)
    
    async def update_url_is_processed(self, url_id, is_processed):
        await self.url_dao.update_url_is_processed(url_id, is_processed)

    async def delete_url(self, url_id: ObjectId):
        await self.url_dao.delete_one(url_id)

    async def create_urls_from_text(self, urls: list[str], authorized_users: list[ObjectId], 
                                   uploader: ObjectId, upload_source: str, 
                                   line_group_id: str = '', parent_text_id: str = None):
        """从文本中创建URL记录"""
        try:            
            url_models = []
            for url in urls:
                url_model = UrlModel(url=url, 
                                    authorized_users=authorized_users,
                                    uploader=uploader,
                                    metadata=MetadataModel(upload_source=upload_source, 
                                                           line_group_id=line_group_id,),
                                    description=UrlDescriptionModel(),
                                    parent_text=parent_text_id)
                url_models.append(url_model)
            
            url_ids = await self.url_dao.insert_many(url_models)
            return url_ids
        except Exception as e:
            logger.error(f"Error creating URLs from text: {e}")
            raise e

class UrlAnalysisService:
    def __init__(self):
        self.url_dao = UrlDAO()
        self.url_management_service = UrlManagementService()
        self.label_application_service = LabelApplicationService()
        self.llm_service = CloudflareAIService()
        self.max_workers = 5  # 可以根据需要调整线程数量

    async def process_urls(self):
        unprocessed_urls = await self.url_management_service.get_unprocessed_urls()
        if not unprocessed_urls:
            logger.info("没有未处理的URL")
            return
            
        # 创建任务列表
        tasks = []
        for url_doc in unprocessed_urls:
            task = self._process_single_url(url_doc)
            tasks.append(task)
            
        # 并发执行所有任务
        await asyncio.gather(*tasks)
        logger.info(f"已完成处理 {len(tasks)} 个URL")
        
    async def _process_single_url(self, url_doc):
        url = url_doc["url"]
        user_id = url_doc["user_id"]

        try:
            url_preview = await get_url_preview(url)
            logger.info(f"获取URL预览: {url}")
            
            # 获取url的title, thumbnail_url, description_summary
            title = url_preview.get("title", '')
            thumbnail_url = url_preview.get("thumbnail_url", '')
            description_summary = url_preview.get("description", '')
            summary_vector = await self.llm_service.get_embedding(description_summary)
            labels = await self.label_application_service.match_user_labels(user_id, summary_vector)
            label_ids = [label["_id"] for label in labels]
            await self.url_management_service.update_url_preview(url_doc["_id"], title, thumbnail_url, description_summary, summary_vector, label_ids)
            await self.url_management_service.update_url_is_processed(url_doc["_id"], True)

            logger.info(f"已处理URL: {url_doc['_id']}")
            
        except Exception as e:
            logger.error(f"处理URL时出错: {e}")
            await self.url_management_service.update_url_is_processed(url_doc["_id"], False)