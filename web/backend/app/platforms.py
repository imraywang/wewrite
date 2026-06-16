"""平台档案：配置驱动的多平台改写规范（toolkit/platforms/*.yaml）+ 质量门阈值。"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from .config import get_settings

# 质量门阈值（v1 初值，按实测调）
SIMILARITY_THRESHOLD = 0.6   # 源↔版本 / 版本↔版本 字符3-gram Jaccard 上限
HUMANNESS_THRESHOLD = 0.6    # humanness_score 下限
MAX_REWRITE_RETRIES = 2      # 单平台改写不过的重试次数（写进 prompt 给 agent）


@dataclass
class PlatformProfile:
    id: str
    label: str
    output_kind: str           # graphic_text | oral_script
    output_filename: str
    min_chars: int = 0
    max_chars: int = 0
    needs_images: bool = False
    tag_count: tuple[int, int] = (0, 0)
    rewrite_brief: str = ""


def load_profile(path: Path) -> PlatformProfile:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    pid = data["id"]
    tc = data.get("tag_count") or [0, 0]
    return PlatformProfile(
        id=pid,
        label=data.get("label", pid),
        output_kind=data.get("output_kind", "graphic_text"),
        output_filename=data.get("output_filename", f"{pid}.md"),
        min_chars=int(data.get("min_chars", 0)),
        max_chars=int(data.get("max_chars", 0)),
        needs_images=bool(data.get("needs_images", False)),
        tag_count=(int(tc[0]), int(tc[1])),
        rewrite_brief=data.get("rewrite_brief", ""),
    )


def _platform_dir() -> Path:
    return get_settings().skill_dir / "toolkit" / "platforms"


@lru_cache
def all_profiles() -> dict[str, PlatformProfile]:
    out: dict[str, PlatformProfile] = {}
    d = _platform_dir()
    if d.exists():
        for p in sorted(d.glob("*.yaml")):
            prof = load_profile(p)
            out[prof.id] = prof
    return out


def get_profile(pid: str) -> PlatformProfile | None:
    return all_profiles().get(pid)
