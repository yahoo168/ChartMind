from app.infrastructure.daos.user_daos import UserDAO
from app.utils.auth_utils import generate_random_string, create_access_token, hash_password, verify_password
from app.exceptions.user_exceptions import UserAlreadyExistsError, InvalidCredentialsError, UserCreationError

class UserManagementService:
    """用户管理服务，处理用户相关的核心业务逻辑"""    
    def __init__(self):
        self.user_dao = UserDAO()
    
    async def get_user(self, by: str, value: str):
        """根据指定字段获取用户"""
        if by not in ["user_id", "username", "line_id", "google_id"]:
            raise TypeError(f"Invalid search field: {by}")
        return await self.user_dao.find_user(**{by: value})
    
    async def get_users_by_line_group_id(self, line_group_id: str):
        """根据Line Group ID获取用户"""
        return await self.user_dao.find_users_by_line_group_id(line_group_id, only_id = True)

    async def create_user(self, user: dict):
        """从网站注册创建用户"""
        await self.user_dao.create_user(user)

    async def is_user_exists(self, by: str, value: str):
        """检查用户是否存在"""
        user = await self.get_user(by=by, value=value)
        if user:
            return True
        return False

    async def generate_random_username_and_password(self):
        username = generate_random_string()
        # 检查用户名是否已存在
        while await self.get_user(by="username", value=username):
            username = generate_random_string()
        password = generate_random_string()
        return username, password
        
class UserAuthService:
    """用户认证领域服务，处理用户相关的核心业务逻辑"""
    def __init__(self, user_dao=None, user_management_service=None):
        self.user_dao = user_dao or UserDAO()
        self.user_management_service = user_management_service or UserManagementService()
        
    async def login_user(self, username: str, password: str):
        """用户登录"""
        user = await self.user_management_service.get_user(by="username", value=username)
        if not user:
            raise InvalidCredentialsError("Invalid username or password")
        
        # 验证密码
        if not verify_password(password, user.get("password", "")):
            raise InvalidCredentialsError("Invalid username or password")
        
        return {
            "user_id": str(user.get("_id")),
            "username": user.get("username"),
            "access_token": create_access_token(data={"sub": username}),
        }
    
    async def register_user_from_website(self, user: dict):
        """从网站注册创建用户"""
        if await self.user_management_service.is_user_exists(by="username", value=user.username):
            raise UserAlreadyExistsError(f"Username {user.username} already exists")
        
        user_data = {
            "username": user.username,
            "password": hash_password(user.password), # 对密码进行加密
        }
        try:
            await self.user_management_service.create_user(user_data)
            return {
                "username": user.username,
                "password": user.password,
            }
        except Exception as e:
            raise UserCreationError(f"Failed to create user: {str(e)}")
    
    async def register_user_from_line(self, line_id: str):
        """从Line创建用户"""
        if await self.user_management_service.is_user_exists(by="line_id", value=line_id):
            raise UserAlreadyExistsError(f"User with Line Id {line_id} already exists")
        
        username, plain_password = await self.user_management_service.generate_random_username_and_password()
        password = hash_password(plain_password)
        
        user_data = {
            "username": username,
            "password": password,
            "external_ids": {"line_id": line_id},
        }
        try:
            await self.user_management_service.create_user(user_data)
            return {
                "username": username,
                "password": plain_password,
            }
        except Exception as e:
            raise UserCreationError(f"Failed to create user: {str(e)}")