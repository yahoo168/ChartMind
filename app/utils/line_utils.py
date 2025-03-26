import os

def download_image_message(line_bot_api, message_id: str, save_dir: str = "temp") -> str:
    # 使用臨時文件夾
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
        
    # 下載圖片到臨時文件夾
    image_content = line_bot_api.get_message_content(message_id).content
    image_path = os.path.join(save_dir, f"{message_id}.jpg")
    with open(image_path, "wb") as f:
        f.write(image_content)
            
    return image_path
