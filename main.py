"""
飞书日记应用主入口
启动FastAPI应用，接收飞书机器人回调
"""

from fastapi import FastAPI
from src.utils.config import settings
from src.utils.logger import logger
from src.utils.database import db

# 创建FastAPI应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug
)


@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    logger.info(f"{settings.app_name} v{settings.app_version} 启动成功")
    logger.info(f"数据库路径: {db.db_path}")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    logger.info(f"{settings.app_name} 已关闭")


@app.get("/")
async def root():
    """根路径，返回应用信息"""
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "code": 0}


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"启动服务器: {settings.host}:{settings.port}")
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
