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
    
    async def create_label(self, user_id: str, label_name: str, label_description: str, 
                           include_keywords: List[str] = [], exclude_keywords: List[str] = []):
        """创建标签"""
        if len(label_name) >= 30:
            logger.info(f"标签名称过长: {label_name}，限制为30个字符")
            return None
        
        if len(label_description) >= 200:
            logger.info(f"标签描述过长: {label_description}，限制为200个字符")
            return None
        
        if await self.is_label_exists(user_id, label_name):
            logger.info(f"标签已存在: {label_name}")
            return None
        
        vector = await self.llm_service.get_embedding(label_description)
        
        label = LabelModel(
            name=label_name,
            description=label_description,
            user_id=user_id,
            vector=vector,
            is_deleted=False,
            include_keywords=include_keywords,
            exclude_keywords=exclude_keywords
        )
        await self.dao.insert_one(label)
        return label
    
    async def get_labels_by_user(self, user_id: str, contain_vector: bool = True):
        """获取用户的所有标签"""
        return await self.dao.find_labels_by_user_id(user_id, contain_vector)
    
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
        self.llm_service = CloudflareAIService()

    async def match_user_labels(self, user_id:str, representative_content:str, content_vector:List[float], max_labels: int = 5):
        """获取并匹配用户标签
        
        Args:
            user_id: 用户ID
            representative_content: 内容代表性文本
            content_vector: 内容向量
            max_labels: 最大标签数量，默认为5
            
        Returns:
            匹配到的标签列表
        """
        # 获取用户已存在的标签
        user_labels = await self.label_management_service.get_labels_by_user(user_id=user_id)
        
        # 根据关键词筛选标签
        included_labels, remaining_labels = self._filter_labels_by_keywords(user_labels, representative_content)
        
        # 计算相似度并分类剩余标签
        potential_labels = self._categorize_labels_by_similarity(remaining_labels, content_vector)
        
        # 选择最终标签，优先选择包含关键词的标签
        final_labels = included_labels.copy()
        
        # 如果还有剩余名额，添加高优先级标签
        remaining_slots = max_labels - len(final_labels)
        if remaining_slots > 0:
            high_priority_labels = [item[0] for item in potential_labels['high']]
            final_labels.extend(high_priority_labels[:remaining_slots])
            remaining_slots -= len(high_priority_labels[:remaining_slots])
        
        # 如果高优先级标签不足，添加低优先级标签
        if remaining_slots > 0:
            final_labels.extend([item[0] for item in potential_labels['low'][:remaining_slots]])
        
        return final_labels
    
    def _filter_labels_by_keywords(self, labels: List[dict], content: str):
        """根据关键词过滤标签
        
        Args:
            labels: 标签列表
            content: 内容文本
            
        Returns:
            包含两个元素的元组: (包含关键词匹配的标签, 待进一步处理的标签)
        """
        
        included_labels = []
        remaining_labels = []
        
        for label in labels:
            exclude_keywords = label.get('exclude_keywords', [])
            include_keywords = label.get('include_keywords', [])
            
            # 检查排除关键词
            should_exclude = False
            if exclude_keywords:
                for keyword in exclude_keywords:
                    if keyword and keyword.strip() and keyword.lower() in content.lower():
                        logger.info(f"标签 {label['name']} 因排除关键词 '{keyword}' 被过滤")
                        should_exclude = True
                        break
            
            # 如果标签应该被排除，则跳过后续处理
            if should_exclude:
                continue
                
            # 检查包含关键词
            if include_keywords:
                for keyword in include_keywords:
                    if keyword and keyword.strip() and keyword.lower() in content.lower():
                        included_labels.append(label)
                        logger.info(f"标签 {label['name']} 因包含关键词 '{keyword}' 被优先选择")
                        break
                else:
                    # 如果没有匹配到包含关键词，加入剩余标签列表
                    remaining_labels.append(label)
            else:
                # 没有包含关键词的标签，加入剩余标签列表
                remaining_labels.append(label)
                
        return included_labels, remaining_labels

    
    def _categorize_labels_by_similarity(self, labels:List[LabelModel], content_vector:List[float], high_threshold=0.7, low_threshold=0.25):
        """根据相似度对标签进行分类"""
        high_priority = []
        low_priority = []
        
        for label in labels:
            similarity = cosine_similarity(content_vector, label['vector'])
            logger.info(f"标签: {label['name']} 相似度: {similarity}")
            if similarity > high_threshold:
                high_priority.append((label, similarity))
            elif similarity > low_threshold:
                low_priority.append((label, similarity))
                
        # 按相似度排序
        high_priority.sort(key=lambda x: x[1], reverse=True)
        low_priority.sort(key=lambda x: x[1], reverse=True)
        
        return {'high': high_priority, 'low': low_priority}

    # 待修改
    async def consolidate_labels(self, user_id: str, potential_labels: List[str], max_labels: int = 3) -> List[dict]:
        """从潜在标签中提取并生成最具代表性的标签
        
        Args:
            user_id: 用户ID
            potential_labels: 潜在标签列表
            max_labels: 最大标签数量，默认为3
            
        Returns:
            生成的标签列表
        """
        logger.info(f"从 {len(potential_labels)} 个潜在标签中提取 {max_labels} 个代表性标签")
        
        # 将标签列表转换为字符串以供LLM分析
        labels_text = ", ".join(potential_labels)
        
        prompt = f"""分析以下标签列表，找出最具代表性的{max_labels}个标签，确保这些标签能概括所有输入标签的主要含义：
            {labels_text}
            
            请严格按照以下JSON数组格式返回标签，不要添加任何其他文字说明：
            ["标签1", "标签2", "标签3"]
            
            返回的标签数量不要超过{max_labels}个。每个标签应简洁明了，不超过5个字。"""
            
        try:
            consolidated_labels = await self.llm_service.analyze_text(labels_text, prompt, json_response=True)
            
            labels = []
            for label_name in consolidated_labels[:max_labels]:
                logger.info(f"生成标签: {label_name}")
                label = await self.label_management_service.create_label(user_id, label_name)
                if label:
                    labels.append(label)
            return labels
            
        except Exception as e:
            logger.error(f"生成标签时出错: {str(e)}")
            return []