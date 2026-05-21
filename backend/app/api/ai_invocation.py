"""
AI 调用记录 API
按 task_id 列表查询、按 id 查看详情（含全量 prompt/response）。
"""
from fastapi import APIRouter, Depends

from app.auth import verify_token
from app.services.ai_invocation_service import AiInvocationService
from app.schemas.response import Response, AiInvocationListItem, AiInvocationDetailResponse
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/task/{task_id}/ai-invocations", response_model=Response)
async def list_ai_invocations_by_task(
    task_id: int,
    token: str = Depends(verify_token),
):
    """
    查询某分析任务下的 AI 调用记录列表（不含 LONGTEXT 正文）。

    Args:
        task_id: 分析任务 ID
        token: 认证 token

    Returns:
        Response: data 为 AiInvocationListItem 列表
    """
    try:
        rows = AiInvocationService.list_by_task_id(task_id)
        items = [AiInvocationListItem(**row) for row in rows]
        return Response(code=0, message="success", data=items)
    except Exception as exc:
        logger.error("list_ai_invocations_by_task failed: %s", exc, exc_info=True)
        return Response(code=500, message=str(exc))


@router.get("/ai-invocations/{invocation_id}", response_model=Response)
async def get_ai_invocation_detail(
    invocation_id: int,
    token: str = Depends(verify_token),
):
    """
    查询单条 AI 调用详情（含 prompt_text、response_text 全量）。

    Args:
        invocation_id: 调用记录 ID
        token: 认证 token

    Returns:
        Response: data 为 AiInvocationDetailResponse
    """
    try:
        detail = AiInvocationService.get_by_id(invocation_id)
        if not detail:
            return Response(code=404, message=f"AI invocation not found: {invocation_id}")
        return Response(
            code=0,
            message="success",
            data=AiInvocationDetailResponse(**detail),
        )
    except Exception as exc:
        logger.error("get_ai_invocation_detail failed: %s", exc, exc_info=True)
        return Response(code=500, message=str(exc))
