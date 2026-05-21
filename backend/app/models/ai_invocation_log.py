"""
AI 调用记录模型
记录每次 LLM / Agent 调用的 prompt、响应与元数据，便于反查与审计。
"""
from sqlalchemy import Column, BigInteger, String, Text, DateTime, Integer, SmallInteger, ForeignKey
from sqlalchemy.sql import func

from ..database import Base


class AiInvocationLog(Base):
    """
    AI 调用明细表

    与 analysis_task 为 1:N；每次 _call_llm 对应一行（mock 且无 context 时不写入）。
    """

    __tablename__ = "ai_invocation_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    task_id = Column(
        BigInteger,
        ForeignKey("analysis_task.id"),
        nullable=True,
        index=True,
        comment="关联分析任务 ID",
    )
    trace_id = Column(String(64), nullable=True, index=True, comment="同一次 run_analysis 内共用")
    purpose = Column(String(64), nullable=False, comment="analyze / select_context_files")
    backend = Column(String(32), nullable=False, comment="cursor_agent / claude_api / mock")
    model = Column(String(128), nullable=True, comment="模型 ID")
    agent_id = Column(String(128), nullable=True, comment="Cursor agent id")
    run_id = Column(String(128), nullable=True, comment="Cursor run id")
    external_request_id = Column(String(128), nullable=True, comment="Claude 等 request id")
    prompt_template = Column(String(64), nullable=True, comment="模板名")
    prompt_version = Column(String(32), nullable=True, comment="模板版本")
    prompt_text = Column(Text, nullable=False, comment="完整 prompt")
    prompt_chars = Column(Integer, nullable=False, default=0, comment="prompt 字符数")
    response_text = Column(Text, nullable=True, comment="完整原始响应")
    response_chars = Column(Integer, nullable=True, comment="响应字符数")
    response_status = Column(
        String(32),
        nullable=False,
        default="running",
        comment="running/success/empty/timeout/api_error/parse_error",
    )
    error_message = Column(Text, nullable=True, comment="失败摘要")
    http_status = Column(SmallInteger, nullable=True, comment="HTTP 状态码")
    run_status = Column(String(32), nullable=True, comment="Cursor 终态")
    failure_stage = Column(String(32), nullable=True, comment="create_agent/poll/stream/claude_request")
    started_at = Column(DateTime, nullable=False, comment="开始时间")
    finished_at = Column(DateTime, nullable=True, comment="结束时间")
    duration_ms = Column(Integer, nullable=True, comment="耗时毫秒")
    input_tokens = Column(Integer, nullable=True, comment="输入 token")
    output_tokens = Column(Integer, nullable=True, comment="输出 token")
    release_no = Column(String(200), nullable=True, comment="上线单/存储键冗余")
    module_id = Column(String(64), nullable=True, comment="代码模块")
    jira_key = Column(String(50), nullable=True, comment="Jira 单号")
    compare_mode = Column(String(32), nullable=True, comment="prev_commit / vs_master")
    caller_source = Column(String(32), nullable=True, comment="analyze_api / webhook")
    parent_invocation_id = Column(BigInteger, nullable=True, comment="多步调用链父 ID")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")

    def to_list_dict(self) -> dict:
        """列表项（不含 LONGTEXT 正文）。"""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "trace_id": self.trace_id,
            "purpose": self.purpose,
            "backend": self.backend,
            "model": self.model,
            "agent_id": self.agent_id,
            "run_id": self.run_id,
            "response_status": self.response_status,
            "duration_ms": self.duration_ms,
            "prompt_chars": self.prompt_chars,
            "response_chars": self.response_chars,
            "compare_mode": self.compare_mode,
            "caller_source": self.caller_source,
            "run_status": self.run_status,
            "failure_stage": self.failure_stage,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def to_detail_dict(self) -> dict:
        """详情（含全量 prompt / response）。"""
        detail = self.to_list_dict()
        detail.update(
            {
                "prompt_template": self.prompt_template,
                "prompt_version": self.prompt_version,
                "prompt_text": self.prompt_text,
                "response_text": self.response_text,
                "error_message": self.error_message,
                "http_status": self.http_status,
                "external_request_id": self.external_request_id,
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "release_no": self.release_no,
                "module_id": self.module_id,
                "jira_key": self.jira_key,
                "parent_invocation_id": self.parent_invocation_id,
            }
        )
        return detail
