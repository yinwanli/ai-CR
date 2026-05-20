# CR代码分析平台设计文档

> 创建日期: 2026-05-17

## 一、项目概述

### 1.1 项目目标

开发一个代码CR（Code Review）分析平台，将需求文档和代码变更进行匹配分析，检查代码是否符合需求功能预期，并检测潜在问题。

### 1.2 核心功能

| 功能 | 说明 |
|------|------|
| 需求覆盖率分析 | 分析代码是否100%实现需求功能点 |
| 夹带检测 | 检测是否有需求之外的代码变更 |
| 语法检查 | 检查代码是否存在语法错误 |
| 边界场景分析 | 检查是否处理边界条件 |
| 异常兜底分析 | 检查是否有异常处理和容错机制 |
| 代码质量分析 | 检查命名规范、代码重复、潜在bug等 |
| 人工标记 | 支持用户纠正AI分析结果，覆盖率实时更新 |

### 1.3 项目目录

```
/Users/sunbingyan/11学习/python/ai_diff/
```

---

## 二、系统架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                           CR 分析平台                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌─────────────┐         ┌─────────────┐                          │
│   │  Vue 前端   │  HTTP   │  Python API │                          │
│   │  (Nginx)    │ ◄─────► │ (FastAPI)   │                          │
│   └─────────────┘         └──────┬──────┘                          │
│                                  │                                  │
│                    ┌─────────────┼─────────────┐                    │
│                    │             │             │                    │
│                    ▼             ▼             ▼                    │
│            ┌───────────┐  ┌───────────┐  ┌───────────┐             │
│            │Background │  │   MySQL   │  │  日志文件  │             │
│            │  Tasks    │  │  (持久化)  │  │           │             │
│            └─────┬─────┘  └───────────┘  └───────────┘             │
│                  │                                                  │
│                  ▼                                                  │
│         ┌───────────────┐                                          │
│         │  AI 分析引擎  │                                          │
│         │ (Claude API)  │                                          │
│         └───────────────┘                                          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
       ┌──────────┐    ┌──────────┐    ┌──────────┐
       │   Jira   │    │ OP平台   │    │ Git/SVN  │
       │   API    │    │ 接口对接  │    │  仓库    │
       └──────────┘    └──────────┘    └──────────┘
```

### 2.2 技术选型

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端 | Vue 3 + Element Plus | 组件库成熟，开发效率高 |
| Web服务器 | Nginx | 静态资源 + 反向代理 |
| 后端框架 | FastAPI | 异步支持好，自动生成API文档 |
| 任务处理 | BackgroundTasks | Demo阶段使用，生产可升级Celery |
| 数据库 | MySQL 8.0 | 关系型存储，事务支持 |
| AI接口 | Claude API | 可配置切换其他模型 |

### 2.3 架构演进

**Demo阶段**
```
Vue前端 ◄──► FastAPI ◄──► MySQL
                  │
                  ▼
         BackgroundTasks
                  │
                  ▼
           Claude API
```

**生产阶段**
```
Vue前端 ◄──► FastAPI ◄──► MySQL
                  │
                  ▼
           Redis (任务队列)
                  │
                  ▼
           Celery Worker
                  │
                  ▼
           Claude API
```

---

## 三、后端设计

### 3.1 目录结构

```
backend/
├── app/
│   ├── main.py                 # FastAPI 入口
│   ├── config.py               # 配置管理
│   ├── auth.py                 # 简单Token认证
│   │
│   ├── api/                    # API 路由
│   │   ├── analyze.py          # 分析接口
│   │   ├── report.py           # 报告查询接口
│   │   └── webhook.py          # OP回调接收接口
│   │
│   ├── services/               # 业务逻辑层
│   │   ├── jira_service.py     # Jira API 对接
│   │   ├── op_service.py       # OP平台对接
│   │   ├── diff_parser.py      # Git/SVN diff解析
│   │   └── ai_analyzer.py      # AI分析引擎封装
│   │
│   ├── models/                 # 数据模型
│   │   ├── task.py             # 分析任务模型
│   │   └── report.py           # 报告模型
│   │
│   ├── schemas/                # Pydantic模型
│   │   ├── request.py          # 请求体定义
│   │   └── response.py         # 响应体定义
│   │
│   └── utils/                  # 工具函数
│       ├── jira_parser.py      # 上线单号解析Jira单号
│       └── prompt_builder.py   # AI Prompt构建
│
├── logs/                       # 日志目录
├── requirements.txt
└── .env                        # 环境变量配置
```

### 3.2 API接口设计

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/analyze | 提交分析任务 |
| GET | /api/task/:id | 查询任务状态 |
| GET | /api/report/:id | 获取报告详情 |
| POST | /api/report/:id/mark | 人工标记 |
| GET | /api/history | 历史记录列表 |
| POST | /api/webhook/op | OP平台推送接口 |

#### 3.2.1 提交分析任务

**Request**
```json
POST /api/analyze
{
    "release_no": "REL-20240517-PROJ-123"
}
```

**Response**
```json
{
    "code": 0,
    "data": {
        "task_id": 1,
        "report_url": "http://localhost:5173/report/1",
        "status": "pending"
    }
}
```

#### 3.2.2 查询任务状态

**Request**
```
GET /api/task/1
```

**Response**
```json
{
    "code": 0,
    "data": {
        "task_id": 1,
        "release_no": "REL-20240517-PROJ-123",
        "status": "analyzing",
        "progress": "正在分析代码...",
        "created_at": "2024-05-17 10:00:00"
    }
}
```

#### 3.2.3 获取报告详情

**Request**
```
GET /api/report/1
```

**Response**
```json
{
    "code": 0,
    "data": {
        "task_id": 1,
        "release_no": "REL-20240517-PROJ-123",
        "jira_key": "PROJ-123",
        "status": "success",
        "coverage": {
            "total": 85.0,
            "manual_coverage": 90.0,
            "total_requirements": 20,
            "covered_requirements": 17,
            "irrelevant_requirements": 1
        },
        "requirements": [...],
        "issues": [...],
        "summary": "本次代码变更整体实现质量良好..."
    }
}
```

#### 3.2.4 人工标记

**Request**
```json
POST /api/report/1/mark
{
    "item_type": "requirement",
    "item_id": "req_001",
    "marked_status": "covered",
    "remark": "实际已有实现"
}
```

**Response**
```json
{
    "code": 0,
    "data": {
        "new_coverage": 90.0
    }
}
```

#### 3.2.5 OP平台推送

**Request**
```json
POST /api/webhook/op
Header: X-OP-Token: xxx
{
    "release_no": "REL-20240517-PROJ-123",
    "diff": "diff --git a/xxx.py...",
    "diff_type": "git",
    "callback_url": "http://op.internal/callback"
}
```

**Response**
```json
{
    "code": 0,
    "data": {
        "task_id": 1,
        "report_url": "http://cr.local/report/1"
    }
}
```

---

## 四、数据库设计

### 4.1 ER图

```
┌─────────────────┐     ┌─────────────────┐
│ analysis_task   │     │ analysis_report │
├─────────────────┤     ├─────────────────┤
│ id (PK)         │◄────│ task_id (FK)    │
│ release_no      │     │ id (PK)         │
│ jira_key        │     │ requirement_    │
│ status          │     │   coverage      │
│ error_message   │     │ requirement_    │
│ created_at      │     │   details       │
│ updated_at      │     │ extra_code_     │
└─────────────────┘     │   issues        │
                        │ syntax_errors   │
                        │ boundary_issues │
                        │ exception_issues│
                        │ quality_issues  │
                        │ total_issues    │
                        │ summary         │
                        └────────┬────────┘
                                 │
                        ┌────────▼────────┐
                        │ manual_mark     │
                        ├─────────────────┤
                        │ id (PK)         │
                        │ report_id (FK)  │
                        │ item_type       │
                        │ item_id         │
                        │ original_status │
                        │ marked_status   │
                        │ marked_by       │
                        │ marked_at       │
                        │ remark          │
                        └─────────────────┘
```

### 4.2 表结构定义

#### analysis_task - 分析任务表

```sql
CREATE TABLE analysis_task (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    release_no VARCHAR(100) NOT NULL COMMENT '上线单号',
    jira_key VARCHAR(50) COMMENT 'Jira单号',
    status ENUM('pending', 'analyzing', 'success', 'failed') DEFAULT 'pending',
    error_message TEXT COMMENT '错误信息',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_release_no (release_no)
);
```

#### analysis_report - 分析报告表

```sql
CREATE TABLE analysis_report (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    task_id BIGINT NOT NULL COMMENT '关联任务ID',

    -- 覆盖率统计
    requirement_coverage DECIMAL(5,2) COMMENT '需求覆盖率 0-100',
    manual_coverage DECIMAL(5,2) COMMENT '人工修正后覆盖率',
    total_requirements INT DEFAULT 0 COMMENT '需求总数',
    covered_requirements INT DEFAULT 0 COMMENT '已覆盖数',
    irrelevant_requirements INT DEFAULT 0 COMMENT '标记无关数',

    -- 分析结果详情
    requirement_details JSON COMMENT '需求条目覆盖详情',
    extra_code_issues JSON COMMENT '夹带问题列表',
    syntax_errors JSON COMMENT '语法错误列表',
    boundary_issues JSON COMMENT '边界场景问题',
    exception_issues JSON COMMENT '异常兜底问题',
    quality_issues JSON COMMENT '代码质量问题',

    -- 汇总
    total_issues INT DEFAULT 0 COMMENT '问题总数',
    summary TEXT COMMENT '分析总结',

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (task_id) REFERENCES analysis_task(id)
);
```

#### manual_mark - 人工标记表

```sql
CREATE TABLE manual_mark (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    report_id BIGINT NOT NULL,

    item_type ENUM('requirement', 'issue') COMMENT '标记项类型',
    item_id VARCHAR(100) COMMENT '需求条目ID或问题ID',

    original_status VARCHAR(50) COMMENT '原始状态',
    marked_status VARCHAR(50) COMMENT '人工标记状态',
    marked_by VARCHAR(100) COMMENT '标记人',
    marked_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    remark TEXT COMMENT '备注说明',

    FOREIGN KEY (report_id) REFERENCES analysis_report(id)
);
```

#### system_config - 系统配置表

```sql
CREATE TABLE system_config (
    id INT PRIMARY KEY AUTO_INCREMENT,
    config_key VARCHAR(100) NOT NULL UNIQUE,
    config_value JSON NOT NULL,
    description VARCHAR(500),
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

---

## 五、前端设计

### 5.1 目录结构

```
frontend/
├── public/
├── src/
│   ├── main.js
│   ├── App.vue
│   │
│   ├── views/                   # 页面
│   │   ├── Home.vue             # 首页/分析入口
│   │   ├── Report.vue           # 报告详情页
│   │   └── History.vue          # 历史记录页
│   │
│   ├── components/              # 组件
│   │   ├── AnalyzeForm.vue      # 分析表单
│   │   ├── ReportStatus.vue     # 报告状态
│   │   ├── RequirementCard.vue  # 需求覆盖卡片
│   │   ├── IssueList.vue        # 问题列表
│   │   └── CodeDiffViewer.vue   # 代码diff展示
│   │
│   ├── api/                     # API调用
│   │   └── index.js             # axios封装
│   │
│   ├── router/
│   │   └── index.js
│   │
│   └── utils/
│       └── polling.js           # 轮询工具
│
├── package.json
└── vite.config.js
```

### 5.2 页面设计

#### 首页 (Home.vue)

```
┌─────────────────────────────────────────────────────────────────┐
│  首页                                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌───────────────────────────────────────────────────────┐    │
│   │  上线单号: [________________]  [开始分析]              │    │
│   └───────────────────────────────────────────────────────┘    │
│                                                                 │
│   最近分析:                                                     │
│   ┌─────────────┬──────────┬─────────────┐                    │
│   │ REL-2024... │ 成功     │ 2024-05-17  │                    │
│   │ REL-2024... │ 分析中   │ 2024-05-17  │                    │
│   └─────────────┴──────────┴─────────────┘                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 报告页 (Report.vue)

```
┌─────────────────────────────────────────────────────────────────┐
│  报告页 (/report/:id)                                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌───────────────────────────────────────────────────────┐    │
│   │        需求覆盖率: 85%                                 │    │
│   │   ████████████████████░░░░░                           │    │
│   │   已覆盖: 17/20    未覆盖: 2    无关: 1                │    │
│   └───────────────────────────────────────────────────────┘    │
│                                                                 │
│   ┌───────────────────────────────────────────────────────┐    │
│   │  文件变更统计                                          │    │
│   │  后端文件: 5 个 (已分析)                               │    │
│   │  前端文件: 3 个 (暂未分析)                             │    │
│   └───────────────────────────────────────────────────────┘    │
│                                                                 │
│   ┌───────────────────────────────────────────────────────┐    │
│   │  需求覆盖详情                                          │    │
│   │  ✅ 用户登录功能        auth/login.py    [标记错误]    │    │
│   │  ⚠️ 密码加密存储        未发现实现       [已实现][无关] │    │
│   │  ✅ 权限校验           auth/permission.py [标记错误]   │    │
│   └───────────────────────────────────────────────────────┘    │
│                                                                 │
│   ┌───────────────────────────────────────────────────────┐    │
│   │  发现问题 (3)                                          │    │
│   │  🔴 夹带: 新增了未关联需求的工具类  [误报][确认]       │    │
│   │  🟡 边界: 用户名为空时未做校验      [误报][确认]       │    │
│   │  🟡 兜底: 数据库连接失败无重试机制  [误报][确认]       │    │
│   └───────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 六、核心分析流程

### 6.1 分析执行流程

```
1. 解析上线单号 → 提取Jira单号
         ↓
2. 调用Jira API → 获取需求文档内容
         ↓
3. 获取代码diff (OP推送 / 主动拉取)
         ↓
4. 文件过滤 → 排除前端文件、无关目录
         ↓
5. 智能上下文选择 → 两阶段分析确定需要的上下文文件
         ↓
6. 构造Prompt → 需求 + diff + 上下文 + 分析指令
         ↓
7. 调用Claude API → 获取分析结果
         ↓
8. 解析结果 → 结构化存储到数据库
         ↓
9. 生成报告 → 返回给用户
```

### 6.2 智能上下文选择

**两阶段分析流程**

```
阶段一：分析diff，识别需要的上下文
┌─────────┐
│  diff   │ ──→ CC分析 ──→ 返回需要的文件列表
└─────────┘
                  ↓
     ["auth/utils.py", "models/user.py", ...]
                  ↓
阶段二：读取相关文件，进行完整分析
┌─────────┐     ┌─────────────┐
│  diff   │  +  │ 上下文文件   │ ──→ CC完整分析 ──→ 报告
└─────────┘     └─────────────┘
```

### 6.3 AI Prompt模板

```python
ANALYZE_PROMPT = """
你是一个代码审查专家。请分析以下代码变更是否完整实现了需求功能。

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
{format_example}
"""
```

---

## 七、配置管理

### 7.1 文件过滤配置

```python
FILE_FILTER = {
    "exclude_patterns": [
        "*.vue", "*.jsx", "*.tsx",
        "*.css", "*.scss", "*.less",
        "*.html", "*.js", "*.ts",
        "package.json", "package-lock.json",
        "yarn.lock", "pnpm-lock.yaml",
    ],
    "include_patterns": [
        "*.py", "*.java", "*.go", "*.sql",
    ],
    "exclude_dirs": [
        "node_modules/", "dist/", "build/",
        ".venv/", "venv/", "__pycache__/",
    ]
}
```

### 7.2 AI配置

```python
AI_CONFIG = {
    "model": "claude-sonnet-4-6",
    "single_call_timeout": 60,      # 单次AI调用超时(秒)
    "total_analysis_timeout": 300,  # 总分析超时(秒)
    "max_context_files": 5,         # 最多读取上下文文件数
    "max_file_lines": 500,          # 每个文件最多读取行数
}
```

### 7.3 环境变量配置

```env
# .env

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
```

---

## 八、日志设计

### 8.1 日志级别

详细日志，记录完整请求响应、AI调用耗时。

### 8.2 日志格式

```
[2024-05-17 10:00:00] [INFO] [analyze.py:45] 开始分析任务 task_id=1, release_no=REL-20240517-PROJ-123
[2024-05-17 10:00:01] [INFO] [jira_service.py:32] 获取Jira需求成功 jira_key=PROJ-123
[2024-05-17 10:00:02] [INFO] [ai_analyzer.py:78] AI调用开始, 预估tokens=15000
[2024-05-17 10:01:30] [INFO] [ai_analyzer.py:95] AI调用完成, 耗时=88s, 实际tokens=12345
[2024-05-17 10:01:31] [INFO] [analyze.py:89] 分析任务完成 task_id=1, status=success
```

---

## 九、Mock测试数据

Demo阶段使用Mock数据进行测试，模拟以下场景：

1. 正常分析流程 - 需求完全覆盖
2. 部分覆盖 - 需求未完全实现
3. 夹带检测 - 包含无关代码变更
4. 语法错误 - 包含语法问题
5. 边界问题 - 缺少边界处理

---

## 十、覆盖率计算逻辑

```python
def calculate_coverage(report_id):
    """
    覆盖率 = 已覆盖需求数 / 总需求数
    总需求数 = 原始需求数 - 标记为"无关需求"的数量
    """
    requirements = get_requirements(report_id)
    manual_marks = get_manual_marks(report_id)

    total = len(requirements)
    covered = 0
    irrelevant = 0

    for req in requirements:
        status = req.status

        # 检查是否有人工标记覆盖
        mark = manual_marks.get(req.id)
        if mark:
            if mark.marked_status == 'irrelevant':
                irrelevant += 1
                continue
            status = mark.marked_status

        if status == 'covered':
            covered += 1

    effective_total = total - irrelevant
    coverage = (covered / effective_total * 100) if effective_total > 0 else 0

    return round(coverage, 2)
```

---

## 十一、人工标记操作类型

| 场景 | 原始状态 | 可标记为 |
|------|---------|---------|
| 需求覆盖 | ✅ 已覆盖 | ❌ 未覆盖（误报） |
| 需求覆盖 | ⚠️ 未覆盖 | ✅ 已覆盖 / 🔕 无关需求 |
| 问题检测 | 🔴/🟡 有问题 | ✅ 误报（无问题） |
| 问题检测 | ✅ 无问题 | 🔴 确实有问题（漏报） |

---

## 十二、后续扩展

| 功能 | 说明 |
|------|------|
| 前端代码分析 | 支持Vue/React等前端代码分析 |
| 多模态支持 | 支持设计图、流程图等分析 |
| Celery升级 | 生产环境使用Celery处理异步任务 |
| 结果回传OP | 分析结果回调通知OP平台 |
| 批量分析 | 支持批量分析多个上线单 |
| 报告导出 | 支持导出PDF/Excel格式报告 |
