"""
分析API路由
提供代码分析相关的REST API端点
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db, SessionLocal
from app.auth import verify_token
from app.models import AnalysisTask, TaskStatus, AnalysisReport
from app.schemas.request import AnalyzeRequest
from app.schemas.response import (
    Response,
    AnalyzeResponse,
    TaskResponse,
    HistoryItem
)
from app.services.jira_service import jira_service
from app.services.diff_parser import diff_parser
from app.services.ai_analyzer import ai_analyzer
from app.services.ai_invocation_context import InvocationContext
from app.services.mock_data import MockDataService
from app.services.github_service import GitHubService
from app.services.code_module_service import get_code_module
from app.utils.jira_parser import extract_jira_key
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

COMPARE_MODE_PREV = "prev_commit"
COMPARE_MODE_VS_MASTER = "vs_master"


def _storage_release_no(module_id: str, release_no: str, compare_mode: str) -> str:
    """模块 + 版本 + 对比模式 组成任务唯一键。"""
    key = f"{module_id}:{release_no}"
    if compare_mode == COMPARE_MODE_VS_MASTER:
        return f"{key}@vs-master"
    return key


@router.post("/analyze", response_model=Response)
async def submit_analysis(
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    token: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    提交分析任务

    接收上线单号，创建分析任务并在后台执行分析

    Args:
        request: 包含 release_no 的请求体
        background_tasks: FastAPI后台任务
        token: 认证token
        db: 数据库会话

    Returns:
        Response: 包含 task_id, report_url, status 的响应
    """
    try:
        module = get_code_module(request.module_id)
        if not module:
            return Response(code=400, message=f"Unknown code module: {request.module_id}")

        storage_release_no = _storage_release_no(
            request.module_id, request.release_no, request.compare_mode
        )

        # 检查是否已存在相同的任务（模块 + 版本 + 对比模式）
        existing_task = db.query(AnalysisTask).filter(
            AnalysisTask.release_no == storage_release_no
        ).first()

        if existing_task:
            logger.warning(f"Task already exists for release_no: {storage_release_no}")
            return Response(
                code=1,
                message="Task already exists",
                data=AnalyzeResponse(
                    task_id=existing_task.id,
                    report_url=f"/report/{existing_task.id}",
                    status=existing_task.status.value
                )
            )

        # 从上线单号提取Jira单号
        jira_key = extract_jira_key(request.release_no)
        logger.info(f"Extracted jira_key: {jira_key} from release_no: {request.release_no}")

        # 创建分析任务
        task = AnalysisTask(
            release_no=storage_release_no,
            jira_key=jira_key,
            status=TaskStatus.PENDING
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        logger.info(
            "Created analysis task: id=%s release_no=%s compare_mode=%s",
            task.id,
            storage_release_no,
            request.compare_mode,
        )

        # 启动后台任务（diff 在后台按 compare_mode 从 GitHub compare 拉取）
        background_tasks.add_task(
            run_analysis,
            task_id=task.id,
            release_no=request.release_no,
            jira_key=jira_key,
            module_id=request.module_id,
            head_sha=request.head_sha,
            base_sha=request.base_sha,
            compare_mode=request.compare_mode,
            branch=request.branch,
        )

        return Response(
            code=0,
            message="Analysis task submitted successfully",
            data=AnalyzeResponse(
                task_id=task.id,
                report_url=f"/report/{task.id}",
                status=task.status.value
            )
        )

    except Exception as e:
        logger.error(f"Error submitting analysis task: {e}", exc_info=True)
        return Response(code=500, message=f"Failed to submit task: {str(e)}")


@router.get("/task/{task_id}", response_model=Response)
async def get_task_status(
    task_id: int,
    token: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    获取任务状态

    查询指定任务ID的分析状态和信息

    Args:
        task_id: 任务ID
        token: 认证token
        db: 数据库会话

    Returns:
        Response: 包含任务信息的响应
    """
    try:
        task = db.query(AnalysisTask).filter(AnalysisTask.id == task_id).first()

        if not task:
            logger.warning(f"Task not found: id={task_id}")
            raise HTTPException(status_code=404, detail="Task not found")

        # 构建进度信息
        progress = None
        if task.status == TaskStatus.ANALYZING:
            progress = "Analyzing code changes..."
        elif task.status == TaskStatus.SUCCESS:
            progress = "Analysis completed"
        elif task.status == TaskStatus.FAILED:
            progress = f"Analysis failed: {task.error_message or 'Unknown error'}"

        return Response(
            code=0,
            message="success",
            data=TaskResponse(
                task_id=task.id,
                release_no=task.release_no,
                jira_key=task.jira_key,
                status=task.status.value,
                progress=progress,
                created_at=task.created_at.isoformat() if task.created_at else ""
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task status: {e}", exc_info=True)
        return Response(code=500, message=f"Failed to get task: {str(e)}")


@router.get("/history", response_model=Response)
async def get_history(
    limit: int = 20,
    token: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    获取历史记录

    查询最近的分析任务历史记录，包含覆盖率信息

    Args:
        limit: 返回记录数量限制
        token: 认证token
        db: 数据库会话

    Returns:
        Response: 包含历史记录列表的响应
    """
    try:
        # 限制最大查询数量
        limit = min(limit, settings.max_page_size)

        # 查询最近的任务
        tasks = db.query(AnalysisTask).order_by(
            AnalysisTask.created_at.desc()
        ).limit(limit).all()

        # 构建历史记录列表
        history_items = []
        for task in tasks:
            # 获取关联的报告信息
            report = db.query(AnalysisReport).filter(
                AnalysisReport.task_id == task.id
            ).first()

            coverage = None
            if report and report.requirement_coverage:
                coverage = float(report.requirement_coverage)

            history_items.append(
                HistoryItem(
                    task_id=task.id,
                    release_no=task.release_no,
                    status=task.status.value,
                    coverage=coverage,
                    created_at=task.created_at.isoformat() if task.created_at else ""
                )
            )

        return Response(
            code=0,
            message="success",
            data=history_items
        )

    except Exception as e:
        logger.error(f"Error getting history: {e}", exc_info=True)
        return Response(code=500, message=f"Failed to get history: {str(e)}")


def _load_diff_content(
    module_id: str,
    release_no: str,
    head_sha: Optional[str] = None,
    base_sha: Optional[str] = None,
    compare_mode: str = COMPARE_MODE_PREV,
    branch: Optional[str] = None,
) -> str:
    """
    按模块 + 对比模式拉取 GitHub compare diff。
    - prev_commit: 本提交 vs 分支相邻上一提交
    - vs_master: 本提交 vs 模块基线分支 tip
    """
    ref = (head_sha or release_no or "").strip()
    if not ref:
        logger.warning("No head_sha/release_no for GitHub, using mock diff")
        return MockDataService.get_mock_diff("git")

    module = get_code_module(module_id)
    if not module:
        raise ValueError(f"Unknown code module: {module_id}")

    gh = GitHubService.for_module(module)
    if not gh.is_configured:
        logger.warning("Module repo not configured, using mock diff")
        return MockDataService.get_mock_diff("git")

    if compare_mode == COMPARE_MODE_VS_MASTER:
        diff_text, head, base = gh.get_vs_master_diff(
            ref, branch=branch, master_branch=module.baseline_branch
        )
        logger.info(
            "Loaded compare vs baseline %s...%s (%d bytes, module=%s baseline=%s)",
            base[:7],
            head[:7],
            len(diff_text),
            module_id,
            module.baseline_branch,
        )
    else:
        diff_text, head, base = gh.get_release_diff(
            ref, base_sha=base_sha, branch=branch or module.default_branch
        )
        logger.info(
            "Loaded compare prev_commit %s...%s (%d bytes, module=%s)",
            base[:7],
            head[:7],
            len(diff_text),
            module_id,
        )
    return diff_text


def run_analysis(
    task_id: int,
    release_no: str,
    jira_key: str,
    module_id: str,
    head_sha: Optional[str] = None,
    base_sha: Optional[str] = None,
    compare_mode: str = COMPARE_MODE_PREV,
    branch: Optional[str] = None,
):
    """
    执行分析的后台任务

    完整的分析流程:
    1. 更新任务状态为 ANALYZING
    2. 从 GitHub 拉取 diff（相邻提交 或 相对 master）
    3. 获取需求文档
    4. 解析代码diff
    5. 过滤文件（后端/前端）
    6. 调用AI分析
    7. 创建分析报告
    8. 更新任务状态为 SUCCESS 或 FAILED

    Args:
        task_id: 任务ID
        release_no: 发布版本标识
        jira_key: Jira单号
        module_id: 代码模块 ID
        head_sha: 本版本 commit
        base_sha: 上一版本 commit（prev_commit 模式，可选）
        compare_mode: prev_commit | vs_master
        branch: 功能分支名
    """
    # 创建新的数据库会话（后台任务需要独立的会话）
    db = SessionLocal()

    try:
        logger.info(f"Starting analysis for task_id={task_id}, release_no={release_no}")

        # 1. 更新任务状态为 ANALYZING
        task = db.query(AnalysisTask).filter(AnalysisTask.id == task_id).first()
        if not task:
            logger.error(f"Task not found: id={task_id}")
            return

        task.status = TaskStatus.ANALYZING
        db.commit()
        logger.info(f"Task {task_id} status updated to ANALYZING")

        # 2. GitHub compare diff
        try:
            diff_content = _load_diff_content(
                module_id,
                release_no,
                head_sha=head_sha,
                base_sha=base_sha,
                compare_mode=compare_mode,
                branch=branch,
            )
        except ValueError as e:
            logger.error("GitHub diff error: %s", e)
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            db.commit()
            return
        except Exception as e:
            logger.error("Failed to load GitHub diff: %s", e, exc_info=True)
            task.status = TaskStatus.FAILED
            task.error_message = f"Failed to load GitHub diff: {e}"
            db.commit()
            return

        # 3. 获取需求文档
        requirement_doc = ""
        if jira_key:
            logger.info(f"Fetching requirement document for jira_key={jira_key}")
            requirement_doc = jira_service.get_requirement_doc(jira_key)
        else:
            logger.warning(f"No jira_key extracted from release_no: {release_no}")
            requirement_doc = "# 需求文档\n\n未找到关联的Jira需求文档。"

        # 4. 解析diff内容
        logger.info("Parsing diff content...")
        files = diff_parser.parse_diff(diff_content, diff_type="git")
        if not files:
            logger.warning("No files found in diff content")

        # 4. 过滤文件（区分后端和前端）
        logger.info("Filtering files...")
        filtered_files = diff_parser.filter_files(files)
        backend_files = filtered_files.get('backend_files', [])
        frontend_files = filtered_files.get('frontend_files', [])

        logger.info(f"Found {len(backend_files)} backend files and {len(frontend_files)} frontend files")

        # 5. 调用AI分析
        logger.info("Calling AI analyzer...")
        invocation_context = InvocationContext(
            task_id=task_id,
            release_no=task.release_no if task else release_no,
            module_id=module_id,
            jira_key=jira_key,
            compare_mode=compare_mode,
            caller_source="analyze_api",
        )
        analysis_result = ai_analyzer.analyze(
            requirement_doc,
            diff_content,
            invocation_context=invocation_context,
        )

        if not analysis_result:
            logger.error("AI analysis returned empty result")
            raise Exception("AI analysis failed to produce results")

        logger.info(f"AI analysis completed with coverage: {analysis_result.get('coverage_percent', 'N/A')}%")

        # 6. 创建分析报告
        logger.info("Creating analysis report...")

        # 提取分析结果
        requirements = analysis_result.get('requirements', [])
        issues = analysis_result.get('issues', [])
        coverage_percent = analysis_result.get('coverage_percent', 0.0)
        summary = analysis_result.get('summary', '')

        # 统计需求数据
        total_requirements = len(requirements)
        covered_requirements = sum(1 for r in requirements if r.get('status') == 'covered')
        irrelevant_requirements = sum(1 for r in requirements if r.get('status') == 'irrelevant')

        # 分类问题
        extra_code_issues = [i for i in issues if i.get('type') == 'extra_code']
        syntax_errors = [i for i in issues if i.get('type') == 'syntax_error']
        boundary_issues = [i for i in issues if i.get('type') == 'boundary_issue']
        exception_issues = [i for i in issues if i.get('type') == 'exception_handling']
        quality_issues = [i for i in issues if i.get('type') not in [
            'extra_code', 'syntax_error', 'boundary_issue', 'exception_handling'
        ]]

        # 创建报告记录
        report = AnalysisReport(
            task_id=task_id,
            requirement_coverage=coverage_percent,
            total_requirements=total_requirements,
            covered_requirements=covered_requirements,
            irrelevant_requirements=irrelevant_requirements,
            requirement_details=requirements,
            extra_code_issues=extra_code_issues,
            syntax_errors=syntax_errors,
            boundary_issues=boundary_issues,
            exception_issues=exception_issues,
            quality_issues=quality_issues,
            total_issues=len(issues),
            summary=summary,
            backend_file_count=len(backend_files),
            frontend_file_count=len(frontend_files)
        )

        db.add(report)

        # 7. 更新任务状态为 SUCCESS
        task.status = TaskStatus.SUCCESS
        db.commit()

        logger.info(f"Analysis completed successfully for task_id={task_id}")

    except Exception as e:
        logger.error(f"Analysis failed for task_id={task_id}: {e}", exc_info=True)

        # 更新任务状态为 FAILED
        try:
            task = db.query(AnalysisTask).filter(AnalysisTask.id == task_id).first()
            if task:
                task.status = TaskStatus.FAILED
                task.error_message = str(e)
                db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update task status: {db_error}", exc_info=True)

    finally:
        # 关闭数据库会话
        db.close()
        logger.info(f"Database session closed for task_id={task_id}")
