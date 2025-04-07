# application_services.py
import os
from datetime import datetime, timezone
from app.infrastructure.db.r2 import upload_to_r2
from app.infrastructure.models.image_models import ImageModel, ImageDescriptionModel
from app.infrastructure.daos.image import ImageDAO
from app.utils.logging_utils import logger

class ImageAnalysisApplicationService:
    """处理图像分析相关的跨领域业务流程"""
    
    def __init__(self):
        # 注意：这里的 ImageService 可视情况为领域服务或简单包装实体
        from backend.app.domain.entities.image import ImageService  
        # 改为使用领域服务
        from domain_services import UserAuthDomainService, LabelDomainService
        self.image_service = ImageService()
        self.user_service = UserAuthDomainService()
        self.label_service = LabelDomainService()

class ImageApplicationService:
    """图像应用服务，处理与图像相关的应用层逻辑"""
    
    def __init__(self):
        self.image_dao = ImageDAO()
        from domain_services import ImageDomainService
        self.domain_service = ImageDomainService()
    
    async def get_user_images(self, user_id: str):
        """获取用户的所有图像"""
        return await self.image_dao.find_user_images(user_id=user_id)
    
    async def find_unprocessed_images(self):
        """获取未处理的图像"""
        images = await self.image_dao.find_unprocessed_images()
        logger.info(f"获取到未处理图像: {len(images)}")
        return images
    
    async def update_image_with_labels(self, image_id, labels):
        """更新图像的标签信息"""
        await self.image_dao.update_image_labels(image_id, labels)
    
    async def add_description(self, image_id, description):
        """添加图像描述"""
        await self.image_dao.add_description(image_id, description)
    
    async def update_is_processed(self, image_id, is_processed):
        """更新图像处理状态"""
        await self.image_dao.update_is_processed(image_id, is_processed)
    
    async def analyze_image(self, image: dict):
        """分析图像并生成描述"""
        user_id = image["user_id"]
        image_url = image["file_url"]
        
        ocr_text = await self.domain_service.get_image_ocr_text(image_url)
        image_analysis = await self.domain_service.get_image_analysis(image_url)
        
        summary_vector = image_analysis.get("summary_vector", [])
        tags = image_analysis.get("tags", [])
        labels = await self.domain_service.get_image_labels(user_id, summary_vector, tags)
        
        description = ImageDescriptionModel(
            ocr_text=ocr_text,
            title=image_analysis.get("title", ''),
            summary=image_analysis.get("summary", ''),
            summary_vector=summary_vector,
            labels=labels
        )
        return description
    
    async def process_images(self):
        """处理所有未处理的图像"""
        logger.info("开始处理图像")
        images = await self.find_unprocessed_images()
        processed_images = []
        for image in images:
            try:
                description = await self.analyze_image(image)
                await self.add_description(image["_id"], description)
                processed_images.append(image)
                await self.update_is_processed(image["_id"], True)
                logger.info(f"已更新图像处理状态 ID: {image['_id']}")
            except Exception as e:
                logger.error(f"处理图像时出错 ID: {image['_id']}, 错误: {str(e)}")
        logger.info(f"已成功处理图像: {len(processed_images)}")
        return processed_images
    
    async def upload_image(self, local_file_path: str, user_id: str) -> str:
        """上传图像到R2存储并将元数据保存到数据库"""
        file_url = upload_to_r2(local_file_path, user_id)
        image_data = ImageModel(
            user_id=user_id,
            file_name=os.path.basename(file_url),
            file_url=file_url, 
            file_size=os.path.getsize(local_file_path),
            content_type="image/jpg",
            created_timestamp=datetime.now(timezone.utc),
            status="active",
            source="line",
            description=ImageDescriptionModel(),
        )
        await self.image_dao.insert_one(image_data)
        try:
            os.remove(local_file_path)
        except Exception as e:
            logger.error(f"删除本地文件失败: {local_file_path}, 错误: {str(e)}")
        return file_url

class UserManagementApplicationService:
    """处理用户管理相关的跨领域业务流程"""
    
    def __init__(self):
        from domain_services import UserAuthDomainService, LabelDomainService
        self.user_service = UserAuthDomainService()
        self.label_service = LabelDomainService()
    
    async def register_and_initialize_user(self, user_data, source="website"):
        """注册用户并初始化相关资源"""
        if source == "website":
            user = await self.user_service.create_user_from_website(user_data)
        elif source == "line":
            user = await self.user_service.create_user_from_line(user_data)
        else:
            raise ValueError(f"不支持的用户来源: {source}")
        
        default_labels = ["图表", "数据", "报告"]
        for label in default_labels:
            await self.label_service.create_label(user["_id"], label)
        return user

class UserImageApplicationService:
    """用户图像应用服务，处理与用户图像相关的应用层逻辑"""
    
    def __init__(self, user_dao=None, image_dao=None):
        from app.daos.user_daos import UserDAO
        from app.daos.image_daos import ImageDAO
        self.user_dao = user_dao or UserDAO()
        self.image_dao = image_dao or ImageDAO()
        from domain_services import LabelDomainService
        self.label_service = LabelDomainService()
    
    async def get_user_images(self, user_id: str):
        images = await self.image_dao.get_user_images(user_id=user_id)
        label_name_mapping = await self.label_service.get_label_name_mapping(user_id=user_id)
        for image in images:
            image.description.label_names = [
                label_name_mapping.get(str(label_id), "未知标签") 
                for label_id in image.description.labels
            ]
        return images
