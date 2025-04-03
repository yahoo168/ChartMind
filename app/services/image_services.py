from app.daos.image_daos import ImageDAO
from app.models.image_models import ImageModel, ImageDescriptionModel
import os
from datetime import datetime, timezone
from app.utils.logging_config import logger
from app.utils.r2_utils import upload_to_r2

class ImageService:
    def __init__(self):
        self.image_dao = ImageDAO()
    
    async def upload_image(self, local_file_path: str, user_id: str) -> str:
        """上传图像到R2存储并将元数据保存到数据库"""
        # 上传文件到 R2
        file_url = upload_to_r2(local_file_path, user_id)
        
        # 准备元数据(ImageModel)
        image_data = ImageModel(
            user_id=user_id,
            file_name=os.path.basename(file_url),
            file_url=file_url, 
            file_size=os.path.getsize(local_file_path),
            content_type="image/jpg",  # 暂时硬编码
            created_timestamp=datetime.now(timezone.utc),
            status="active",
            source="line",
            description=ImageDescriptionModel(),
        )
        
        # 保存图像元数据到数据库
        await self.image_dao.insert_one(image_data)

        # 處理完後刪除local臨時文件
        try:
            os.remove(local_file_path)
        except:
            logger.error(f"[log] Failed to delete local file: {local_file_path}")

        return file_url
    
    