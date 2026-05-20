from pydantic import BaseModel
from typing import Optional, List, Any, Dict


class Response(BaseModel):
    """通用响应"""
    code: int = 0
    message: str = "success"
    data: Optional[Any] = None


class AnalyzeResponse(BaseModel):
    """分析响应"""
    task_id: int
    report_url: str
    status: str


class TaskResponse(BaseModel):
    """任务响应"""
    task_id: int
    release_no: str
    jira_key: Optional[str]
    status: str
    progress: Optional[str] = None
    created_at: str


class CoverageInfo(BaseModel):
    """覆盖率信息"""
    total: float
    manual_coverage: Optional[float] = None
    total_requirements: int
    covered_requirements: int
    irrelevant_requirements: int


class RequirementItem(BaseModel):
    """需求条目"""
    id: str
    content: str
    status: str
    confidence: float
    related_files: List[str] = []
    related_lines: List[List[int]] = []
    marked_status: Optional[str] = None


class IssueItem(BaseModel):
    """问题条目"""
    id: str
    type: str
    severity: str
    description: str
    file: Optional[str] = None
    lines: Optional[List[int]] = None
    suggestion: Optional[str] = None
    marked_status: Optional[str] = None


class ReportResponse(BaseModel):
    """报告响应"""
    task_id: int
    release_no: str
    jira_key: Optional[str]
    status: str
    coverage: CoverageInfo
    file_stats: Dict[str, int]
    requirements: List[RequirementItem]
    issues: List[IssueItem]
    summary: Optional[str] = None


class MarkResponse(BaseModel):
    """标记响应"""
    new_coverage: float


class HistoryItem(BaseModel):
    """历史记录条目"""
    task_id: int
    release_no: str
    status: str
    coverage: Optional[float] = None
    created_at: str
