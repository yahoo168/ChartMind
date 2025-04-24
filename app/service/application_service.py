from app.service.image_service import ImageService
from app.service.label_service import LabelManagementService

from app.service.file_service import FileService
from app.service.image_service import ImageService
from app.service.text_service import TextService
from app.service.url_services import UrlService

from app.service.user_service import UserManagementService
from app.service.user_service import UserContentMetaService
from app.utils.logging_utils import logger
from bson import ObjectId

class UserContentUploadService:
    """用户内容上传服务，处理与用户内容相关的应用层逻辑"""
    def __init__(self):
        self.file_service = FileService()
        self.image_service = ImageService()
        self.text_service = TextService()
        self.user_management_service = UserManagementService()
        self.user_content_meta_service = UserContentMetaService()
    
    async def _get_users_by_line_group_id(self, line_group_id: str):
        """根据Line Group ID获取用户ID"""
        return await self.user_management_service.get_users_by_line_group_id(line_group_id)
    
    async def _get_content_authorized_users(self, uploader_id: str, source: str, line_group_id: str = ''):
        """获取授权用户列表"""
        if line_group_id and source == "linebot":
            return await self._get_users_by_line_group_id(line_group_id)
        else:
            return [ObjectId(uploader_id)]

    async def upload_text(self, text: str, uploader_id: str, upload_source: str, line_group_id: str = ''):
        authorized_users = await self._get_content_authorized_users(uploader_id, upload_source, line_group_id)
        
        upload_metadata = {
            "upload_source": upload_source,
            "line_group_id": line_group_id
        }
        
        upload_result = await self.text_service.create_content(
            text=text, 
            uploader_id=ObjectId(uploader_id), 
            authorized_users=authorized_users, 
            upload_metadata=upload_metadata
        )
        text_id, url_ids = upload_result["text_id"], upload_result["url_ids"]
        logger.info(f"text_id: {text_id}, url_ids: {url_ids}")
        

    async def upload_image(self, file_path: str, user_id: str, upload_source: str, line_group_id: str = ''):
        """上传图像到R2存储并将元数据保存到数据库"""
        authorized_users = await self._get_content_authorized_users(user_id, upload_source, line_group_id)
        upload_metadata={
            "upload_source": upload_source,
            "line_group_id": line_group_id
        }
        await self.image_service.create_content(
            file_path=file_path, 
            uploader_id=ObjectId(user_id), 
            authorized_users=authorized_users, 
            upload_metadata=upload_metadata
        )

    async def upload_file(self, file_type: str, file_name: str, file_path: str, user_id: str, upload_source: str, line_group_id: str = ''):
        """上传文件到R2存储并将元数据保存到数据库"""
        if file_type != "pdf":
            raise ValueError(f"不支持的文件类型: {file_type}")
        
        authorized_users = await self._get_content_authorized_users(user_id, upload_source, line_group_id)
        upload_metadata={
            "upload_source": upload_source,
            "line_group_id": line_group_id
        }
        
        await self.file_service.create_content(
            file_type=file_type,
            file_name=file_name,
            file_path=file_path,
            uploader_id=ObjectId(user_id), 
            authorized_users=authorized_users, 
            upload_metadata=upload_metadata
        )

class UserContentRetrievalService:
    """用户材料检索服务，处理与用户材料相关的应用层逻辑"""

    def __init__(self):
        self.text_service = TextService()
        self.image_service = ImageService()
        self.url_service = UrlService()
        self.file_service = FileService()
        
        self.label_management_service = LabelManagementService()
        self.user_content_meta_service = UserContentMetaService()

    async def get_user_labels(self, user_id: ObjectId):
        return await self.label_management_service.get_labels_by_user(user_id, contain_vector=False)
    
    async def _filter_content_by_criteria(self, user_id: ObjectId, content_type: str, labels: list[ObjectId] = None, query_text: str = '', limit: int = 10):
        """根据标签和搜索词筛选内容，返回内容或内容ID列表"""
        service_map = {
            "text": self.text_service,
            "file": self.file_service,
            "image": self.image_service,
            "url": self.url_service
        }
        
        service = service_map.get(content_type)
        if not service:
            raise ValueError(f"不支持的内容类型: {content_type}")
        
        # 首先获取用户有权限访问的内容ID列表（考虑标签过滤）
        accessible_content_ids = await self.user_content_meta_service.get_user_content_ids(user_id, content_type, labels)
        logger.info(f"accessible_content_ids: {len(accessible_content_ids)}")
        
        # 如果没有搜索词，直接返回基于标签过滤的结果
        if not query_text:
            content_ids = accessible_content_ids[:limit]
            return await service.find_content_by_ids(content_ids)
        
        # 如果有搜索词，在用户可访问的内容中进行搜索
        search_result = await service.smart_search(query_text, user_id, limit)
        
        # 过滤搜索结果，只保留用户有权访问的内容
        filtered_results = [result for result in search_result if result["_id"] in accessible_content_ids]
        
        # logger.info(f"search_results: {query_text} {len(search_result)}")
        # logger.info(f"filtered_results: {query_text} {len(filtered_results)}")
        # print("Accessible Content IDs: ", accessible_content_ids)
        # print()
        # print("Search Result: ", search_result)
        
        # 如果需要限制结果数量
        return filtered_results[:limit] if limit else filtered_results
    
    async def get_user_texts(self, user_id: ObjectId, labels: list[ObjectId] = [], query_text: str = '', limit: int = 10):
        return await self._filter_content_by_criteria(user_id, "text", labels, query_text, limit)
    
    async def get_user_files(self, user_id: ObjectId, labels: list[ObjectId] = [], query_text: str = '', limit: int = 10):
        return await self._filter_content_by_criteria(user_id, "file", labels, query_text, limit)
    
    async def get_user_images(self, user_id: ObjectId, labels: list[ObjectId] = [], query_text: str = '', limit: int = 10):
        return await self._filter_content_by_criteria(user_id, "image", labels, query_text, limit)
    
    async def get_user_urls(self, user_id: ObjectId, labels: list[ObjectId] = [], query_text: str = '', limit: int = 10):
        return await self._filter_content_by_criteria(user_id, "url", labels, query_text, limit)