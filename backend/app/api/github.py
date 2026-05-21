"""
GitHub 相关 API：按代码模块级联提供分支、提交列表。
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import verify_token
from app.schemas.response import Response
from app.services.code_module_service import get_code_module, get_default_module
from app.services.github_service import GitHubService
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


def _resolve_module(module_id: Optional[str]):
    module = get_code_module(module_id) if module_id else get_default_module()
    if not module:
        raise HTTPException(status_code=400, detail="Unknown or missing code module")
    gh = GitHubService.for_module(module)
    if not gh.is_configured:
        raise HTTPException(status_code=500, detail="Invalid module repo configuration")
    return module, gh


@router.get("/github/branches", response_model=Response)
async def list_repo_branches(
    module_id: Optional[str] = Query(None, description="代码模块 ID"),
    token: str = Depends(verify_token),
):
    """获取指定模块仓库的分支列表。"""
    try:
        module, gh = _resolve_module(module_id)
        branches = gh.list_branches()
        return Response(
            code=0,
            message="success",
            data={
                "module_id": module.id,
                "module_name": module.name,
                "repo": module.repo,
                "default_branch": module.default_branch,
                "baseline_branch": module.baseline_branch,
                "branches": branches,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to list branches: %s", e, exc_info=True)
        return Response(code=500, message=str(e), data={"branches": []})


@router.get("/github/commits", response_model=Response)
async def list_branch_commits(
    module_id: Optional[str] = Query(None, description="代码模块 ID"),
    branch: Optional[str] = Query(None, description="分支名，默认模块的 default_branch"),
    token: str = Depends(verify_token),
):
    """
    获取指定模块、分支上的提交列表。
    每条含 base_sha（分支时间线上一提交），用于相邻提交对比。
    """
    try:
        module, gh = _resolve_module(module_id)
        active_branch = (branch or module.default_branch).strip()
        commits = gh.list_commits(branch=active_branch)
        return Response(
            code=0,
            message="success",
            data={
                "module_id": module.id,
                "module_name": module.name,
                "repo": module.repo,
                "branch": active_branch,
                "baseline_branch": module.baseline_branch,
                "commits": commits,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to list GitHub commits: %s", e, exc_info=True)
        return Response(code=500, message=str(e), data={"commits": []})
