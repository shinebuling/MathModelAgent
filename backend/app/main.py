from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
import os
from app.routers import modeling_router, ws_router, common_router, files_router
from app.utils.log_util import logger
from app.config.setting import settings
from fastapi.staticfiles import StaticFiles
from app.utils.cli import get_ascii_banner, center_cli_str
from app.services.redis_manager import redis_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(get_ascii_banner())
    print(center_cli_str("GitHub:https://github.com/jihe520/MathModelAgent"))
    logger.info("Starting MathModelAgent")

    PROJECT_FOLDER = "./project"
    os.makedirs(PROJECT_FOLDER, exist_ok=True)

    # 测试Redis连接
    try:
        logger.info("Testing Redis connection...")
        redis_client = await redis_manager.get_client()
        await redis_client.ping()
        logger.info("✅ Redis connection successful!")
        
        # 测试发布/订阅功能
        await redis_client.set("startup_test", "connected")
        test_value = await redis_client.get("startup_test")
        if test_value == "connected":
            logger.info("✅ Redis read/write test successful!")
        else:
            logger.warning("⚠️ Redis read/write test failed!")
            
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {str(e)}")
        logger.error("Please check if Redis server is running and accessible")

    yield
    logger.info("Stopping MathModelAgent")
    # 关闭Redis连接
    try:
        await redis_manager.close()
        logger.info("Redis connection closed")
    except Exception as e:
        logger.error(f"Error closing Redis connection: {str(e)}")


app = FastAPI(
    title="MathModelAgent",
    description="Agents for MathModel",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(modeling_router.router)
app.include_router(ws_router.router)
app.include_router(common_router.router)
app.include_router(files_router.router)


# 跨域 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],  # 暴露所有响应头
)

app.mount(
    "/static",  # 这是访问时的前缀
    StaticFiles(directory="project/work_dir"),  # 这是本地文件夹路径
    name="static",
)
