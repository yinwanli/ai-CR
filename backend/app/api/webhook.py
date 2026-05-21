"""
Webhook API路由
提供OP平台webhook接收端点
"""
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.auth import verify_op_token
from app.models import AnalysisTask, TaskStatus
from app.schemas.request import WebhookRequest
from app.schemas.response import Response, AnalyzeResponse
from app.utils.jira_parser import extract_jira_key
from app.config import settings
from app.services.jira_service import jira_service
from app.services.diff_parser import diff_parser
from app.services.ai_analyzer import ai_analyzer
from app.services.ai_invocation_context import InvocationContext
from app.models.report import AnalysisReport
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/op", response_model=Response)
async def receive_op_webhook(
    request: WebhookRequest,
    background_tasks: BackgroundTasks,
    token: str = Depends(verify_op_token),
    db: Session = Depends(get_db)
):
    """
    接收OP平台的diff推送

    接收来自OP平台的webhook请求，创建分析任务并启动后台分析

    Args:
        request: 包含 release_no, diff, diff_type, callback_url 的请求体
        background_tasks: FastAPI后台任务
        token: OP平台认证token
        db: 数据库会话

    Returns:
        Response: 包含 task_id, report_url, status 的响应
    """
    try:
        logger.info(
            f"Received webhook from OP platform: release_no={request.release_no}, "
            f"diff_type={request.diff_type}, callback_url={request.callback_url}"
        )

        # 检查是否已存在相同的任务
        existing_task = db.query(AnalysisTask).filter(
            AnalysisTask.release_no == request.release_no
        ).first()

        if existing_task:
            logger.warning(f"Task already exists for release_no: {request.release_no}")
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
            release_no=request.release_no,
            jira_key=jira_key,
            status=TaskStatus.PENDING
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        logger.info(f"Created analysis task from webhook: id={task.id}, release_no={request.release_no}")

        # 启动后台任务
        background_tasks.add_task(
            run_analysis,
            task_id=task.id,
            release_no=request.release_no,
            jira_key=jira_key,
            diff_content=request.diff,
            diff_type=request.diff_type,
            callback_url=request.callback_url
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
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        return Response(code=500, message=f"Failed to process webhook: {str(e)}")


def run_analysis(
    task_id: int,
    release_no: str,
    jira_key: str,
    diff_content: str,
    diff_type: str = "git",
    callback_url: str = None
):
    """
    执行分析的后台任务

    完整的分析流程:
    1. 更新任务状态为 ANALYZING
    2. 获取需求文档
    3. 解析代码diff
    4. 过滤文件（后端/前端）
    5. 调用AI分析
    6. 创建分析报告
    7. 更新任务状态为 SUCCESS 或 FAILED

    Args:
        task_id: 任务ID
        release_no: 上线单号
        jira_key: Jira单号
        diff_content: diff内容
        diff_type: diff类型 (git/svn)
        callback_url: 回调URL（可选）
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

        # 2. 获取需求文档
        requirement_doc = ""
        if jira_key:
            logger.info(f"Fetching requirement document for jira_key={jira_key}")
            requirement_doc = jira_service.get_requirement_doc(jira_key)
        else:
            logger.warning(f"No jira_key extracted from release_no: {release_no}")
            requirement_doc = "# 需求文档\n\n未找到关联的Jira需求文档。"

        # 3. 解析diff内容
        logger.info(f"Parsing diff content with type: {diff_type}")
        files = diff_parser.parse_diff(diff_content, diff_type=diff_type)
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
            release_no=release_no,
            jira_key=jira_key,
            caller_source="webhook",
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

        # 8. 如果有回调URL，通知OP平台（可选实现）
        if callback_url:
            logger.info(f"Analysis completed, callback URL available: {callback_url}")
            # 这里可以添加回调通知逻辑
            # 例如: requests.post(callback_url, json={"task_id": task_id, "status": "success"})

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
