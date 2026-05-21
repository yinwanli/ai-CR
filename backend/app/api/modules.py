"""
代码模块 API：供前端级联选择（模块 → 分支 → 对比 → 版本）。
"""
from fastapi import APIRouter, Depends

from app.auth import verify_token
from app.schemas.response import Response
from app.services.code_module_service import list_code_modules
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/code-modules", response_model=Response)
async def list_modules(token: str = Depends(verify_token)):
    """获取可分析的代码模块列表（Demo 默认一项，生产由配置扩展）。"""
    modules = [m.to_dict() for m in list_code_modules()]
    if not modules:
        return Response(code=500, message="No code modules configured", data=[])
    return Response(code=0, message="success", data=modules)
