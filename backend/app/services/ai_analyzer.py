"""
AI分析服务
后端路由优先级: Cursor Cloud Agent > Claude API > mock
"""
import json
import re
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, TYPE_CHECKING

from ..config import settings
from ..utils.prompt_builder import build_analyze_prompt, build_context_selection_prompt
from .mock_data import MockDataService
from .ai_invocation_service import AiInvocationService, LlmInvokeOutcome

if TYPE_CHECKING:
    from .ai_invocation_context import InvocationContext

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

    def analyze(
        self,
        requirement_doc: str,
        code_diff: str,
        invocation_context: Optional["InvocationContext"] = None,
    ) -> Dict[str, Any]:
        """
        分析代码变更是否满足需求

        Args:
            requirement_doc: 需求文档内容
            code_diff: 代码diff内容
            invocation_context: AI 调用日志上下文（可选）

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
            response = self._call_llm(
                prompt,
                purpose="analyze",
                invocation_context=invocation_context,
            )

            if not response:
                logger.error(f"Empty response from backend={self.backend}")
                return {}

            result = self._extract_json(response)

            if not result:
                logger.error(f"Failed to extract JSON from backend={self.backend} response")
                if invocation_context and invocation_context.last_invocation_id:
                    AiInvocationService.mark_parse_error(
                        invocation_context.last_invocation_id,
                        "Failed to extract JSON from analyze response",
                    )
                return {}

            logger.info(f"Analysis completed (backend={self.backend}) coverage: {result.get('coverage_percent', 'N/A')}%")
            return result

        except Exception as e:
            logger.error(f"Error during analysis (backend={self.backend}): {e}", exc_info=True)
            return {}

    def select_context_files(
        self,
        changed_files: List[str],
        diff: str,
        invocation_context: Optional["InvocationContext"] = None,
    ) -> List[str]:
        """
        选择需要额外读取的上下文文件

        Args:
            changed_files: 已变更的文件列表
            diff: 代码diff内容
            invocation_context: AI 调用日志上下文（可选）

        Returns:
            需要额外读取的文件路径列表
        """
        if self.mock_mode:
            return self._heuristic_file_selection(changed_files, diff)

        try:
            prompt = build_context_selection_prompt(changed_files, diff)
            response = self._call_llm(
                prompt,
                purpose="select_context_files",
                invocation_context=invocation_context,
            )

            if not response:
                logger.warning(
                    "Empty response for context selection (backend=%s), using heuristic",
                    self.backend,
                )
                return self._heuristic_file_selection(changed_files, diff)

            result = self._extract_json(response)

            if not result or "required_files" not in result:
                logger.warning(
                    "Invalid context selection JSON (backend=%s), using heuristic",
                    self.backend,
                )
                return self._heuristic_file_selection(changed_files, diff)

            files = result.get("required_files", [])
            return files[: self.max_context_files]

        except Exception as e:
            logger.error(f"Error selecting context files: {e}", exc_info=True)
            return self._heuristic_file_selection(changed_files, diff)

    def _call_llm(
        self,
        prompt: str,
        purpose: str = "analyze",
        invocation_context: Optional["InvocationContext"] = None,
    ) -> Optional[str]:
        """
        按当前 backend 调用 LLM（Cursor Cloud Agent 或 Claude API）。

        Args:
            prompt: 提示词
            purpose: 日志用途标识，如 analyze / select_context_files
            invocation_context: 传入时写入 ai_invocation_log

        Returns:
            模型响应文本，失败返回 None
        """
        if self.mock_mode:
            return None

        model_name = self.cursor_model if self.use_cursor_agent else self.model
        invocation_id: Optional[int] = None
        started_at = datetime.utcnow()

        if invocation_context is not None:
            try:
                invocation_id = AiInvocationService.start_invocation(
                    context=invocation_context,
                    purpose=purpose,
                    backend=self.backend,
                    model=model_name,
                    prompt_text=prompt,
                )
            except Exception as exc:
                logger.warning("AI invocation log start skipped: %s", exc)

        if self.use_cursor_agent:
            logger.info(
                "Calling Cursor Cloud Agent for %s (model=%s)",
                purpose,
                self.cursor_model,
            )
            outcome = self._call_cursor_agent(prompt)
        else:
            logger.info("Calling Claude API for %s (model=%s)", purpose, self.model)
            outcome = self._call_claude_api(prompt)

        if invocation_id is not None:
            try:
                AiInvocationService.finish_invocation(invocation_id, outcome, started_at)
            except Exception as exc:
                logger.warning("AI invocation log finish skipped: %s", exc)

        return outcome.text if outcome.text else None

    def _call_claude_api(self, prompt: str) -> LlmInvokeOutcome:
        """
        调用Claude API

        Args:
            prompt: 提示词内容

        Returns:
            LlmInvokeOutcome 包含文本与 token 等元数据
        """
        outcome = LlmInvokeOutcome()
        if self.mock_mode or not self.client:
            return outcome

        try:
            import anthropic

            message = self.client.messages.create(
                model=self.model,
                max_tokens=settings.claude_max_tokens,
                temperature=settings.claude_temperature,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )

            outcome.external_request_id = getattr(message, "id", None)
            usage = getattr(message, "usage", None)
            if usage is not None:
                outcome.input_tokens = getattr(usage, "input_tokens", None)
                outcome.output_tokens = getattr(usage, "output_tokens", None)

            if message.content and len(message.content) > 0:
                text_content = ""
                for block in message.content:
                    if hasattr(block, "text"):
                        text_content += block.text
                outcome.text = text_content or None

            return outcome

        except anthropic.APIConnectionError as e:
            logger.error(f"Claude API connection error: {e}")
            outcome.failure_stage = "claude_request"
            outcome.error_message = str(e)
            return outcome
        except anthropic.RateLimitError as e:
            logger.error(f"Claude API rate limit error: {e}")
            outcome.failure_stage = "claude_request"
            outcome.error_message = str(e)
            return outcome
        except anthropic.APIStatusError as e:
            logger.error(f"Claude API status error: {e}")
            outcome.failure_stage = "claude_request"
            outcome.http_status = getattr(e, "status_code", None)
            outcome.error_message = str(e)
            return outcome
        except Exception as e:
            logger.error(f"Unexpected error calling Claude API: {e}", exc_info=True)
            outcome.failure_stage = "claude_request"
            outcome.error_message = str(e)
            return outcome

    # ------------------------------------------------------------------
    # Cursor Cloud Agent  (REST `/v1/agents` — v1 public beta schema)
    # ------------------------------------------------------------------
    _RUN_DONE_STATES = {"FINISHED", "COMPLETED", "DONE", "SUCCESS", "SUCCEEDED"}
    _RUN_FAIL_STATES = {"ERROR", "FAILED", "CANCELLED", "CANCELED", "ABORTED"}

    def _build_cursor_create_payload(self, prompt: str) -> Dict[str, Any]:
        """
        构造 POST /v1/agents 请求体（v1 要求 prompt/model 为 object，仓库用 repos[]）。
        """
        payload: Dict[str, Any] = {
            "prompt": {"text": prompt},
        }
        model_id = (self.cursor_model or "").strip()
        if model_id and model_id.lower() != "auto":
            payload["model"] = {"id": model_id}

        repo_url = (self.cursor_repo_url or "").strip()
        if repo_url:
            if not repo_url.startswith("http"):
                repo_url = f"https://github.com/{repo_url.strip('/')}"
            payload["repos"] = [
                {
                    "url": repo_url,
                    "startingRef": self.cursor_repo_ref or "master",
                }
            ]
        return payload

    @staticmethod
    def _parse_cursor_create_response(created: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
        """从 create 响应解析 agent_id、run_id（兼容 v1 {agent, run} 与旧扁平结构）。"""
        agent = created.get("agent") if isinstance(created.get("agent"), dict) else created
        run = created.get("run") if isinstance(created.get("run"), dict) else {}
        agent_id = (
            agent.get("id")
            or created.get("id")
            or created.get("agent_id")
        )
        run_id = (
            run.get("id")
            or agent.get("latestRunId")
            or created.get("run_id")
            or created.get("latestRunId")
        )
        return agent_id, run_id

    def _collect_cursor_run_text(
        self, client: Any, base: str, headers: Dict[str, str], agent_id: str, run_id: str
    ) -> str:
        """通过 GET .../runs/{runId}/stream 收集 assistant 文本增量。"""
        url = f"{base}/{agent_id}/runs/{run_id}/stream"
        stream_headers = {**headers, "Accept": "text/event-stream"}
        parts: List[str] = []
        event_type: Optional[str] = None
        try:
            with client.stream(
                "GET",
                url,
                headers=stream_headers,
                timeout=settings.CURSOR_AGENT_TIMEOUT,
            ) as resp:
                if resp.status_code >= 400:
                    logger.warning(
                        "Cursor run stream unavailable: agent=%s run=%s HTTP %s %s",
                        agent_id,
                        run_id,
                        resp.status_code,
                        resp.text[:300],
                    )
                    return ""
                for line in resp.iter_lines():
                    if not line:
                        continue
                    if line.startswith("event:"):
                        event_type = line[6:].strip()
                    elif line.startswith("data:"):
                        data_str = line[5:].strip()
                        if event_type == "assistant" and data_str:
                            try:
                                data = json.loads(data_str)
                                if isinstance(data, dict):
                                    parts.append(data.get("text") or "")
                            except json.JSONDecodeError:
                                parts.append(data_str)
                        elif event_type in ("done", "result"):
                            break
        except Exception as e:
            logger.warning("Cursor run stream read error: %s", e)
        return "".join(parts)

    def _call_cursor_agent(self, prompt: str) -> LlmInvokeOutcome:
        """
        通过 Cursor Cloud Agents REST API 创建 agent + run，轮询 run 状态并拉取输出。

        Args:
            prompt: 提示词

        Returns:
            LlmInvokeOutcome 含 assistant 文本与 agent/run 元数据
        """
        import httpx

        outcome = LlmInvokeOutcome()
        base = settings.CURSOR_API_BASE.rstrip("/")
        headers = {
            "Authorization": f"Bearer {self.cursor_api_key}",
            "Content-Type": "application/json",
        }
        payload = self._build_cursor_create_payload(prompt)

        try:
            with httpx.Client(timeout=60) as client:
                create_resp = client.post(base, headers=headers, json=payload)
                if create_resp.status_code >= 400:
                    logger.error(
                        "Cursor agent create failed: HTTP %s body=%s",
                        create_resp.status_code,
                        create_resp.text[:500],
                    )
                    outcome.failure_stage = "create_agent"
                    outcome.http_status = create_resp.status_code
                    outcome.error_message = create_resp.text[:500]
                    return outcome

                created = create_resp.json() if create_resp.content else {}
                agent_id, run_id = self._parse_cursor_create_response(created)
                if not agent_id or not run_id:
                    logger.error("Cursor agent create missing id: %s", created)
                    outcome.failure_stage = "create_agent"
                    outcome.error_message = f"missing agent_id/run_id in response: {created}"
                    return outcome

                outcome.agent_id = str(agent_id)
                outcome.run_id = str(run_id)
                logger.info("Cursor agent created: agent_id=%s run_id=%s", agent_id, run_id)

                deadline = time.time() + settings.CURSOR_AGENT_TIMEOUT
                last_status: Optional[str] = None
                while time.time() < deadline:
                    poll = client.get(
                        f"{base}/{agent_id}/runs/{run_id}",
                        headers=headers,
                    )
                    if poll.status_code >= 400:
                        logger.error(
                            "Cursor run poll failed: agent=%s run=%s HTTP %s %s",
                            agent_id,
                            run_id,
                            poll.status_code,
                            poll.text[:500],
                        )
                        outcome.failure_stage = "poll"
                        outcome.http_status = poll.status_code
                        outcome.error_message = poll.text[:500]
                        outcome.run_status = last_status
                        return outcome

                    body = poll.json() if poll.content else {}
                    status = str(body.get("status") or "").upper()
                    if status != last_status:
                        logger.info(
                            "Cursor run status: agent=%s run=%s status=%s",
                            agent_id,
                            run_id,
                            status,
                        )
                        last_status = status

                    if status in self._RUN_DONE_STATES:
                        outcome.run_status = status
                        text = self._collect_cursor_run_text(
                            client, base, headers, agent_id, run_id
                        )
                        if text.strip():
                            outcome.text = text
                            return outcome
                        fallback = self._extract_cursor_response(body)
                        outcome.text = fallback
                        if not fallback:
                            outcome.failure_stage = "stream"
                            outcome.error_message = "Run finished but no extractable text"
                        return outcome

                    if status in self._RUN_FAIL_STATES:
                        logger.error(
                            "Cursor run failed: agent=%s run=%s status=%s body=%s",
                            agent_id,
                            run_id,
                            status,
                            str(body)[:500],
                        )
                        outcome.run_status = status
                        outcome.failure_stage = "poll"
                        outcome.error_message = str(body)[:500]
                        return outcome

                    time.sleep(settings.CURSOR_AGENT_POLL_INTERVAL)

                logger.error(
                    "Cursor run timeout: agent=%s run=%s after %ss last_status=%s",
                    agent_id,
                    run_id,
                    settings.CURSOR_AGENT_TIMEOUT,
                    last_status,
                )
                outcome.failure_stage = "timeout"
                outcome.run_status = last_status
                outcome.error_message = (
                    f"Timeout after {settings.CURSOR_AGENT_TIMEOUT}s last_status={last_status}"
                )
                return outcome
        except httpx.HTTPError as e:
            logger.error(f"Cursor agent HTTP error: {e}", exc_info=True)
            outcome.failure_stage = "create_agent"
            outcome.error_message = str(e)
            return outcome
        except Exception as e:
            logger.error(f"Cursor agent unexpected error: {e}", exc_info=True)
            outcome.failure_stage = "create_agent"
            outcome.error_message = str(e)
            return outcome

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
