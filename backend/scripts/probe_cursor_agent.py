"""
独立探针: 验证 CURSOR_API_KEY 是否可用、能否创建 + 拉取 cloud agent。

用法 (在 backend/ 目录下):
    source venv/bin/activate
    python -m scripts.probe_cursor_agent

或显式传 prompt:
    python -m scripts.probe_cursor_agent "用一句话介绍你能做什么"

会读取 backend/.env 里的 CURSOR_API_KEY / CURSOR_AGENT_REPO_URL / CURSOR_AGENT_MODEL。
脚本只做最小连通性测试: 创建 agent -> 轮询直到 finished/error/timeout -> 打印 status + 截取的输出。
"""
from __future__ import annotations

import sys
import time
import json

import httpx

# 复用应用配置以读取 .env (确保 .env 与生产路径一致)
from app.config import settings


def main(prompt: str) -> int:
    api_key = settings.CURSOR_API_KEY.strip()
    if not api_key or api_key.lower().startswith("your_"):
        print("[FAIL] CURSOR_API_KEY 没配置 (在 backend/.env 里填一个真实 key 再跑)")
        return 2

    base = settings.CURSOR_API_BASE.rstrip("/")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": prompt,
        "model": settings.CURSOR_AGENT_MODEL or "auto",
    }
    if settings.CURSOR_AGENT_REPO_URL:
        payload["source"] = {
            "repository": settings.CURSOR_AGENT_REPO_URL,
            "ref": settings.CURSOR_AGENT_REPO_REF or "master",
        }

    print(f"[INFO] POST {base}")
    print(f"[INFO] payload = {json.dumps(payload, ensure_ascii=False)[:300]}")

    try:
        with httpx.Client(timeout=30) as client:
            r = client.post(base, headers=headers, json=payload)
            print(f"[INFO] create status={r.status_code}")
            if r.status_code >= 400:
                print(f"[FAIL] body={r.text[:1000]}")
                return 1
            body = r.json()
            agent_id = body.get("id") or body.get("agent_id")
            if not agent_id:
                print(f"[FAIL] 没有 agent id, body={body}")
                return 1
            print(f"[OK] agent id = {agent_id}")

            deadline = time.time() + settings.CURSOR_AGENT_TIMEOUT
            last = None
            done = {"FINISHED", "COMPLETED", "DONE", "SUCCESS", "SUCCEEDED"}
            fail = {"ERROR", "FAILED", "CANCELLED", "CANCELED", "ABORTED"}
            while time.time() < deadline:
                p = client.get(f"{base}/{agent_id}", headers=headers)
                if p.status_code >= 400:
                    print(f"[FAIL] poll status={p.status_code} body={p.text[:500]}")
                    return 1
                pj = p.json()
                status = str(pj.get("status") or pj.get("state") or "").upper()
                if status != last:
                    print(f"[POLL] status={status}")
                    last = status
                if status in done:
                    print(f"[OK] finished. body keys = {list(pj.keys())}")
                    print(f"[OK] body preview = {json.dumps(pj, ensure_ascii=False)[:800]}")
                    return 0
                if status in fail:
                    print(f"[FAIL] terminal state. body = {json.dumps(pj, ensure_ascii=False)[:800]}")
                    return 1
                time.sleep(settings.CURSOR_AGENT_POLL_INTERVAL)
            print(f"[FAIL] timeout after {settings.CURSOR_AGENT_TIMEOUT}s, last status={last}")
            return 1
    except httpx.HTTPError as e:
        print(f"[FAIL] HTTP error: {e}")
        return 1


if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv) > 1 else "Reply with the JSON: {\"ping\":\"pong\"} only. No other text."
    sys.exit(main(p))
