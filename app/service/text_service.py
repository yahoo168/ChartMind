from app.utils.format_utils import extract_urls_from_text
from app.infrastructure.models.text_models import TextModel, TextDescriptionModel,UrlModel, UrlDescriptionModel
from bson import ObjectId
from app.infrastructure.daos.text import TextDAO, UrlDAO
from app.utils.logging_utils import logger

class TextManagementService:
    def __init__(self):
        self.text_dao = TextDAO()
        self.url_dao = UrlDAO()
    
    async def upload_text(self, text: str, user_id: str, source: str):
        logger.info(f"Uploading text: {text} for user: {user_id} with source: {source}")
        try:
            text_model = TextModel(content=text, user_id=ObjectId(user_id), source=source)
            text_id = await self.text_dao.insert_one(text_model)
        except Exception as e:
            logger.error(f"Error uploading text: {e}")
            raise e
            
        try:
            # 提取文本中的URL，并保存到数据库
            urls = extract_urls_from_text(text)
            if urls:
                url_models = []
                for url in urls:
                    url_model = UrlModel(url=url, user_id=ObjectId(user_id), source=source, parent_text=text_id)
                    url_models.append(url_model)
                url_ids = await self.url_dao.insert_many(url_models)
                # 更新文本的子URL
                await self.text_dao.update_child_urls(text_id, url_ids)
        except Exception as e:
            logger.error(f"Error uploading urls: {e}")
            raise e
        

# class TextAnalysisService:
#     def __init__(self):
#         pass

#     async def analyze_text(self, text: str):
#         urls = extract_urls_from_text(text)
#         return urls
