"""
应用配置模块
使用 pydantic-settings 管理环境变量配置
"""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    """应用配置类"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    # 数据库配置（分离字段）
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_NAME: str = "cr_platform"
    DB_USER: str = "root"
    DB_PASSWORD: str = ""

    # Jira 配置
    JIRA_BASE_URL: str = ""
    JIRA_EMAIL: str = ""  # 改名自 jira_username
    JIRA_API_TOKEN: str = ""

    # Claude API 配置
    CLAUDE_API_KEY: str = ""
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"

    # Cursor Cloud Agent 配置 (优先级高于 CLAUDE_API_KEY；占位符或空值会被忽略)
    CURSOR_API_KEY: str = ""
    CURSOR_AGENT_REPO_URL: str = ""
    CURSOR_AGENT_REPO_REF: str = "master"
    CURSOR_AGENT_MODEL: str = "auto"
    CURSOR_AGENT_POLL_INTERVAL: int = 5     # 轮询间隔（秒）
    CURSOR_AGENT_TIMEOUT: int = 600         # agent 最长等待时间（秒）
    CURSOR_API_BASE: str = "https://api.cursor.com/v1/agents"

    # 认证配置
    AUTH_TOKEN: str = "demo-token"

    # 前端配置
    FRONTEND_URL: str = "http://localhost:5173"

    # AI 分析配置
    SINGLE_CALL_TIMEOUT: int = 60
    TOTAL_ANALYSIS_TIMEOUT: int = 300
    MAX_CONTEXT_FILES: int = 5
    MAX_FILE_LINES: int = 500

    # 文件过滤配置
    EXCLUDE_PATTERNS: str = "*.vue,*.jsx,*.tsx,*.css,*.scss,*.less,*.html,*.js,*.ts,package.json,package-lock.json,yarn.lock,pnpm-lock.yaml"
    INCLUDE_PATTERNS: str = "*.py,*.java,*.go,*.sql"
    EXCLUDE_DIRS: str = "node_modules/,dist/,build/,.venv/,venv/,__pycache__/"

    @property
    def DATABASE_URL(self) -> str:
        """构建数据库连接字符串"""
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @field_validator('EXCLUDE_PATTERNS', 'INCLUDE_PATTERNS', 'EXCLUDE_DIRS', mode='before')
    @classmethod
    def parse_patterns(cls, v: str) -> str:
        """解析文件模式配置"""
        if isinstance(v, str):
            return v
        return str(v)

    def get_exclude_patterns_list(self) -> List[str]:
        """获取排除文件模式列表"""
        return [p.strip() for p in self.EXCLUDE_PATTERNS.split(',') if p.strip()]

    def get_include_patterns_list(self) -> List[str]:
        """获取包含文件模式列表"""
        return [p.strip() for p in self.INCLUDE_PATTERNS.split(',') if p.strip()]

    def get_exclude_dirs_list(self) -> List[str]:
        """获取排除目录列表"""
        return [d.strip().rstrip('/') for d in self.EXCLUDE_DIRS.split(',') if d.strip()]

    # 应用配置
    app_env: str = "development"
    app_debug: bool = True
    log_level: str = "INFO"

    # Claude 模型配置
    claude_max_tokens: int = 4096
    claude_temperature: float = 0.3

    # 分页配置
    default_page_size: int = 20
    max_page_size: int = 100


# 创建全局配置实例
settings = Settings()
