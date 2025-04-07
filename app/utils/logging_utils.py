import logging
import sys

# 创建一个应用专用的logger
app_logger = logging.getLogger("chartmind")
app_logger.setLevel(logging.INFO)
# 防止日志传播到根记录器，避免重复
app_logger.propagate = False
# 添加处理器
app_logger.addHandler(logging.StreamHandler(sys.stdout))

# 使用uvicorn的日志管道
logger = logging.getLogger("uvicorn.error")
# 确保此logger也能显示INFO级别及以上的日志
logger.setLevel(logging.INFO)

# 配置日志格式
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
for handler in app_logger.handlers:
    handler.setFormatter(formatter)

# 注释掉根日志配置，避免重复日志
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.StreamHandler(sys.stdout)
#     ]
# )