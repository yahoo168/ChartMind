import os
from bson import ObjectId
from app.infrastructure.external.GoogleDocumentAI_service import GoogleDocumentAIService
from app.utils.logging_utils import logger
from app.infrastructure.daos.image_daos import ImageDAO
from app.infrastructure.models.image_models import ImageDescriptionModel, ImageModel
from app.infrastructure.models.base_models import MetadataModel
from typing import Dict, Any

from app.service.content_service import ContentService
from app.service.user_service import UserContentMetaService

class ImageService(ContentService):
    """图像服务，处理图像上传、存储和分析"""
    
    def __init__(self):
        super().__init__()
        self.content_type = "image"
        self.content_dao = ImageDAO()
        self.user_content_meta_service = UserContentMetaService()
        self.google_document_service = GoogleDocumentAIService()
    
    async def create_content(self, file_path: str, uploader_id: ObjectId, authorized_users: list[ObjectId], upload_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """上传图像"""
        upload_result = None
        image_id = None
        
        try:
            # 步骤1: 上传文件到R2存储
            upload_result = await self.r2_storage.upload(file_path, uploader_id)
            file_url = upload_result["url"]
            object_key = upload_result["object_key"]
            
            # 步骤2: 创建图像记录
            image_data = ImageModel(
                file_url=file_url, 
                authorized_users=authorized_users,
                uploader=uploader_id,
                file_size=os.path.getsize(file_path),
                file_type=os.path.splitext(file_path)[1].lstrip('.'),
                metadata=MetadataModel(**upload_metadata),
                description=ImageDescriptionModel(),
            )
            image_id = await self.content_dao.insert_one(image_data)
            
            # 步骤3: 创建User Content Metadata
            await self.user_content_meta_service.create_content_meta(
                content_type="image",
                content_ids=[image_id],
                user_ids=authorized_users
            )
            
            return {
                "image_id": image_id,
                "file_url": file_url,
                "object_key": object_key
            }
            
        except Exception as e:
            # 统一的资源清理逻辑
            await self._cleanup_resources(upload_result, image_id, e)
            raise e
    
    async def _cleanup_resources(self, upload_result, image_id, error):
        """清理上传过程中创建的资源"""
        # 记录错误
        logger.error(f"图像上传过程中出错: {error}")
        
        # 清理已上传的R2文件
        if upload_result and "object_key" in upload_result:
            object_key = upload_result["object_key"]
            logger.info(f"清理R2文件: {object_key}")
            try:
                await self.r2_storage.delete(object_key)
            except Exception as delete_error:
                logger.error(f"清理R2文件时出错: {delete_error}")
        
        # 清理已创建的图像记录
        if image_id:
            logger.info(f"清理图像记录: {image_id}")
            try:
                await self.content_dao.delete_one(image_id)
            except Exception as delete_error:
                logger.error(f"清理图像记录时出错: {delete_error}")
    
    async def get_content_description(self, content: Dict, language: str = "zh-TW") -> ImageDescriptionModel:
        async def _get_image_ocr_text(image_url: str):
            """获取图像的OCR文本"""
            try:    
                document = await self.google_document_service.process_document_from_url(image_url)
                return self.google_document_service.extract_document_text(document)
            except Exception as e:
                logger.error(f"获取OCR文本时出错: {e}")
                return None
        
        """获取图像描述"""
        image_url = content["file_url"]
        
        # 获取OCR文本
        ocr_text = await _get_image_ocr_text(image_url)
        
        # 获取图像分析结果
        analysis_result = await self.get_content_analysis(image_url=image_url, language=language)
        
        return ImageDescriptionModel(
            auto_title=analysis_result.get("title", ''),
            summary=analysis_result.get("summary", ''),
            summary_vector=analysis_result.get("summary_vector", []),
            ocr_text=ocr_text or '',
            keywords=analysis_result.get("keywords", [])
        )
    
    