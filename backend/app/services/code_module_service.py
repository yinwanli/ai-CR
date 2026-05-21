"""
代码模块配置：Demo 从 .env 派生单模块，生产可扩展为 JSON / 数据库配置。
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import List, Optional

from ..config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CodeModule:
    """一个代码模块 = 一个 Git 仓库 + 默认/基线分支。"""

    id: str
    name: str
    repo: str  # owner/name
    default_branch: str
    baseline_branch: str  # vs_master 对比基线（通常 main/master）

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "repo": self.repo,
            "default_branch": self.default_branch,
            "baseline_branch": self.baseline_branch,
        }


def _default_demo_module() -> CodeModule:
    repo = settings.GITHUB_REPO.strip()
    default_branch = settings.GITHUB_DEFAULT_BRANCH.strip() or "main"
    baseline = (settings.GITHUB_MASTER_BRANCH or "").strip() or default_branch
    module_id = repo.replace("/", "-").lower() if repo else "default"
    name = repo.split("/")[-1] if "/" in repo else (repo or "默认模块")
    return CodeModule(
        id=module_id,
        name=name,
        repo=repo,
        default_branch=default_branch,
        baseline_branch=baseline,
    )


def _parse_modules_json(raw: str) -> List[CodeModule]:
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("CODE_MODULES_JSON must be a JSON array")
    modules: List[CodeModule] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        mid = str(item.get("id") or "").strip()
        repo = str(item.get("repo") or "").strip()
        if not mid or not repo:
            continue
        default_branch = str(item.get("default_branch") or "main").strip()
        baseline = str(item.get("baseline_branch") or default_branch).strip()
        modules.append(
            CodeModule(
                id=mid,
                name=str(item.get("name") or mid).strip(),
                repo=repo,
                default_branch=default_branch,
                baseline_branch=baseline,
            )
        )
    return modules


def list_code_modules() -> List[CodeModule]:
    """返回可用代码模块列表（Demo 至少一项）。"""
    raw = (getattr(settings, "CODE_MODULES_JSON", None) or "").strip()
    if raw:
        try:
            modules = _parse_modules_json(raw)
            if modules:
                return modules
        except Exception as e:
            logger.warning("Invalid CODE_MODULES_JSON, fallback to demo module: %s", e)
    demo = _default_demo_module()
    if demo.repo:
        return [demo]
    return []


def get_code_module(module_id: str) -> Optional[CodeModule]:
    mid = (module_id or "").strip()
    if not mid:
        return None
    for m in list_code_modules():
        if m.id == mid:
            return m
    return None


def get_default_module() -> Optional[CodeModule]:
    modules = list_code_modules()
    return modules[0] if modules else None
