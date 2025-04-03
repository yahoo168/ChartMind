from bson import ObjectId
import logging
from app.daos.base_daos import BaseDAO, ensure_initialized
from app.models.image_models import ImageModel

class ImageDAO(BaseDAO):
    def __init__(self):
        # 先調用父類初始化，確保所有屬性都已存在
        super().__init__()
        # 然後設置子類特定的屬性
        self.database_name = "Materials"
        self.collection_name = "Images"

    @ensure_initialized
    async def get_one_image(self, image_id: str):
        try:
            image = await self.collection.find_one({"_id": ObjectId(image_id)})
            if image:
                image['_id'] = str(image['_id'])
            return image
        except Exception as e:
            logging.error(f"Error getting image {image_id}: {str(e)}")
            return None
    
    @ensure_initialized
    async def get_user_images(self, user_id: str):
        try:
            cursor = self.collection.find({"user_id": user_id})
            images = await cursor.to_list(length=None)
            for image in images:
                image['_id'] = str(image['_id'])
            return images
        except Exception as e:
            logging.error(f"Error getting user images for {user_id}: {str(e)}")
            return []

    @ensure_initialized
    async def insert_one(self, image_data: ImageModel):
        result = await self.collection.insert_one(image_data.model_dump())
        return str(result.inserted_id)

    # async def analyze_image(self, image_url: str):
        # 使用Vision模型獲取圖片描述
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "請分析這張圖片，並提供以下資訊：\n1. 詳細的圖片描述\n2. 5-8個相關標籤\n3. 一個簡短的標題"
                        },
                        {
                            "type": "image_url",
                            "image_url": image_url
                        }
                    ]
                }
            ],
            max_tokens=500
        )
        
        try:
            # 解析回應
            analysis = response.choices[0].message.content
            # 使用更健壯的解析方法
            lines = analysis.strip().split('\n')
            description = ""
            tags = []
            title = ""
            
            current_section = ""
            for line in lines:
                if '標籤:' in line:
                    current_section = "tags"
                    tags = [tag.strip() for tag in line.replace('標籤:', '').split(',')]
                elif '標題:' in line:
                    current_section = "title"
                    title = line.replace('標題:', '').strip()
                else:
                    if current_section == "":
                        description += line + "\n"
            
            description = description.strip()
            
            # 生成描述的向量表示
            embedding_response = self.client.embeddings.create(
                model="text-embedding-3-small",
                input=description
            )
            vector = embedding_response.data[0].embedding

            return {
                "summary": description,
                "vector": vector,
                "tags": tags,
                "title": title
            }
        except Exception as e:
            return {"error": str(e)}

    