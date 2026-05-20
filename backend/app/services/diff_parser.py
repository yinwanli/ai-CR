"""
Diff解析服务模块
用于解析Git/SVN diff内容并过滤文件
"""
import re
import fnmatch
from typing import List, Dict, Optional
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DiffParser:
    """Diff解析器类，用于解析Git/SVN diff并过滤文件"""

    # Git diff文件头正则表达式
    GIT_DIFF_PATTERN = re.compile(r'^diff --git a/(.+?) b/(.+)$', re.MULTILINE)

    # SVN diff文件头正则表达式
    SVN_DIFF_PATTERN = re.compile(r'^Index: (.+)$', re.MULTILINE)

    # Git diff hunk头正则表达式
    GIT_HUNK_PATTERN = re.compile(r'^@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@', re.MULTILINE)

    def parse_diff(self, diff_content: str, diff_type: str = "git") -> List[Dict]:
        """
        解析diff内容，返回文件变更列表

        Args:
            diff_content: diff内容字符串
            diff_type: diff类型，支持 "git" 或 "svn"

        Returns:
            List[Dict]: 文件变更列表，每个元素包含:
                - path: 文件路径
                - additions: 新增行数
                - deletions: 删除行数
                - diff: diff内容
        """
        if not diff_content or not diff_content.strip():
            logger.warning("Empty diff content provided")
            return []

        try:
            if diff_type.lower() == "git":
                return self._parse_git_diff(diff_content)
            elif diff_type.lower() == "svn":
                return self._parse_svn_diff(diff_content)
            else:
                logger.error(f"Unsupported diff type: {diff_type}")
                return []
        except Exception as e:
            logger.error(f"Error parsing diff content: {e}")
            return []

    def _parse_git_diff(self, diff_content: str) -> List[Dict]:
        """
        解析Git diff格式

        Args:
            diff_content: Git diff内容

        Returns:
            List[Dict]: 文件变更列表
        """
        files = []

        # 分割每个文件的diff
        diff_blocks = re.split(r'(?=^diff --git )', diff_content, flags=re.MULTILINE)

        for block in diff_blocks:
            if not block.strip():
                continue

            # 提取文件路径
            match = self.GIT_DIFF_PATTERN.search(block)
            if not match:
                continue

            # 使用b/后面的路径作为实际路径（目标文件）
            file_path = match.group(2).strip()

            # 检查是否为删除文件（diff中只有 a/ 路径）
            if file_path.startswith('/dev/null'):
                file_path = match.group(1).strip()

            # 跳过 /dev/null
            if file_path == '/dev/null' or file_path.startswith('dev/null'):
                continue

            # 统计新增和删除行数
            additions, deletions = self._count_changes(block)

            files.append({
                'path': file_path,
                'additions': additions,
                'deletions': deletions,
                'diff': block.strip()
            })

        logger.info(f"Parsed {len(files)} files from git diff")
        return files

    def _parse_svn_diff(self, diff_content: str) -> List[Dict]:
        """
        解析SVN diff格式

        Args:
            diff_content: SVN diff内容

        Returns:
            List[Dict]: 文件变更列表
        """
        files = []

        # 分割每个文件的diff
        diff_blocks = re.split(r'(?=^Index: )', diff_content, flags=re.MULTILINE)

        for block in diff_blocks:
            if not block.strip():
                continue

            # 提取文件路径
            match = self.SVN_DIFF_PATTERN.search(block)
            if not match:
                continue

            file_path = match.group(1).strip()

            # 统计新增和删除行数
            additions, deletions = self._count_changes(block)

            files.append({
                'path': file_path,
                'additions': additions,
                'deletions': deletions,
                'diff': block.strip()
            })

        logger.info(f"Parsed {len(files)} files from svn diff")
        return files

    def _count_changes(self, diff_block: str) -> tuple:
        """
        统计diff块中的新增和删除行数

        Args:
            diff_block: 单个文件的diff内容

        Returns:
            tuple: (additions, deletions)
        """
        additions = 0
        deletions = 0

        lines = diff_block.split('\n')
        for line in lines:
            # 跳过diff元数据行
            if line.startswith('diff --git') or \
               line.startswith('index ') or \
               line.startswith('--- ') or \
               line.startswith('+++ ') or \
               line.startswith('@@ ') or \
               line.startswith('Index:') or \
               line.startswith('===') or \
               line.startswith('\\ No newline'):
                continue

            # 统计变更行
            if line.startswith('+') and not line.startswith('+++'):
                additions += 1
            elif line.startswith('-') and not line.startswith('---'):
                deletions += 1

        return additions, deletions

    def filter_files(self, files: List[Dict]) -> Dict:
        """
        过滤文件，区分后端文件和前端文件

        Args:
            files: 文件变更列表

        Returns:
            Dict: 包含以下字段:
                - backend_files: 后端文件列表
                - frontend_files: 前端文件列表
                - backend_count: 后端文件数量
                - frontend_count: 前端文件数量
        """
        backend_files = []
        frontend_files = []

        exclude_patterns = settings.get_exclude_patterns_list()
        include_patterns = settings.get_include_patterns_list()
        exclude_dirs = settings.get_exclude_dirs_list()

        for file_info in files:
            file_path = file_info.get('path', '')

            if not file_path:
                continue

            # 检查是否在排除目录中
            if self._is_in_excluded_dir(file_path, exclude_dirs):
                logger.debug(f"File {file_path} is in excluded directory, skipping")
                continue

            # 判断是后端文件还是前端文件
            if self._is_backend_file(file_path, include_patterns, exclude_patterns):
                backend_files.append(file_info)
            else:
                frontend_files.append(file_info)

        result = {
            'backend_files': backend_files,
            'frontend_files': frontend_files,
            'backend_count': len(backend_files),
            'frontend_count': len(frontend_files)
        }

        logger.info(f"Filtered files: {len(backend_files)} backend, {len(frontend_files)} frontend")
        return result

    def _is_in_excluded_dir(self, file_path: str, exclude_dirs: List[str]) -> bool:
        """
        检查文件是否在排除目录中

        Args:
            file_path: 文件路径
            exclude_dirs: 排除目录列表

        Returns:
            bool: 是否在排除目录中
        """
        for exclude_dir in exclude_dirs:
            if file_path.startswith(exclude_dir + '/') or file_path.startswith(exclude_dir):
                return True
        return False

    def _is_backend_file(self, file_path: str, include_patterns: List[str], exclude_patterns: List[str]) -> bool:
        """
        判断文件是否为后端文件

        Args:
            file_path: 文件路径
            include_patterns: 包含模式列表
            exclude_patterns: 排除模式列表

        Returns:
            bool: 是否为后端文件
        """
        # 提取文件名
        file_name = file_path.split('/')[-1]

        # 首先检查排除模式
        for pattern in exclude_patterns:
            if fnmatch.fnmatch(file_name, pattern):
                return False

        # 然后检查包含模式
        for pattern in include_patterns:
            if fnmatch.fnmatch(file_name, pattern):
                return True

        # 默认根据文件扩展名判断
        backend_extensions = {'.py', '.java', '.go', '.rs', '.rb', '.php', '.cs', '.sql'}
        for ext in backend_extensions:
            if file_path.endswith(ext):
                return True

        return False

    def get_changed_file_paths(self, files: List[Dict]) -> List[str]:
        """
        获取变更文件的路径列表

        Args:
            files: 文件变更列表

        Returns:
            List[str]: 文件路径列表
        """
        paths = []
        for file_info in files:
            path = file_info.get('path')
            if path:
                paths.append(path)
        return paths

    def get_diff_summary(self, files: List[Dict]) -> str:
        """
        生成diff变更摘要

        Args:
            files: 文件变更列表

        Returns:
            str: 变更摘要字符串
        """
        if not files:
            return "No files changed."

        total_additions = 0
        total_deletions = 0
        file_count = len(files)

        for file_info in files:
            total_additions += file_info.get('additions', 0)
            total_deletions += file_info.get('deletions', 0)

        summary_parts = [f"{file_count} file{'s' if file_count > 1 else ''} changed"]

        if total_additions > 0:
            summary_parts.append(f"{total_additions} insertion{'s' if total_additions > 1 else ''}(+)")

        if total_deletions > 0:
            summary_parts.append(f"{total_deletions} deletion{'s' if total_deletions > 1 else ''}(-)")

        summary = ", ".join(summary_parts)
        return summary


# 创建全局实例
diff_parser = DiffParser()
