from app.infrastructure.daos.user_daos import UserContentMetaDAO
from app.infrastructure.models.user_models import UserContentMetadataModel

class UserContentMetaManagementService:
    def __init__(self):
        self.user_content_meta_dao = UserContentMetaDAO()
        
    async def insert_one(self, user_content_meta_data: UserContentMetadataModel):
        return await self.user_content_meta_dao.insert_one(user_content_meta_data)
    
    async def insert_many(self, user_content_meta_data: list[UserContentMetadataModel]):
        return await self.user_content_meta_dao.insert_many(user_content_meta_data)
    
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
        
        for user_id, content_id in zip(user_ids, content_ids):
            meta_records.append(
                UserContentMetadataModel(
                    user_id=user_id,
                    content_id=content_id,
                    content_type=content_type
                )
            )
        return await self.insert_many(meta_records)