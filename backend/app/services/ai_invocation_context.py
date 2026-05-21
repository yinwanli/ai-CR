"""
AI 调用上下文
在业务任务与 AIAnalyzer 之间传递 task_id、trace、业务冗余字段等。
"""
from dataclasses import dataclass, field
from typing import Optional
import uuid


PURPOSE_PROMPT_META = {
    "analyze": ("analyze", "analyze_v1"),
    "select_context_files": ("context_selection", "context_selection_v1"),
}


@dataclass
class InvocationContext:
    """
    单次分析 run 内的 AI 调用上下文。

    Attributes:
        task_id: 分析任务 ID
        trace_id: 同一次后台 run 内多条 AI 调用共用
        release_no: 上线单或存储键
        module_id: 代码模块
        jira_key: Jira 单号
        compare_mode: prev_commit / vs_master
        caller_source: analyze_api / webhook
        parent_invocation_id: 多步链路的父调用 ID
    """

    task_id: Optional[int] = None
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    release_no: Optional[str] = None
    module_id: Optional[str] = None
    jira_key: Optional[str] = None
    compare_mode: Optional[str] = None
    caller_source: Optional[str] = None
    parent_invocation_id: Optional[int] = None
    last_invocation_id: Optional[int] = field(default=None, repr=False)

    def prompt_meta_for(self, purpose: str) -> tuple[str, str]:
        """
        根据 purpose 返回 (prompt_template, prompt_version)。

        Args:
            purpose: analyze / select_context_files

        Returns:
            模板名与版本号元组
        """
        return PURPOSE_PROMPT_META.get(purpose, (purpose, "v1"))
