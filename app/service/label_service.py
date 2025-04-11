from app.infrastructure.daos.label_daos import LabelDAO
from app.infrastructure.external.cloudflare_ai_service import CloudflareAIService
from app.infrastructure.models.label_models import LabelModel
from app.utils.logging_utils import logger
from app.utils.math_utils import cosine_similarity
from typing import List

class LabelManagementService:
    """标签管理服务，处理标签相关的核心业务逻辑"""
    
    def __init__(self):
        self.dao = LabelDAO()
        self.llm_service = CloudflareAIService()
    
    async def is_label_exists(self, user_id: str, label_name: str):
        """检查标签是否存在"""
        return await self.dao.is_label_exists(user_id, label_name)
    
    async def create_label(self, user_id: str, label_name: str):
        """创建标签"""
        if len(label_name) >= 50:
            logger.info(f"标签名称过长: {label_name}，限制为50个字符")
            return None
        
        if await self.is_label_exists(user_id, label_name):
            logger.info(f"标签已存在: {label_name}")
            return None
        
        vector = await self.llm_service.get_embedding(label_name)
        
        label = LabelModel(
            name=label_name,
            user_id=user_id,
            vector=vector,
            is_deleted=False
        )
        await self.dao.insert_one(label)
        return label
    
    async def get_labels_by_user(self, user_id: str):
        """获取用户的所有标签"""
        return await self.dao.find_labels_by_user_id(user_id)
    
    async def count_labels_by_user(self, user_id: str):
        """计算用户的标签数量"""
        return await self.dao.count_labels_by_user_id(user_id)

    async def get_id_to_name_mapping(self, user_id: str):
        """获取标签ID到名称的映射"""
        labels = await self.get_labels_by_user(user_id)
        return {label['_id']: label['name'] for label in labels}
    
    async def get_name_to_id_mapping(self, user_id: str):
        """获取标签名称到ID的映射"""
        labels = await self.get_labels_by_user(user_id)
        return {label['name']: str(label['_id']) for label in labels}

class LabelApplicationService:
    """标签应用服务，处理与标签相关的核心业务逻辑"""
    
    def __init__(self):
        self.label_management_service = LabelManagementService()
    
    async def match_user_labels(self, user_id:str, content_vector:List[float], potential_labels:List[str]):
        """获取图像标签"""
        # 优先匹配用户已存在的标签
        user_labels = await self.label_management_service.get_labels_by_user(user_id=user_id)
        labels = await self.match_content_labels(content_vector, user_labels)
        
        if not labels:
            logger.info(f"未找到匹配的用户标签，使用AI生成标签")
            labels = await self._generate_new_labels(user_id, potential_labels)
    
        return labels
    
    async def _generate_new_labels(self, user_id:str, potential_labels:List[str], max_labels=3):
        """生成新的标签"""
        logger.info("未找到用户标签，使用AI生成标签")
        labels = []
        for label in potential_labels[:max_labels]: # 限制最多生成3个标签
            logger.info(f"生成标签: {label}")
            label = await self.label_management_service.create_label(user_id, label)
            if label:
                labels.append(label)
        return labels
    
    """标签领域服务，处理标签相关的核心业务逻辑"""    
    async def match_content_labels(self, content_vector: List[float], 
                              labels: List[LabelModel], max_labels: int = 5):
        """匹配用户标签"""
        # 计算相似度并分类标签
        potential_labels = self._categorize_labels_by_similarity(labels, content_vector)
        
        # 选择最终标签
        """从分类后的标签中选择最终标签"""
        final_labels = [item[0] for item in potential_labels['high']]
        
        # 如果高优先级标签不足，添加低优先级标签
        remaining_slots = max_labels - len(final_labels)
        if remaining_slots > 0:
            final_labels.extend([item[0] for item in potential_labels['low'][:remaining_slots]])
        return final_labels
    
    def _categorize_labels_by_similarity(self, labels:List[LabelModel], content_vector:List[float], high_threshold=0.7, low_threshold=0.2):
        """根据相似度对标签进行分类"""
        high_priority = []
        low_priority = []
        
        for label in labels:
            similarity = cosine_similarity(content_vector, label['vector'])
            # logger.info(f"label: {label['name']} 相似度: {similarity}")
            
            if similarity > high_threshold:
                high_priority.append((label, similarity))
            elif similarity > low_threshold:
                low_priority.append((label, similarity))
                
        # 按相似度排序
        high_priority.sort(key=lambda x: x[1], reverse=True)
        low_priority.sort(key=lambda x: x[1], reverse=True)
        
        return {'high': high_priority, 'low': low_priority}