class LabelDomainService:
    """标签领域服务，处理标签相关的核心业务逻辑"""
    
    def __init__(self):
        self.dao = ImageLabelDAO()
        self.openai_service = OpenAIService()
    
    async def create_label(self, user_id: ObjectId, label_name: str):
        """创建标签"""
        vector = await self.openai_service.get_embedding(label_name)
        label = ImageLabelModel(
            name=label_name,
            user_id=user_id,
            vector=vector,
            is_deleted=False
        )
        result = await self.dao.insert_one(label)
        return result.inserted_id
    
    async def match_user_labels(self, user_id: ObjectId, text_vector: list, 
                                high_threshold: float = 0.7, low_threshold: float = 0.2, max_labels: int = 5):
        """匹配用户标签"""
        pre_defined_labels = await self.get_label_by_user(user_id)
        high_priority = []
        low_priority = []
        for label in pre_defined_labels:
            similarity = cosine_similarity(text_vector, label['vector'])
            logger.info(f"label: {label['name']} 相似度: {similarity}")
            if similarity > high_threshold:
                high_priority.append((label, similarity))
            elif similarity > low_threshold:
                low_priority.append((label, similarity))
        high_priority.sort(key=lambda x: x[1], reverse=True)
        low_priority.sort(key=lambda x: x[1], reverse=True)
        result = [item[0] for item in high_priority]
        remaining_slots = max_labels - len(result)
        if remaining_slots > 0:
            result.extend([item[0] for item in low_priority[:remaining_slots]])
        return result
    
    async def get_or_create_labels(self, user_id, text_vector, candidate_tags):
        """获取或创建标签"""
        label_ids = []
        pre_defined_labels = await self.match_user_labels(user_id, text_vector)
        if not pre_defined_labels:
            logger.info("未找到用户标签，使用AI生成标签")
            for tag in candidate_tags[:3]:
                logger.info(f"生成标签: {tag}")
                label_id = await self.create_label(user_id, tag)
                if label_id:
                    label_ids.append(label_id)
        else:
            label_ids = [label["_id"] for label in pre_defined_labels]
            logger.info(f"找到匹配的用户标签: {len(label_ids)}个")
        logger.info(f"获取到图像标签: {label_ids}")
        return label_ids
    
    async def get_label_name_mapping(self, user_id: str):
        """获取标签ID到名称的映射"""
        labels = await self.get_label_by_user(user_id)
        return {str(label['_id']): label['name'] for label in labels}
    
    async def get_label_by_user(self, user_id: str):
        """获取用户的所有标签"""
        return await self.dao.get_label_by_user(user_id)
    
    async def count_label_by_user(self, user_id: str):
        """计算用户的标签数量"""
        return await self.dao.count_label_by_user(user_id)
    
    async def get_label_by_id(self, label_id: str):
        """根据ID获取标签"""
        return await self.dao.get_label_by_id(label_id)