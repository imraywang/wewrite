"""集合/评分辅助函数 —— 供 runner 与调度层复用。
SDK 执行逻辑（consume_stream、make_options_and_prompt 等）已移至 pipeline.py。
"""
from __future__ import annotations

import importlib.util as _ilu
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from .config import get_settings
from .platforms import HUMANNESS_THRESHOLD, SIMILARITY_THRESHOLD
from .store import Job

_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".gif")

# 文件名 / 首标题里出现这些标记，视为辅助产物（配图提示词、SEO 备注等），不是正文
_AUX_NAME_HINTS = ("prompt", "preview", "metadata", "seo", "image", "提示词", "配图")
_AUX_HEADING_HINTS = ("配图", "提示词", "prompt", "封面文案", "seo")

_TAG_RE = re.compile(r"#(\w[\w一-鿿]*)")


def gate_passes(humanness: float | None, max_similarity: float | None) -> bool:
    if humanness is not None and humanness < HUMANNESS_THRESHOLD:
        return False
    if max_similarity is not None and max_similarity > SIMILARITY_THRESHOLD:
        return False
    return True


def _extract_tags(md: str) -> list[str]:
    seen, out = set(), []
    for m in _TAG_RE.findall(md):
        if m not in seen:
            seen.add(m)
            out.append(m)
    return out


def _humanness_best_effort(ws: Path, filename: str) -> float | None:
    """跑 humanness_score.py 取分；失败则返回 None（降级，不阻断）。"""
    py = ws / ".venv" / "bin" / "python3"
    python = str(py) if py.exists() else "python3"
    try:
        r = subprocess.run(
            [python, "scripts/humanness_score.py", f"output/{filename}", "--json"],
            cwd=str(ws), capture_output=True, timeout=120, check=False, text=True,
        )
        data = json.loads(r.stdout or "{}")
        for key in ("composite", "score", "humanness"):
            if isinstance(data.get(key), (int, float)):
                return float(data[key])
    except Exception:  # noqa: BLE001 - 评分失败不阻断
        return None
    return None


def _collect_platform_versions(job, ws: Path, source_md: str, profiles: list) -> list[dict]:
    out = ws / "output"
    try:
        similarity = _load_similarity()
    except Exception:  # noqa: BLE001 - 相似度脚本不可用则降级，不丢已产出的版本
        def similarity(a, b):  # noqa: ANN001
            return 0.0
    read: list[tuple] = []
    versions: list[dict] = []
    for prof in profiles:
        f = out / prof.output_filename
        if not f.is_file():
            versions.append({
                "platform": prof.id, "label": prof.label, "output_kind": prof.output_kind,
                "title": "", "markdown": "", "images": [], "tags": [],
                "humanness": None, "max_similarity": None, "passed": False,
                "status": "failed", "warning": "未产出该平台版本",
            })
            continue
        read.append((prof, f.read_text(encoding="utf-8")))
    for prof, md in read:
        sim_src = similarity(source_md, md)
        sim_peers = max((similarity(md, other) for p2, other in read if p2.id != prof.id),
                        default=0.0)
        max_sim = round(max(sim_src, sim_peers), 4)
        hu = _humanness_best_effort(ws, prof.output_filename)
        passed = gate_passes(hu, max_sim)
        v = {
            "platform": prof.id, "label": prof.label, "output_kind": prof.output_kind,
            "title": _first_heading(md) or prof.label,
            "markdown": _rewrite_md_images(md, job) if prof.needs_images else md,
            "images": list(getattr(job, "images", [])) if prof.needs_images else [],
            "tags": _extract_tags(md),
            "humanness": hu, "max_similarity": max_sim,
            "passed": passed, "status": "done",
            "warning": "" if passed else "未完全通过质量门（相似度偏高或反AI偏低），建议人工微调",
        }
        versions.append(v)
    return versions


def _collect_outputs(job: Job, ws: Path, *, theme: str) -> None:
    out = ws / "output"
    if not out.exists():
        return
    # 先持久化图片（工作区随后会被清理）
    _persist_images(job, out)
    md = _pick_article(out)
    if md is None:
        return
    text = md.read_text(encoding="utf-8")
    job.preview_html = _generate_preview(ws, md, theme=theme)  # 预览基于原始相对路径
    # 把正文里的本地图片引用改写成持久化后的 URL，使 markdown 自包含
    job.article_markdown = _rewrite_md_images(text, job)
    job.title = _first_heading(text) or md.stem


def _looks_auxiliary(p: Path) -> bool:
    name = p.stem.lower()
    if any(h in name for h in _AUX_NAME_HINTS):
        return True
    try:
        head = _first_heading(p.read_text(encoding="utf-8")) or ""
    except OSError:
        return False
    return any(h in head.lower() for h in _AUX_HEADING_HINTS)


def _pick_article(out: Path) -> Optional[Path]:
    """从 output/ 里挑出"文章正文"。

    不能盲取最近修改的 .md —— 管道在正文之后常会再写辅助产物（配图提示词包、SEO 备注），
    那些 mtime 更新，会被误当成正文。选取顺序：
      1) 约定的固定名 output/article.md（pipeline 的 generate_user_prompt 已要求 agent 这样存）；
      2) 排除 assets/ 子目录与明显的辅助产物后，取最新的 .md；
      3) 若全被排除（极端情况），兜底取最新的任意 .md。
    """
    canonical = out / "article.md"
    if canonical.is_file():
        return canonical
    mds = [
        p for p in out.glob("**/*.md")
        if p.is_file() and "assets" not in p.relative_to(out).parts[:-1]
    ]
    if not mds:
        return None
    non_aux = [p for p in mds if not _looks_auxiliary(p)]
    pool = non_aux or mds
    return max(pool, key=lambda p: p.stat().st_mtime)


def _image_sort_key(p: Path) -> tuple:
    name = p.name.lower()
    if "cover" in name or "封面" in name:
        return (0, 0, name)
    m = re.search(r"fig(\d+)", name)
    if m:
        return (1, int(m.group(1)), name)
    return (2, 0, name)


def _persist_images(job: Job, out: Path) -> None:
    from .config import get_settings

    settings = get_settings()
    imgs = sorted(
        (p for p in out.glob("**/*") if p.is_file() and p.suffix.lower() in _IMAGE_EXTS),
        key=_image_sort_key,
    )
    if not imgs:
        return
    dest = settings.artifact_root / job.id
    dest.mkdir(parents=True, exist_ok=True)
    for p in imgs:
        target = dest / p.name
        try:
            shutil.copy2(p, target)
        except OSError:
            continue
        rel = f"/artifacts/{job.id}/{p.name}"
        job.images.append(settings.public_base_url + rel if settings.public_base_url else rel)
        job.image_paths.append(str(target))


def _rewrite_md_images(md: str, job: Job) -> str:
    if not job.images:
        return md
    # basename -> URL
    by_name = {Path(u).name: u for u in job.images}

    def repl(m: re.Match) -> str:
        alt, path = m.group(1), m.group(2)
        url = by_name.get(Path(path).name)
        return f"![{alt}]({url})" if url else m.group(0)

    return re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", repl, md)


def _first_heading(markdown: str) -> Optional[str]:
    for line in markdown.splitlines():
        line = line.strip()
        if line.startswith("#"):
            return line.lstrip("#").strip()
        if line:
            return line[:60]
    return None


def _generate_preview(ws: Path, md: Path, *, theme: str) -> Optional[str]:
    """用 toolkit 把 Markdown 渲染成微信风格 HTML（best-effort）。"""
    py = ws / ".venv" / "bin" / "python3"
    python = str(py) if py.exists() else "python3"
    preview = ws / "output" / "preview.html"
    try:
        subprocess.run(
            [python, "toolkit/cli.py", "preview", str(md), "--theme", theme,
             "--no-open", "-o", str(preview)],
            cwd=str(ws), capture_output=True, timeout=120, check=False,
        )
        if preview.exists():
            return preview.read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001 - 预览失败不影响主产物
        return None
    return None


def _load_similarity():
    """从仓库 scripts/similarity_check.py 动态加载 similarity 函数。"""
    settings = get_settings()
    path = settings.skill_dir / "scripts" / "similarity_check.py"
    spec = _ilu.spec_from_file_location("similarity_check", path)
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod.similarity


def _seed_source_images(job: Job, ws: Path) -> None:
    """把内联源（generate job）已持久化的图片拷进改写工作区 output/，供小红书复用。"""
    for p in getattr(job, "source_image_paths", None) or []:
        src = Path(p)
        if src.is_file():
            try:
                shutil.copy2(src, ws / "output" / src.name)
            except OSError:
                continue
