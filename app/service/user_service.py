from app.infrastructure.daos.user_daos import UserDAO
from app.infrastructure.daos.user_daos import UserContentMetaDAO
from app.utils.auth_utils import generate_random_string, create_access_token, hash_password, verify_password
from app.exceptions.user_exceptions import UserAlreadyExistsError, InvalidCredentialsError, UserCreationError
from app.infrastructure.models.user_models import UserContentMetadataModel
from app.utils.logging_utils import logger
from bson import ObjectId

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

class UserContentMetaService:
    def __init__(self):
        self.user_content_meta_dao = UserContentMetaDAO()
    
    async def get_user_content_meta(self, content_id: ObjectId):
        """获取用户内容元数据"""
        return await self.user_content_meta_dao.find_user_content_meta(content_id)
    
    async def update_content_labels(self, user_id: ObjectId, content_id: ObjectId, content_type: str, label_ids: list[ObjectId]):
        """更新内容标签"""
        return await self.user_content_meta_dao.update_content_labels(user_id, content_id, content_type, label_ids)

    async def create_content_meta(self, content_type: str, content_ids: list[str], user_ids: list[str]):
        """
        批量创建用户内容元数据
        
        Args:
            content_type: 内容类型，如"text"、"url"、"file"、"image"等
            content_ids: 内容ID列表
            user_ids: 用户ID列表，可以是单个用户ID或多个用户ID
            
        Returns:
            插入的元数据记录
        """
        meta_records = []
        
        # 为每个用户创建每个内容的元数据记录（笛卡尔积）
        for user_id in user_ids:
            for content_id in content_ids:
                meta_records.append(
                    UserContentMetadataModel(
                        user_id=user_id,
                        content_id=content_id,
                        content_type=content_type
                    )
                )
        
        return await self.user_content_meta_dao.insert_many(meta_records)