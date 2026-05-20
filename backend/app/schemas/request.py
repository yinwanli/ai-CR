from pydantic import BaseModel, Field
from typing import Optional


class AnalyzeRequest(BaseModel):
    """提交分析请求"""
    release_no: str = Field(..., description="发布版本标识（如短 SHA）", min_length=1, max_length=100)
    head_sha: Optional[str] = Field(None, description="本版本 commit SHA（完整或短 SHA）")
    base_sha: Optional[str] = Field(None, description="上一版本 commit SHA，用于 compare diff")


class MarkRequest(BaseModel):
    """人工标记请求"""
    item_type: str = Field(..., description="标记项类型: requirement/issue")
    item_id: str = Field(..., description="需求条目ID或问题ID")
    marked_status: str = Field(..., description="标记状态")
    remark: Optional[str] = Field(None, description="备注说明")


class WebhookRequest(BaseModel):
    """OP平台Webhook请求"""
    release_no: str = Field(..., description="上线单号")
    diff: str = Field(..., description="代码diff内容")
    diff_type: str = Field(default="git", description="diff类型: git/svn")
    callback_url: Optional[str] = Field(None, description="回调URL")
