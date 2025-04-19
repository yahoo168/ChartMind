import logging
from app.infrastructure.daos.content_dao import ContentDAO, ensure_initialized
from app.infrastructure.models.image_models import ImageModel, ImageDescriptionModel
from bson import ObjectId
from typing import List

class ImageDAO(ContentDAO[ImageModel]):
    def __init__(self):
        super().__init__(model_class=ImageModel)
        self.collection_name = "Images"
    
    @ensure_initialized
    async def update_description(self, image_id: str, description: ImageDescriptionModel):
        """更新图片描述信息"""
        result = await self.collection.update_one(
            {"_id": ObjectId(image_id)},
            {"$set": {"description": description.model_dump()}}
        )
        return result.modified_count
    
    @ensure_initialized
    async def update_ocr_text(self, image_id: str, ocr_text: str):
        """更新图片OCR文本"""
        result = await self.collection.update_one(
            {"_id": ObjectId(image_id)},
            {"$set": {"description.ocr_text": ocr_text}}
        )
        return result.modified_count
            
    @ensure_initialized
    async def update_labels(self, image_id: str, labels: List[str]):
        """更新图片标签"""
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(image_id)},
                {"$set": {"description.labels": labels}}
            )
            return result.modified_count
        except Exception as e:
            logging.error(f"更新图片标签时出错 {image_id}: {str(e)}")
            return 0
    
    @ensure_initialized
    async def update_summary(self, image_id: str, summary: str):
        """更新图片摘要"""
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(image_id)},
                {"$set": {"description.summary": summary}}
            )
            return result.modified_count
        except Exception as e:
            logging.error(f"更新GPT摘要时出错 {image_id}: {str(e)}")
            return 0
    
    @ensure_initialized
    async def find_images_by_label(self, label_id: str, user_id: str = None):
        """根据标签查找图片"""
        try:
            query = {"description.labels": ObjectId(label_id)}
            if user_id:
                query["user_id"] = ObjectId(user_id)
                
            cursor = self.collection.find(query)
            images = await cursor.to_list(length=None)
            images = [ImageModel(**image_data) for image_data in images]
            return images
        except Exception as e:
            logging.error(f"按标签查找图片时出错: {str(e)}")
            return []