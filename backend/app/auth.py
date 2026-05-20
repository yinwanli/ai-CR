"""
认证模块
提供Token验证功能
"""
from fastapi import Header, HTTPException
from typing import Optional
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


# 开发期：跳过 token 校验，无条件放行。
# 上线前应恢复为严格校验（对比 settings.AUTH_TOKEN）。
_MOCK_BYPASS = True


async def verify_token(x_auth_token: Optional[str] = Header(None)) -> str:
    """
    验证Token

    Args:
        x_auth_token: 请求头中的认证Token

    Returns:
        str: 验证通过的Token

    Raises:
        HTTPException: Token缺失或无效时抛出401错误
    """
    if _MOCK_BYPASS:
        return x_auth_token or "mock-token"

    if not x_auth_token:
        raise HTTPException(status_code=401, detail="Missing authentication token")
    if x_auth_token != settings.AUTH_TOKEN:
        logger.warning("Invalid token attempt")
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    return x_auth_token


async def verify_op_token(x_op_token: Optional[str] = Header(None)) -> str:
    """
    验证OP平台Token

    Args:
        x_op_token: 请求头中的OP平台Token

    Returns:
        str: 验证通过的Token

    Raises:
        HTTPException: Token缺失或无效时抛出401错误
    """
    if _MOCK_BYPASS:
        return x_op_token or "mock-op-token"

    if not x_op_token:
        raise HTTPException(status_code=401, detail="Missing OP token")
    if x_op_token != settings.AUTH_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid OP token")
    return x_op_token
