"""Unified history.yaml access with legacy-list compatibility."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import yaml

from .paths import history_path

HISTORY_VERSION = 1


def normalize_history(data) -> dict:
    """Return the canonical mapping shape for any supported legacy value."""
    if isinstance(data, list):
        return {"version": HISTORY_VERSION, "articles": data}
    if isinstance(data, dict):
        articles = data.get("articles", [])
        if not isinstance(articles, list):
            articles = []
        return {**data, "version": data.get("version", HISTORY_VERSION), "articles": articles}
    return {"version": HISTORY_VERSION, "articles": []}


def load_history(path: Path | None = None) -> dict:
    path = path or history_path()
    if not path.exists():
        return normalize_history(None)
    with path.open("r", encoding="utf-8") as f:
        return normalize_history(yaml.safe_load(f))


def save_history(data: dict, path: Path | None = None) -> Path:
    """Atomically save canonical history data."""
    path = path or history_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    canonical = normalize_history(data)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=path.stem, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            yaml.safe_dump(canonical, f, allow_unicode=True, sort_keys=False)
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    return path


def append_article(article: dict, path: Path | None = None) -> Path:
    data = load_history(path)
    data["articles"].append(article)
    return save_history(data, path)


def upsert_article(article: dict, path: Path | None = None) -> Path:
    """Insert an article or refresh the existing entry for the same run."""
    data = load_history(path)
    run_id = article.get("run_id")
    if run_id:
        for index, existing in enumerate(data["articles"]):
            if existing.get("run_id") == run_id:
                merged = {**existing, **article}
                if article.get("stats") is None and existing.get("stats") is not None:
                    merged["stats"] = existing["stats"]
                data["articles"][index] = merged
                return save_history(data, path)
    data["articles"].append(article)
    return save_history(data, path)
