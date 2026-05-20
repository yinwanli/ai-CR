import re
from typing import Optional, Tuple

def extract_jira_key(release_no: str) -> Optional[str]:
    """
    从上线单号中提取Jira单号
    支持格式: REL-20240517-PROJ-123 -> PROJ-123
    """
    if not release_no:
        return None
    pattern = r'([A-Z][A-Z0-9]+-\d+)'
    match = re.search(pattern, release_no.upper())
    if match:
        return match.group(1)
    return None

def parse_release_info(release_no: str) -> Tuple[Optional[str], Optional[str]]:
    """解析上线单号信息，返回(Jira单号, 项目前缀)"""
    jira_key = extract_jira_key(release_no)
    if jira_key:
        project_prefix = jira_key.split('-')[0]
        return jira_key, project_prefix
    return None, None
