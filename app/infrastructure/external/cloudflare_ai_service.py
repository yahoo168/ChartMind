import os
import json
import base64
import aiohttp
from app.utils.logging_utils import logger

class CloudflareAIService:
    def __init__(self, 
                 model="gpt-4o-mini", 
                 embedding_model="text-embedding-3-large"):
        
        self.api_endpoint = os.environ.get("CLOUDFLARE_AI_ENDPOINT")
        self.api_token = os.environ.get("OPENAI_API_TOKEN")
        self.model = model
        self.embedding_model = embedding_model
        # 添加一個共享的 ClientSession 以提高效率
        self.session = None

        if not self.api_endpoint or not self.api_token:
            raise ValueError("請設定 CLOUDFLARE_AI_ENDPOINT 與 OPENAI_API_TOKEN 環境變數")
            
    async def __aenter__(self):
        """支持異步上下文管理器模式"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """關閉會話"""
        if self.session:
            await self.session.close()
            self.session = None

    async def _make_api_request(self, url: str, payload: dict) -> dict:
        """
        向 Cloudflare AI Gateway 發送通用 API 請求
        """
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        try:
            # 使用共享會話或創建臨時會話
            session_to_use = self.session or aiohttp.ClientSession()
            should_close = not self.session
            
            try:
                async with session_to_use.post(url, headers=headers, json=payload) as response:
                    response_text = await response.text()
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"Cloudflare AI Gateway 返回錯誤: 狀態碼 {response.status}, URL: {url}, 回應: {response_text}")
                        return {"error": f"API 請求失敗，狀態碼: {response.status}", "details": response_text}
            finally:
                # 如果是臨時創建的會話，則關閉它
                if should_close:
                    await session_to_use.close()
        except Exception as e:
            logger.error(f"API 請求發生錯誤: {str(e)}, URL: {url}")
            return {"error": f"API 請求異常: {str(e)}"}

    async def _fetch_image_data(self, image_url: str) -> str:
        """
        下載圖片並轉換為 base64 編碼
        """
        try:
            # 使用共享會話或創建臨時會話
            session_to_use = self.session or aiohttp.ClientSession()
            should_close = not self.session
            
            try:
                async with session_to_use.get(image_url) as img_response:
                    if img_response.status != 200:
                        logger.error(f"圖片載入失敗: {img_response.status}")
                        return ""
                    image_data = await img_response.read()
                    return base64.b64encode(image_data).decode('utf-8')
            finally:
                # 如果是臨時創建的會話，則關閉它
                if should_close:
                    await session_to_use.close()
        except Exception as e:
            logger.error(f"下載圖片時發生錯誤: {str(e)}")
            return ""

    async def get_embedding(self, text: str) -> list:
        """
        使用 Cloudflare AI Gateway 取得向量表示
        """
        # 修正 URL 格式，根據 Cloudflare Workers AI 文檔
        url = f"{self.api_endpoint}/v1/embeddings"
        
        payload = {
            "model": self.embedding_model,
            "input": text
        }
        
        result = await self._make_api_request(url, payload)
        
        if "error" in result:
            logger.error(f"獲取嵌入向量失敗: {result}")
            return []
        
        # 根據 Cloudflare Workers AI 的回應格式調整
        if "data" in result and len(result["data"]) > 0:
            return result["data"][0].get("embedding", [])
        
        logger.warning(f"嵌入向量回應格式異常: {result}")
        return []
    
    async def _prepare_chat_completion_payload(self, messages: list, max_tokens: int = 1000, json_response: bool = False) -> dict:
        """
        準備聊天完成請求的通用 payload
        
        Args:
            messages: 消息列表，包含角色和內容
            max_tokens: 回應的最大 token 數
            json_response: 是否要求 JSON 格式的回應
            
        Returns:
            dict: 準備好的 payload
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens
        }
        
        if json_response:
            payload["response_format"] = {"type": "json_object"}
            
        return payload
    
    async def _process_chat_completion_response(self, result: dict, json_response: bool = False) -> dict:
        """
        處理聊天完成 API 的回應
        
        Args:
            result: API 回應結果
            json_response: 是否期望 JSON 格式的回應
            
        Returns:
            dict: 處理後的結果，如果 json_response=True 則返回解析後的 JSON，否則返回文本內容
        """
        try:
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                # 如果 json_response=True，則返回解析後的 JSON，否則返回文本內容
                if json_response:
                    return json.loads(content)
                else:
                    return content
            
            logger.error(f"Cloudflare AI Gateway 返回格式異常: {result}")
            return {}
        except Exception as e:
            logger.error(f"處理 API 回應時發生錯誤: {str(e)}, 回應: {result}")
            return {}
    
    async def analyze_text(self, text: str, prompt: str, max_tokens: int = 1000, json_response: bool = False) -> dict:
        """
        使用 Cloudflare AI Gateway 分析文本，根據提供的提示進行處理
        
        Args:
            text: 要分析的文本內容
            prompt: 指導模型如何分析文本的提示
            max_tokens: 回應的最大 token 數
            
        Returns:
            dict: 模型分析的結果
        """
        url = f"{self.api_endpoint}/v1/chat/completions"
        
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"{prompt}\n\n{text}"}
                ]
            }
        ]
        
        payload = await self._prepare_chat_completion_payload(messages, max_tokens, json_response)
        result = await self._make_api_request(url, payload)
        return await self._process_chat_completion_response(result, json_response)

    async def analyze_image(self, image_url: str, prompt: str = None, max_tokens: int = 1000, json_response: bool = False) -> dict:
        """
        使用 Cloudflare AI Gateway 分析圖片
        
        Args:
            image_url: 圖片的 URL
            prompt: 指導模型如何分析圖片的提示，如果為 None 則使用默認提示
            max_tokens: 回應的最大 token 數
            
        Returns:
            dict: 模型分析的結果，包含 summary、labels、title
        """

        # 下載圖片並轉換為 base64
        image_base64 = await self._fetch_image_data(image_url)
        if not image_base64:
            return {}

        url = f"{self.api_endpoint}/v1/chat/completions"
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                ]
            }
        ]
        
        payload = await self._prepare_chat_completion_payload(messages, max_tokens, json_response)
        result = await self._make_api_request(url, payload)
        return await self._process_chat_completion_response(result, json_response)