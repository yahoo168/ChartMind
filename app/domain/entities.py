class ImageEntity:
    """图像实体，表示系统中的图像对象及其基本属性"""
    
    def __init__(self, image_data: dict = None):
        self.id = image_data.get("_id") if image_data else None
        self.user_id = image_data.get("user_id") if image_data else None
        self.file_url = image_data.get("file_url") if image_data else None
        self.file_name = image_data.get("file_name") if image_data else None
        self.file_size = image_data.get("file_size") if image_data else None
        self.content_type = image_data.get("content_type") if image_data else None
        self.created_timestamp = image_data.get("created_timestamp") if image_data else None
        self.status = image_data.get("status") if image_data else None
        self.source = image_data.get("source") if image_data else None
        self.description = image_data.get("description") if image_data else None
        self.is_processed = image_data.get("is_processed", False) if image_data else False
