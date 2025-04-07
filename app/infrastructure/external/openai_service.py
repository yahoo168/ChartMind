from openai import OpenAI
import os
import json

class OpenAIService:
    def __init__(self, model="gpt-4o-mini"):
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.model = model

    async def get_embedding(self, text: str) -> list:
        """
        獲取文本的向量表示
        
        Args:
            text: 需要向量化的文本
            
        Returns:
            list: 文本的向量表示
        """
        try:
            embedding_response = self.client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return embedding_response.data[0].embedding
        except Exception as e:
            print(f"生成向量時發生錯誤: {str(e)}")
            return []

    async def _get_image_analysis(self, image_url: str) -> dict:
        """
        使用Vision模型分析圖片
        
        Args:
            image_url: 圖片URL
            
        Returns:
            dict: 包含summary、tags和title的字典
        """
        prompt = """請分析這張圖片，並提供以下資訊：
        1. 詳細的圖片描述，約150字
        2. 5個相關tag
        3. 一個簡短的title

        請以JSON格式回應，包含三個鍵：summary、tags（陣列）和title。"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user", 
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": image_url}
                            }
                        ]
                    }
                ],
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"分析圖片時發生錯誤: {str(e)}")
            return {}

    async def analyze_image(self, image_url: str):
        """
        分析圖片並返回完整的分析結果
        
        Args:
            image_url: 圖片URL
            
        Returns:
            dict: 包含summary、vector、tags和title的字典
        """
        try:
            # 獲取圖片分析結果
            analysis = await self._get_image_analysis(image_url)
            
            if not analysis:
                return {"error": "圖片分析失敗"}

            # 獲取各個部分
            summary = analysis.get("summary", "")
            tags = analysis.get("tags", [])
            title = analysis.get("title", "")
            
            # 生成描述的向量表示
            summary_vector = await self.get_embedding(summary)

            return {
                "summary": summary,
                "summary_vector": summary_vector,
                "tags": tags,
                "title": title
            }
        except Exception as e:
            return {"error": str(e)}