"""
分析报告模型
定义代码审查报告和人工标记的数据结构
"""
from sqlalchemy import Column, BigInteger, Integer, String, Text, DateTime, JSON, ForeignKey, Enum, DECIMAL
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base
import enum


class ItemType(str, enum.Enum):
    """标记类型枚举"""
    requirement = "requirement"  # 需求覆盖
    issue = "issue"              # 问题标记


class AnalysisReport(Base):
    """
    分析报告表

    存储每次代码审查分析生成的详细报告
    """
    __tablename__ = "analysis_report"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(BigInteger, ForeignKey("analysis_task.id"), nullable=False)

    # Coverage stats - use DECIMAL for percentages
    requirement_coverage = Column(DECIMAL(5, 2))
    manual_coverage = Column(DECIMAL(5, 2))
    total_requirements = Column(Integer, default=0)
    covered_requirements = Column(Integer, default=0)
    irrelevant_requirements = Column(Integer, default=0)

    # Analysis results as JSON
    requirement_details = Column(JSON)
    extra_code_issues = Column(JSON)
    syntax_errors = Column(JSON)
    boundary_issues = Column(JSON)
    exception_issues = Column(JSON)
    quality_issues = Column(JSON)

    # Summary
    total_issues = Column(Integer, default=0)
    summary = Column(Text)

    # File stats
    backend_file_count = Column(Integer, default=0)
    frontend_file_count = Column(Integer, default=0)

    created_at = Column(DateTime, server_default=func.now())

    # Relationship to AnalysisTask
    task = relationship("AnalysisTask", back_populates="report")


class ManualMark(Base):
    """
    人工标记表

    记录用户对分析结果的人工标记和审核
    """
    __tablename__ = "manual_mark"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    report_id = Column(BigInteger, ForeignKey("analysis_report.id"), nullable=False)

    item_type = Column(Enum(ItemType))  # ItemType: requirement, issue
    item_id = Column(String(100))

    original_status = Column(String(50))
    marked_status = Column(String(50))  # NOT an enum, just String
    marked_by = Column(String(100))
    marked_at = Column(DateTime, server_default=func.now())

    remark = Column(Text)
