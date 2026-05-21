"""
AI 调用记录服务
负责 ai_invocation_log 的创建、完成与状态更新。
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.ai_invocation_log import AiInvocationLog
from app.services.ai_invocation_context import InvocationContext
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class LlmInvokeOutcome:
    """单次后端 LLM 调用的结果与元数据。"""

    text: Optional[str] = None
    agent_id: Optional[str] = None
    run_id: Optional[str] = None
    run_status: Optional[str] = None
    failure_stage: Optional[str] = None
    http_status: Optional[int] = None
    error_message: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    external_request_id: Optional[str] = None


class AiInvocationService:
    """AI 调用日志持久化。"""

    @staticmethod
    def start_invocation(
        context: InvocationContext,
        purpose: str,
        backend: str,
        model: Optional[str],
        prompt_text: str,
    ) -> int:
        """
        插入 running 状态记录并返回 id。

        Args:
            context: 调用上下文
            purpose: analyze / select_context_files
            backend: cursor_agent / claude_api
            model: 模型名
            prompt_text: 完整 prompt

        Returns:
            新记录主键 id
        """
        prompt_template, prompt_version = context.prompt_meta_for(purpose)
        started_at = datetime.utcnow()
        db: Session = SessionLocal()
        try:
            row = AiInvocationLog(
                task_id=context.task_id,
                trace_id=context.trace_id,
                purpose=purpose,
                backend=backend,
                model=model,
                prompt_template=prompt_template,
                prompt_version=prompt_version,
                prompt_text=prompt_text,
                prompt_chars=len(prompt_text),
                response_status="running",
                started_at=started_at,
                release_no=context.release_no,
                module_id=context.module_id,
                jira_key=context.jira_key,
                compare_mode=context.compare_mode,
                caller_source=context.caller_source,
                parent_invocation_id=context.parent_invocation_id,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            context.last_invocation_id = row.id
            logger.info(
                "AI invocation started: id=%s task_id=%s purpose=%s backend=%s",
                row.id,
                context.task_id,
                purpose,
                backend,
            )
            return row.id
        except Exception as exc:
            db.rollback()
            logger.error("Failed to start AI invocation log: %s", exc, exc_info=True)
            raise
        finally:
            db.close()

    @staticmethod
    def finish_invocation(
        invocation_id: int,
        outcome: LlmInvokeOutcome,
        started_at: datetime,
    ) -> None:
        """
        根据 LlmInvokeOutcome 更新终态。

        Args:
            invocation_id: 记录 id
            outcome: 后端调用结果
            started_at: 开始时间（用于 duration_ms）
        """
        finished_at = datetime.utcnow()
        duration_ms = int((finished_at - started_at).total_seconds() * 1000)
        response_text = outcome.text or ""
        if outcome.failure_stage == "timeout":
            status = "timeout"
        elif outcome.text and outcome.text.strip():
            status = "success"
        elif outcome.failure_stage or outcome.error_message or outcome.http_status:
            status = "api_error"
        else:
            status = "empty"

        db: Session = SessionLocal()
        try:
            row = db.query(AiInvocationLog).filter(AiInvocationLog.id == invocation_id).first()
            if not row:
                logger.warning("AI invocation log not found for finish: id=%s", invocation_id)
                return
            row.finished_at = finished_at
            row.duration_ms = duration_ms
            row.response_text = response_text or None
            row.response_chars = len(response_text) if response_text else None
            row.response_status = status
            row.error_message = outcome.error_message
            row.http_status = outcome.http_status
            row.agent_id = outcome.agent_id
            row.run_id = outcome.run_id
            row.run_status = outcome.run_status
            row.failure_stage = outcome.failure_stage
            row.input_tokens = outcome.input_tokens
            row.output_tokens = outcome.output_tokens
            row.external_request_id = outcome.external_request_id
            db.commit()
            logger.info(
                "AI invocation finished: id=%s status=%s duration_ms=%s",
                invocation_id,
                status,
                duration_ms,
            )
        except Exception as exc:
            db.rollback()
            logger.error("Failed to finish AI invocation log: %s", exc, exc_info=True)
        finally:
            db.close()

    @staticmethod
    def mark_parse_error(invocation_id: Optional[int], error_message: str) -> None:
        """
        将最近一次调用标记为 JSON 解析失败。

        Args:
            invocation_id: 记录 id，为 None 时跳过
            error_message: 错误说明
        """
        if not invocation_id:
            return
        db: Session = SessionLocal()
        try:
            row = db.query(AiInvocationLog).filter(AiInvocationLog.id == invocation_id).first()
            if not row:
                return
            row.response_status = "parse_error"
            row.error_message = (row.error_message or "") + ("; " if row.error_message else "") + error_message
            if not row.finished_at:
                row.finished_at = datetime.utcnow()
            db.commit()
        except Exception as exc:
            db.rollback()
            logger.error("Failed to mark parse_error: %s", exc, exc_info=True)
        finally:
            db.close()

    @staticmethod
    def list_by_task_id(task_id: int) -> list[dict]:
        """按 task_id 查询列表（不含大字段）。"""
        db: Session = SessionLocal()
        try:
            rows = (
                db.query(AiInvocationLog)
                .filter(AiInvocationLog.task_id == task_id)
                .order_by(AiInvocationLog.id.asc())
                .all()
            )
            return [row.to_list_dict() for row in rows]
        finally:
            db.close()

    @staticmethod
    def get_by_id(invocation_id: int) -> Optional[dict]:
        """按 id 查询详情。"""
        db: Session = SessionLocal()
        try:
            row = db.query(AiInvocationLog).filter(AiInvocationLog.id == invocation_id).first()
            if not row:
                return None
            return row.to_detail_dict()
        finally:
            db.close()


ai_invocation_service = AiInvocationService()
