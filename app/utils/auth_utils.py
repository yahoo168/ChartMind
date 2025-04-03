import random
import string
from datetime import datetime, timedelta, timezone
import os
from jose import jwt

# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token") 
def create_access_token(data: dict, expires_minutes: int = 15):
    SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key") #用來加密和解密 JWT 的密鑰
    to_encode = data.copy() 
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
    return encoded_jwt

def _generate_random_string(min_len=6, max_len=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=random.randint(min_len, max_len)))