import os
import boto3
from dotenv import load_dotenv
from datetime import datetime, timezone
from pymongo import MongoClient
from data_models.image import ImageModel, DescriptionModel
import logging

logger = logging.getLogger("uvicorn.error")  # 使用 uvicorn 的 log 管道

load_dotenv()

def upload_to_r2(local_path: str, user_id: str) -> str:
    access_key = os.getenv("R2_ACCESS_KEY")
    secret_key = os.getenv("R2_SECRET_KEY")
    endpoint_url = os.getenv("R2_ENDPOINT")
    bucket = "chartmind-images" #設定的 Bucket 名稱
    public_base_url = os.getenv("R2_PUBLIC_URL_BASE")  # 你設定的 CDN URL
    public_base_url = "https://r2-image-worker.a86305394.workers.dev"  # Cloudflare Workers設定的 CDN URL
    
    # 用日期/用戶ID產生檔名
    filename = os.path.basename(local_path)
    today = datetime.now().strftime("%Y-%m-%d")
    object_key = f"{user_id}/{today}/{filename}"

    # 初始化 S3 client
    s3 = boto3.client(
        's3',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        endpoint_url=endpoint_url
    )

    logger.info(f"[log] Uploading {local_path} to R2 as {object_key}...")
    # 上傳
    s3.upload_file(local_path, bucket, object_key)

    # 回傳可用連結（你可以用 Cloudflare Worker/Route 建立公開網址）
    return f"{public_base_url}/{object_key}"

def upload_to_mongodb(doc: dict):
    from data_models.image import ImageModel, DescriptionModel
    
    mongo_uri = os.getenv("MONGODB_URI")
    mdb_client = MongoClient(mongo_uri)
    collection = mdb_client['upload_materials']['images']
    # 插入数据到 MongoDB
    collection.insert_one(doc)
    mdb_client.close()

def upload_and_store(local_file_path: str, user_id: str) -> str:
    # 上传文件到 R2
    file_url = upload_to_r2(local_file_path, user_id)
    
    # 准备元数据
    # 创建 ImageModel 实例
    image_data = ImageModel(
        user_id=user_id,
        file_name=os.path.basename(file_url),
        file_url=file_url, 
        thumbnail_url="",  # 暂时为空
        file_size=os.path.getsize(local_file_path),
        content_type="image/jpeg",  # 暂时硬编码
        created_timestamp=datetime.now(timezone.utc),
        status="active",
        source="line",
        description=DescriptionModel(
            tags=[],
            ocr_text="",
            gpt_summary="",
            comments=[]
        ),
        metadata={}
    )
    document = image_data.model_dump() # 将 ImageModel Instance 转换为字典
    # 上传元数据到 MongoDB
    upload_to_mongodb(document)
    
    # 處理完後刪除local臨時文件
    try:
        os.remove(local_file_path)
    except:
        logger.error(f"[log] Failed to delete local file: {local_file_path}")

    return file_url
