import os

from app.service.image_service import ImageManagementService
from app.service.label_service import LabelManagementService
from app.service.text_service import TextManagementService
from app.service.file_service import FileManagementService
from app.utils.logging_utils import logger

class UserMaterialsUploadService:
    """用户材料上传服务，处理与用户材料相关的应用层逻辑"""
    def __init__(self):
        self.image_management_service = ImageManagementService()
        self.text_management_service = TextManagementService()
        self.file_management_service = FileManagementService()
    
    async def upload_image(self, local_file_path: str, user_id: str, source: str, auto_delete: bool = True):
        """上传图像到R2存储并将元数据保存到数据库"""
        image_id = await self.image_management_service.upload_image(local_file_path, user_id, source)

        if auto_delete:
            try:
                os.remove(local_file_path)
                logger.info(f"删除本地文件: {local_file_path}")
            except Exception as e:
                logger.error(f"删除本地文件失败: {local_file_path}, 错误: {str(e)}")
        
        return image_id
    
    async def upload_text(self, text: str, user_id: str, source: str):
        """上传文本到R2存储并将元数据保存到数据库"""
        text_id = await self.text_management_service.upload_text(text, user_id, source)
        return text_id

    async def upload_file(self, file_ext: str, file_name: str, file_path: str, user_id: str, source: str):
        """上传文件到R2存储并将元数据保存到数据库"""
        if file_ext == ".pdf":
            file_id = await self.file_management_service.upload_file(file_name, file_path, user_id, source, "pdf")
        else:
            raise ValueError(f"不支持的文件类型: {file_ext}")
        return file_id


class UserMaterialsRetrievalService:
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