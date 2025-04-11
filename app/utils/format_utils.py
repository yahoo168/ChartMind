from bson import ObjectId
import re
import os
import fitz

def convert_objectid_to_str(obj):
    """递归转换所有 ObjectId 为字符串"""
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, dict):
        return {k: convert_objectid_to_str(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_objectid_to_str(item) for item in obj]
    return obj

def clean_text(text: str) -> str:
    """
    清洗文本，去除特殊符號和多餘的空白
    
    Args:
        text: 原始文本
    
    Returns:
        str: 清洗後的文本
    """
    import re
    
    # 去除特殊符號，但保留中文、英文、數字、基本標點和常見格式符號
    cleaned_text = re.sub(r'[^\w\s\u4e00-\u9fff.,;:!?，。；：！？、（）()""\'\'\-\[\]／/]', '', text)
    
    # 处理目录中的点线
    cleaned_text = re.sub(r'\.{3,}', ' ... ', cleaned_text)
    
    # 去除多餘的空白行和空格
    cleaned_text = re.sub(r'\n\s*\n', '\n', cleaned_text)
    cleaned_text = re.sub(r' +', ' ', cleaned_text)
    
    return cleaned_text.strip()

def remove_scattered_numbers(text: str) -> str:
    """
    清除零碎的數字行和單字行
    
    Args:
        text: 原始文本
    
    Returns:
        str: 清除零碎數字和單字後的文本
    """
    # 分行處理
    lines = text.split('\n')
    
    # 過濾條件:
    # 1. 跳過只包含數字和符號的行
    # 2. 跳過只有一個單字的行
    # 3. 跳過表格式的數據行(含有多個數字和空格分隔)
    filtered_lines = []
    for line in lines:
        stripped_line = line.strip()
        
        # 跳過空行
        if not stripped_line:
            continue
            
        # 跳過純數字和符號的行
        if re.match(r'^[\d\s\.\-\+%]+$', stripped_line):
            continue
            
        # 跳過只有一個單字的行
        words = re.findall(r'\w+', stripped_line)
        if len(words) <= 3:
            continue
            
        # 跳過表格式的數據行
        numbers = re.findall(r'\d+', stripped_line)
        if len(numbers) > 2:  # 如果一行中數字太多，可能是表格數據
            continue
            
        filtered_lines.append(line)
    
    return '\n'.join(filtered_lines)

def extract_pdf_content(pdf_path: str, output_dir: str = None):
    """
    從PDF提取文字，每頁作為一個元素
    
    Args:
        pdf_path: PDF文件路徑
        output_dir: 輸出目錄路徑（可選，不再用於保存圖片）
    
    Returns:
        list: 文字頁面列表，每頁為一個元素
    """
    # 創建輸出目錄（如果提供）
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    doc = fitz.open(pdf_path)
    pages_text = []
    
    # 提取文字，每頁作為一個元素
    for page in doc:
        text = page.get_text("text")
        cleaned_text = clean_text(text)
        # 清除零碎數字和單字
        cleaned_text = remove_scattered_numbers(cleaned_text)
        pages_text.append(cleaned_text)
            
    doc.close()
    return pages_text

def count_words(text):
    """
    计算文本中的单词数，中文一个字算1，英文一个单词算1
    
    参数:
        text (str): 需要计算单词数的文本
    
    返回:
        int: 单词总数
    """
    if not text or not isinstance(text, str):
        return 0
    
    # 分割英文单词
    text_with_spaces = re.sub(r'[^\w\s]', ' ', text)
    
    # 分割英文单词
    english_words = [word for word in text_with_spaces.split() if re.match(r'^[a-zA-Z0-9]+$', word)]
    english_count = len(english_words)
    
    # 计算中文字符数
    chinese_count = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
    
    return english_count + chinese_count