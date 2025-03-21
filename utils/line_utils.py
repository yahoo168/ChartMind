import os

def download_image(line_bot_api, message_id: str, save_dir: str = "images") -> str:
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    image_content = line_bot_api.get_message_content(message_id).content
    image_path = os.path.join(save_dir, f"{message_id}.jpg")
    with open(image_path, "wb") as f:
        f.write(image_content)
    return image_path
