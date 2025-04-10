import os
from google.cloud import documentai_v1 as documentai
from google.api_core.client_options import ClientOptions
import aiohttp
import aiofiles

class GoogleDocumentAIService:
    """Google Document AI API 异步服务类"""
    
    def __init__(self, project_id=None, location="us", processor_id=None, credentials_path=None):
        """
        初始化 Google Document AI 服务
        
        Args:
            project_id: Google Cloud 项目ID，默认从环境变量获取
            location: 处理器所在区域，默认为 'us'
            processor_id: Document AI 处理器ID，默认从环境变量获取
            credentials_path: Google API 凭证文件路径，默认从环境变量获取
        """
        if credentials_path is None:
            credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        else:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
            
        if not credentials_path:
            raise ValueError("必须提供 Google API 凭证路径")
            
        self.project_id = project_id or os.environ.get('GOOGLE_CLOUD_PROJECT')
        if not self.project_id:
            raise ValueError("必须提供 Google Cloud 项目ID")
        
        self.processor_id = processor_id or os.environ.get('DOCUMENT_AI_PROCESSOR_ID')
        if not self.processor_id:
            raise ValueError("必须提供 Document AI 处理器ID")
            
        self.location = location
        
        # 初始化客户端
        client_options = ClientOptions(api_endpoint=f"{self.location}-documentai.googleapis.com")
        self.client = documentai.DocumentProcessorServiceClient(client_options=client_options)
        
        # 设置处理器名称
        self.processor_name = self.client.processor_path(
            self.project_id, self.location, self.processor_id
        )
    
    async def _process_document_internal(self, file_content, mime_type="application/pdf"):
        """
        内部文档处理方法（异步）
        
        Args:
            file_content: 文档字节内容
            mime_type: 文档MIME类型
            
        Returns:
            document: 处理后的文档对象
        """
        # 创建处理请求
        raw_document = documentai.RawDocument(content=file_content, mime_type=mime_type)
        request = documentai.ProcessRequest(
            name=self.processor_name,
            raw_document=raw_document
        )
        
        try:
            # 注意：如果 Google 客户端不支持原生异步，需要使用 loop.run_in_executor
            import asyncio
            response = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: self.client.process_document(request=request)
            )
            return response.document
        except Exception as e:
            print(f"处理文档时出错: {e}")
            return None
    
    async def process_document(self, file_path, mime_type=None):
        """
        处理文档（异步）
        
        Args:
            file_path: 文档文件路径
            mime_type: 文档MIME类型，如果为None则自动检测
            
        Returns:
            document: 处理后的文档对象
        """
        # 如果未指定MIME类型，根据文件扩展名自动检测
        if mime_type is None:
            file_extension = os.path.splitext(file_path)[1].lower()
            
            if not mime_type:
                mime_type = 'application/pdf'  # 默认为PDF
        
        # 异步读取文件内容
        async with aiofiles.open(file_path, "rb") as file:
            file_content = await file.read()
        
        return await self._process_document_internal(file_content, mime_type)
    
    async def process_document_from_bytes(self, file_content, mime_type="application/pdf"):
        """
        从字节数据处理文档（异步）
        
        Args:
            file_content: 文档字节内容
            mime_type: 文档MIME类型，默认为PDF
            
        Returns:
            document: 处理后的文档对象
        """
        return await self._process_document_internal(file_content, mime_type)
    
    async def process_document_from_url(self, image_url, mime_type=None):
        """
        从图片URL处理文档（异步）
        
        Args:
            image_url: 图片的URL地址
            mime_type: 文档MIME类型，如果为None则自动检测
            
        Returns:
            document: 处理后的文档对象
        """
        try:
            # 异步下载图片内容
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    response.raise_for_status()
                    file_content = await response.read()
                    
                    # MIME类型处理逻辑保持不变
                    if mime_type is None:
                        file_extension = os.path.splitext(image_url.split('?')[0])[1].lower()
                        mime_type = self._get_mime_type_from_extension(file_extension)
                        
                        if not mime_type and 'Content-Type' in response.headers:
                            mime_type = response.headers['Content-Type']
                        
                        if not mime_type:
                            mime_type = 'application/pdf'
            
            return await self._process_document_internal(file_content, mime_type)
            
        except Exception as e:
            print(f"从URL处理文档时出错: {e}")
            return None
    
    def _get_mime_type_from_extension(self, file_extension):
        """
        根据文件扩展名获取MIME类型
        
        Args:
            file_extension: 文件扩展名（包含点，如 '.pdf'）
            
        Returns:
            mime_type: 对应的MIME类型，如果不支持则返回None
        """
        mime_types = {
            '.pdf': 'application/pdf',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.tiff': 'image/tiff',
            '.tif': 'image/tiff',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.webp': 'image/webp',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.ppt': 'application/vnd.ms-powerpoint',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.txt': 'text/plain',
        }
        return mime_types.get(file_extension)
    
    def extract_document_text(self, document):
        """
        从处理后的文档中提取文本
        
        Args:
            document: Document AI 处理后的文档对象
            
        Returns:
            text: 提取的文本内容
        """
        if not document:
            return ""
        return document.text
    
    def extract_document_entities(self, document):
        """
        从处理后的文档中提取实体
        
        Args:
            document: Document AI 处理后的文档对象
            
        Returns:
            entities: 提取的实体列表
        """
        if not document or not hasattr(document, 'entities'):
            return []
            
        entities = []
        for entity in document.entities:
            entity_data = {
                'type': entity.type_,
                'mention_text': entity.mention_text,
                'confidence': entity.confidence,
                'normalized_value': entity.normalized_value.text if entity.normalized_value else None
            }
            entities.append(entity_data)
            
        return entities
    
    def extract_document_tables(self, document):
        """
        从处理后的文档中提取表格
        
        Args:
            document: Document AI 处理后的文档对象
            
        Returns:
            tables: 提取的表格数据
        """
        if not document or not hasattr(document, 'pages'):
            return []
            
        tables = []
        for page in document.pages:
            for table in page.tables:
                table_data = []
                # 获取行数和列数
                rows = {}
                for cell in table.body_cells:
                    row_index = cell.row_index
                    col_index = cell.column_index
                    
                    if row_index not in rows:
                        rows[row_index] = {}
                    
                    # 提取单元格文本
                    text = ""
                    for segment in cell.layout.text_anchor.text_segments:
                        start_index = segment.start_index
                        end_index = segment.end_index
                        text += document.text[start_index:end_index]
                    
                    rows[row_index][col_index] = text
                
                # 将行数据转换为表格
                for row_index in sorted(rows.keys()):
                    row_data = []
                    for col_index in sorted(rows[row_index].keys()):
                        row_data.append(rows[row_index][col_index])
                    table_data.append(row_data)
                
                tables.append(table_data)
                
        return tables
    
    def extract_document_form_fields(self, document):
        """
        从处理后的文档中提取表单字段
        
        Args:
            document: Document AI 处理后的文档对象
            
        Returns:
            form_fields: 提取的表单字段
        """
        if not document or not hasattr(document, 'pages'):
            return {}
            
        form_fields = {}
        for page in document.pages:
            for field in page.form_fields:
                # 提取字段名称
                name_text = ""
                for segment in field.field_name.text_anchor.text_segments:
                    start_index = segment.start_index
                    end_index = segment.end_index
                    name_text += document.text[start_index:end_index]
                
                # 提取字段值
                value_text = ""
                for segment in field.field_value.text_anchor.text_segments:
                    start_index = segment.start_index
                    end_index = segment.end_index
                    value_text += document.text[start_index:end_index]
                
                form_fields[name_text.strip()] = value_text.strip()
                
        return form_fields
