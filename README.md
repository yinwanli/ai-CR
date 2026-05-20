# ai-CR

AI 辅助代码评审平台：对比需求文档与代码 diff，输出覆盖率与问题清单。

## 项目结构

```
ai_diff/
├── backend/     # FastAPI 后端
├── frontend/    # Vue 3 + Vite 前端
└── docs/        # 文档
```

## 快速启动

### 后端

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env：数据库、CURSOR_API_KEY 等
uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

浏览器访问 Vite 提示的地址（默认 `http://localhost:5173`）。

## AI 后端优先级

1. **Cursor Cloud Agent** — 配置 `CURSOR_API_KEY`（见 `backend/.env.example`）
2. **Claude API** — 配置 `CLAUDE_API_KEY`
3. **Mock** — 均未配置时使用模拟数据

探针测试 Cursor Agent：

```bash
cd backend && source venv/bin/activate
python -m scripts.probe_cursor_agent
```

## 配置说明

复制 `backend/.env.example` 为 `backend/.env`，不要提交 `.env` 到 Git。
