import aiohttp
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from app.utils.logging_utils import logger

def check_is_pure_url(text):
    """
    檢查輸入的字串是否只包含URL

    參數:
        text (str): 輸入字串

    回傳:
        bool: 如果只包含URL則返回True，否則返回False
    """
    if not text or not text.strip():
        return False
        
    urls = extract_urls_from_text(text)
    if not urls:
        return False
        
    # 创建一个标记数组，标记哪些字符是URL的一部分
    is_url_char = [False] * len(text)
    for url in urls:
        start_pos = 0
        while True:
            pos = text.find(url, start_pos)
            if pos == -1:
                break
            # 标记这个URL的所有字符
            for i in range(pos, pos + len(url)):
                is_url_char[i] = True
            start_pos = pos + 1
    
    # 检查所有非URL字符是否都是空白字符
    for i, char in enumerate(text):
        if not is_url_char[i] and not char.isspace():
            return False
    
    return True

def extract_urls_from_text(text):
    """
    從輸入的字串中擷取所有網址連結

    參數:
        text (str): 輸入字串

    回傳:
        list: 包含所有找到的 URL 字串
    """
    # URL regex pattern (支援 http, https, www)
    url_pattern = re.compile(
        r'(https?://[^\s]+|www\.[^\s]+)',
        re.IGNORECASE
    )
    return url_pattern.findall(text)

def remove_urls_from_text(text):
    """
    從輸入的字串中移除所有網址連結
    
    參數:
        text (str): 輸入字串
        
    回傳:
        str: 移除所有URL後的字串
    """
    if not text:
        return text
        
    # 使用與extract_urls_from_text相同的URL正則表達式模式
    url_pattern = re.compile(
        r'(https?://[^\s]+|www\.[^\s]+)',
        re.IGNORECASE
    )
    
    # 將所有匹配的URL替換為空字串
    return url_pattern.sub('', text)

async def get_url_preview(url):
    """
    非同步獲取網址的縮圖URL和內文預覽
    
    參數:
        url (str): 要獲取預覽的網址
        
    返回:
        dict: 包含縮圖URL和內文預覽的字典
    """
    # 初始化結果
    result = {
        'title': '',
        'thumbnail_url': '',
        'description': '',
    }
    
    # 檢查是否為YouTube URL
    youtube_pattern = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:watch\?v=|embed\/)|youtu\.be\/)([a-zA-Z0-9_-]+)'
    youtube_match = re.match(youtube_pattern, url)
    
    if youtube_match:
        return await _get_youtube_preview(url, youtube_match, result)
    
    # 檢查是否為Twitter（X）URL
    twitter_pattern = r'(?:https?:\/\/)?(?:www\.)?(?:twitter\.com|x\.com)\/([a-zA-Z0-9_]+)\/status\/([0-9]+)'
    twitter_match = re.match(twitter_pattern, url)
    
    if twitter_match:
        return await _get_twitter_preview(url, twitter_match, result)
    
    # 處理一般網址
    return await _get_general_preview(url, result)

async def _get_youtube_preview(url, youtube_match, result):
    """處理YouTube鏈接的預覽信息"""
    video_id = youtube_match.group(1)
    result['thumbnail_url'] = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
    # 備用縮圖，如果maxresdefault不存在
    result['thumbnail_url_fallback'] = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
    
    # 獲取標題和描述
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # 獲取標題
                    title_tag = soup.find('title')
                    if title_tag:
                        result['title'] = title_tag.text.strip()
                        # 移除YouTube標題中的" - YouTube"後綴
                        if " - YouTube" in result['title']:
                            result['title'] = result['title'].replace(" - YouTube", "")
                    
                    # 獲取描述
                    meta_desc = soup.find('meta', attrs={'name': 'description'})
                    if meta_desc and meta_desc.get('content'):
                        result['description'] = meta_desc['content']
    except Exception as e:
        result['error'] = f"獲取YouTube信息時出錯: {str(e)}"
    
    return result

async def _get_twitter_preview(url, twitter_match, result):
    """處理Twitter（X）鏈接的預覽信息"""
    username = twitter_match.group(1)
    tweet_id = twitter_match.group(2)
    
    # 初始化結果
    result['twitter_username'] = username
    result['twitter_tweet_id'] = tweet_id
    
    # 由於Twitter的反爬蟲機制，我們提供基本信息而不嘗試爬取頁面
    result['title'] = f"@{username} 的推文"
    result['description'] = f"Twitter推文 ID: {tweet_id}"
    
    # 嘗試使用Twitter的oEmbed API（這個API相對開放）
    try:
        oembed_url = f"https://publish.twitter.com/oembed?url={url}"
        async with aiohttp.ClientSession() as session:
            async with session.get(oembed_url, timeout=10) as response:
                if response.status == 200:
                    oembed_data = await response.json()
                    if 'author_name' in oembed_data:
                        result['title'] = f"{oembed_data['author_name']} (@{username})"
                    if 'html' in oembed_data:
                        # 從HTML中提取純文本
                        soup = BeautifulSoup(oembed_data['html'], 'html.parser')
                        text = soup.get_text()
                        if text:
                            result['description'] = text[:200] + '...' if len(text) > 200 else text
    except Exception as e:
        # 如果oEmbed API也失敗，我們至少有基本信息
        result['error'] = f"獲取Twitter信息時出錯: {str(e)}"
    
    return result

async def _get_general_preview(url, result):
    """處理一般網址的預覽信息"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status != 200:
                    return {
                        'error': f"HTTP錯誤: {response.status}",
                        'thumbnail_url': '',
                        'title': '',
                        'description': '',
                        'url': url
                    }
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                _extract_thumbnail(url, result, soup)
                _extract_title(result, soup)
                _extract_description(result, soup)
                
                return result
    
    except Exception as e:
        return {
            'error': str(e),
            'thumbnail_url': '',
            'title': '',
            'description': '',
            'url': url
        }

def _extract_thumbnail(url, result, soup):
    """從網頁中提取縮圖URL"""
    # 嘗試獲取Open Graph圖片
    og_image = soup.find('meta', property='og:image') or soup.find('meta', attrs={'name': 'og:image'})
    if og_image and og_image.get('content'):
        result['thumbnail_url'] = urljoin(url, og_image['content'])
        return
    
    # 嘗試Twitter卡片圖片
    twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
    if twitter_image and twitter_image.get('content'):
        result['thumbnail_url'] = urljoin(url, twitter_image['content'])
        return
    
    # 嘗試獲取頁面上的第一張大圖
    images = soup.find_all('img')
    for img in images:
        # 嘗試找到有合理尺寸的圖片
        src = img.get('src')
        if src and (img.get('width') is None or int(img.get('width', 0)) > 100):
            if src.startswith('http') or src.startswith('/'):
                result['thumbnail_url'] = urljoin(url, src)
                break

def _extract_title(result, soup):
    """從網頁中提取標題"""
    og_title = soup.find('meta', property='og:title') or soup.find('meta', attrs={'name': 'og:title'})
    if og_title and og_title.get('content'):
        result['title'] = og_title['content']
        return
    
    title_tag = soup.find('title')
    if title_tag:
        result['title'] = title_tag.text.strip()

def _extract_description(result, soup):
    """從網頁中提取描述"""
    # 獲取描述（內文預覽）
    og_desc = soup.find('meta', property='og:description') or soup.find('meta', attrs={'name': 'og:description'})
    if og_desc and og_desc.get('content'):
        result['description'] = og_desc['content']
        return
    
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if meta_desc and meta_desc.get('content'):
        result['description'] = meta_desc['content']
        return
    
    # 如果沒有描述，嘗試獲取頁面上的第一段文字
    first_p = soup.find('p')
    if first_p:
        text = first_p.text.strip()
        result['description'] = text[:200] + '...' if len(text) > 200 else text