import os
import boto3
from dotenv import load_dotenv
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient

from app.models.image_models import ImageModel, ImageDescriptionModel
from app.utils.logging_config import logger
from app.utils.mongodb_utils import MongoDB
from app.utils.r2_utils import upload_to_r2

load_dotenv()
    
async def upload_image(local_file_path: str, user_id: str) -> str:
    # 上传文件到 R2
    file_url = upload_to_r2(local_file_path, user_id)
    
    # 准备元数据
    # 创建 ImageModel 实例
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
    
    document = image_data.model_dump() # 将 ImageModel Instance 转换为字典
    
    # 上传元数据到 MongoDB
    db = MongoDB.get_db("Materials")
    collection = db["Images"]
    await collection.insert_one(document)

    # 處理完後刪除local臨時文件
    try:
        os.remove(local_file_path)
    except:
        logger.error(f"[log] Failed to delete local file: {local_file_path}")

    return file_url
