from app.infrastructure.daos.label_daos import ImageLabelDAO
from app.infrastructure.external.openai_service import OpenAIService
from app.infrastructure.models.label_models import LabelModel
from app.utils.logging_utils import logger
from app.utils.math_utils import cosine_similarity
from typing import List

class LabelManagementService:
    """标签管理服务，处理标签相关的核心业务逻辑"""
    
    def __init__(self):
        self.dao = ImageLabelDAO()
        self.openai_service = OpenAIService()
    
    async def create_label(self, user_id: str, label_name: str):
        """创建标签"""
        vector = await self.openai_service.get_embedding(label_name)
        
        label = LabelModel(
            name=label_name,
            user_id=user_id,
            vector=vector,
            is_deleted=False
        )
        await self.dao.insert_one(label)
        return label
    
    async def get_label_by_user(self, user_id: str):
        """获取用户的所有标签"""
        return await self.dao.get_label_by_user(user_id)
    
    async def count_label_by_user(self, user_id: str):
        """计算用户的标签数量"""
        return await self.dao.count_label_by_user(user_id)
    
    async def get_label_by_id(self, label_id: str):
        """根据ID获取标签"""
        return await self.dao.get_label_by_id(label_id)

    async def get_id_to_name_mapping(self, user_id: str):
        """获取标签ID到名称的映射"""
        labels = await self.get_label_by_user(user_id)
        return {str(label['_id']): label['name'] for label in labels}
    
    async def get_name_to_id_mapping(self, user_id: str):
        """获取标签名称到ID的映射"""
        labels = await self.get_label_by_user(user_id)
        return {label['name']: str(label['_id']) for label in labels}

class LabelDomainService:
    """标签领域服务，处理标签相关的核心业务逻辑"""    
    async def get_content_labels(self, content_vector: List[float], 
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
            logger.info(f"label: {label['name']} 相似度: {similarity}")
            
            if similarity > high_threshold:
                high_priority.append((label, similarity))
            elif similarity > low_threshold:
                low_priority.append((label, similarity))
                
        # 按相似度排序
        high_priority.sort(key=lambda x: x[1], reverse=True)
        low_priority.sort(key=lambda x: x[1], reverse=True)
        
        return {'high': high_priority, 'low': low_priority}