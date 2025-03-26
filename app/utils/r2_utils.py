import os
import boto3
from dotenv import load_dotenv
from datetime import datetime, timezone
from app.utils.logging_config import logger

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
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
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