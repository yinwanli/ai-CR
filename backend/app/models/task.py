"""
分析任务模型
定义代码审查分析任务的数据结构
"""
from sqlalchemy import Column, BigInteger, String, Enum, Text, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base
import enum


class TaskStatus(str, enum.Enum):
    """任务状态枚举"""
    PENDING = "pending"      # 待处理
    ANALYZING = "analyzing"  # 分析中
    SUCCESS = "success"      # 成功
    FAILED = "failed"        # 失败


class AnalysisTask(Base):
    """
    分析任务表

    记录每次代码审查分析任务的基本信息和状态
    """
    __tablename__ = "analysis_task"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    release_no = Column(String(100), unique=True, nullable=False, comment="上线单号")
    jira_key = Column(String(50), comment="Jira单号")
    status = Column(
        Enum(TaskStatus),
        default=TaskStatus.PENDING,
        comment="任务状态: pending-待处理, analyzing-分析中, success-成功, failed-失败"
    )
    error_message = Column(Text, comment="错误信息，任务失败时记录详细错误")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间"
    )

    # 关联分析报告（一对一）
    report = relationship("AnalysisReport", back_populates="task", uselist=False)

    def __repr__(self):
        return f"<AnalysisTask(id={self.id}, release_no='{self.release_no}', status='{self.status}')>"

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "release_no": self.release_no,
            "jira_key": self.jira_key,
            "status": self.status.value if self.status else None,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
