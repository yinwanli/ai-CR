"""
AI分析服务
后端路由优先级: Cursor Cloud Agent > Claude API > mock
"""
import json
import re
import time
import logging
from typing import Dict, List, Any, Optional

from ..config import settings
from ..utils.prompt_builder import build_analyze_prompt, build_context_selection_prompt
from .mock_data import MockDataService

logger = logging.getLogger(__name__)


def _is_configured(value: str) -> bool:
    """判断配置项是否为有效值 (排除空串和 your_xxx 占位符)。"""
    if not value:
        return False
    v = value.strip().lower()
    if v.startswith("your_") or v in ("your_password", "your_auth_token", "changeme"):
        return False
    return True


class AIAnalyzer:
    """
    AI分析服务类。

    后端路径优先级:
        1. Cursor Cloud Agent (REST `/v1/agents`)  — 当 CURSOR_API_KEY 配置时
        2. Claude API (anthropic SDK)              — 当 CLAUDE_API_KEY 配置时
        3. Mock 数据                                 — 都没配置时
    """

    BACKEND_CURSOR = "cursor_agent"
    BACKEND_CLAUDE = "claude_api"
    BACKEND_MOCK = "mock"

    def __init__(self):
        """初始化AI分析器，根据配置决定后端路径。"""
        self.api_key = settings.CLAUDE_API_KEY
        self.model = settings.CLAUDE_MODEL
        self.timeout = settings.SINGLE_CALL_TIMEOUT
        self.max_context_files = settings.MAX_CONTEXT_FILES

        self.cursor_api_key = settings.CURSOR_API_KEY
        self.cursor_repo_url = settings.CURSOR_AGENT_REPO_URL
        self.cursor_repo_ref = settings.CURSOR_AGENT_REPO_REF
        self.cursor_model = settings.CURSOR_AGENT_MODEL

        self.use_cursor_agent = _is_configured(self.cursor_api_key)
        claude_configured = _is_configured(self.api_key)
        self.mock_mode = (not self.use_cursor_agent) and (not claude_configured)

        if self.use_cursor_agent:
            self.backend = self.BACKEND_CURSOR
            self.client = None
            logger.info(
                f"AIAnalyzer init: backend=cursor_agent, model={self.cursor_model}, "
                f"repo={self.cursor_repo_url or '<none>'}"
            )
        elif claude_configured:
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.api_key)
                self.backend = self.BACKEND_CLAUDE
                logger.info(f"AIAnalyzer init: backend=claude_api, model={self.model}")
            except ImportError:
                logger.warning("anthropic library not installed, falling back to mock mode")
                self.client = None
                self.mock_mode = True
                self.backend = self.BACKEND_MOCK
            except Exception as e:
                logger.error(f"Failed to initialize Claude API client: {e}")
                self.client = None
                self.mock_mode = True
                self.backend = self.BACKEND_MOCK
        else:
            self.client = None
            self.backend = self.BACKEND_MOCK
            logger.info("AIAnalyzer init: backend=mock (no CURSOR_API_KEY / CLAUDE_API_KEY configured)")

    def analyze(self, requirement_doc: str, code_diff: str) -> Dict[str, Any]:
        """
        分析代码变更是否满足需求

        Args:
            requirement_doc: 需求文档内容
            code_diff: 代码diff内容

        Returns:
            分析结果字典，包含:
            - requirements: 需求覆盖状态列表
            - issues: 检测到的问题列表
            - coverage_percent: 覆盖率百分比
            - summary: 分析摘要
        """
        if self.mock_mode:
            logger.info("Using mock mode for analysis")
            return MockDataService.get_mock_analysis_result()

        try:
            prompt = build_analyze_prompt(requirement_doc, code_diff)

            if self.use_cursor_agent:
                logger.info(f"Calling Cursor Cloud Agent (model={self.cursor_model})")
                response = self._call_cursor_agent(prompt)
            else:
                logger.info(f"Calling Claude API with model {self.model}")
                response = self._call_claude_api(prompt)

            if not response:
                logger.error(f"Empty response from backend={self.backend}")
                return {}

            result = self._extract_json(response)

            if not result:
                logger.error(f"Failed to extract JSON from backend={self.backend} response")
                return {}

            logger.info(f"Analysis completed (backend={self.backend}) coverage: {result.get('coverage_percent', 'N/A')}%")
            return result

        except Exception as e:
            logger.error(f"Error during analysis (backend={self.backend}): {e}", exc_info=True)
            return {}

    def select_context_files(self, changed_files: List[str], diff: str) -> List[str]:
        """
        选择需要额外读取的上下文文件

        Args:
            changed_files: 已变更的文件列表
            diff: 代码diff内容

        Returns:
            需要额外读取的文件路径列表
        """
        if self.mock_mode:
            # Mock模式下返回空列表或简单的启发式选择
            return self._heuristic_file_selection(changed_files, diff)

        if self.use_cursor_agent:
            # Cursor cloud agent 直接 clone 仓库自己看代码,
            # 无需上层手动挑上下文文件; 这里直接退回启发式或空表即可。
            return self._heuristic_file_selection(changed_files, diff)

        try:
            # 构建提示词
            prompt = build_context_selection_prompt(changed_files, diff)

            # 调用Claude API
            response = self._call_claude_api(prompt)

            if not response:
                logger.warning("Empty response for context selection, using heuristic")
                return self._heuristic_file_selection(changed_files, diff)

            # 解析JSON响应
            result = self._extract_json(response)

            if not result or "required_files" not in result:
                logger.warning("Invalid response for context selection, using heuristic")
                return self._heuristic_file_selection(changed_files, diff)

            files = result.get("required_files", [])
            # 限制最大文件数量
            return files[:self.max_context_files]

        except Exception as e:
            logger.error(f"Error selecting context files: {e}", exc_info=True)
            return self._heuristic_file_selection(changed_files, diff)

    def _call_claude_api(self, prompt: str) -> Optional[str]:
        """
        调用Claude API

        Args:
            prompt: 提示词内容

        Returns:
            Claude的响应文本，失败返回None
        """
        if self.mock_mode or not self.client:
            return None

        try:
            import anthropic

            message = self.client.messages.create(
                model=self.model,
                max_tokens=settings.claude_max_tokens,
                temperature=settings.claude_temperature,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # 提取响应内容
            if message.content and len(message.content) > 0:
                # content是TextBlock列表
                text_content = ""
                for block in message.content:
                    if hasattr(block, 'text'):
                        text_content += block.text
                return text_content

            return None

        except anthropic.APIConnectionError as e:
            logger.error(f"Claude API connection error: {e}")
            return None
        except anthropic.RateLimitError as e:
            logger.error(f"Claude API rate limit error: {e}")
            return None
        except anthropic.APIStatusError as e:
            logger.error(f"Claude API status error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error calling Claude API: {e}", exc_info=True)
            return None

    # ------------------------------------------------------------------
    # Cursor Cloud Agent  (REST `/v1/agents`)
    # ------------------------------------------------------------------
    # 终态字段名可能因 Cursor 版本而异, 这里做宽松匹配 (大写后判断关键字)
    _AGENT_DONE_STATES = {"FINISHED", "COMPLETED", "DONE", "SUCCESS", "SUCCEEDED"}
    _AGENT_FAIL_STATES = {"ERROR", "FAILED", "CANCELLED", "CANCELED", "ABORTED"}

    def _call_cursor_agent(self, prompt: str) -> Optional[str]:
        """
        通过 Cursor Cloud Agents REST API 起一个 agent 任务并轮询拿结果。

        Args:
            prompt: 提示词

        Returns:
            最后一段 assistant 文本; 失败 / 超时 / 解析异常时返回 None。
        """
        import httpx

        base = settings.CURSOR_API_BASE.rstrip("/")
        headers = {
            "Authorization": f"Bearer {self.cursor_api_key}",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "prompt": prompt,
            "model": self.cursor_model,
        }
        if self.cursor_repo_url:
            payload["source"] = {
                "repository": self.cursor_repo_url,
                "ref": self.cursor_repo_ref or "master",
            }

        try:
            with httpx.Client(timeout=30) as client:
                # 1) 创建 agent
                r = client.post(base, headers=headers, json=payload)
                if r.status_code >= 400:
                    logger.error(f"Cursor agent create failed: HTTP {r.status_code} body={r.text[:500]}")
                    return None
                created = r.json() if r.content else {}
                agent_id = created.get("id") or created.get("agent_id")
                if not agent_id:
                    logger.error(f"Cursor agent create returned no id: {created}")
                    return None
                logger.info(f"Cursor agent created: id={agent_id}")

                # 2) 轮询
                deadline = time.time() + settings.CURSOR_AGENT_TIMEOUT
                last_status = None
                while time.time() < deadline:
                    poll = client.get(f"{base}/{agent_id}", headers=headers)
                    if poll.status_code >= 400:
                        logger.error(
                            f"Cursor agent poll failed: id={agent_id} HTTP {poll.status_code} "
                            f"body={poll.text[:500]}"
                        )
                        return None
                    body = poll.json() if poll.content else {}
                    status_raw = body.get("status") or body.get("state") or ""
                    status = str(status_raw).upper()
                    if status != last_status:
                        logger.info(f"Cursor agent status: id={agent_id} status={status}")
                        last_status = status
                    if status in self._AGENT_DONE_STATES:
                        return self._extract_cursor_response(body)
                    if status in self._AGENT_FAIL_STATES:
                        logger.error(f"Cursor agent failed: id={agent_id} status={status} body={str(body)[:500]}")
                        return None
                    time.sleep(settings.CURSOR_AGENT_POLL_INTERVAL)

                logger.error(
                    f"Cursor agent timeout: id={agent_id} after {settings.CURSOR_AGENT_TIMEOUT}s, last_status={last_status}"
                )
                return None
        except httpx.HTTPError as e:
            logger.error(f"Cursor agent HTTP error: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Cursor agent unexpected error: {e}", exc_info=True)
            return None

    @staticmethod
    def _extract_cursor_response(body: Dict[str, Any]) -> Optional[str]:
        """从 cursor agent 返回 body 里抽出最后一段 assistant 文本，兼容多种 schema。"""
        # 形态 A: { result: "..." } 或 { output: "..." }
        for key in ("result", "output", "answer", "text"):
            val = body.get(key)
            if isinstance(val, str) and val.strip():
                return val

        # 形态 B: { messages: [ {role, content (str | list[block])} ] }
        for key in ("messages", "transcript", "history"):
            arr = body.get(key)
            if isinstance(arr, list) and arr:
                for m in reversed(arr):
                    if not isinstance(m, dict):
                        continue
                    if m.get("role") != "assistant":
                        continue
                    content = m.get("content")
                    if isinstance(content, str):
                        return content
                    if isinstance(content, list):
                        text = "".join(
                            c.get("text", "")
                            for c in content
                            if isinstance(c, dict) and c.get("type") in ("text", "output_text")
                        )
                        if text:
                            return text

        logger.warning(f"Cursor agent finished but no extractable text found. top_keys={list(body.keys())}")
        return None

    def _extract_json(self, content: str) -> Dict[str, Any]:
        """
        从Claude响应中提取JSON

        Claude可能返回纯JSON或包含在代码块中的JSON

        Args:
            content: Claude响应内容

        Returns:
            解析后的字典，解析失败返回空字典
        """
        if not content:
            return {}

        # 尝试直接解析
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # 尝试提取代码块中的JSON
        # 匹配 ```json ... ``` 或 ``` ... ``` 格式
        code_block_patterns = [
            r'```json\s*\n(.*?)\n```',
            r'```\s*\n(.*?)\n```',
            r'```json\s+(.*?)\n```',
            r'```\s+(.*?)\n```',
        ]

        for pattern in code_block_patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            if matches:
                for match in matches:
                    try:
                        return json.loads(match.strip())
                    except json.JSONDecodeError:
                        continue

        # 尝试查找JSON对象 {...}
        json_object_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_object_pattern, content, re.DOTALL)
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

        # 尝试更宽松的模式，查找最大的JSON对象
        brace_count = 0
        start_idx = None
        for i, char in enumerate(content):
            if char == '{':
                if start_idx is None:
                    start_idx = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_idx is not None:
                    try:
                        return json.loads(content[start_idx:i+1])
                    except json.JSONDecodeError:
                        start_idx = None
                        continue

        logger.warning("Failed to extract JSON from content")
        return {}

    def _heuristic_file_selection(self, changed_files: List[str], diff: str) -> List[str]:
        """
        启发式文件选择方法

        当API不可用时使用简单的启发式规则选择上下文文件

        Args:
            changed_files: 已变更的文件列表
            diff: 代码diff内容

        Returns:
            推荐的上下文文件列表
        """
        recommended_files = []

        # 分析diff中的导入语句
        import_pattern = r'^(?:import|from)\s+([a-zA-Z_][a-zA-Z0-9_.]*)'
        imports = re.findall(import_pattern, diff, re.MULTILINE)

        # 如果有导入语句，尝试推断相关文件
        # 这里只是简单示例，实际应用中可能需要更复杂的逻辑
        for imp in imports[:self.max_context_files]:
            # 将模块名转换为可能的文件路径
            module_path = imp.replace('.', '/')
            for changed_file in changed_files:
                if module_path in changed_file and changed_file not in recommended_files:
                    recommended_files.append(changed_file)
                    if len(recommended_files) >= self.max_context_files:
                        break

        return recommended_files

    def is_mock_mode(self) -> bool:
        """
        检查是否运行在mock模式

        Returns:
            True表示使用mock模式，False表示使用真实后端
        """
        return self.mock_mode

    def get_model_info(self) -> Dict[str, Any]:
        """
        获取当前使用的后端 + 模型信息

        Returns:
            包含 backend / model / 其他参数的字典
        """
        info: Dict[str, Any] = {
            "backend": self.backend,
            "mock_mode": self.mock_mode,
            "timeout": self.timeout,
            "max_context_files": self.max_context_files,
        }
        if self.backend == self.BACKEND_CURSOR:
            info.update({
                "model": self.cursor_model,
                "repo_url": self.cursor_repo_url,
                "repo_ref": self.cursor_repo_ref,
                "poll_interval": settings.CURSOR_AGENT_POLL_INTERVAL,
                "agent_timeout": settings.CURSOR_AGENT_TIMEOUT,
            })
        else:
            info.update({
                "model": self.model,
                "max_tokens": settings.claude_max_tokens,
                "temperature": settings.claude_temperature,
            })
        return info


ai_analyzer = AIAnalyzer()
