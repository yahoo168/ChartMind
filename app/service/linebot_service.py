import os
import tempfile

from linebot import LineBotApi
from linebot.models import TextSendMessage

from app.service.user_service import UserManagementService, UserAuthService
from app.service.application_service import UserContentUploadService
from app.utils.logging_utils import logger

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))

# 處理圖片訊息
async def handle_image_message(message_id, line_id, reply_token, line_group_id):
    image_path = None
    try:
        # 檢查用戶狀態
        user_status = await check_and_register_user(line_id)
        user_id = user_status["user_data"]["_id"]
        
        content_type = line_bot_api.get_message_content(message_id).content_type
        if "jpeg" in content_type or "jpg" in content_type:
            file_ext = ".jpg"
        elif "png" in content_type:
            file_ext = ".png"
        else:
            raise ValueError(f"不支持的圖片類型: {content_type}")
        
        # 使用臨時文件保存圖片
        try:
            image_path = await download_line_content(message_id, file_ext)
                
            user_content_upload_service = UserContentUploadService()
            await user_content_upload_service.upload_image(image_path, user_id, "linebot", line_group_id)
            # 構建基本回覆
            reply_text = f"✅ 已收到圖表！"
        except Exception as e:
            logger.warning(f"圖片上傳失敗: {e}")
            reply_text = "❌ 圖片上傳失敗，請稍後再試。"
        
        # 回覆用戶
        await reply_to_user(reply_token, reply_text)
    except Exception as e:
        logger.warning(f"處理圖片訊息時發生錯誤: {e}")
        await reply_to_user(reply_token, "❌ 伺服器發生錯誤，請稍後再試。")
    finally:
        # 確保在任何情況下都刪除臨時文件
        await cleanup_temp_file(image_path)

# 處理文字訊息
async def handle_text_message(text, line_id, reply_token, line_group_id):
    try:
        logger.info(f"收到文字訊息: {text}")
        # 檢查用戶狀態
        
        user_status = await check_and_register_user(line_id)
        user_id = user_status["user_data"]["_id"]
        
        if len(text) < 15:
            reply_text = "❌ 訊息過短，不進行處理。"
        else:
            user_content_upload_service = UserContentUploadService()
            await user_content_upload_service.upload_text(text=text, 
                                                          uploader_id=user_id, 
                                                          source="linebot", 
                                                          line_group_id=line_group_id)
            reply_text = "✅ 確認接收文字訊息！"
        # 回覆用戶
        await reply_to_user(reply_token, reply_text)
        
    except Exception as e:
        logger.warning(f"處理文字訊息時發生錯誤: {e}")
        await reply_to_user(reply_token, "❌ 處理訊息時發生錯誤，請稍後再試。")

# 處理文件訊息
async def handle_file_message(message_id, line_id, reply_token, file_name, line_group_id):
    """处理用户上传的文件消息
    
    Args:
        message_id: Line消息ID
        line_id: 用户Line ID
        reply_token: 回复令牌
        file_name: 文件名称
    """
    file_path = None
    try:
        user_status = await check_and_register_user(line_id)
        user_id = user_status["user_data"]["_id"]

        # 获取文件扩展名
        file_ext = os.path.splitext(file_name)[1].lower().lstrip('.')
        
        # 检查是否为PDF文件
        if file_ext not in ['pdf']:
            await reply_to_user(reply_token, f"❌ 暂不支持处理{file_ext}类型的文件。目前仅支持PDF文件。")
            return
        
        # 下载文件内容
        file_path = await download_line_content(message_id, file_ext)
            
        user_content_upload_service = UserContentUploadService()
        logger.info(f"linebot-service: {line_group_id}")
        await user_content_upload_service.upload_file(file_ext=file_ext, 
                                                      file_name=file_name, 
                                                      file_path=file_path, 
                                                      user_id=user_id, 
                                                      source="linebot", 
                                                      line_group_id=line_group_id)
        
        # 回复用户
        reply_text = f"✅ 確認接收{file_ext}文件！"
        await reply_to_user(reply_token, reply_text)
            
    except Exception as e:
        logger.warning(f"處理文件訊息時發生錯誤: {e}")
        # 发生错误时通知用户
        await reply_to_user(reply_token, f"❌ 處理文件時發生錯誤，請稍後再試。")
    finally:
        # 清理临时文件
        await cleanup_temp_file(file_path)

async def check_and_register_user(line_id):
    """檢查用戶是否存在，不存在則創建，並返回用戶狀態"""
    user_management_service = UserManagementService()
    
    # 先檢查用戶是否存在
    user_data = await user_management_service.get_user(by="line_id", value=line_id)
    
    # 如果用戶已存在，直接返回
    if user_data:
        return {"is_new_user": False, "user_data": user_data}
    
    # 用戶不存在，進行註冊
    logger.info(f"用戶 {line_id} 不存在，進行註冊。")
    user_auth_service = UserAuthService()
    user_data = await user_auth_service.register_user_from_line(line_id)
    
    return {"is_new_user": True, "user_data": user_data}

async def download_line_content(message_id, file_ext):
    """下載Line消息內容並返回臨時文件路徑
    
    Args:
        message_id: Line消息ID
        file_ext: 文件擴展名，如 '.jpg', '.pdf'
        
    Returns:
        str: 臨時文件路徑
    """
    with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as temp_file:
        file_path = temp_file.name
        
        # 下載內容
        message_content = line_bot_api.get_message_content(message_id)
        with open(file_path, 'wb') as fd:
            for chunk in message_content.iter_content():
                fd.write(chunk)
                
        return file_path

async def cleanup_temp_file(file_path):
    """清理臨時文件
    
    Args:
        file_path: 臨時文件路徑
    """
    if file_path and os.path.exists(file_path):
        try:
            os.unlink(file_path)
            logger.debug(f"已刪除臨時文件: {file_path}")
        except Exception as e:
            logger.warning(f"刪除臨時文件失敗: {e}")

async def reply_to_user(reply_token, message):
    """向用戶發送回覆訊息"""
    line_bot_api.reply_message(
        reply_token,
        TextSendMessage(text=message)
    )