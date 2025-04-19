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
    
    async def get_content_authorized_users(self, uploader_id: str, source: str, line_group_id: str = ''):
        """获取授权用户列表"""
        if line_group_id and source == "linebot":
            return await self._get_users_by_line_group_id(line_group_id)
        else:
            return [ObjectId(uploader_id)]

    async def upload_text(self, text: str, uploader_id: str, upload_source: str, line_group_id: str = ''):
        authorized_users = await self.get_content_authorized_users(uploader_id, upload_source, line_group_id)
        
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
        authorized_users = await self.get_content_authorized_users(user_id, upload_source, line_group_id)
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
        
        authorized_users = await self.get_content_authorized_users(user_id, upload_source, line_group_id)
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
        self.image_service = ImageService()
        self.label_management_service = LabelManagementService()
    
    async def get_user_images(self, user_id: str):
        labels_id_to_name = await self.label_management_service.get_id_to_name_mapping(user_id)
        
        images = await self.image_service.get_images_by_user(user_id)
        
        result = []
        for image in images:
            image_dict = image.model_dump()
            image_dict["description"]["labels"] = [ 
                {"name": labels_id_to_name[label_id], "id": str(label_id)} 
                for label_id in image_dict["description"]["labels"]
            ]
            result.append(image_dict)
        return result