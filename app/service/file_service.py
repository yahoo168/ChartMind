from typing import Dict, Any, List
from bson import ObjectId
import os

from app.utils.logging_utils import logger
from app.utils.format_utils import extract_pdf_content

from app.infrastructure.daos.file_daos import FileDAO
from app.infrastructure.models.file_models import FileModel, FileDescriptionModel
from app.infrastructure.models.text_models import TextModel
from app.infrastructure.models.base_models import MetadataModel
from app.infrastructure.daos.text_daos import TextDAO

from app.service.content_service import ContentService
from app.service.user_service import UserContentMetaService
from app.service.text_service import TextService
from app.infrastructure.models.text_models import TextModel
from app.infrastructure.db.r2 import download_to_temp

class FileService(ContentService):
    """文件服务，处理文件上传、存储和分析"""
    
    def __init__(self):
        super().__init__()
        self.content_type = "file"
        self.content_dao = FileDAO()
        self.text_dao = TextDAO()
        self.text_service = TextService()
        self.user_content_meta_service = UserContentMetaService()
    
    async def create_content(self, file_name: str, file_path: str, file_type: str, uploader_id: ObjectId, 
                             authorized_users: list[ObjectId], upload_metadata: Dict[str, Any]):
        """上传文件的通用方法"""
        file_id = None
        object_key = None
        
        try:
            # 步骤1: 上传文件到R2
            upload_result = await self.r2_storage.upload(file_path, uploader_id)
            file_url = upload_result["url"]
            object_key = upload_result["object_key"]
            
            # 步骤2: 创建文件记录
            file_data = FileModel(
                    file_type=file_type, 
                    title=file_name, 
                    file_url=file_url,
                    authorized_users=authorized_users,
                    uploader=uploader_id,
                    file_size=os.path.getsize(file_path),
                    metadata=MetadataModel(**upload_metadata),
                    description=FileDescriptionModel()
                )
            file_id = await self.content_dao.insert_one(file_data)
            
            # 步骤3: 创建User Content Metadata
            await self.user_content_meta_service.create_content_meta(
                content_type="file",
                content_ids=[file_id],
                user_ids=authorized_users
            )
            
            return file_id
            
        except Exception as e:
            # 删除数据库记录
            if file_id:
                try:
                    logger.error(f"删除已创建的文件记录: {file_id}, 错误: {e}")
                    await self.content_dao.delete_one(file_id)
                except Exception as cleanup_error:
                    logger.error(f"清理文件记录时出错: {cleanup_error}")
            
            # 删除R2存储的文件
            if object_key:
                try:
                    logger.error(f"删除R2文件: {object_key}, 错误: {e}")
                    await self.r2_storage.delete(object_key)
                except Exception as cleanup_error:
                    logger.error(f"清理R2文件时出错: {cleanup_error}")
    
    async def _process_file_text(self, file_url: str, file_type: str, uploader_id: ObjectId, authorized_users: list[ObjectId], upload_metadata: Dict[str, Any],
                              file_id: ObjectId):
        """处理文件文本提取，根据文件类型调用不同的处理函数"""
        text_ids = []
        url_ids = []
        
        # 根据文件类型选择不同的处理方法
        if file_type.lower() == "pdf":
            file_texts = await self._get_pdf_content(file_url)
        elif file_type.lower() in ["docx", "doc"]:
            file_texts = await self._get_word_content(file_url)
        elif file_type.lower() in ["txt", "md"]:
            file_texts = await self._get_text_content(file_url)
        else:
            # 不支持的文件类型
            logger.warning(f"不支持的文件类型: {file_type}")
            return []
        
        # 创建文本模型
        for i in range(len(file_texts)):
            result = await self.text_service.create_content(
                text=file_texts[i],
                authorized_users=authorized_users,
                uploader_id=uploader_id,
                upload_metadata=upload_metadata,
                parent_file=file_id,
                file_page_num=i+1
            )
            text_ids.append(result["text_id"])
            url_ids.extend(result["url_ids"])
            
        return text_ids, file_texts
    
    async def get_file_child_texts(self, file_id: ObjectId) -> List[str]:
        """获取文件中的文本内容"""
        return await self.content_dao.get_child_texts(file_id)
    
    async def get_content_description(self, content: Dict, language: str = "zh-TW") -> FileDescriptionModel:
        """获取文件描述"""
        file_id = content["_id"]
        file_url = content.get("file_url")
        file_type = content.get("file_type", "")
        uploader_id = content.get("uploader")
        authorized_users = content.get("authorized_users", [])
        
        upload_metadata = {
            "upload_source": content.get("metadata", {}).get("upload_source", ""),
            "line_group_id": content.get("metadata", {}).get("line_group_id", "")
        }
        
        # 確認文件是否已處理，若無則處理
        text_ids = content.get("child_texts", [])
        if not text_ids and file_url:
            # 處理文本提取並關聯到文件
            text_ids, file_texts = await self._process_file_text(file_url, file_type, uploader_id, authorized_users, upload_metadata, file_id)
            await self.content_dao.update_child_texts(file_id, text_ids)
        
        file_text = '\n'.join(file_texts)[:10000]  # 限制不超过10000字，避免Token超限

        # 获取通用分析结果
        analysis_result = await self.get_content_analysis(text=file_text, language=language)
        return FileDescriptionModel(
            auto_title=analysis_result["title"],
            summary=analysis_result["summary"],
            summary_vector=analysis_result["summary_vector"],
            keywords=analysis_result["keywords"],
        )
    
    async def _get_pdf_content(self, file_url: str) -> List[str]:
        """从URL提取PDF内容"""
        # 从URL下载临时文件
        temp_file_path = await download_to_temp(file_url)
        try:
            # 提取PDF内容
            pages_texts = extract_pdf_content(temp_file_path)
            return pages_texts
        finally:
            # 清理临时文件
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
    
    async def _get_word_content(self, file_url: str) -> List[str]:
        """从URL提取Word文档内容"""
        # TODO: 实现Word文档内容提取
        # 这里需要实现从Word文档提取文本的逻辑
        return ["暂不支持Word文档内容提取"]
    
    async def _get_text_content(self, file_url: str) -> List[str]:
        """从URL提取纯文本内容"""
        # 从URL下载临时文件
        temp_file_path = await download_to_temp(file_url)
        try:
            with open(temp_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            # 将文本内容作为单页返回
            return [content]
        finally:
            # 清理临时文件
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)