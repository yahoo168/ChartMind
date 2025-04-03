from app.daos.user_daos import UserDAO
from app.daos.image_daos import ImageDAO

from app.utils.auth_utils import _generate_random_string, create_access_token
from datetime import datetime, timezone, timedelta
from app.models.user_models import UserRegistrationModel, UserLoginModel
from app.exceptions.user_exceptions import UserAlreadyExistsError, InvalidCredentialsError, UserCreationError


#Uf6048653a6cfc5e8d2a87f35b8cf12ad
class UserImageService:
    def __init__(self, user_dao=None, image_dao=None):
        # 正常使用（不手動傳 DAO） / 單元測試（傳 mock DAO）
        self.user_dao = user_dao or UserDAO()
        self.image_dao = image_dao or ImageDAO()

    async def get_user_images(self, user_id: str):
        return await self.image_dao.get_user_images(user_id=user_id)

class UserAuthService:
    def __init__(self, user_dao=None):
        # 正常使用（不手動傳 DAO） / 單元測試（傳 mock DAO）
        self.user_dao = user_dao or UserDAO()
    
    async def get_user(self, by: str, value: str):
        if not by in ["user_id", "username", "line_id", "google_id"]:
            raise TypeError(f"Invalid search field: {by}")
        return await self.user_dao.find_user(**{by: value})

    async def login_user(self, username: str, password: str):
        user = await self.user_dao.find_user(username=username)
        if not user or user.get("password") != password:
            raise InvalidCredentialsError("Invalid username or password")
        
        access_token = create_access_token(data={"sub": username},)

        return {
            "user_id": str(user.get("_id")),
            "username": user.get("username"),
            "access_token": access_token,
        }
    
    async def create_user_from_website(self, user: UserRegistrationModel):
        existing_user = await self.get_user(by="username", value=user.username)
        if existing_user:
            raise UserAlreadyExistsError(f"Username {user.username} already exists")

        try:
            user_data = {
                "username": user.username,
                "password": user.password,
            }
            await self.user_dao.create_user(user_data)
            return user_data
        
        except Exception as e:
            raise UserCreationError(f"Failed to create user: {str(e)}")

    async def create_user_from_line(self, line_id: str):
        # Check if the user exists.
        existing_user = await self.get_user(by="line_id", value=line_id)
        if existing_user:
            raise UserAlreadyExistsError(f"Line Id {line_id} already exists")
        
        # If the line user has not registered, generate a random username
        username = _generate_random_string()
        while await self.get_user(by="username", value=username):
            username = _generate_random_string()
        password = _generate_random_string()

        user_data = {
            "username": username,
            "password": password,
            "external_ids": {"line_id": line_id},
        }

        await self.user_dao.create_user(user_data)
        return user_data
        
    