"""
数据库配置模块
使用 SQLAlchemy 进行数据库连接和会话管理
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.config import settings


# 创建数据库引擎
# echo=True 在开发环境下打印 SQL 语句
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # 启用连接池预检测
    pool_recycle=3600,   # 连接回收时间（秒）
    echo=settings.app_debug
)

# 创建会话工厂
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# 创建模型基类
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话的依赖函数

    用于 FastAPI 的 Depends 注入，确保每个请求有独立的数据库会话

    Yields:
        Session: SQLAlchemy 数据库会话对象

    Example:
        @app.get("/items/")
        def read_items(db: Session = Depends(get_db)):
            items = db.query(Item).all()
            return items
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    初始化数据库

    创建所有表结构，需要在所有模型导入后调用
    """
    import app.models  # noqa: F401 — 注册全部 ORM 表（含 ai_invocation_log）

    Base.metadata.create_all(bind=engine)


def close_db() -> None:
    """
    关闭数据库连接池

    应用关闭时调用，清理资源
    """
    engine.dispose()
