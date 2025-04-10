import os
from datetime import datetime, timezone
from bson import ObjectId

from app.infrastructure.external.GoogleDocumentAI_service import GoogleDocumentAIService
from app.infrastructure.external.openai_service import OpenAIService
from app.utils.logging_utils import logger
from app.service.label_service import LabelApplicationService
from app.infrastructure.daos.image import ImageDAO
from app.infrastructure.models.image_models import ImageDescriptionModel, ImageModel
from app.infrastructure.db.r2 import R2Storage

class ImageManagementService:
    def __init__(self):
        self.image_dao = ImageDAO()
        self.r2_storage = R2Storage()
    
    async def get_images_by_user(self, user_id: str):
        """获取用户的所有图像"""
        return await self.image_dao.find_images_by_user_id(user_id)

    async def find_unprocessed_images(self):
        """获取未处理的图像"""
        images = await self.image_dao.find_unprocessed_images()
        return images
    
    async def update_image_labels(self, image_id, labels):
        """更新图像的标签信息"""
        await self.image_dao.update_labels(image_id, labels)
    
    async def update_description(self, image_id, description):
        """添加图像描述"""
        await self.image_dao.update_description(image_id, description)
    
    async def update_is_processed(self, image_id, is_processed):
        """更新图像处理状态"""
        await self.image_dao.update_is_processed(image_id, is_processed)
    
    async def upload_image(self, local_file_path: str, user_id: str, source: str) -> str:
        """上传图像到R2存储并将元数据保存到数据库"""
        upload_result = self.r2_storage.upload(local_file_path, user_id)
        file_url = upload_result["url"]
        object_key = upload_result["object_key"]
        
        try:
            image_data = ImageModel(
                user_id=ObjectId(user_id),
                file_name=os.path.basename(file_url),
                file_url=file_url, 
                file_size=os.path.getsize(local_file_path),
                content_type="image/jpg", # TODO: 根据文件类型确定
                created_timestamp=datetime.now(timezone.utc),
                source=source,
                description=ImageDescriptionModel(),
            )
            result = await self.image_dao.insert_one(image_data)
            return result
        
        except Exception as e:
            # 数据库插入失败，删除已上传到R2的文件
            logger.error(f"Mongodb数据插入失败，删除R2文件: {object_key}, 错误: {str(e)}")
            self.r2_storage.delete(object_key)
            raise e
        

class ImageAnalysisService:
    """图像领域服务，处理与图像相关的核心业务逻辑"""
    
    def __init__(self):
        self.google_document_service = GoogleDocumentAIService()
        self.openai_service = OpenAIService(model="gpt-4o-mini")
        self.image_management_service = ImageManagementService()
        self.label_application_service = LabelApplicationService()
    
    async def _get_image_ocr_text(self, image_url: str):
        """获取图像的OCR文本"""
        try:    
            document = await self.google_document_service.process_document_from_url(image_url)
            return self.google_document_service.extract_document_text(document)
        except Exception as e:
            logger.error(f"获取 OCR 文本时出错: {e}")
            return None
    
    async def _get_image_llm_analysis(self, image_url: str):
        """获取图像分析结果"""
        try:
            result = await self.openai_service.analyze_image(image_url)
            return result
        except Exception as e:
            logger.error(f"获取图像摘要时出错: {e}")
            return None
    
    async def get_image_analysis(self, image_url: str):
        """处理图像分析，返回分析结果但不更新数据库"""
        ocr_text = await self._get_image_ocr_text(image_url)
        image_analysis = await self._get_image_llm_analysis(image_url)
        
        return {
            "title": image_analysis.get("title", ''),
            "summary": image_analysis.get("summary", ''),
            "summary_vector": image_analysis.get("summary_vector", []),
            "ocr_text": ocr_text,
            "labels": image_analysis.get("labels", [])
        }
    
    async def get_image_description(self, image: dict):
        """分析图像并生成描述"""
        user_id, image_url = image["user_id"], image["file_url"]
        image_analysis = await self.get_image_analysis(image_url)
        
        summary_vector = image_analysis.get("summary_vector", [])
        potential_labels = image_analysis.get("labels", [])
        
        matched_labels = await self.label_application_service.match_user_labels(user_id, summary_vector, potential_labels)
        matched_label_ids = [label["_id"] for label in matched_labels]
        # 打印匹配的标签
        for label in matched_labels:
            logger.info(f"Matched Labels: {label['name']}")
        
        description = ImageDescriptionModel(
            ocr_text=image_analysis.get("ocr_text", ''),
            title=image_analysis.get("title", ''),
            summary=image_analysis.get("summary", ''),
            summary_vector=summary_vector,
            labels=matched_label_ids
        )
        return description
    
    async def process_images(self):
        """处理所有未处理的图像"""
        logger.info("开始处理图像")
        unprocessed_images = await self.image_management_service.find_unprocessed_images()
        logger.info(f"未处理的图像数量: {len(unprocessed_images)}")
        processed_image_ids = []
        for image in unprocessed_images:
            try:
                description = await self.get_image_description(image)
                
                await self.image_management_service.update_description(image["_id"], description)
                await self.image_management_service.update_is_processed(image["_id"], True)
                processed_image_ids.append(image["_id"])
                
                logger.info(f"已更新图像处理状态 ID: {image['_id']}")
            except Exception as e:
                logger.error(f"处理图像时出错 ID: {image['_id']}, 错误: {str(e)}")
        logger.info(f"已成功处理图像: {len(processed_image_ids)}")
        return processed_image_ids

