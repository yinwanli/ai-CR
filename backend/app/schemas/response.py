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


class AiInvocationListItem(BaseModel):
    """AI 调用记录列表项（不含 prompt/response 全文）"""
    id: int
    task_id: Optional[int] = None
    trace_id: Optional[str] = None
    purpose: str
    backend: str
    model: Optional[str] = None
    agent_id: Optional[str] = None
    run_id: Optional[str] = None
    response_status: str
    duration_ms: Optional[int] = None
    prompt_chars: int
    response_chars: Optional[int] = None
    compare_mode: Optional[str] = None
    caller_source: Optional[str] = None
    run_status: Optional[str] = None
    failure_stage: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    created_at: Optional[str] = None


class AiInvocationDetailResponse(BaseModel):
    """AI 调用记录详情（含全量 prompt/response）"""
    id: int
    task_id: Optional[int] = None
    trace_id: Optional[str] = None
    purpose: str
    backend: str
    model: Optional[str] = None
    agent_id: Optional[str] = None
    run_id: Optional[str] = None
    response_status: str
    duration_ms: Optional[int] = None
    prompt_chars: int
    response_chars: Optional[int] = None
    compare_mode: Optional[str] = None
    caller_source: Optional[str] = None
    run_status: Optional[str] = None
    failure_stage: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    created_at: Optional[str] = None
    prompt_template: Optional[str] = None
    prompt_version: Optional[str] = None
    prompt_text: str
    response_text: Optional[str] = None
    error_message: Optional[str] = None
    http_status: Optional[int] = None
    external_request_id: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    release_no: Optional[str] = None
    module_id: Optional[str] = None
    jira_key: Optional[str] = None
    parent_invocation_id: Optional[int] = None
