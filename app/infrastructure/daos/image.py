import logging
from datetime import datetime, timezone
from typing import List, Dict
from bson import ObjectId
from app.infrastructure.daos.mongodb_base import MongodbBaseDAO, ensure_initialized
from app.infrastructure.models.image_models import ImageModel, ImageDescriptionModel

class ImageDAO(MongodbBaseDAO):
    def __init__(self):
        # 先調用父類初始化，確保所有屬性都已存在
        super().__init__()
        # 然後設置子類特定的屬性
        self.database_name = "Materials"
        self.collection_name = "Images"

    @ensure_initialized
    async def insert_one(self, image_data: ImageModel):
        result = await self.collection.insert_one(image_data.model_dump())
        return result.inserted_id
    
    @ensure_initialized
    async def update_is_processed(self, image_id: str, is_processed: bool):
        result = await self.collection.update_one(
            {"_id": ObjectId(image_id)},
            {"$set": {"description.is_processed": is_processed}}
        )
        return result.modified_count

    @ensure_initialized
    async def update_description(self, image_id: str, description: ImageDescriptionModel):
        result = await self.collection.update_one(
            {"_id": ObjectId(image_id)},
            {"$set": {"description": description.model_dump()}}
        )
        return result.modified_count
    
    @ensure_initialized
    async def update_ocr_text(self, image_id: str, ocr_text: str):
        result = await self.collection.update_one(
            {"_id": ObjectId(image_id)},
            {"$set": {"description.ocr_text": ocr_text}}
        )
        return result.modified_count
            
    @ensure_initialized
    async def update_labels(self, image_id: str, labels: List[str]):
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
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(image_id)},
                {"$set": {"description.gpt_summary": summary}}
            )
            return result.modified_count
        except Exception as e:
            logging.error(f"更新GPT摘要时出错 {image_id}: {str(e)}")
            return 0
    

    # @ensure_initialized
    # async def find_image_by_id(self, image_id: str):
    #     try:
    #         image = await self.collection.find_one({"_id": ObjectId(image_id)})
    #         if image:
    #             image['_id'] = str(image['_id'])
    #         return image
    #     except Exception as e:
    #         logging.error(f"Error getting image {image_id}: {str(e)}")
    #         return None
    
    @ensure_initialized
    async def find_images_by_label(self, label_id: str, user_id: str = None):
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
        
    @ensure_initialized
    async def find_images_by_user_id(self, user_id: str):
        try:
            cursor = self.collection.find({"user_id": ObjectId(user_id)})
            images = await cursor.to_list(length=None)
            images = [ImageModel(**image_data) for image_data in images]
            return images
        
        except Exception as e:
            logging.error(f"Error getting user images for {user_id}: {str(e)}")
            return []
    
    @ensure_initialized
    async def find_unprocessed_images(self):
        try:
            cursor = self.collection.find({"description.is_processed": False})
            images = await cursor.to_list(length=None)
            return images
        except Exception as e:
            logging.error(f"Error finding unprocessed images: {str(e)}")
            return []

    @ensure_initialized
    async def update_processed_status(self, image_id: str, is_processed: bool):
        result = await self.collection.update_one(
            {"_id": ObjectId(image_id)},
            {"$set": {"description.is_processed": is_processed, 
                      "description.processed_timestamp": datetime.now(timezone.utc)}}
        )
        return result.modified_count

    @ensure_initialized
    async def delete_image_by_id(self, image_id: str):
        try:
            result = await self.collection.delete_one({"_id": ObjectId(image_id)})
            return result.deleted_count
        except Exception as e:
            logging.error(f"删除图片时出错 {image_id}: {str(e)}")
            return 0