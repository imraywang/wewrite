"""WeWrite Web 后端入口。"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .routes import account, catalog, distribute, jobs, publish

app = FastAPI(title="WeWrite Web", version="0.1.0")

settings = get_settings()
# 生成的图片产物（公开可取，供 <img> 与发布渠道读取）。
# NOTE(生产): 换对象存储 + CDN；如需鉴权改为签名 URL。
settings.artifact_root.mkdir(parents=True, exist_ok=True)
app.mount("/artifacts", StaticFiles(directory=str(settings.artifact_root)), name="artifacts")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(catalog.router)
app.include_router(account.router)
app.include_router(jobs.router)
app.include_router(publish.router)
app.include_router(distribute.router)


def _runner_ready(s) -> bool:
    if s.runner != "container":
        return True
    import shutil
    import subprocess
    if not shutil.which("docker"):
        return False
    try:
        r = subprocess.run(["docker", "image", "inspect", s.job_image],
                           capture_output=True, timeout=5)
        return r.returncode == 0
    except Exception:  # noqa: BLE001
        return False


@app.get("/api/health")
def health() -> dict:
    s = get_settings()
    return {
        "ok": True,
        "model": s.model,
        "runner": s.runner,
        "runner_ready": _runner_ready(s),
        "llm_key_configured": bool(s.anthropic_api_key or s.anthropic_auth_token),
        "image_pool_configured": bool(s.image_config()),
        "skill_dir": str(s.skill_dir),
    }


# 前端静态产物（next export 的 out/）。最后挂在 "/"：上面的 /api、/artifacts 已先注册、优先匹配；
# 单进程单源服务前端 + API + 产物，省一个常驻进程，外层只需把 wewrite.cc 反代到本服务。
# 未设 WEWRITE_FRONTEND_DIR（如纯本地后端开发）时不挂载，行为不变。
_frontend_dir = os.environ.get("WEWRITE_FRONTEND_DIR", "")
if _frontend_dir and Path(_frontend_dir).is_dir():
    app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")
