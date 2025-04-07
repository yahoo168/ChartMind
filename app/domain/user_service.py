from app.daos.user_daos import UserDAO
from app.daos.image_daos import ImageDAO

from app.utils.auth_utils import _generate_random_string, create_access_token
from datetime import datetime, timezone, timedelta
from app.infrastructure.models.user_models import UserRegistrationModel, UserLoginModel
from app.exceptions.user_exceptions import UserAlreadyExistsError, InvalidCredentialsError, UserCreationError
from backend.app.domain.entities.label import LabelService

class UserAuthDomainService:
    """用户认证领域服务，处理用户相关的核心业务逻辑"""
    
    def __init__(self, user_dao=None):
        from app.daos.user_daos import UserDAO
        self.user_dao = user_dao or UserDAO()
        from app.utils.auth_utils import _generate_random_string, create_access_token
        self._generate_random_string = _generate_random_string
        self.create_access_token = create_access_token
    
    async def get_user(self, by: str, value: str):
        """根据指定字段获取用户"""
        if by not in ["user_id", "username", "line_id", "google_id"]:
            raise TypeError(f"Invalid search field: {by}")
        return await self.user_dao.find_user(**{by: value})
    
    async def login_user(self, username: str, password: str):
        """用户登录"""
        user = await self.user_dao.find_user(username=username)
        if not user or user.get("password") != password:
            from app.exceptions.user_exceptions import InvalidCredentialsError
            raise InvalidCredentialsError("Invalid username or password")
        access_token = self.create_access_token(data={"sub": username})
        return {
            "user_id": str(user.get("_id")),
            "username": user.get("username"),
            "access_token": access_token,
        }
    
    async def create_user_from_website(self, user):
        """从网站注册创建用户"""
        existing_user = await self.get_user(by="username", value=user.username)
        if existing_user:
            from app.exceptions.user_exceptions import UserAlreadyExistsError
            raise UserAlreadyExistsError(f"Username {user.username} already exists")
        try:
            user_data = {
                "username": user.username,
                "password": user.password,
            }
            await self.user_dao.create_user(user_data)
            return user_data
        except Exception as e:
            from app.exceptions.user_exceptions import UserCreationError
            raise UserCreationError(f"Failed to create user: {str(e)}")
    
    async def create_user_from_line(self, line_id: str):
        """从Line创建用户"""
        existing_user = await self.get_user(by="line_id", value=line_id)
        if existing_user:
            from app.exceptions.user_exceptions import UserAlreadyExistsError
            raise UserAlreadyExistsError(f"Line Id {line_id} already exists")
        username = self._generate_random_string()
        while await self.get_user(by="username", value=username):
            username = self._generate_random_string()
        password = self._generate_random_string()
        user_data = {
            "username": username,
            "password": password,
            "external_ids": {"line_id": line_id},
        }
        await self.user_dao.create_user(user_data)
        return user_data