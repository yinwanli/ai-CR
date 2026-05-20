"""
GitHub 相关 API：分支提交列表（含上一版本 SHA）。
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.auth import verify_token
from app.schemas.response import Response
from app.services.github_service import github_service
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/github/commits", response_model=Response)
async def list_branch_commits(
    branch: Optional[str] = Query(None, description="分支名，默认 GITHUB_DEFAULT_BRANCH"),
    repo: Optional[str] = Query(None, description="owner/repo，Demo 后由 Jira 传入；默认配置项"),
    token: str = Depends(verify_token),
):
    """
    获取指定分支的提交列表，用于首页发布版本下拉。
    每条记录包含 base_sha（分支上上一版），便于「本版 vs 上一版」对比分析。
    """
    try:
        if not github_service.is_configured:
            return Response(code=500, message="GITHUB_REPO is not configured", data=[])

        # repo 参数预留供 Jira 多仓库；Demo 使用 .env 中的 GITHUB_REPO
        if repo and repo.strip() and repo.strip() != settings.GITHUB_REPO:
            logger.info("github/commits: repo param %s ignored in demo, using %s", repo, settings.GITHUB_REPO)

        commits = github_service.list_commits(branch=branch)

        return Response(
            code=0,
            message="success",
            data={
                "repo": settings.GITHUB_REPO,
                "branch": branch or settings.GITHUB_DEFAULT_BRANCH,
                "commits": commits,
            },
        )
    except Exception as e:
        logger.error("Failed to list GitHub commits: %s", e, exc_info=True)
        return Response(code=500, message=str(e), data={"commits": []})
