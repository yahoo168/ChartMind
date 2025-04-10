import os
import boto3
from dotenv import load_dotenv
from datetime import datetime, timezone
from app.utils.logging_utils import logger

load_dotenv()

class R2Storage:
    def __init__(self):
        self.access_key = os.getenv("R2_ACCESS_KEY")
        self.secret_key = os.getenv("R2_SECRET_KEY")
        self.endpoint_url = os.getenv("R2_ENDPOINT")
        self.bucket = os.getenv("R2_BUCKET", "chartmind-images")  # 从环境变量获取bucket名称
        self.public_base_url = os.getenv("R2_PUBLIC_URL", "https://r2-image-worker.a86305394.workers.dev")  # 从环境变量获取CDN URL
        
        # 初始化 S3 client
        self.s3 = boto3.client(
            's3',
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            endpoint_url=self.endpoint_url
        )
    
    def upload(self, local_path: str, user_id: str) -> str:
        """
        上傳檔案到 R2 儲存桶
        
        Args:
            local_path: 本地檔案路徑
            user_id: 用戶ID
            
        Returns:
            str: 上傳後的公開URL
        """
        # 用日期/用戶ID產生檔名
        filename = os.path.basename(local_path)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        object_key = f"{user_id}/{today}/{filename}"

        logger.info(f"[log] Uploading {local_path} to R2 as {object_key}...")
        # 上傳
        self.s3.upload_file(local_path, self.bucket, object_key)

        # 回傳可用連結
        return {
            "url": f"{self.public_base_url}/{object_key}",
            "object_key": object_key
        }
    
    def delete(self, object_key: str) -> bool:
        """
        從 R2 儲存桶中刪除指定的檔案
        
        Args:
            object_key: 要刪除的檔案的完整路徑/鍵值
            
        Returns:
            bool: 刪除成功返回 True，失敗返回 False
        """
        try:
            logger.info(f"[log] 正在從 R2 刪除檔案: {object_key}...")
            # 刪除檔案
            self.s3.delete_object(Bucket=self.bucket, Key=object_key)
            
            logger.info(f"[log] 成功從 R2 刪除檔案: {object_key}")
            return True
        except Exception as e:
            logger.error(f"[error] 從 R2 刪除檔案時發生錯誤: {str(e)}")
            return False

# 提供函數接口
def upload_to_r2(local_path: str, user_id: str) -> str:
    r2 = R2Storage()
    return r2.upload(local_path, user_id)

def delete_from_r2(object_key: str) -> bool:
    r2 = R2Storage()
    return r2.delete(object_key)