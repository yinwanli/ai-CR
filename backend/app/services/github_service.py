"""
GitHub API 服务：拉取分支提交列表、对比相邻版本 diff。
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import httpx

from ..config import settings
from .code_module_service import CodeModule

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


def _is_configured_token(token: str) -> bool:
    if not token or not token.strip():
        return False
    v = token.strip().lower()
    return not (v.startswith("your_") or v in ("changeme",))


class GitHubService:
    """封装 GitHub REST API（公开库可无 Token）。"""

    def __init__(
        self,
        *,
        repo: Optional[str] = None,
        default_branch: Optional[str] = None,
        master_branch: Optional[str] = None,
    ) -> None:
        self.repo = (repo or settings.GITHUB_REPO).strip()
        self.default_branch = (default_branch or settings.GITHUB_DEFAULT_BRANCH).strip() or "main"
        master = (master_branch or settings.GITHUB_MASTER_BRANCH or "").strip()
        self.master_branch = master or self.default_branch
        self.token = settings.GITHUB_TOKEN.strip()
        self.commits_limit = settings.GITHUB_COMMITS_LIMIT
        self.branches_limit = settings.GITHUB_BRANCHES_LIMIT
        self._owner: Optional[str] = None
        self._name: Optional[str] = None
        if "/" in self.repo:
            parts = self.repo.split("/", 1)
            self._owner, self._name = parts[0], parts[1]

    @classmethod
    def for_module(cls, module: CodeModule) -> "GitHubService":
        return cls(
            repo=module.repo,
            default_branch=module.default_branch,
            master_branch=module.baseline_branch,
        )

    @property
    def is_configured(self) -> bool:
        return bool(self._owner and self._name)

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if _is_configured_token(self.token):
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        timeout: float = 30,
    ) -> Any:
        if not self.is_configured:
            raise ValueError("GITHUB_REPO is not configured (expected owner/repo)")
        url = f"{GITHUB_API}{path}"
        with httpx.Client(timeout=timeout) as client:
            resp = client.request(method, url, headers=self._headers(), params=params)
            if resp.status_code >= 400:
                detail = resp.text[:500]
                logger.error("GitHub API %s %s -> %s %s", method, path, resp.status_code, detail)
                raise httpx.HTTPStatusError(
                    f"GitHub API error {resp.status_code}: {detail}",
                    request=resp.request,
                    response=resp,
                )
            return resp.json() if resp.content else {}

    def list_branches(self, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """列出仓库分支（名称）。"""
        per_page = min(limit or self.branches_limit, 100)
        path = f"/repos/{self._owner}/{self._name}/branches"
        raw = self._request("GET", path, params={"per_page": per_page})
        if not isinstance(raw, list):
            return []
        names = []
        for b in raw:
            name = b.get("name") if isinstance(b, dict) else None
            if name:
                names.append({"name": name})
        names.sort(key=lambda x: x["name"])
        return names

    def list_commits(
        self,
        branch: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        列出分支上的提交（新 → 旧）。每条含上一版 base_sha（分支时间线上紧邻的更旧提交）。
        """
        branch = (branch or self.default_branch).strip()
        per_page = min(limit or self.commits_limit, 100)
        path = f"/repos/{self._owner}/{self._name}/commits"
        raw = self._request("GET", path, params={"sha": branch, "per_page": per_page})

        if not isinstance(raw, list):
            return []

        items: List[Dict[str, Any]] = []
        for i, c in enumerate(raw):
            sha = c.get("sha") or ""
            commit = c.get("commit") or {}
            message = (commit.get("message") or "").split("\n")[0]
            author = commit.get("author") or {}
            date = author.get("date") or ""
            short_sha = sha[:7] if sha else ""
            base_sha: Optional[str] = None
            if i + 1 < len(raw):
                base_sha = raw[i + 1].get("sha")
            items.append(
                {
                    "sha": sha,
                    "short_sha": short_sha,
                    "message": message,
                    "date": date,
                    "base_sha": base_sha,
                    "branch": branch,
                }
            )
        return items

    def resolve_head_sha(self, ref: str) -> str:
        """将短 SHA 或完整 SHA 解析为完整 commit SHA。"""
        ref = ref.strip()
        if len(ref) >= 40:
            return ref
        path = f"/repos/{self._owner}/{self._name}/commits/{ref}"
        data = self._request("GET", path)
        sha = data.get("sha")
        if not sha:
            raise ValueError(f"Cannot resolve commit ref: {ref}")
        return sha

    def find_base_sha_on_branch(self, head_sha: str, branch: Optional[str] = None) -> Optional[str]:
        """在分支提交列表中查找 head 的上一版（分支时间线）。"""
        commits = self.list_commits(branch=branch)
        for item in commits:
            if item["sha"] == head_sha or item["sha"].startswith(head_sha) or item["short_sha"] == head_sha[:7]:
                return item.get("base_sha")
        return None

    def get_compare_diff(self, base_sha: str, head_sha: str) -> str:
        """
        获取 base..head 的 unified diff 文本（供 diff_parser 使用）。
        """
        path = f"/repos/{self._owner}/{self._name}/compare/{base_sha}...{head_sha}"
        data = self._request("GET", path)
        return self._compare_json_to_diff(data)

    @staticmethod
    def _compare_json_to_diff(data: Dict[str, Any]) -> str:
        parts: List[str] = []
        for f in data.get("files") or []:
            filename = f.get("filename") or "unknown"
            patch = f.get("patch")
            if not patch:
                status = f.get("status", "changed")
                parts.append(f"diff --git a/{filename} b/{filename}\n# no patch ({status}, possibly too large)\n")
                continue
            if not patch.startswith("diff --git"):
                parts.append(f"diff --git a/{filename} b/{filename}\n{patch}")
            else:
                parts.append(patch)
        return "\n".join(parts)

    def get_release_diff(
        self,
        head_sha: str,
        base_sha: Optional[str] = None,
        branch: Optional[str] = None,
    ) -> Tuple[str, str, str]:
        """
        本版本相对分支上一提交的 diff。

        Returns:
            (diff_text, resolved_head_sha, resolved_base_sha)
        """
        head = self.resolve_head_sha(head_sha) if len(head_sha) < 40 else head_sha
        base = base_sha
        if not base:
            base = self.find_base_sha_on_branch(head, branch=branch)
        if not base:
            raise ValueError(
                "No previous commit on this branch (first commit). Cannot compare to previous version."
            )
        diff_text = self.get_compare_diff(base, head)
        if not diff_text.strip():
            logger.warning("Compare returned empty diff for %s...%s", base[:7], head[:7])
        return diff_text, head, base

    def resolve_branch_tip(self, branch: Optional[str] = None) -> str:
        """解析分支当前 tip 的完整 commit SHA（用于 master 基线）。"""
        ref = (branch or self.master_branch).strip()
        return self.resolve_head_sha(ref)

    def get_vs_master_diff(
        self,
        head_sha: str,
        *,
        branch: Optional[str] = None,
        master_branch: Optional[str] = None,
    ) -> Tuple[str, str, str]:
        """
        功能分支（或指定 head）相对 master/main 基线分支 tip 的 diff。

        Returns:
            (diff_text, resolved_head_sha, resolved_base_sha)
        """
        head = self.resolve_head_sha(head_sha) if len(head_sha) < 40 else head_sha
        base = self.resolve_branch_tip(master_branch or self.master_branch)
        diff_text = self.get_compare_diff(base, head)
        if not diff_text.strip():
            logger.warning(
                "Compare vs master returned empty diff for %s...%s (branch=%s)",
                base[:7],
                head[:7],
                branch or self.default_branch,
            )
        return diff_text, head, base


github_service = GitHubService()
