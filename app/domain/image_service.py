from app.infrastructure.daos.image import ImageDAO
from app.infrastructure.external.documentAI_service import GoogleDocumentAIService
from app.infrastructure.external.openai_service import OpenAIService

from app.utils.logging_utils import logger
from app.domain.label_service import LabelDomainService

class ImageDomainService:
    """图像领域服务，处理与图像相关的核心业务逻辑"""
    
    def __init__(self):
        self.image_dao = ImageDAO()
        self.google_document_service = GoogleDocumentAIService()
        self.openai_service = OpenAIService(model="gpt-4o-mini")
        self.label_service = LabelDomainService()
    
    async def get_image_ocr_text(self, image_url: str):
        """获取图像的OCR文本"""
        try:    
            document = await self.google_document_service.process_document_from_url(image_url)
            return self.google_document_service.extract_document_text(document)
        except Exception as e:
            logger.error(f"获取 OCR 文本时出错: {e}")
            return None
    
    async def get_image_llm_analysis(self, image_url: str):
        """获取图像分析结果"""
        try:
            result = await self.openai_service.analyze_image(image_url)
            return result
        except Exception as e:
            logger.error(f"获取图像摘要时出错: {e}")
            return None
    
    async def process_image_analysis(self, image_url: str):
        """处理图像分析，返回分析结果但不更新数据库"""
        ocr_text = await self.get_image_ocr_text(image_url)
        image_analysis = await self.get_image_llm_analysis(image_url)
        
        return {
            "ocr_text": ocr_text,
            "title": image_analysis.get("title", ''),
            "summary": image_analysis.get("summary", ''),
            "summary_vector": image_analysis.get("summary_vector", []),
            "candidate_tags": image_analysis.get("tags", [])
        }
    
    async def get_image_labels(self, user_id, text_vector, candidate_tags):
        """获取图像标签"""
        # 优先匹配用户已存在的标签
        pre_defined_labels = await self.label_service.match_user_labels(user_id, text_vector)
        
        if pre_defined_labels:
            return await self._process_existing_labels(pre_defined_labels)
        else:
            return await self._generate_new_labels(user_id, candidate_tags)
    
    async def _process_existing_labels(self, pre_defined_labels):
        """处理已存在的标签"""
        label_ids = [label["_id"] for label in pre_defined_labels]
        logger.info(f"找到匹配的用户标签: {len(label_ids)}个")
        logger.info(f"获取到图像标签: {label_ids}")
        return label_ids
    
    async def _generate_new_labels(self, user_id, candidate_tags, max_labels=3):
        """生成新的标签"""
        logger.info("未找到用户标签，使用AI生成标签")
        label_ids = []
        for tag in candidate_tags[:max_labels]: # 限制最多生成3个标签
            logger.info(f"生成标签: {tag}")
            label_id = await self.label_service.create_label(user_id, tag)
            if label_id:
                label_ids.append(label_id)
        
        logger.info(f"获取到图像标签: {label_ids}")
        return label_ids




