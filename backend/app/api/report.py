"""
报告API路由
提供分析报告查询和人工标记相关的REST API端点
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, List

from app.database import get_db
from app.auth import verify_token
from app.models import AnalysisTask, AnalysisReport, ManualMark, ItemType
from app.schemas.request import MarkRequest
from app.schemas.response import (
    Response,
    ReportResponse,
    CoverageInfo,
    RequirementItem,
    IssueItem,
    MarkResponse
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


def calculate_manual_coverage(db: Session, report: AnalysisReport) -> float:
    """
    计算人工标记覆盖率

    基于人工标记状态计算覆盖率:
    - covered: 已覆盖的需求
    - irrelevant: 不相关的需求（不计入分母）
    - 公式: covered / (total - irrelevant) * 100

    Args:
        db: 数据库会话
        report: 分析报告对象

    Returns:
        float: 人工标记覆盖率百分比
    """
    # 获取该报告的所有人工标记
    manual_marks = db.query(ManualMark).filter(
        ManualMark.report_id == report.id
    ).all()

    # 统计标记状态
    covered_count = 0
    irrelevant_count = 0

    for mark in manual_marks:
        if mark.item_type == ItemType.requirement:
            if mark.marked_status == "covered":
                covered_count += 1
            elif mark.marked_status == "irrelevant":
                irrelevant_count += 1

    # 计算总数
    total = report.total_requirements or 0
    if total == 0:
        return 0.0

    # 减去不相关的数量
    effective_total = total - irrelevant_count
    if effective_total == 0:
        return 100.0  # 如果所有需求都被标记为不相关，则覆盖率为100%

    # 计算覆盖率
    coverage = (covered_count / effective_total) * 100
    return round(coverage, 2)


def get_marked_status(db: Session, report_id: int, item_type: ItemType, item_id: str) -> str:
    """
    获取指定条目的人工标记状态

    Args:
        db: 数据库会话
        report_id: 报告ID
        item_type: 条目类型
        item_id: 条目ID

    Returns:
        str: 标记状态，如果没有标记则返回None
    """
    mark = db.query(ManualMark).filter(
        ManualMark.report_id == report_id,
        ManualMark.item_type == item_type,
        ManualMark.item_id == item_id
    ).first()

    return mark.marked_status if mark else None


@router.get("/report/{task_id}", response_model=Response)
async def get_report(
    task_id: int,
    token: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    获取分析报告

    查询指定任务ID的完整分析报告，包括:
    - 覆盖率信息
    - 需求覆盖详情（包含人工标记状态）
    - 问题列表（包含人工标记状态）
    - 摘要

    Args:
        task_id: 任务ID
        token: 认证token
        db: 数据库会话

    Returns:
        Response: 包含完整报告的响应

    Raises:
        HTTPException: 任务或报告不存在时返回404
    """
    try:
        # 查询任务
        task = db.query(AnalysisTask).filter(AnalysisTask.id == task_id).first()
        if not task:
            logger.warning(f"Task not found: id={task_id}")
            raise HTTPException(status_code=404, detail="Task not found")

        # 查询报告
        report = db.query(AnalysisReport).filter(AnalysisReport.task_id == task_id).first()
        if not report:
            logger.warning(f"Report not found for task_id={task_id}")
            raise HTTPException(status_code=404, detail="Report not found")

        # 构建文件统计
        file_stats: Dict[str, int] = {
            "backend": report.backend_file_count or 0,
            "frontend": report.frontend_file_count or 0
        }

        # 构建需求列表（包含人工标记状态）
        requirements: List[RequirementItem] = []
        requirement_details = report.requirement_details or []
        for req in requirement_details:
            req_id = req.get("id", "")
            marked_status = get_marked_status(db, report.id, ItemType.requirement, req_id)

            requirements.append(RequirementItem(
                id=req_id,
                content=req.get("content", ""),
                status=req.get("status", ""),
                confidence=req.get("confidence", 0.0),
                related_files=req.get("related_files", []),
                related_lines=req.get("related_lines", []),
                marked_status=marked_status
            ))

        # 构建问题列表（包含人工标记状态）
        issues: List[IssueItem] = []

        # 合并所有类型的问题
        all_issues = []
        if report.extra_code_issues:
            all_issues.extend(report.extra_code_issues)
        if report.syntax_errors:
            all_issues.extend(report.syntax_errors)
        if report.boundary_issues:
            all_issues.extend(report.boundary_issues)
        if report.exception_issues:
            all_issues.extend(report.exception_issues)
        if report.quality_issues:
            all_issues.extend(report.quality_issues)

        for issue in all_issues:
            issue_id = issue.get("id", "")
            marked_status = get_marked_status(db, report.id, ItemType.issue, issue_id)

            issues.append(IssueItem(
                id=issue_id,
                type=issue.get("type", ""),
                severity=issue.get("severity", ""),
                description=issue.get("description", ""),
                file=issue.get("file"),
                lines=issue.get("lines"),
                suggestion=issue.get("suggestion"),
                marked_status=marked_status
            ))

        # 构建覆盖率信息
        coverage = CoverageInfo(
            total=float(report.requirement_coverage or 0),
            manual_coverage=float(report.manual_coverage) if report.manual_coverage else None,
            total_requirements=report.total_requirements or 0,
            covered_requirements=report.covered_requirements or 0,
            irrelevant_requirements=report.irrelevant_requirements or 0
        )

        # 构建响应
        report_response = ReportResponse(
            task_id=task.id,
            release_no=task.release_no,
            jira_key=task.jira_key,
            status=task.status.value,
            coverage=coverage,
            file_stats=file_stats,
            requirements=requirements,
            issues=issues,
            summary=report.summary
        )

        logger.info(f"Report retrieved successfully for task_id={task_id}")
        return Response(code=0, message="success", data=report_response)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting report: {e}", exc_info=True)
        return Response(code=500, message=f"Failed to get report: {str(e)}")


@router.post("/report/{task_id}/mark", response_model=Response)
async def create_mark(
    task_id: int,
    request: MarkRequest,
    token: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    创建或更新人工标记

    为报告中的需求或问题创建人工标记，并重新计算人工覆盖率

    Args:
        task_id: 任务ID
        request: 标记请求（item_type, item_id, marked_status, remark）
        token: 认证token
        db: 数据库会话

    Returns:
        Response: 包含新覆盖率的响应

    Raises:
        HTTPException: 任务或报告不存在时返回404
    """
    try:
        # 查询任务
        task = db.query(AnalysisTask).filter(AnalysisTask.id == task_id).first()
        if not task:
            logger.warning(f"Task not found: id={task_id}")
            raise HTTPException(status_code=404, detail="Task not found")

        # 查询报告
        report = db.query(AnalysisReport).filter(AnalysisReport.task_id == task_id).first()
        if not report:
            logger.warning(f"Report not found for task_id={task_id}")
            raise HTTPException(status_code=404, detail="Report not found")

        # 验证item_type
        try:
            item_type = ItemType(request.item_type)
        except ValueError:
            return Response(
                code=400,
                message=f"Invalid item_type: {request.item_type}. Must be 'requirement' or 'issue'"
            )

        # 查找是否已存在标记
        existing_mark = db.query(ManualMark).filter(
            ManualMark.report_id == report.id,
            ManualMark.item_type == item_type,
            ManualMark.item_id == request.item_id
        ).first()

        if existing_mark:
            # 更新现有标记
            existing_mark.marked_status = request.marked_status
            existing_mark.remark = request.remark
            existing_mark.marked_by = token  # 使用token作为标记人标识
            logger.info(f"Updated mark for {request.item_type}/{request.item_id}")
        else:
            # 创建新标记
            new_mark = ManualMark(
                report_id=report.id,
                item_type=item_type,
                item_id=request.item_id,
                original_status="",  # 可从原始数据中获取，此处简化处理
                marked_status=request.marked_status,
                marked_by=token,
                remark=request.remark
            )
            db.add(new_mark)
            logger.info(f"Created mark for {request.item_type}/{request.item_id}")

        db.commit()

        # 重新计算人工覆盖率
        new_coverage = calculate_manual_coverage(db, report)

        # 更新报告中的manual_coverage字段
        report.manual_coverage = new_coverage
        db.commit()

        logger.info(f"Manual coverage recalculated: {new_coverage}%")

        return Response(
            code=0,
            message="Mark created successfully",
            data=MarkResponse(new_coverage=new_coverage)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating mark: {e}", exc_info=True)
        return Response(code=500, message=f"Failed to create mark: {str(e)}")
