import logging
import sys

# 创建一个应用专用的logger
app_logger = logging.getLogger("ChartMind")
app_logger.setLevel(logging.INFO)
# 防止日志传播到根记录器，避免重复
app_logger.propagate = False
# 添加处理器
app_logger.addHandler(logging.StreamHandler(sys.stdout))

# 配置日志格式
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
for handler in app_logger.handlers:
    handler.setFormatter(formatter)

# 导出app_logger作为主要日志记录器供应用使用
logger = app_logger

# 同时配置uvicorn的日志格式，使其与应用日志格式一致
uvicorn_logger = logging.getLogger("uvicorn.error")
uvicorn_logger.setLevel(logging.INFO)
# 为uvicorn日志记录器也设置相同的格式化器
for handler in uvicorn_logger.handlers:
    handler.setFormatter(formatter)

# 以下代码可以删除，除非你确实需要修改uvicorn的日志格式
# # 使用uvicorn的日志管道
# logger = logging.getLogger("uvicorn.error")
# # 确保此logger也能显示INFO级别及以上的日志
# logger.setLevel(logging.INFO)
# # 为uvicorn日志记录器也设置相同的格式化器
# for handler in logger.handlers:
#     handler.setFormatter(formatter)