"""多平台分发：把一份源内容改写到多个平台（异步 agent 任务，SSE 复用 jobs 流）。"""
from __future__ import annotations

import asyncio
import subprocess

from fastapi import APIRouter, Depends, HTTPException

from ..agent_runner import submit_distribute
from ..config import get_settings
from ..models import DistributeRequest, JobSummary
from ..store import STORE
from . import current_user

router = APIRouter(prefix="/api/distribute", tags=["distribute"])


def _fetch_url_sync(url: str) -> str:
    """同步抓取文章（在线程里调用，勿直接在事件循环线程跑）。优先用仓库 venv 的 python3。"""
    settings = get_settings()
    py = settings.skill_dir / ".venv" / "bin" / "python3"
    python = str(py) if py.exists() else "python3"
    try:
        r = subprocess.run(
            [python, "scripts/fetch_article.py", url],
            cwd=str(settings.skill_dir), capture_output=True, timeout=120,
            check=False, text=True,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"抓取文章失败：{exc}") from exc
    raise HTTPException(status_code=502, detail="抓取文章失败或内容为空")


async def _resolve_source(req: DistributeRequest, user_id: str) -> tuple[str, list[str]]:
    """返回 (源 markdown, 源图片本机路径列表)。"""
    if req.source_job_id:
        job = STORE.get_job(req.source_job_id)
        if not job or job.user_id != user_id:
            raise HTTPException(status_code=404, detail="源任务不存在")
        if not job.article_markdown:
            raise HTTPException(status_code=400, detail="源任务还没有成稿")
        return job.article_markdown, list(getattr(job, "image_paths", []))
    if req.source_text and req.source_text.strip():
        return req.source_text, []
    if req.source_url and req.source_url.strip():
        # 子进程抓取放到线程，避免阻塞事件循环（否则会冻结所有 SSE 流）
        return await asyncio.to_thread(_fetch_url_sync, req.source_url), []
    raise HTTPException(status_code=400, detail="需提供 source_job_id / source_text / source_url 之一")


@router.post("", response_model=JobSummary)
async def distribute(req: DistributeRequest, user_id: str = Depends(current_user)) -> JobSummary:
    source_md, source_imgs = await _resolve_source(req, user_id)
    job = STORE.create_job(
        user_id=user_id, prompt=f"分发到 {', '.join(req.platforms)}",
        kind="distribute", source_markdown=source_md,
        target_platforms=req.platforms, persona=req.persona, theme=req.theme,
        source_image_paths=source_imgs,
    )
    submit_distribute(job)
    return JobSummary(id=job.id, status=job.status, prompt=job.prompt,
                      created_at=job.created_at, completion=job.completion, kind=job.kind)
