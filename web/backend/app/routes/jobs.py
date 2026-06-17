"""任务：创建 / 列表 / 详情 / SSE 进度流。"""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sse_starlette.sse import EventSourceResponse

from ..agent_runner import submit_generate
from ..models import CreateJobRequest, JobSummary
from ..store import STORE, Job
from . import current_user

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _summary(job: Job) -> JobSummary:
    return JobSummary(
        id=job.id,
        status=job.status,  # type: ignore[arg-type]
        prompt=job.prompt,
        created_at=job.created_at,
        completion=job.completion,
        kind=job.kind,
    )


@router.post("", response_model=JobSummary)
async def create_job(req: CreateJobRequest, user_id: str = Depends(current_user)) -> JobSummary:
    job = STORE.create_job(
        user_id=user_id,
        prompt=req.prompt,
        interactive=req.interactive,
        theme=req.theme,
        persona=req.persona,
        publish_draft=req.publish_draft,
    )
    submit_generate(job)
    return _summary(job)


@router.get("", response_model=list[JobSummary])
def list_jobs(user_id: str = Depends(current_user)) -> list[JobSummary]:
    return [_summary(j) for j in STORE.list_jobs(user_id)]


@router.get("/{job_id}")
def get_job(job_id: str, user_id: str = Depends(current_user)) -> dict:
    job = STORE.get_job(job_id)
    if not job or job.user_id != user_id:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {
        **_summary(job).model_dump(),
        "error": job.error,
        "title": job.title,
        "article_markdown": job.article_markdown,
        "preview_html": job.preview_html,
        "images": job.images,
        "events": job.events,
        "platform_versions": job.platform_versions,
    }


@router.get("/{job_id}/stream")
async def stream_job(
    job_id: str,
    user_id: str = Depends(current_user),
    user_id_q: str | None = Query(default=None, alias="user_id"),
) -> EventSourceResponse:
    # EventSource 无法自定义请求头，允许用 ?user_id= 查询参数兜底标识用户
    effective_user = user_id if user_id != "default" else (user_id_q or user_id)
    job = STORE.get_job(job_id)
    if not job or job.user_id != effective_user:
        raise HTTPException(status_code=404, detail="任务不存在")

    async def event_gen():
        # 先回放已产生的事件（应对 SSE 在若干事件之后才连上）
        replayed = 0
        for ev in list(job.events):
            replayed = ev["seq"] + 1
            yield {"data": json.dumps(ev, ensure_ascii=False)}
        if job._done.is_set():
            yield {"event": "end", "data": "{}"}
            return
        # 再追实时事件，按 seq 去重
        while True:
            item = await job._queue.get()
            if item is None:
                yield {"event": "end", "data": "{}"}
                break
            if item["seq"] < replayed:
                continue
            replayed = item["seq"] + 1
            yield {"data": json.dumps(item, ensure_ascii=False)}

    return EventSourceResponse(event_gen())
