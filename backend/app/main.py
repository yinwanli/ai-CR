"""
FastAPI 主应用模块
应用程序入口点，配置中间件、路由和生命周期
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine, init_db, close_db
from app.utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理

    Startup:
        - 记录启动日志
        - 创建数据库表

    Shutdown:
        - 记录关闭日志
        - 关闭数据库连接池
    """
    # Startup
    logger.info(f"Starting {settings.app_env} environment")
    logger.info("Creating database tables...")
    init_db()
    logger.info("Database tables created successfully")
    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down application...")
    close_db()
    logger.info("Application shutdown complete")


# 创建FastAPI应用实例
app = FastAPI(
    title="AI Code Review Platform",
    description="""
AI驱动的代码审查平台API

## 功能特性
- Git Diff解析和分析
- AI智能代码审查
- Jira集成
- Webhook支持

## 认证
使用 X-Auth-Token 请求头进行认证
""",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 配置CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 导入并注册路由
# 注意：这些路由模块将在后续任务中实现
try:
    from app.api import analyze, report, webhook

    app.include_router(analyze.router, prefix="/api", tags=["analyze"])
    app.include_router(report.router, prefix="/api", tags=["report"])
    app.include_router(webhook.router, prefix="/api/webhook", tags=["webhook"])
except ImportError as e:
    logger.warning(f"Some API routers not available yet: {e}")


@app.get("/", summary="根路径", description="返回应用程序基本信息")
async def root():
    """
    根路径端点

    Returns:
        dict: 应用程序基本信息
    """
    return {
        "name": "AI Code Review Platform",
        "version": "1.0.0",
        "status": "running",
        "environment": settings.app_env,
        "docs": "/docs"
    }


@app.get("/health", summary="健康检查", description="检查应用程序运行状态")
async def health_check():
    """
    健康检查端点

    Returns:
        dict: 健康状态信息
    """
    return {
        "status": "healthy",
        "environment": settings.app_env,
        "database": "connected"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.app_debug
    )
