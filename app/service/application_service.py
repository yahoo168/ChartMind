from app.service.image_service import ImageManagementService
from app.service.label_service import LabelManagementService
from app.service.text_service import TextManagementService
from app.service.file_service import FileManagementService
from app.service.user_service import UserManagementService
from app.service.user_content_meta_service import UserContentMetaManagementService
from app.service.url_services import UrlManagementService

from app.utils.logging_utils import logger
from bson import ObjectId

class UserContentUploadService:
    """用户内容上传服务，处理与用户内容相关的应用层逻辑"""
    def __init__(self):
        self.image_management_service = ImageManagementService()
        self.text_management_service = TextManagementService()
        self.url_management_service = UrlManagementService()
        self.file_management_service = FileManagementService()
        self.user_management_service = UserManagementService()
        self.user_content_meta_management_service = UserContentMetaManagementService()
    
    async def _get_users_by_line_group_id(self, line_group_id: str):
        """根据Line Group ID获取用户ID"""
        return await self.user_management_service.get_users_by_line_group_id(line_group_id)
    
    async def _get_authorized_users(self, uploader_id: str, source: str, line_group_id: str = ''):
        """获取授权用户列表"""
        if line_group_id and source == "linebot":
            return await self._get_users_by_line_group_id(line_group_id)
        else:
            return [ObjectId(uploader_id)]

    async def _create_content_meta_with_rollback(self, content_type: str, content_ids: list, user_ids: list, 
                                               rollback_func=None, rollback_args=None):
        """创建内容元数据，失败时执行回滚操作"""
        try:
            if content_ids:
                await self.user_content_meta_management_service.create_content_meta(
                    content_type=content_type, 
                    content_ids=content_ids, 
                    user_ids=user_ids
                )
        except Exception as e:
            logger.error(f"创建{content_type}元数据失败: {e}")
            # 执行回滚
            if rollback_func and rollback_args:
                try:
                    await rollback_func(**rollback_args)
                    logger.info(f"成功回滚已上传的{content_type}: {rollback_args}")
                except Exception as rollback_error:
                    logger.error(f"回滚{content_type}失败: {rollback_error}")
            raise e

    async def upload_text(self, text: str, uploader_id: str, source: str, line_group_id: str = ''):
        """上传文本到R2存储并将元数据保存到数据库"""
        authorized_users = await self._get_authorized_users(uploader_id, source, line_group_id)
        
        upload_result = await self.text_management_service.upload_text(
            text=text, 
            uploader=ObjectId(uploader_id), 
            authorized_users=authorized_users, 
            upload_source=source, 
            line_group_id=line_group_id
        )
        text_id, url_ids = upload_result["text_id"], upload_result["url_ids"]
        
        # 定义回滚函数
        async def rollback_text_upload(text_id=None, url_ids=None):
            if text_id:
                await self.text_management_service.delete_text(text_id)
            if url_ids and len(url_ids) > 0:
                for url_id in url_ids:
                    await self.url_management_service.delete_url(url_id)
        
        # 创建文本元数据
        await self._create_content_meta_with_rollback(
            content_type="text", 
            content_ids=[text_id] if text_id else [], 
            user_ids=authorized_users,
            rollback_func=rollback_text_upload,
            rollback_args={"text_id": text_id, "url_ids": url_ids}
        )
        
        # 创建URL元数据
        if url_ids:
            await self._create_content_meta_with_rollback(
                content_type="url", 
                content_ids=url_ids, 
                user_ids=authorized_users,
                rollback_func=rollback_text_upload,
                rollback_args={"text_id": text_id, "url_ids": url_ids}
            )
        
        return {"text_id": text_id, "url_ids": url_ids}

    async def upload_image(self, local_file_path: str, user_id: str, source: str, line_group_id: str = ''):
        """上传图像到R2存储并将元数据保存到数据库"""
        authorized_users = await self._get_authorized_users(user_id, source, line_group_id)
        
        image_id = await self.image_management_service.upload_image(
            file_path=local_file_path, 
            uploader=ObjectId(user_id), 
            authorized_users=authorized_users, 
            upload_source=source, 
            line_group_id=line_group_id
        )
        
        # 定义回滚函数
        async def rollback_image_upload(image_id=None):
            if image_id:
                await self.image_management_service.delete_image(image_id)
        
        # 创建图像元数据
        await self._create_content_meta_with_rollback(
            content_type="image", 
            content_ids=[image_id] if image_id else [], 
            user_ids=authorized_users,
            rollback_func=rollback_image_upload,
            rollback_args={"image_id": image_id}
        )
        
        return image_id

    async def upload_file(self, file_ext: str, file_name: str, file_path: str, user_id: str, source: str, line_group_id: str = ''):
        """上传文件到R2存储并将元数据保存到数据库"""
        if file_ext != "pdf":
            raise ValueError(f"不支持的文件类型: {file_ext}")
        
        authorized_users = await self._get_authorized_users(user_id, source, line_group_id)
        logger.info(f"application-service: {line_group_id}")
        file_id = await self.file_management_service.create_file(
            file_name=file_name, 
            file_path=file_path, 
            user_id=user_id, 
            source=source, 
            file_type=file_ext,
            line_group_id=line_group_id
        )
        
        # 定义回滚函数
        async def rollback_file_upload(file_id=None):
            if file_id:
                await self.file_management_service.delete_file(file_id)
        
        # 创建文件元数据
        await self._create_content_meta_with_rollback(
            content_type="file", 
            content_ids=[file_id] if file_id else [], 
            user_ids=authorized_users,
            rollback_func=rollback_file_upload,
            rollback_args={"file_id": file_id}
        )
        
        return file_id

class UserContentRetrievalService:
    """用户材料检索服务，处理与用户材料相关的应用层逻辑"""

    def __init__(self):
        self.image_management_service = ImageManagementService()
        self.label_management_service = LabelManagementService()
    
    async def get_user_images(self, user_id: str):
        labels_id_to_name = await self.label_management_service.get_id_to_name_mapping(user_id)
        
        images = await self.image_management_service.get_images_by_user(user_id)
        
        result = []
        for image in images:
            image_dict = image.model_dump()
            image_dict["description"]["labels"] = [ 
                {"name": labels_id_to_name[label_id], "id": str(label_id)} 
                for label_id in image_dict["description"]["labels"]
            ]
            result.append(image_dict)
        return result