"""
系统配置模型
定义系统配置项的数据结构
"""
from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.sql import func
from ..database import Base


class SystemConfig(Base):
    """
    系统配置表

    存储系统运行所需的配置信息，采用键值对形式
    """
    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, autoincrement=True)  # Integer, not BigInteger
    config_key = Column(String(100), unique=True, nullable=False)
    config_value = Column(JSON, nullable=False)  # JSON type
    description = Column(String(500))
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
