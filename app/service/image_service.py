import os
from bson import ObjectId
import asyncio

from app.infrastructure.external.GoogleDocumentAI_service import GoogleDocumentAIService
from app.infrastructure.external.cloudflare_ai_service import CloudflareAIService
from app.utils.logging_utils import logger
from app.service.label_service import LabelApplicationService
from app.infrastructure.daos.image_daos import ImageDAO
from app.infrastructure.models.image_models import ImageDescriptionModel, ImageModel
from app.infrastructure.models.base_models import MetadataModel
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
    
    async def upload_image(self, file_path: str, user_id: str, source: str) -> str:
        """上传图像到R2存储并将元数据保存到数据库"""
        upload_result = self.r2_storage.upload(file_path, user_id)
        file_url = upload_result["url"]
        object_key = upload_result["object_key"]
        result = None
        
        try:
            image_data = ImageModel(
                user_id=ObjectId(user_id),
                file_url=file_url, 
                file_size=os.path.getsize(file_path),
                file_type=os.path.splitext(file_path)[1],
                metadata=MetadataModel(source=source),
                description=ImageDescriptionModel(),
            )
            result = await self.image_dao.insert_one(image_data)
            return result
        
        except Exception as e:
            # 上傳失敗時，清理已创建的资源，並删除已上传到R2的文件
            logger.error(f"删除R2文件: {object_key}, 错误: {str(e)}")
            self.r2_storage.delete(object_key)
            
            if result:
                logger.error(f"删除已创建的图像记录: {result}")
                await self.image_dao.delete_one(result)
            raise e
        

class ImageAnalysisService:
    """图像领域服务，处理与图像相关的核心业务逻辑"""
    
    def __init__(self):
        self.google_document_service = GoogleDocumentAIService()
        self.llm_service = CloudflareAIService()
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
    
    async def _get_image_llm_analysis(self, image_url: str, language: str = "zh-TW"):
        """获取图像分析结果"""
        try:
            if language == "zh-TW":
                prompt = """請分析這張圖片，並提供以下資訊：
                    1. 詳細的圖片描述，約150字
                    2. 5個相關label
                    3. 一個簡短的title
                    請以JSON格式回應，包含三個鍵：summary、labels（Array）和title。
                    請確保所有回應內容均使用繁體中文。
                    """
            else:
                prompt = """Please analyze this image and provide the following information:
                    1. Detailed image description, about 150 words
                    2. 5 related labels
                    3. A concise title
                    Please return the response in JSON format, containing three keys: summary, labels (Array), and title.
                    Please ensure all content is in English.
                    """

            llm_result = await self.llm_service.analyze_image(image_url, prompt, json_response=True)
            
            title = llm_result.get("title", '')
            summary = llm_result.get("summary", '')
            labels = llm_result.get("labels", [])
            summary_vector = await self.llm_service.get_embedding(summary)
            
            return {
                "title": title,
                "summary": summary,
                "summary_vector": summary_vector,
                "labels": labels
            }
        
        except Exception as e:
            logger.error(f"获取图像摘要时出错: {e}")
            return {}
    
    async def get_image_analysis(self, image_url: str):
        """处理图像分析，返回分析结果但不更新数据库"""
        ocr_text = await self._get_image_ocr_text(image_url)
        
        llm_analysis_result = await self._get_image_llm_analysis(image_url)
        
        return {
            "title": llm_analysis_result.get("title", ''),
            "summary": llm_analysis_result.get("summary", ''),
            "summary_vector": llm_analysis_result.get("summary_vector", []),
            "ocr_text": ocr_text,
            "labels": llm_analysis_result.get("labels", [])
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
            auto_title=image_analysis.get("title", ''),
            summary=image_analysis.get("summary", ''),
            summary_vector=summary_vector,
            labels=matched_label_ids
        )
        return description
    
    async def process_images(self):
        """处理所有未处理的图像"""
        try:
            logger.info("开始处理图像")
            unprocessed_images = await self.image_management_service.find_unprocessed_images()
            logger.info(f"未处理的图像数量: {len(unprocessed_images)}")
            
            if not unprocessed_images:
                logger.info("没有未处理的图像")
                return []
            
            # 创建任务列表以并行处理图像
            tasks = []
            for image in unprocessed_images:
                task = self._process_single_image(image)
                tasks.append(task)
            
            # 并行执行所有任务
            processed_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 过滤出成功处理的图像ID
            processed_image_ids = [img_id for img_id in processed_results if img_id and not isinstance(img_id, Exception)]
            
            logger.info(f"已成功处理图像: {len(processed_image_ids)}/{len(unprocessed_images)}")
            return processed_image_ids
            
        except Exception as e:
            logger.error(f"批量处理图像时出错: {str(e)}")
            return []
    
    async def _process_single_image(self, image: dict):
        """处理单个图像"""
        try:
            image_id = image["_id"]
            logger.info(f"开始处理图像 ID: {image_id}")
            
            description = await self.get_image_description(image)
            
            await self.image_management_service.update_description(image_id, description)
            await self.image_management_service.update_is_processed(image_id, True)
            
            logger.info(f"已完成图像处理 ID: {image_id}")
            return image_id
            
        except Exception as e:
            logger.error(f"处理图像时出错 ID: {image['_id']}, 错误: {str(e)}")
            return None

