from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.interfaces.api_v1 import api_router
from app.infrastructure.db.mongodb import MongodbClient

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时连接数据库
    await MongodbClient.connect_client()
    yield
    # 关闭时断开数据库连接
    await MongodbClient.close_client()

app = FastAPI(title="ChartMind", lifespan=lifespan)
app.include_router(api_router, prefix="/api")

# CORS 配置: 供前端呼叫
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # 只允许前端开发服务器的来源
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有头部
)

# 挂载静态文件目录
# app.mount("/", StaticFiles(directory="frontend", html=True), name="static")