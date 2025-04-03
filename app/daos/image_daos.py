from app.utils.mongodb_utils import MongoDB
from bson import ObjectId

class ImageDAO:
    def __init__(self):
        db = MongoDB.get_db("Materials")
        self.collection = db["Images"]

    async def find_image(self, image_id: str):
        return self.collection.find_one({"_id": image_id})
    
    async def get_user_images(self, user_id: str):
        # 获取查询结果并转换为列表
        cursor = self.collection.find({"user_id": user_id})
        images = await cursor.to_list(length=None)
        # 确保返回的是可序列化的数据，将ObjectId转换为字符串
        for image in images:
            image['_id'] = str(image['_id'])
        return images