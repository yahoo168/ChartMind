import random
import string
from datetime import datetime, timedelta, timezone
import os
from jose import jwt
import bcrypt

def create_access_token(data: dict, expires_minutes: int = 15):
    SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key") #用來加密和解密 JWT 的密鑰
    to_encode = data.copy() 
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
    return encoded_jwt

def generate_random_string(min_len=6, max_len=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=random.randint(min_len, max_len)))

def hash_password(password: str) -> str:
        """对密码进行哈希处理"""
        # 将密码转换为字节并加盐哈希
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')  # 将字节转回字符串存储

def verify_password(plain_password: str, hashed_password: str) -> bool:
        """验证密码是否匹配"""
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )