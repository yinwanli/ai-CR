# CR代码分析平台实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个代码CR分析平台，实现需求文档与代码变更的匹配分析，支持六维度分析、人工标记和覆盖率计算。

**Architecture:** 前后端分离架构，后端使用FastAPI + MySQL + BackgroundTasks，前端使用Vue3 + Element Plus，AI分析使用Claude API。

**Tech Stack:** Python 3.9+, FastAPI, SQLAlchemy, MySQL 8.0, Vue 3, Element Plus, Vite, Claude API

---

## 文件结构概览

```
ai_diff/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI入口
│   │   ├── config.py            # 配置管理
│   │   ├── auth.py              # Token认证
│   │   ├── database.py          # 数据库连接
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── analyze.py       # 分析接口
│   │   │   ├── report.py        # 报告接口
│   │   │   └── webhook.py       # Webhook接口
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── jira_service.py  # Jira对接
│   │   │   ├── diff_parser.py   # Diff解析
│   │   │   ├── ai_analyzer.py   # AI分析
│   │   │   └── mock_data.py     # Mock数据
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── task.py          # 任务模型
│   │   │   ├── report.py        # 报告模型
│   │   │   └── config.py        # 配置模型
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── request.py       # 请求模型
│   │   │   └── response.py      # 响应模型
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── jira_parser.py   # Jira单号解析
│   │       ├── prompt_builder.py # Prompt构建
│   │       └── logger.py        # 日志工具
│   ├── logs/
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── main.js
│   │   ├── App.vue
│   │   ├── views/
│   │   │   ├── Home.vue
│   │   │   ├── Report.vue
│   │   │   └── History.vue
│   │   ├── components/
│   │   │   ├── AnalyzeForm.vue
│   │   │   ├── CoverageCard.vue
│   │   │   ├── RequirementList.vue
│   │   │   └── IssueList.vue
│   │   ├── api/
│   │   │   └── index.js
│   │   ├── router/
│   │   │   └── index.js
│   │   └── utils/
│   │       └── polling.js
│   ├── package.json
│   └── vite.config.js
│
├── docs/
│   └── cr-platform-design.md

└── README.md
```

---

## Task 1: 后端项目初始化

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`

- [ ] **Step 1: 创建后端目录结构**

```bash
cd /Users/sunbingyan/11学习/python/ai_diff
mkdir -p backend/app/api backend/app/services backend/app/models backend/app/schemas backend/app/utils backend/logs backend/tests
touch backend/app/__init__.py backend/app/api/__init__.py backend/app/services/__init__.py backend/app/models/__init__.py backend/app/schemas/__init__.py backend/app/utils/__init__.py
```

- [ ] **Step 2: 创建 requirements.txt**

```txt
# Web框架
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-multipart==0.0.6

# 数据库
sqlalchemy==2.0.25
pymysql==1.1.0
alembic==1.13.1

# HTTP客户端
httpx==0.26.0
requests==2.31.0

# AI
anthropic==0.18.1

# 配置
python-dotenv==1.0.0
pydantic==2.5.3
pydantic-settings==2.1.0

# 日志
loguru==0.7.2

# 测试
pytest==7.4.4
pytest-asyncio==0.23.3
```

- [ ] **Step 3: 创建 .env.example**

```env
# 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_NAME=cr_platform
DB_USER=root
DB_PASSWORD=your_password

# Jira配置
JIRA_BASE_URL=https://your-company.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your_jira_api_token

# Claude API配置
CLAUDE_API_KEY=your_claude_api_key

# 认证配置
AUTH_TOKEN=your_auth_token

# 前端URL
FRONTEND_URL=http://localhost:5173
```

- [ ] **Step 4: 创建配置管理 config.py**

```python
# backend/app/config.py
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # 数据库配置
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_NAME: str = "cr_platform"
    DB_USER: str = "root"
    DB_PASSWORD: str = ""

    # Jira配置
    JIRA_BASE_URL: str = ""
    JIRA_EMAIL: str = ""
    JIRA_API_TOKEN: str = ""

    # Claude API配置
    CLAUDE_API_KEY: str = ""
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"

    # 认证配置
    AUTH_TOKEN: str = "demo-token"

    # 前端URL
    FRONTEND_URL: str = "http://localhost:5173"

    # AI配置
    SINGLE_CALL_TIMEOUT: int = 60
    TOTAL_ANALYSIS_TIMEOUT: int = 300
    MAX_CONTEXT_FILES: int = 5
    MAX_FILE_LINES: int = 500

    # 文件过滤配置
    EXCLUDE_PATTERNS: List[str] = [
        "*.vue", "*.jsx", "*.tsx",
        "*.css", "*.scss", "*.less",
        "*.html", "*.js", "*.ts",
        "package.json", "package-lock.json",
        "yarn.lock", "pnpm-lock.yaml",
    ]
    INCLUDE_PATTERNS: List[str] = [
        "*.py", "*.java", "*.go", "*.sql",
    ]
    EXCLUDE_DIRS: List[str] = [
        "node_modules/", "dist/", "build/",
        ".venv/", "venv/", "__pycache__/",
    ]

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
```

- [ ] **Step 5: 创建数据库连接 database.py**

```python
# backend/app/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 6: 验证配置加载**

```bash
cd /Users/sunbingyan/11学习/python/ai_diff/backend
python -c "from app.config import settings; print(f'DB: {settings.DB_HOST}:{settings.DB_PORT}')"
```

Expected: 输出数据库配置信息

---

## Task 2: 数据库模型创建

**Files:**
- Create: `backend/app/models/task.py`
- Create: `backend/app/models/report.py`
- Create: `backend/app/models/config.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: 创建任务模型 task.py**

```python
# backend/app/models/task.py
from sqlalchemy import Column, BigInteger, String, Enum, Text, DateTime
from sqlalchemy.sql import func
from ..database import Base
import enum


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    ANALYZING = "analyzing"
    SUCCESS = "success"
    FAILED = "failed"


class AnalysisTask(Base):
    __tablename__ = "analysis_task"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    release_no = Column(String(100), unique=True, nullable=False, comment="上线单号")
    jira_key = Column(String(50), comment="Jira单号")
    status = Column(
        Enum(TaskStatus),
        default=TaskStatus.PENDING,
        comment="任务状态"
    )
    error_message = Column(Text, comment="错误信息")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间"
    )
```

- [ ] **Step 2: 创建报告模型 report.py**

```python
# backend/app/models/report.py
from sqlalchemy import Column, BigInteger, Int, Decimal, Text, JSON, ForeignKey, DateTime, String, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base
import enum


class ItemType(str, enum.Enum):
    REQUIREMENT = "requirement"
    ISSUE = "issue"


class AnalysisReport(Base):
    __tablename__ = "analysis_report"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(BigInteger, ForeignKey("analysis_task.id"), nullable=False, comment="关联任务ID")

    # 覆盖率统计
    requirement_coverage = Column(Decimal(5, 2), comment="需求覆盖率")
    manual_coverage = Column(Decimal(5, 2), comment="人工修正后覆盖率")
    total_requirements = Column(Int, default=0, comment="需求总数")
    covered_requirements = Column(Int, default=0, comment="已覆盖数")
    irrelevant_requirements = Column(Int, default=0, comment="标记无关数")

    # 分析结果详情
    requirement_details = Column(JSON, comment="需求条目覆盖详情")
    extra_code_issues = Column(JSON, comment="夹带问题列表")
    syntax_errors = Column(JSON, comment="语法错误列表")
    boundary_issues = Column(JSON, comment="边界场景问题")
    exception_issues = Column(JSON, comment="异常兜底问题")
    quality_issues = Column(JSON, comment="代码质量问题")

    # 汇总
    total_issues = Column(Int, default=0, comment="问题总数")
    summary = Column(Text, comment="分析总结")

    # 文件统计
    backend_file_count = Column(Int, default=0, comment="后端文件数")
    frontend_file_count = Column(Int, default=0, comment="前端文件数")

    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")

    # 关联
    task = relationship("AnalysisTask", backref="report")
    marks = relationship("ManualMark", back_populates="report")


class ManualMark(Base):
    __tablename__ = "manual_mark"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    report_id = Column(BigInteger, ForeignKey("analysis_report.id"), nullable=False)

    item_type = Column(Enum(ItemType), comment="标记项类型")
    item_id = Column(String(100), comment="需求条目ID或问题ID")

    original_status = Column(String(50), comment="原始状态")
    marked_status = Column(String(50), comment="人工标记状态")
    marked_by = Column(String(100), comment="标记人")
    marked_at = Column(DateTime, server_default=func.now(), comment="标记时间")

    remark = Column(Text, comment="备注说明")

    # 关联
    report = relationship("AnalysisReport", back_populates="marks")
```

- [ ] **Step 3: 创建配置模型 config.py**

```python
# backend/app/models/config.py
from sqlalchemy import Column, Int, String, JSON, Text, DateTime
from sqlalchemy.sql import func
from ..database import Base


class SystemConfig(Base):
    __tablename__ = "system_config"

    id = Column(Int, primary_key=True, autoincrement=True)
    config_key = Column(String(100), unique=True, nullable=False)
    config_value = Column(JSON, nullable=False)
    description = Column(String(500))
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

- [ ] **Step 4: 更新 models/__init__.py**

```python
# backend/app/models/__init__.py
from .task import AnalysisTask, TaskStatus
from .report import AnalysisReport, ManualMark, ItemType
from .config import SystemConfig

__all__ = [
    "AnalysisTask",
    "TaskStatus",
    "AnalysisReport",
    "ManualMark",
    "ItemType",
    "SystemConfig",
]
```

- [ ] **Step 5: 验证模型导入**

```bash
cd /Users/sunbingyan/11学习/python/ai_diff/backend
python -c "from app.models import AnalysisTask, AnalysisReport; print('Models imported successfully')"
```

Expected: 输出 "Models imported successfully"

---

## Task 3: Pydantic Schemas 创建

**Files:**
- Create: `backend/app/schemas/request.py`
- Create: `backend/app/schemas/response.py`

- [ ] **Step 1: 创建请求模型 request.py**

```python
# backend/app/schemas/request.py
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class AnalyzeRequest(BaseModel):
    """提交分析请求"""
    release_no: str = Field(..., description="上线单号", min_length=1, max_length=100)


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
```

- [ ] **Step 2: 创建响应模型 response.py**

```python
# backend/app/schemas/response.py
from pydantic import BaseModel
from typing import Optional, List, Any, Dict
from datetime import datetime


class Response(BaseModel):
    """通用响应"""
    code: int = 0
    message: str = "success"
    data: Optional[Any] = None


class AnalyzeResponse(BaseModel):
    """分析响应"""
    task_id: int
    report_url: str
    status: str


class TaskResponse(BaseModel):
    """任务响应"""
    task_id: int
    release_no: str
    jira_key: Optional[str]
    status: str
    progress: Optional[str] = None
    created_at: str


class CoverageInfo(BaseModel):
    """覆盖率信息"""
    total: float
    manual_coverage: Optional[float] = None
    total_requirements: int
    covered_requirements: int
    irrelevant_requirements: int


class RequirementItem(BaseModel):
    """需求条目"""
    id: str
    content: str
    status: str
    confidence: float
    related_files: List[str] = []
    related_lines: List[List[int]] = []
    marked_status: Optional[str] = None


class IssueItem(BaseModel):
    """问题条目"""
    id: str
    type: str
    severity: str
    description: str
    file: Optional[str] = None
    lines: Optional[List[int]] = None
    suggestion: Optional[str] = None
    marked_status: Optional[str] = None


class ReportResponse(BaseModel):
    """报告响应"""
    task_id: int
    release_no: str
    jira_key: Optional[str]
    status: str
    coverage: CoverageInfo
    file_stats: Dict[str, int]
    requirements: List[RequirementItem]
    issues: List[IssueItem]
    summary: Optional[str] = None


class MarkResponse(BaseModel):
    """标记响应"""
    new_coverage: float


class HistoryItem(BaseModel):
    """历史记录条目"""
    task_id: int
    release_no: str
    status: str
    coverage: Optional[float] = None
    created_at: str
```

- [ ] **Step 3: 验证Schema导入**

```bash
cd /Users/sunbingyan/11学习/python/ai_diff/backend
python -c "from app.schemas.request import AnalyzeRequest; req = AnalyzeRequest(release_no='TEST-123'); print(f'Request: {req.release_no}')"
```

Expected: 输出 "Request: TEST-123"

---

## Task 4: 日志工具和工具函数

**Files:**
- Create: `backend/app/utils/logger.py`
- Create: `backend/app/utils/jira_parser.py`
- Create: `backend/app/utils/prompt_builder.py`

- [ ] **Step 1: 创建日志工具 logger.py**

```python
# backend/app/utils/logger.py
import sys
import os
from loguru import logger

# 移除默认处理器
logger.remove()

# 获取日志目录
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# 控制台输出格式
CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)

# 文件输出格式
FILE_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss} | "
    "{level: <8} | "
    "{name}:{function}:{line} | "
    "{message}"
)

# 添加控制台处理器
logger.add(
    sys.stdout,
    format=CONSOLE_FORMAT,
    level="DEBUG",
    colorize=True
)

# 添加文件处理器
logger.add(
    os.path.join(LOG_DIR, "app_{time:YYYY-MM-DD}.log"),
    format=FILE_FORMAT,
    level="DEBUG",
    rotation="00:00",
    retention="7 days",
    encoding="utf-8"
)

# 添加错误日志文件
logger.add(
    os.path.join(LOG_DIR, "error_{time:YYYY-MM-DD}.log"),
    format=FILE_FORMAT,
    level="ERROR",
    rotation="00:00",
    retention="30 days",
    encoding="utf-8"
)


def get_logger(name: str = None):
    """获取logger实例"""
    if name:
        return logger.bind(name=name)
    return logger
```

- [ ] **Step 2: 创建Jira单号解析 jira_parser.py**

```python
# backend/app/utils/jira_parser.py
import re
from typing import Optional, Tuple


def extract_jira_key(release_no: str) -> Optional[str]:
    """
    从上线单号中提取Jira单号

    支持格式:
    - REL-20240517-PROJ-123 -> PROJ-123
    - PROJ-123 -> PROJ-123
    - release-PROJ-123 -> PROJ-123

    Args:
        release_no: 上线单号

    Returns:
        Jira单号或None
    """
    if not release_no:
        return None

    # Jira单号正则: 大写字母 + 连字符 + 数字
    pattern = r'([A-Z][A-Z0-9]+-\d+)'
    match = re.search(pattern, release_no.upper())

    if match:
        return match.group(1)

    return None


def parse_release_info(release_no: str) -> Tuple[Optional[str], Optional[str]]:
    """
    解析上线单号信息

    Args:
        release_no: 上线单号

    Returns:
        (Jira单号, 项目前缀)
    """
    jira_key = extract_jira_key(release_no)

    if jira_key:
        # 提取项目前缀
        project_prefix = jira_key.split('-')[0]
        return jira_key, project_prefix

    return None, None


if __name__ == "__main__":
    # 测试
    test_cases = [
        "REL-20240517-PROJ-123",
        "PROJ-456",
        "release-DMP-789",
        "invalid_format",
    ]

    for case in test_cases:
        jira_key, prefix = parse_release_info(case)
        print(f"{case} -> Jira: {jira_key}, Prefix: {prefix}")
```

- [ ] **Step 3: 创建Prompt构建器 prompt_builder.py**

```python
# backend/app/utils/prompt_builder.py
from typing import List, Dict, Any


ANALYZE_PROMPT = """你是一个代码审查专家。请分析以下代码变更是否完整实现了需求功能。

## 需求文档
{requirement_doc}

## 代码变更
{code_diff}

## 分析要求
请从以下维度进行分析，并以JSON格式返回结果：

1. **需求覆盖率分析**
   - 逐条检查每个需求点是否在代码中实现
   - 标注每个需求对应的代码文件和行号

2. **夹带检测**
   - 检查是否存在与需求无关的代码变更
   - 标注疑似夹带的代码及其位置

3. **语法检查**
   - 检查代码是否存在语法错误
   - 标注错误位置和修复建议

4. **边界场景**
   - 检查是否处理了边界条件（空值、极值、异常输入等）
   - 标注缺失的边界处理

5. **异常兜底**
   - 检查是否有try-catch、重试、降级等容错机制
   - 标注缺少异常处理的位置

6. **代码质量**
   - 检查命名规范、代码重复、潜在bug等
   - 给出改进建议

## 返回格式
请严格按照以下JSON格式返回，不要添加任何其他内容：

```json
{{
  "requirements": [
    {{
      "id": "req_001",
      "content": "需求描述",
      "status": "covered",
      "confidence": 0.95,
      "related_files": ["file1.py"],
      "related_lines": [[10, 25]]
    }}
  ],
  "issues": [
    {{
      "id": "issue_001",
      "type": "extra_code",
      "severity": "warning",
      "description": "问题描述",
      "file": "file.py",
      "lines": [10, 20],
      "suggestion": "建议"
    }}
  ],
  "coverage_percent": 85,
  "summary": "分析总结"
}}
```
"""

CONTEXT_SELECTION_PROMPT = """分析以下代码变更，告诉我需要读取哪些额外的文件才能完整理解这些变更。

## 变更文件列表
{changed_files}

## 代码diff
{diff}

请返回JSON格式：
```json
{{
  "required_files": ["path/to/file1.py", "path/to/file2.py"],
  "reason": {{
    "path/to/file1.py": "包含被调用的核心函数",
    "path/to/file2.py": "变更类的父类定义"
  }}
}}
```

注意：只选择必要的文件，最多选择5个文件。
"""


def build_analyze_prompt(requirement_doc: str, code_diff: str) -> str:
    """
    构建分析Prompt

    Args:
        requirement_doc: 需求文档
        code_diff: 代码diff

    Returns:
        构建好的Prompt
    """
    return ANALYZE_PROMPT.format(
        requirement_doc=requirement_doc,
        code_diff=code_diff
    )


def build_context_selection_prompt(changed_files: List[str], diff: str) -> str:
    """
    构建上下文选择Prompt

    Args:
        changed_files: 变更文件列表
        diff: 代码diff

    Returns:
        构建好的Prompt
    """
    return CONTEXT_SELECTION_PROMPT.format(
        changed_files="\n".join(changed_files),
        diff=diff
    )
```

- [ ] **Step 4: 验证工具函数**

```bash
cd /Users/sunbingyan/11学习/python/ai_diff/backend
python -c "
from app.utils.jira_parser import extract_jira_key
result = extract_jira_key('REL-20240517-PROJ-123')
print(f'Jira Key: {result}')
"
```

Expected: 输出 "Jira Key: PROJ-123"

---

## Task 5: Mock数据服务

**Files:**
- Create: `backend/app/services/mock_data.py`

- [ ] **Step 1: 创建Mock数据服务**

```python
# backend/app/services/mock_data.py
from typing import Dict, Any, List
import json


class MockDataService:
    """Mock数据服务，用于Demo测试"""

    @staticmethod
    def get_mock_requirement(jira_key: str) -> str:
        """
        获取Mock需求文档

        Args:
            jira_key: Jira单号

        Returns:
            需求文档内容
        """
        mock_requirements = {
            "PROJ-123": """
## 用户登录功能

### 功能需求
1. 用户可以通过用户名和密码登录系统
2. 密码需要进行加密存储
3. 登录失败时显示错误提示
4. 支持记住密码功能
5. 登录成功后跳转到首页

### 非功能需求
1. 密码需要使用bcrypt加密
2. 登录失败次数超过5次需要锁定账户
3. 需要记录登录日志
""",
            "DMP-456": """
## 订单创建功能

### 功能需求
1. 用户可以创建新订单
2. 订单需要包含商品信息、数量、金额
3. 创建订单前需要校验库存
4. 订单创建成功后发送通知

### 非功能需求
1. 订单号需要唯一
2. 需要支持事务处理
3. 需要记录操作日志
""",
        }

        return mock_requirements.get(
            jira_key,
            """
## 通用功能需求

### 功能需求
1. 实现基本的数据处理功能
2. 支持数据的增删改查操作
3. 提供数据校验功能

### 非功能需求
1. 需要进行参数校验
2. 需要处理异常情况
3. 需要记录操作日志
"""
        )

    @staticmethod
    def get_mock_diff(diff_type: str = "git") -> str:
        """
        获取Mock diff数据

        Args:
            diff_type: diff类型

        Returns:
            diff内容
        """
        mock_diff = """diff --git a/auth/login.py b/auth/login.py
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/auth/login.py
@@ -0,0 +1,50 @@
+import bcrypt
+from flask import request, jsonify
+from models.user import User
+from utils.logger import get_logger
+
+logger = get_logger(__name__)
+
+
+def login():
+    \"\"\"
+    用户登录接口
+    \"\"\"
+    data = request.get_json()
+    username = data.get('username')
+    password = data.get('password')
+
+    # 参数校验
+    if not username or not password:
+        return jsonify({'code': 400, 'message': '用户名和密码不能为空'}), 400
+
+    # 查询用户
+    user = User.query.filter_by(username=username).first()
+    if not user:
+        return jsonify({'code': 401, 'message': '用户名或密码错误'}), 401
+
+    # 验证密码
+    if not bcrypt.checkpw(password.encode(), user.password.encode()):
+        return jsonify({'code': 401, 'message': '用户名或密码错误'}), 401
+
+    # 登录成功，生成token
+    token = generate_token(user.id)
+
+    return jsonify({
+        'code': 200,
+        'message': '登录成功',
+        'data': {'token': token}
+    })
+
+
+def generate_token(user_id):
+    \"\"\"生成JWT token\"\"\"
+    import jwt
+    import datetime
+    payload = {
+        'user_id': user_id,
+        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1)
+    }
+    return jwt.encode(payload, 'secret_key', algorithm='HS256')

diff --git a/utils/helper.py b/utils/helper.py
new file mode 100644
index 0000000..abcdefg
--- /dev/null
+++ b/utils/helper.py
@@ -0,0 +1,10 @@
+def format_date(date_obj):
+    \"\"\"日期格式化工具\"\"\"
+    return date_obj.strftime('%Y-%m-%d')
+
+def validate_email(email):
+    \"\"\"邮箱校验\"\"\"
+    import re
+    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'
+    return bool(re.match(pattern, email))
"""
        return mock_diff

    @staticmethod
    def get_mock_analysis_result() -> Dict[str, Any]:
        """
        获取Mock分析结果

        Returns:
            分析结果字典
        """
        return {
            "requirements": [
                {
                    "id": "req_001",
                    "content": "用户可以通过用户名和密码登录系统",
                    "status": "covered",
                    "confidence": 0.95,
                    "related_files": ["auth/login.py"],
                    "related_lines": [[10, 45]]
                },
                {
                    "id": "req_002",
                    "content": "密码需要进行加密存储",
                    "status": "covered",
                    "confidence": 0.88,
                    "related_files": ["auth/login.py"],
                    "related_lines": [[27, 29]]
                },
                {
                    "id": "req_003",
                    "content": "登录失败时显示错误提示",
                    "status": "covered",
                    "confidence": 0.90,
                    "related_files": ["auth/login.py"],
                    "related_lines": [[20, 30]]
                },
                {
                    "id": "req_004",
                    "content": "支持记住密码功能",
                    "status": "uncovered",
                    "confidence": 0.85,
                    "related_files": [],
                    "related_lines": []
                },
                {
                    "id": "req_005",
                    "content": "登录成功后跳转到首页",
                    "status": "uncovered",
                    "confidence": 0.80,
                    "related_files": [],
                    "related_lines": []
                },
            ],
            "issues": [
                {
                    "id": "issue_001",
                    "type": "extra_code",
                    "severity": "warning",
                    "description": "新增了未关联需求的工具类 utils/helper.py",
                    "file": "utils/helper.py",
                    "lines": [1, 10],
                    "suggestion": "请确认此工具类是否属于本次需求范围"
                },
                {
                    "id": "issue_002",
                    "type": "boundary",
                    "severity": "warning",
                    "description": "用户名超长时未做校验",
                    "file": "auth/login.py",
                    "lines": [14, 15],
                    "suggestion": "建议添加用户名长度校验"
                },
                {
                    "id": "issue_003",
                    "type": "exception",
                    "severity": "info",
                    "description": "数据库查询缺少异常处理",
                    "file": "auth/login.py",
                    "lines": [22, 25],
                    "suggestion": "建议添加try-catch处理数据库异常"
                }
            ],
            "coverage_percent": 60.0,
            "summary": "本次代码变更实现了用户登录的核心功能，包括用户名密码登录和密码加密验证。但缺少记住密码功能和登录后跳转的实现。发现1个夹带代码文件和2个潜在问题需要关注。"
        }
```

- [ ] **Step 2: 验证Mock服务**

```bash
cd /Users/sunbingyan/11学习/python/ai_diff/backend
python -c "
from app.services.mock_data import MockDataService
req = MockDataService.get_mock_requirement('PROJ-123')
print(f'Requirement length: {len(req)}')
"
```

Expected: 输出需求文档长度

---

## Task 6: Diff解析服务

**Files:**
- Create: `backend/app/services/diff_parser.py`

- [ ] **Step 1: 创建Diff解析服务**

```python
# backend/app/services/diff_parser.py
import re
from typing import List, Dict, Any
from fnmatch import fnmatch
from ..config import settings
from ..utils.logger import get_logger

logger = get_logger(__name__)


class DiffParser:
    """Diff解析器"""

    @staticmethod
    def parse_diff(diff_content: str, diff_type: str = "git") -> List[Dict[str, Any]]:
        """
        解析diff内容

        Args:
            diff_content: diff内容
            diff_type: diff类型 (git/svn)

        Returns:
            文件变更列表
        """
        if diff_type == "svn":
            return DiffParser._parse_svn_diff(diff_content)
        return DiffParser._parse_git_diff(diff_content)

    @staticmethod
    def _parse_git_diff(diff_content: str) -> List[Dict[str, Any]]:
        """解析Git diff"""
        files = []

        # Git diff文件头正则
        file_pattern = re.compile(r'diff --git a/(.*?) b/(.*?)$')

        # 分割每个文件的diff
        file_diffs = re.split(r'(?=^diff --git)', diff_content, flags=re.MULTILINE)

        for file_diff in file_diffs:
            if not file_diff.strip():
                continue

            lines = file_diff.split('\n')
            file_path = None
            additions = []
            deletions = []

            for line in lines:
                # 匹配文件路径
                match = file_pattern.match(line)
                if match:
                    file_path = match.group(2)
                    continue

                # 解析变更内容
                if line.startswith('+') and not line.startswith('+++'):
                    additions.append(line[1:])
                elif line.startswith('-') and not line.startswith('---'):
                    deletions.append(line[1:])

            if file_path:
                files.append({
                    "path": file_path,
                    "additions": additions,
                    "deletions": deletions,
                    "diff": file_diff
                })

        logger.info(f"Parsed {len(files)} files from git diff")
        return files

    @staticmethod
    def _parse_svn_diff(diff_content: str) -> List[Dict[str, Any]]:
        """解析SVN diff"""
        files = []

        # SVN diff文件头正则
        file_pattern = re.compile(r'Index: (.*)$')

        # 分割每个文件的diff
        file_diffs = re.split(r'(?=^Index:)', diff_content, flags=re.MULTILINE)

        for file_diff in file_diffs:
            if not file_diff.strip():
                continue

            lines = file_diff.split('\n')
            file_path = None
            additions = []
            deletions = []

            for line in lines:
                # 匹配文件路径
                match = file_pattern.match(line)
                if match:
                    file_path = match.group(1)
                    continue

                # 解析变更内容
                if line.startswith('+') and not line.startswith('+++'):
                    additions.append(line[1:])
                elif line.startswith('-') and not line.startswith('---'):
                    deletions.append(line[1:])

            if file_path:
                files.append({
                    "path": file_path,
                    "additions": additions,
                    "deletions": deletions,
                    "diff": file_diff
                })

        logger.info(f"Parsed {len(files)} files from svn diff")
        return files

    @staticmethod
    def filter_files(files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        过滤文件

        Args:
            files: 文件列表

        Returns:
            过滤结果
        """
        backend_files = []
        frontend_files = []

        for file_info in files:
            file_path = file_info["path"]

            # 检查是否在排除目录
            is_excluded_dir = any(
                excl_dir in file_path
                for excl_dir in settings.EXCLUDE_DIRS
            )
            if is_excluded_dir:
                continue

            # 检查是否匹配排除模式 (前端文件)
            is_frontend = any(
                fnmatch(file_path, pattern)
                for pattern in settings.EXCLUDE_PATTERNS
            )

            # 检查是否匹配包含模式 (后端文件)
            is_backend = any(
                fnmatch(file_path, pattern)
                for pattern in settings.INCLUDE_PATTERNS
            )

            if is_frontend:
                frontend_files.append(file_info)
            elif is_backend:
                backend_files.append(file_info)
            else:
                # 未知类型，默认放入后端
                backend_files.append(file_info)

        logger.info(
            f"Filtered files: {len(backend_files)} backend, {len(frontend_files)} frontend"
        )

        return {
            "backend_files": backend_files,
            "frontend_files": frontend_files,
            "backend_count": len(backend_files),
            "frontend_count": len(frontend_files)
        }

    @staticmethod
    def get_changed_file_paths(files: List[Dict[str, Any]]) -> List[str]:
        """获取变更文件路径列表"""
        return [f["path"] for f in files]

    @staticmethod
    def get_diff_summary(files: List[Dict[str, Any]]) -> str:
        """获取diff摘要"""
        summary_parts = []
        for file_info in files:
            path = file_info["path"]
            additions = len(file_info["additions"])
            deletions = len(file_info["deletions"])
            summary_parts.append(f"{path}: +{additions} -{deletions}")

        return "\n".join(summary_parts)
```

- [ ] **Step 2: 验证Diff解析**

```bash
cd /Users/sunbingyan/11学习/python/ai_diff/backend
python -c "
from app.services.diff_parser import DiffParser
from app.services.mock_data import MockDataService

diff = MockDataService.get_mock_diff()
files = DiffParser.parse_diff(diff)
print(f'Parsed {len(files)} files')
for f in files:
    print(f'  - {f[\"path\"]}')"
```

Expected: 输出解析的文件列表

---

## Task 7: AI分析服务

**Files:**
- Create: `backend/app/services/ai_analyzer.py`

- [ ] **Step 1: 创建AI分析服务**

```python
# backend/app/services/ai_analyzer.py
import json
import asyncio
from typing import Dict, Any, List, Optional
from anthropic import Anthropic
from ..config import settings
from ..utils.logger import get_logger
from ..utils.prompt_builder import build_analyze_prompt, build_context_selection_prompt
from .mock_data import MockDataService

logger = get_logger(__name__)


class AIAnalyzer:
    """AI分析器"""

    def __init__(self):
        self.client = None
        self.model = settings.CLAUDE_MODEL
        self.timeout = settings.SINGLE_CALL_TIMEOUT
        self._use_mock = False

        # 初始化Claude客户端
        if settings.CLAUDE_API_KEY and settings.CLAUDE_API_KEY != "your_claude_api_key":
            self.client = Anthropic(api_key=settings.CLAUDE_API_KEY)
            logger.info(f"AI Analyzer initialized with model: {self.model}")
        else:
            self._use_mock = True
            logger.warning("Claude API key not configured, using mock mode")

    def analyze(self, requirement_doc: str, code_diff: str) -> Dict[str, Any]:
        """
        执行代码分析

        Args:
            requirement_doc: 需求文档
            code_diff: 代码diff

        Returns:
            分析结果
        """
        if self._use_mock:
            logger.info("Using mock analysis result")
            return MockDataService.get_mock_analysis_result()

        try:
            logger.info("Starting AI analysis")
            prompt = build_analyze_prompt(requirement_doc, code_diff)

            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # 解析响应
            content = response.content[0].text
            logger.info(f"AI response received, length: {len(content)}")

            # 提取JSON
            result = self._extract_json(content)
            return result

        except Exception as e:
            logger.error(f"AI analysis failed: {str(e)}")
            raise

    def select_context_files(
        self,
        changed_files: List[str],
        diff: str
    ) -> List[str]:
        """
        选择需要的上下文文件

        Args:
            changed_files: 变更文件列表
            diff: 代码diff

        Returns:
            需要读取的文件列表
        """
        if self._use_mock:
            return []

        try:
            prompt = build_context_selection_prompt(changed_files, diff)

            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            content = response.content[0].text
            result = self._extract_json(content)

            return result.get("required_files", [])[:settings.MAX_CONTEXT_FILES]

        except Exception as e:
            logger.warning(f"Context selection failed: {str(e)}")
            return []

    def _extract_json(self, content: str) -> Dict[str, Any]:
        """
        从响应中提取JSON

        Args:
            content: 响应内容

        Returns:
            解析后的字典
        """
        # 尝试直接解析
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # 尝试提取代码块中的JSON
        import re
        json_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
        matches = re.findall(json_pattern, content)

        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

        # 尝试查找JSON对象
        brace_pattern = r'\{[\s\S]*\}'
        match = re.search(brace_pattern, content)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        logger.error(f"Failed to extract JSON from response")
        return {}


# 全局实例
analyzer = AIAnalyzer()
```

- [ ] **Step 2: 验证AI分析器**

```bash
cd /Users/sunbingyan/11学习/python/ai_diff/backend
python -c "
from app.services.ai_analyzer import AIAnalyzer
analyzer = AIAnalyzer()
print(f'Using mock mode: {analyzer._use_mock}')
"
```

Expected: 输出是否使用Mock模式

---

## Task 8: Jira服务

**Files:**
- Create: `backend/app/services/jira_service.py`

- [ ] **Step 1: 创建Jira服务**

```python
# backend/app/services/jira_service.py
from typing import Optional
import httpx
from ..config import settings
from ..utils.logger import get_logger
from .mock_data import MockDataService

logger = get_logger(__name__)


class JiraService:
    """Jira服务"""

    def __init__(self):
        self.base_url = settings.JIRA_BASE_URL
        self.email = settings.JIRA_EMAIL
        self.api_token = settings.JIRA_API_TOKEN
        self._use_mock = False

        # 检查配置
        if not all([self.base_url, self.email, self.api_token]):
            self._use_mock = True
            logger.warning("Jira not configured, using mock mode")
        else:
            logger.info(f"Jira service initialized: {self.base_url}")

    def get_issue(self, issue_key: str) -> Optional[dict]:
        """
        获取Jira Issue

        Args:
            issue_key: Issue编号

        Returns:
            Issue数据
        """
        if self._use_mock:
            return self._get_mock_issue(issue_key)

        try:
            url = f"{self.base_url}/rest/api/2/issue/{issue_key}"
            auth = (self.email, self.api_token)

            with httpx.Client() as client:
                response = client.get(url, auth=auth, timeout=30)
                response.raise_for_status()

                return response.json()

        except Exception as e:
            logger.error(f"Failed to get Jira issue {issue_key}: {str(e)}")
            return None

    def get_requirement_doc(self, issue_key: str) -> str:
        """
        获取需求文档内容

        Args:
            issue_key: Issue编号

        Returns:
            需求文档
        """
        if self._use_mock:
            return MockDataService.get_mock_requirement(issue_key)

        issue = self.get_issue(issue_key)
        if not issue:
            logger.warning(f"Issue {issue_key} not found, using mock")
            return MockDataService.get_mock_requirement(issue_key)

        # 提取需求内容
        fields = issue.get("fields", {})

        # 获取描述
        description = fields.get("description", "")

        # 获取标题
        summary = fields.get("summary", "")

        # 获取子任务
        subtasks = fields.get("subtasks", [])
        subtask_contents = []
        for subtask in subtasks:
            subtask_key = subtask.get("key", "")
            subtask_summary = subtask.get("fields", {}).get("summary", "")
            subtask_contents.append(f"- {subtask_key}: {subtask_summary}")

        # 组合需求文档
        doc_parts = [f"# {summary}"]
        if description:
            doc_parts.append(f"\n## 描述\n{description}")
        if subtask_contents:
            doc_parts.append(f"\n## 子任务\n" + "\n".join(subtask_contents))

        return "\n".join(doc_parts)

    def _get_mock_issue(self, issue_key: str) -> dict:
        """获取Mock Issue数据"""
        return {
            "key": issue_key,
            "fields": {
                "summary": f"需求: {issue_key}",
                "description": MockDataService.get_mock_requirement(issue_key),
                "status": {"name": "In Progress"},
                "subtasks": []
            }
        }


# 全局实例
jira_service = JiraService()
```

- [ ] **Step 2: 验证Jira服务**

```bash
cd /Users/sunbingyan/11学习/python/ai_diff/backend
python -c "
from app.services.jira_service import JiraService
service = JiraService()
doc = service.get_requirement_doc('PROJ-123')
print(f'Requirement doc length: {len(doc)}')
"
```

Expected: 输出需求文档长度

---

## Task 9: FastAPI主应用和认证

**Files:**
- Create: `backend/app/auth.py`
- Create: `backend/app/main.py`

- [ ] **Step 1: 创建认证模块 auth.py**

```python
# backend/app/auth.py
from fastapi import Header, HTTPException
from typing import Optional
from .config import settings
from .utils.logger import get_logger

logger = get_logger(__name__)


async def verify_token(x_auth_token: Optional[str] = Header(None)) -> str:
    """
    验证Token

    Args:
        x_auth_token: 请求头中的Token

    Returns:
        验证通过的Token

    Raises:
        HTTPException: Token无效
    """
    if not x_auth_token:
        raise HTTPException(
            status_code=401,
            detail="Missing authentication token"
        )

    if x_auth_token != settings.AUTH_TOKEN:
        logger.warning(f"Invalid token attempt: {x_auth_token[:10]}...")
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token"
        )

    return x_auth_token


async def verify_op_token(x_op_token: Optional[str] = Header(None)) -> str:
    """
    验证OP平台Token

    Args:
        x_op_token: OP平台Token

    Returns:
        验证通过的Token
    """
    if not x_op_token:
        raise HTTPException(
            status_code=401,
            detail="Missing OP token"
        )

    # Demo阶段使用相同的Token
    if x_op_token != settings.AUTH_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="Invalid OP token"
        )

    return x_op_token
```

- [ ] **Step 2: 创建主应用 main.py**

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .config import settings
from .database import engine, Base
from .utils.logger import get_logger
from .api import analyze, report, webhook

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    # 启动时
    logger.info("Starting CR Platform...")
    logger.info(f"Database: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")

    # 创建数据库表
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created")
    except Exception as e:
        logger.error(f"Failed to create database tables: {str(e)}")

    yield

    # 关闭时
    logger.info("Shutting down CR Platform...")


# 创建应用
app = FastAPI(
    title="CR代码分析平台",
    description="代码CR分析平台API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(analyze.router, prefix="/api", tags=["分析"])
app.include_router(report.router, prefix="/api", tags=["报告"])
app.include_router(webhook.router, prefix="/api/webhook", tags=["Webhook"])


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "CR代码分析平台",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}
```

- [ ] **Step 3: 验证应用启动**

```bash
cd /Users/sunbingyan/11学习/python/ai_diff/backend
# 先创建空的API路由文件
touch app/api/analyze.py app/api/report.py app/api/webhook.py
python -c "from app.main import app; print(f'App created: {app.title}')"
```

Expected: 输出应用标题

---

## Task 10: 分析API实现

**Files:**
- Create: `backend/app/api/analyze.py`

- [ ] **Step 1: 创建分析API**

```python
# backend/app/api/analyze.py
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..auth import verify_token
from ..models import AnalysisTask, TaskStatus, AnalysisReport
from ..schemas.request import AnalyzeRequest
from ..schemas.response import (
    Response, AnalyzeResponse, TaskResponse, HistoryItem
)
from ..utils.logger import get_logger
from ..utils.jira_parser import extract_jira_key
from ..services.jira_service import jira_service
from ..services.diff_parser import DiffParser
from ..services.ai_analyzer import analyzer
from ..services.mock_data import MockDataService
from ..config import settings

logger = get_logger(__name__)
router = APIRouter()


def run_analysis(task_id: int, release_no: str, jira_key: str, diff_content: str):
    """
    执行分析任务（后台任务）

    Args:
        task_id: 任务ID
        release_no: 上线单号
        jira_key: Jira单号
        diff_content: diff内容
    """
    from ..database import SessionLocal

    db = SessionLocal()
    try:
        # 更新任务状态
        task = db.query(AnalysisTask).filter(AnalysisTask.id == task_id).first()
        if not task:
            logger.error(f"Task {task_id} not found")
            return

        task.status = TaskStatus.ANALYZING
        db.commit()
        logger.info(f"Task {task_id}: Starting analysis for {release_no}")

        # 1. 获取需求文档
        requirement_doc = jira_service.get_requirement_doc(jira_key)
        logger.info(f"Task {task_id}: Got requirement doc, length={len(requirement_doc)}")

        # 2. 解析diff
        files = DiffParser.parse_diff(diff_content)
        filtered = DiffParser.filter_files(files)
        backend_files = filtered["backend_files"]

        logger.info(f"Task {task_id}: Parsed {len(files)} files, {len(backend_files)} backend")

        # 3. 构建分析diff
        analysis_diff = "\n".join([f["diff"] for f in backend_files])

        # 4. AI分析
        analysis_result = analyzer.analyze(requirement_doc, analysis_diff)
        logger.info(f"Task {task_id}: AI analysis completed")

        # 5. 创建报告
        report = AnalysisReport(
            task_id=task_id,
            requirement_coverage=analysis_result.get("coverage_percent", 0),
            manual_coverage=analysis_result.get("coverage_percent", 0),
            total_requirements=len(analysis_result.get("requirements", [])),
            covered_requirements=sum(
                1 for r in analysis_result.get("requirements", [])
                if r.get("status") == "covered"
            ),
            irrelevant_requirements=0,
            requirement_details=analysis_result.get("requirements", []),
            extra_code_issues=[
                i for i in analysis_result.get("issues", [])
                if i.get("type") == "extra_code"
            ],
            syntax_errors=[
                i for i in analysis_result.get("issues", [])
                if i.get("type") == "syntax"
            ],
            boundary_issues=[
                i for i in analysis_result.get("issues", [])
                if i.get("type") == "boundary"
            ],
            exception_issues=[
                i for i in analysis_result.get("issues", [])
                if i.get("type") == "exception"
            ],
            quality_issues=[
                i for i in analysis_result.get("issues", [])
                if i.get("type") == "quality"
            ],
            total_issues=len(analysis_result.get("issues", [])),
            summary=analysis_result.get("summary", ""),
            backend_file_count=filtered["backend_count"],
            frontend_file_count=filtered["frontend_count"]
        )
        db.add(report)

        # 更新任务状态
        task.status = TaskStatus.SUCCESS
        db.commit()
        logger.info(f"Task {task_id}: Analysis completed successfully")

    except Exception as e:
        logger.error(f"Task {task_id}: Analysis failed - {str(e)}")
        task = db.query(AnalysisTask).filter(AnalysisTask.id == task_id).first()
        if task:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            db.commit()

    finally:
        db.close()


@router.post("/analyze", response_model=Response)
async def create_analysis(
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    token: str = Depends(verify_token)
):
    """
    提交分析任务
    """
    logger.info(f"Received analysis request: {request.release_no}")

    # 解析Jira单号
    jira_key = extract_jira_key(request.release_no)
    if not jira_key:
        raise HTTPException(
            status_code=400,
            detail="无法从上线单号中提取Jira单号"
        )

    # 检查是否已存在
    existing = db.query(AnalysisTask).filter(
        AnalysisTask.release_no == request.release_no
    ).first()

    if existing:
        logger.info(f"Task already exists: {existing.id}")
        return Response(
            data=AnalyzeResponse(
                task_id=existing.id,
                report_url=f"{settings.FRONTEND_URL}/report/{existing.id}",
                status=existing.status.value
            )
        )

    # 创建任务
    task = AnalysisTask(
        release_no=request.release_no,
        jira_key=jira_key,
        status=TaskStatus.PENDING
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    logger.info(f"Created task: {task.id}")

    # 获取Mock diff
    diff_content = MockDataService.get_mock_diff()

    # 启动后台任务
    background_tasks.add_task(
        run_analysis,
        task.id,
        request.release_no,
        jira_key,
        diff_content
    )

    return Response(
        data=AnalyzeResponse(
            task_id=task.id,
            report_url=f"{settings.FRONTEND_URL}/report/{task.id}",
            status=task.status.value
        )
    )


@router.get("/task/{task_id}", response_model=Response)
async def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    token: str = Depends(verify_token)
):
    """
    查询任务状态
    """
    task = db.query(AnalysisTask).filter(AnalysisTask.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    progress_map = {
        TaskStatus.PENDING: "等待分析...",
        TaskStatus.ANALYZING: "正在分析代码...",
        TaskStatus.SUCCESS: "分析完成",
        TaskStatus.FAILED: "分析失败"
    }

    return Response(
        data=TaskResponse(
            task_id=task.id,
            release_no=task.release_no,
            jira_key=task.jira_key,
            status=task.status.value,
            progress=progress_map.get(task.status),
            created_at=task.created_at.strftime("%Y-%m-%d %H:%M:%S")
        )
    )


@router.get("/history", response_model=Response)
async def get_history(
    limit: int = 20,
    db: Session = Depends(get_db),
    token: str = Depends(verify_token)
):
    """
    获取历史记录
    """
    tasks = db.query(AnalysisTask).order_by(
        AnalysisTask.created_at.desc()
    ).limit(limit).all()

    history = []
    for task in tasks:
        report = db.query(AnalysisReport).filter(
            AnalysisReport.task_id == task.id
        ).first()

        history.append(HistoryItem(
            task_id=task.id,
            release_no=task.release_no,
            status=task.status.value,
            coverage=float(report.requirement_coverage) if report else None,
            created_at=task.created_at.strftime("%Y-%m-%d %H:%M:%S")
        ))

    return Response(data=history)
```

- [ ] **Step 2: 验证API路由**

```bash
cd /Users/sunbingyan/11学习/python/ai_diff/backend
python -c "from app.api.analyze import router; print(f'Routes: {[r.path for r in router.routes]}')"
```

Expected: 输出路由列表

---

## Task 11: 报告API实现

**Files:**
- Create: `backend/app/api/report.py`

- [ ] **Step 1: 创建报告API**

```python
# backend/app/api/report.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..auth import verify_token
from ..models import AnalysisTask, AnalysisReport, ManualMark
from ..schemas.request import MarkRequest
from ..schemas.response import (
    Response, ReportResponse, CoverageInfo,
    RequirementItem, IssueItem, MarkResponse
)
from ..utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/report/{task_id}", response_model=Response)
async def get_report(
    task_id: int,
    db: Session = Depends(get_db),
    token: str = Depends(verify_token)
):
    """
    获取分析报告
    """
    # 查询任务
    task = db.query(AnalysisTask).filter(AnalysisTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 查询报告
    report = db.query(AnalysisReport).filter(
        AnalysisReport.task_id == task_id
    ).first()

    if not report:
        return Response(
            data={
                "task_id": task_id,
                "release_no": task.release_no,
                "status": task.status.value,
                "message": "报告生成中..."
            }
        )

    # 查询人工标记
    marks = db.query(ManualMark).filter(
        ManualMark.report_id == report.id
    ).all()
    mark_map = {f"{m.item_type}_{m.item_id}": m for m in marks}

    # 构建需求列表
    requirements = []
    for req in (report.requirement_details or []):
        item_id = req.get("id", "")
        mark_key = f"requirement_{item_id}"
        mark = mark_map.get(mark_key)

        requirements.append(RequirementItem(
            id=item_id,
            content=req.get("content", ""),
            status=req.get("status", "unknown"),
            confidence=req.get("confidence", 0),
            related_files=req.get("related_files", []),
            related_lines=req.get("related_lines", []),
            marked_status=mark.marked_status if mark else None
        ))

    # 构建问题列表
    issues = []
    all_issues = (
        (report.extra_code_issues or []) +
        (report.syntax_errors or []) +
        (report.boundary_issues or []) +
        (report.exception_issues or []) +
        (report.quality_issues or [])
    )

    for issue in all_issues:
        item_id = issue.get("id", "")
        mark_key = f"issue_{item_id}"
        mark = mark_map.get(mark_key)

        issues.append(IssueItem(
            id=item_id,
            type=issue.get("type", "unknown"),
            severity=issue.get("severity", "info"),
            description=issue.get("description", ""),
            file=issue.get("file"),
            lines=issue.get("lines"),
            suggestion=issue.get("suggestion"),
            marked_status=mark.marked_status if mark else None
        ))

    # 构建响应
    return Response(
        data=ReportResponse(
            task_id=task_id,
            release_no=task.release_no,
            jira_key=task.jira_key,
            status=task.status.value,
            coverage=CoverageInfo(
                total=float(report.requirement_coverage or 0),
                manual_coverage=float(report.manual_coverage or 0),
                total_requirements=report.total_requirements,
                covered_requirements=report.covered_requirements,
                irrelevant_requirements=report.irrelevant_requirements
            ),
            file_stats={
                "backend": report.backend_file_count,
                "frontend": report.frontend_file_count
            },
            requirements=requirements,
            issues=issues,
            summary=report.summary
        )
    )


@router.post("/report/{task_id}/mark", response_model=Response)
async def create_mark(
    task_id: int,
    request: MarkRequest,
    db: Session = Depends(get_db),
    token: str = Depends(verify_token)
):
    """
    人工标记
    """
    # 查询报告
    report = db.query(AnalysisReport).filter(
        AnalysisReport.task_id == task_id
    ).first()

    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")

    # 查找原始状态
    original_status = None

    if request.item_type == "requirement":
        for req in (report.requirement_details or []):
            if req.get("id") == request.item_id:
                original_status = req.get("status")
                break
    else:
        all_issues = (
            (report.extra_code_issues or []) +
            (report.syntax_errors or []) +
            (report.boundary_issues or []) +
            (report.exception_issues or []) +
            (report.quality_issues or [])
        )
        for issue in all_issues:
            if issue.get("id") == request.item_id:
                original_status = issue.get("severity")
                break

    # 创建或更新标记
    existing_mark = db.query(ManualMark).filter(
        ManualMark.report_id == report.id,
        ManualMark.item_type == request.item_type,
        ManualMark.item_id == request.item_id
    ).first()

    if existing_mark:
        existing_mark.marked_status = request.marked_status
        existing_mark.remark = request.remark
    else:
        mark = ManualMark(
            report_id=report.id,
            item_type=request.item_type,
            item_id=request.item_id,
            original_status=original_status,
            marked_status=request.marked_status,
            remark=request.remark
        )
        db.add(mark)

    db.commit()

    # 重新计算覆盖率
    new_coverage = calculate_manual_coverage(db, report)
    report.manual_coverage = new_coverage

    # 更新无关需求数
    irrelevant_count = db.query(ManualMark).filter(
        ManualMark.report_id == report.id,
        ManualMark.item_type == "requirement",
        ManualMark.marked_status == "irrelevant"
    ).count()
    report.irrelevant_requirements = irrelevant_count

    db.commit()

    logger.info(f"Mark created: {request.item_type}_{request.item_id} -> {request.marked_status}")

    return Response(data=MarkResponse(new_coverage=float(new_coverage)))


def calculate_manual_coverage(db: Session, report: AnalysisReport) -> float:
    """
    计算人工修正后的覆盖率
    """
    requirements = report.requirement_details or []
    marks = db.query(ManualMark).filter(
        ManualMark.report_id == report.id,
        ManualMark.item_type == "requirement"
    ).all()

    mark_map = {m.item_id: m for m in marks}

    total = len(requirements)
    covered = 0
    irrelevant = 0

    for req in requirements:
        req_id = req.get("id", "")
        status = req.get("status")

        # 检查是否有人工标记
        mark = mark_map.get(req_id)
        if mark:
            if mark.marked_status == "irrelevant":
                irrelevant += 1
                continue
            status = mark.marked_status

        if status == "covered":
            covered += 1

    effective_total = total - irrelevant
    if effective_total <= 0:
        return 0.0

    return round(covered / effective_total * 100, 2)
```

- [ ] **Step 2: 验证报告API**

```bash
cd /Users/sunbingyan/11学习/python/ai_diff/backend
python -c "from app.api.report import router; print(f'Routes: {[r.path for r in router.routes]}')"
```

Expected: 输出路由列表

---

## Task 12: Webhook API实现

**Files:**
- Create: `backend/app/api/webhook.py`

- [ ] **Step 1: 创建Webhook API**

```python
# backend/app/api/webhook.py
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..auth import verify_op_token
from ..models import AnalysisTask, TaskStatus
from ..schemas.request import WebhookRequest
from ..schemas.response import Response, AnalyzeResponse
from ..utils.logger import get_logger
from ..utils.jira_parser import extract_jira_key
from ..config import settings

logger = get_logger(__name__)
router = APIRouter()


def run_analysis_from_webhook(
    task_id: int,
    release_no: str,
    jira_key: str,
    diff_content: str
):
    """从webhook执行分析"""
    # 复用analyze.py中的逻辑
    from .analyze import run_analysis
    run_analysis(task_id, release_no, jira_key, diff_content)


@router.post("/op", response_model=Response)
async def op_webhook(
    request: WebhookRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    x_op_token: str = Depends(verify_op_token)
):
    """
    OP平台推送接口
    """
    logger.info(f"Received OP webhook: {request.release_no}")

    # 解析Jira单号
    jira_key = extract_jira_key(request.release_no)
    if not jira_key:
        raise HTTPException(
            status_code=400,
            detail="无法从上线单号中提取Jira单号"
        )

    # 检查是否已存在
    existing = db.query(AnalysisTask).filter(
        AnalysisTask.release_no == request.release_no
    ).first()

    if existing:
        logger.info(f"Task already exists: {existing.id}")
        return Response(
            data=AnalyzeResponse(
                task_id=existing.id,
                report_url=f"{settings.FRONTEND_URL}/report/{existing.id}",
                status=existing.status.value
            )
        )

    # 创建任务
    task = AnalysisTask(
        release_no=request.release_no,
        jira_key=jira_key,
        status=TaskStatus.PENDING
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    logger.info(f"Created task from webhook: {task.id}")

    # 启动后台任务
    background_tasks.add_task(
        run_analysis_from_webhook,
        task.id,
        request.release_no,
        jira_key,
        request.diff
    )

    return Response(
        data=AnalyzeResponse(
            task_id=task.id,
            report_url=f"{settings.FRONTEND_URL}/report/{task.id}",
            status=task.status.value
        )
    )
```

- [ ] **Step 2: 验证Webhook API**

```bash
cd /Users/sunbingyan/11学习/python/ai_diff/backend
python -c "from app.api.webhook import router; print(f'Routes: {[r.path for r in router.routes]}')"
```

Expected: 输出路由列表

---

## Task 13: 后端启动测试

**Files:**
- Create: `backend/.env` (从.env.example复制)

- [ ] **Step 1: 创建.env文件**

```bash
cd /Users/sunbingyan/11学习/python/ai_diff/backend
cp .env.example .env
# 编辑.env设置数据库连接信息
```

- [ ] **Step 2: 启动后端服务**

```bash
cd /Users/sunbingyan/11学习/python/ai_diff/backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Expected: 服务启动成功，访问 http://localhost:8000 可以看到API信息

- [ ] **Step 3: 测试API**

```bash
# 健康检查
curl http://localhost:8000/health

# 提交分析任务 (需要Token)
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -H "X-Auth-Token: demo-token" \
  -d '{"release_no": "REL-20240517-PROJ-123"}'
```

Expected: 返回任务ID和报告URL

---

## Task 14: 前端项目初始化

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.js`
- Create: `frontend/index.html`

- [ ] **Step 1: 创建前端项目**

```bash
cd /Users/sunbingyan/11学习/python/ai_diff
npm create vite@latest frontend -- --template vue
cd frontend
npm install
npm install element-plus axios vue-router
```

- [ ] **Step 2: 配置 vite.config.js**

```javascript
// frontend/vite.config.js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
```

- [ ] **Step 3: 验证前端启动**

```bash
cd /Users/sunbingyan/11学习/python/ai_diff/frontend
npm run dev
```

Expected: 前端服务启动成功，访问 http://localhost:5173

---

## Task 15: 前端API封装和路由

**Files:**
- Create: `frontend/src/api/index.js`
- Create: `frontend/src/router/index.js`

- [ ] **Step 1: 创建API封装**

```javascript
// frontend/src/api/index.js
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

// 请求拦截器
api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token') || 'demo-token'
    config.headers['X-Auth-Token'] = token
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

// API方法
export default {
  // 提交分析
  analyze(releaseNo) {
    return api.post('/analyze', { release_no: releaseNo })
  },

  // 获取任务状态
  getTask(taskId) {
    return api.get(`/task/${taskId}`)
  },

  // 获取报告
  getReport(taskId) {
    return api.get(`/report/${taskId}`)
  },

  // 人工标记
  mark(taskId, data) {
    return api.post(`/report/${taskId}/mark`, data)
  },

  // 获取历史
  getHistory(limit = 20) {
    return api.get('/history', { params: { limit } })
  },

  // OP Webhook
  webhook(data) {
    return api.post('/webhook/op', data, {
      headers: { 'X-OP-Token': 'demo-token' }
    })
  }
}
```

- [ ] **Step 2: 创建路由配置**

```javascript
// frontend/src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Report from '../views/Report.vue'
import History from '../views/History.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/report/:id',
    name: 'Report',
    component: Report
  },
  {
    path: '/history',
    name: 'History',
    component: History
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
```

- [ ] **Step 3: 更新 main.js**

```javascript
// frontend/src/main.js
import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import router from './router'

const app = createApp(App)
app.use(ElementPlus)
app.use(router)
app.mount('#app')
```

---

## Task 16: 前端页面实现

**Files:**
- Create: `frontend/src/App.vue`
- Create: `frontend/src/views/Home.vue`
- Create: `frontend/src/views/Report.vue`
- Create: `frontend/src/views/History.vue`

- [ ] **Step 1: 创建App.vue**

```vue
<!-- frontend/src/App.vue -->
<template>
  <div id="app">
    <el-container>
      <el-header>
        <div class="header-content">
          <h1>CR代码分析平台</h1>
          <el-menu mode="horizontal" :ellipsis="false" router>
            <el-menu-item index="/">首页</el-menu-item>
            <el-menu-item index="/history">历史记录</el-menu-item>
          </el-menu>
        </div>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
</script>

<style>
#app {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  min-height: 100vh;
  background: #f5f7fa;
}

.el-header {
  background: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  padding: 0 20px;
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: 1200px;
  margin: 0 auto;
}

.header-content h1 {
  font-size: 20px;
  color: #409eff;
  margin: 0;
}

.el-main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}
</style>
```

- [ ] **Step 2: 创建首页 Home.vue**

```vue
<!-- frontend/src/views/Home.vue -->
<template>
  <div class="home">
    <el-card class="analyze-card">
      <template #header>
        <span>代码分析</span>
      </template>
      <el-form @submit.prevent="handleAnalyze">
        <el-form-item label="上线单号">
          <el-input
            v-model="releaseNo"
            placeholder="请输入上线单号，如 REL-20240517-PROJ-123"
            clearable
          >
            <template #append>
              <el-button type="primary" @click="handleAnalyze" :loading="loading">
                开始分析
              </el-button>
            </template>
          </el-input>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="history-card" v-if="recentTasks.length > 0">
      <template #header>
        <span>最近分析</span>
      </template>
      <el-table :data="recentTasks" style="width: 100%">
        <el-table-column prop="release_no" label="上线单号" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="coverage" label="覆盖率" width="100">
          <template #default="{ row }">
            <span v-if="row.coverage">{{ row.coverage }}%</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="180" />
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button type="primary" link @click="viewReport(row.task_id)">
              查看
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'
import { ElMessage } from 'element-plus'

const router = useRouter()
const releaseNo = ref('')
const loading = ref(false)
const recentTasks = ref([])

const getStatusType = (status) => {
  const types = {
    pending: 'info',
    analyzing: 'warning',
    success: 'success',
    failed: 'danger'
  }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = {
    pending: '等待中',
    analyzing: '分析中',
    success: '成功',
    failed: '失败'
  }
  return texts[status] || status
}

const handleAnalyze = async () => {
  if (!releaseNo.value.trim()) {
    ElMessage.warning('请输入上线单号')
    return
  }

  loading.value = true
  try {
    const res = await api.analyze(releaseNo.value.trim())
    if (res.code === 0) {
      ElMessage.success('任务已创建')
      router.push(`/report/${res.data.task_id}`)
    } else {
      ElMessage.error(res.message || '创建失败')
    }
  } catch (error) {
    ElMessage.error('请求失败')
  } finally {
    loading.value = false
  }
}

const loadHistory = async () => {
  try {
    const res = await api.getHistory(5)
    if (res.code === 0) {
      recentTasks.value = res.data
    }
  } catch (error) {
    console.error('Load history failed:', error)
  }
}

const viewReport = (taskId) => {
  router.push(`/report/${taskId}`)
}

onMounted(() => {
  loadHistory()
})
</script>

<style scoped>
.home {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.analyze-card, .history-card {
  margin-bottom: 20px;
}
</style>
```

- [ ] **Step 3: 创建报告页 Report.vue**

```vue
<!-- frontend/src/views/Report.vue -->
<template>
  <div class="report" v-loading="loading">
    <template v-if="report">
      <!-- 覆盖率卡片 -->
      <el-card class="coverage-card">
        <div class="coverage-header">
          <div class="coverage-info">
            <h3>需求覆盖率</h3>
            <div class="coverage-value">
              <span class="percent">{{ report.coverage?.manual_coverage || report.coverage?.total || 0 }}</span>
              <span class="unit">%</span>
            </div>
          </div>
          <el-progress
            type="dashboard"
            :percentage="report.coverage?.manual_coverage || report.coverage?.total || 0"
            :width="120"
          />
        </div>
        <div class="coverage-stats">
          <span>已覆盖: {{ report.coverage?.covered_requirements || 0 }}</span>
          <span>未覆盖: {{ (report.coverage?.total_requirements || 0) - (report.coverage?.covered_requirements || 0) - (report.coverage?.irrelevant_requirements || 0) }}</span>
          <span>无关: {{ report.coverage?.irrelevant_requirements || 0 }}</span>
        </div>
      </el-card>

      <!-- 文件统计 -->
      <el-card class="file-stats-card">
        <template #header>
          <span>文件变更统计</span>
        </template>
        <div class="file-stats">
          <el-tag type="success">后端文件: {{ report.file_stats?.backend || 0 }} 个 (已分析)</el-tag>
          <el-tag type="info">前端文件: {{ report.file_stats?.frontend || 0 }} 个 (暂未分析)</el-tag>
        </div>
      </el-card>

      <!-- 需求覆盖详情 -->
      <el-card class="requirements-card">
        <template #header>
          <span>需求覆盖详情</span>
        </template>
        <el-table :data="report.requirements" style="width: 100%">
          <el-table-column label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="row.status === 'covered' ? 'success' : 'warning'" size="small">
                {{ row.status === 'covered' ? '已覆盖' : '未覆盖' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="content" label="需求描述" />
          <el-table-column label="相关文件" width="200">
            <template #default="{ row }">
              <span v-if="row.related_files?.length">{{ row.related_files.join(', ') }}</span>
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200">
            <template #default="{ row }">
              <template v-if="row.status === 'covered'">
                <el-button size="small" @click="markItem('requirement', row.id, 'uncovered')">
                  标记未覆盖
                </el-button>
              </template>
              <template v-else>
                <el-button size="small" type="primary" @click="markItem('requirement', row.id, 'covered')">
                  已实现
                </el-button>
                <el-button size="small" @click="markItem('requirement', row.id, 'irrelevant')">
                  无关
                </el-button>
              </template>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 发现问题 -->
      <el-card class="issues-card">
        <template #header>
          <span>发现问题 ({{ report.issues?.length || 0 }})</span>
        </template>
        <el-table :data="report.issues" style="width: 100%">
          <el-table-column label="级别" width="80">
            <template #default="{ row }">
              <el-tag :type="getSeverityType(row.severity)" size="small">
                {{ row.severity }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="类型" width="100">
            <template #default="{ row }">
              {{ getIssueTypeText(row.type) }}
            </template>
          </el-table-column>
          <el-table-column prop="description" label="问题描述" />
          <el-table-column prop="file" label="文件" width="180" />
          <el-table-column label="操作" width="160">
            <template #default="{ row }">
              <el-button size="small" @click="markItem('issue', row.id, 'false_positive')">
                误报
              </el-button>
              <el-button size="small" type="primary" @click="markItem('issue', row.id, 'confirmed')">
                确认
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 分析总结 -->
      <el-card class="summary-card" v-if="report.summary">
        <template #header>
          <span>分析总结</span>
        </template>
        <p>{{ report.summary }}</p>
      </el-card>
    </template>

    <el-empty v-else-if="!loading" description="报告不存在或未生成" />
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api'
import { ElMessage } from 'element-plus'

const route = useRoute()
const loading = ref(true)
const report = ref(null)
const taskId = computed(() => route.params.id)

const getSeverityType = (severity) => {
  const types = {
    error: 'danger',
    warning: 'warning',
    info: 'info'
  }
  return types[severity] || 'info'
}

const getIssueTypeText = (type) => {
  const texts = {
    extra_code: '夹带',
    syntax: '语法',
    boundary: '边界',
    exception: '兜底',
    quality: '质量'
  }
  return texts[type] || type
}

const loadReport = async () => {
  loading.value = true
  try {
    const res = await api.getReport(taskId.value)
    if (res.code === 0) {
      report.value = res.data
    } else {
      ElMessage.error(res.message || '获取报告失败')
    }
  } catch (error) {
    ElMessage.error('请求失败')
  } finally {
    loading.value = false
  }
}

const markItem = async (itemType, itemId, markedStatus) => {
  try {
    const res = await api.mark(taskId.value, {
      item_type: itemType,
      item_id: itemId,
      marked_status: markedStatus
    })
    if (res.code === 0) {
      ElMessage.success('标记成功')
      loadReport()
    } else {
      ElMessage.error(res.message || '标记失败')
    }
  } catch (error) {
    ElMessage.error('请求失败')
  }
}

onMounted(() => {
  loadReport()
})
</script>

<style scoped>
.report {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.coverage-card {
  margin-bottom: 20px;
}

.coverage-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.coverage-info h3 {
  margin: 0 0 10px 0;
  color: #606266;
}

.coverage-value {
  display: flex;
  align-items: baseline;
}

.coverage-value .percent {
  font-size: 48px;
  font-weight: bold;
  color: #409eff;
}

.coverage-value .unit {
  font-size: 20px;
  color: #909399;
  margin-left: 4px;
}

.coverage-stats {
  margin-top: 20px;
  display: flex;
  gap: 30px;
  color: #606266;
}

.file-stats-card {
  margin-bottom: 20px;
}

.file-stats {
  display: flex;
  gap: 15px;
}

.requirements-card,
.issues-card,
.summary-card {
  margin-bottom: 20px;
}
</style>
```

- [ ] **Step 4: 创建历史记录页 History.vue**

```vue
<!-- frontend/src/views/History.vue -->
<template>
  <div class="history">
    <el-card>
      <template #header>
        <span>历史记录</span>
      </template>
      <el-table :data="tasks" style="width: 100%" v-loading="loading">
        <el-table-column prop="release_no" label="上线单号" />
        <el-table-column label="Jira单号" width="120">
          <template #default="{ row }">
            {{ row.release_no.match(/[A-Z]+-\d+/)?.[0] || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="覆盖率" width="100">
          <template #default="{ row }">
            <span v-if="row.coverage">{{ row.coverage }}%</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button type="primary" link @click="viewReport(row.task_id)">
              查看报告
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'

const router = useRouter()
const tasks = ref([])
const loading = ref(true)

const getStatusType = (status) => {
  const types = {
    pending: 'info',
    analyzing: 'warning',
    success: 'success',
    failed: 'danger'
  }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = {
    pending: '等待中',
    analyzing: '分析中',
    success: '成功',
    failed: '失败'
  }
  return texts[status] || status
}

const loadHistory = async () => {
  loading.value = true
  try {
    const res = await api.getHistory(50)
    if (res.code === 0) {
      tasks.value = res.data
    }
  } catch (error) {
    console.error('Load history failed:', error)
  } finally {
    loading.value = false
  }
}

const viewReport = (taskId) => {
  router.push(`/report/${taskId}`)
}

onMounted(() => {
  loadHistory()
})
</script>

<style scoped>
.history {
  padding: 20px 0;
}
</style>
```

---

## Task 17: 集成测试

- [ ] **Step 1: 启动后端服务**

```bash
cd /Users/sunbingyan/11学习/python/ai_diff/backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- [ ] **Step 2: 启动前端服务**

```bash
cd /Users/sunbingyan/11学习/python/ai_diff/frontend
npm run dev
```

- [ ] **Step 3: 完整流程测试**

1. 访问 http://localhost:5173
2. 输入上线单号 `REL-20240517-PROJ-123`
3. 点击"开始分析"
4. 等待分析完成
5. 查看报告详情
6. 测试人工标记功能

Expected: 所有功能正常工作

---

## 自检清单

| 检查项 | 状态 |
|--------|------|
| Spec覆盖 | 所有设计文档中的功能都有对应实现 |
| Placeholder扫描 | 无TBD/TODO占位符 |
| 类型一致性 | 前后端数据结构一致 |
| 配置完整 | 环境变量配置完整 |
| Mock数据 | Demo测试数据完整 |
