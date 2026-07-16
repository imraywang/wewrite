"""Run-scoped state with immutable source articles and optional derived outputs."""

from __future__ import annotations

import json
import os
import re
import secrets
import tempfile
from datetime import datetime
from pathlib import Path

import yaml

from .history import upsert_article
from .paths import current_run_path, ensure_home, home, runs_dir

RUN_ID_RE = re.compile(r"^[0-9]{8}-[0-9]{6}-[a-f0-9]{6}$")
RUN_MODES = {"draft", "complete", "publish"}
VISUAL_MODES = {"none", "cover", "full", "prompts"}
PROTECTED_FIELDS = {"run_id", "created", "status", "mode", "permissions"}
PROTECTED_ARTIFACTS = {
    "article",
    "brief",
    "claims",
    "draft",
    "illustrated_article",
    "image_prompts",
    "images_manifest",
    "review_report",
    "sources",
    "preview",
}
POST_COMPLETION_FIELDS = {"visual", "images", "publish"}
POST_COMPLETION_STEPS = {"visual", "publish"}


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=path.stem, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _new_run_id() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(3)


def validate_run_id(run_id: str) -> str:
    if not RUN_ID_RE.fullmatch(run_id):
        raise ValueError(f"Invalid run id: {run_id}")
    return run_id


def run_dir(run_id: str) -> Path:
    return runs_dir() / validate_run_id(run_id)


def state_path(run_id: str) -> Path:
    return run_dir(run_id) / "state.yaml"


def _write_state(state: dict) -> Path:
    state["updated"] = _now()
    path = state_path(state["run_id"])
    _atomic_write_text(path, yaml.safe_dump(state, allow_unicode=True, sort_keys=False))
    return path


def set_current_run(run_id: str) -> None:
    validate_run_id(run_id)
    _atomic_write_text(current_run_path(), run_id + "\n")


def resolve_run_id(run_id: str | None = None) -> str:
    if run_id:
        return validate_run_id(run_id)
    env_run = os.environ.get("WEWRITE_RUN_ID", "").strip()
    if env_run:
        return validate_run_id(env_run)
    pointer = current_run_path()
    if pointer.exists():
        candidate = pointer.read_text(encoding="utf-8").strip()
        if candidate and state_path(candidate).exists():
            try:
                pointed = yaml.safe_load(state_path(candidate).read_text(encoding="utf-8")) or {}
            except (OSError, yaml.YAMLError):
                pointed = {}
            if pointed.get("status") in {"active", "failed", "completed"}:
                return candidate
    active = [s for s in list_runs() if s.get("status") in {"active", "failed"}]
    if len(active) == 1:
        return active[0]["run_id"]
    if not active:
        raise FileNotFoundError("No current WeWrite run. Start one with `wewrite run start`.")
    raise ValueError("Multiple active runs. Choose one with `wewrite run resume <run_id>`.")


def create_run(
    *,
    topic: str = "",
    mode: str = "draft",
    visual_mode: str | None = None,
    max_images: int = 4,
    max_image_cost: float | None = None,
    allow_publish: bool = False,
) -> dict:
    ensure_home()
    if mode not in RUN_MODES:
        raise ValueError(f"Unknown mode: {mode}")
    if visual_mode is None:
        visual_mode = "none"
    if visual_mode not in VISUAL_MODES:
        raise ValueError(f"Unknown visual mode: {visual_mode}")
    if max_images < 0 or max_images > 10:
        raise ValueError("max_images must be between 0 and 10")
    if max_image_cost is not None and max_image_cost < 0:
        raise ValueError("max_image_cost must be non-negative")
    if mode == "publish":
        allow_publish = True

    run_id = _new_run_id()
    directory = run_dir(run_id)
    directory.mkdir(parents=True, exist_ok=False)
    created = _now()
    state = {
        "version": 4,
        "run_id": run_id,
        "created": created,
        "updated": created,
        "status": "active",
        "mode": mode,
        "permissions": {"publish": bool(allow_publish)},
        "visual": {
            "mode": visual_mode,
            "max_images": max_images,
            "max_cost": max_image_cost,
        },
        "topic": {
            "title": topic,
            "keywords": [],
            "source": "用户指定" if topic else "",
            "framework_hint": "",
        },
        "artifacts": {
            "article": str((directory / "article.md").relative_to(home())),
            "brief": str((directory / "brief.yaml").relative_to(home())),
            "claims": str((directory / "claims.yaml").relative_to(home())),
            "draft": str((directory / "draft.md").relative_to(home())),
            "illustrated_article": str((directory / "article-illustrated.md").relative_to(home())),
            "image_prompts": str((directory / "image-prompts.md").relative_to(home())),
            "images_manifest": str((directory / "images.json").relative_to(home())),
            "review_report": str((directory / "review-report.json").relative_to(home())),
            "sources": str((directory / "sources.yaml").relative_to(home())),
            "preview": str((directory / "preview.html").relative_to(home())),
        },
        "steps": {},
        "last_error": None,
    }
    _write_state(state)
    _atomic_write_text(
        directory / "sources.yaml",
        yaml.safe_dump({"version": 1, "run_id": run_id, "sources": []}, allow_unicode=True, sort_keys=False),
    )
    set_current_run(run_id)
    return state


def load_run(run_id: str | None = None) -> dict:
    resolved = resolve_run_id(run_id)
    path = state_path(resolved)
    if not path.exists():
        raise FileNotFoundError(f"Run not found: {resolved}")
    with path.open("r", encoding="utf-8") as f:
        state = yaml.safe_load(f) or {}
    if state.get("run_id") != resolved:
        raise ValueError(f"Run state mismatch: {resolved}")
    if _upgrade_state(state):
        _write_state(state)
    return state


def _deep_merge(base: dict, patch: dict) -> dict:
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def _upgrade_state(state: dict) -> bool:
    """Add current artifact paths to older run state without changing source artifacts."""
    run_id = state["run_id"]
    directory = run_dir(run_id)
    artifacts = state.setdefault("artifacts", {})
    expected = {
        "brief": str((directory / "brief.yaml").relative_to(home())),
        "claims": str((directory / "claims.yaml").relative_to(home())),
        "draft": str((directory / "draft.md").relative_to(home())),
        "illustrated_article": str((directory / "article-illustrated.md").relative_to(home())),
        "image_prompts": str((directory / "image-prompts.md").relative_to(home())),
        "images_manifest": str((directory / "images.json").relative_to(home())),
        "review_report": str((directory / "review-report.json").relative_to(home())),
    }
    changed = False
    for key, value in expected.items():
        if not artifacts.get(key):
            artifacts[key] = value
            changed = True
    if state.get("version", 1) < 4:
        state["version"] = 4
        changed = True
    return changed


def update_run(patch: dict, run_id: str | None = None, *, _control: bool = False) -> dict:
    state = load_run(run_id)
    if state.get("status") == "completed":
        allowed = {"steps", "last_error"} if _control else POST_COMPLETION_FIELDS
        blocked = set(patch) - allowed
        if blocked:
            raise ValueError(
                "Completed runs only accept visual, image, and publish outputs; "
                "start a new run to revise the article."
            )
        if _control:
            steps = patch.get("steps", {})
            if not isinstance(steps, dict) or set(steps) - POST_COMPLETION_STEPS:
                raise ValueError("Completed runs only accept visual or publish step updates.")
    if not _control:
        blocked = PROTECTED_FIELDS.intersection(patch)
        if blocked:
            raise ValueError(
                "Protected run fields cannot be changed: " + ", ".join(sorted(blocked))
            )
        artifact_patch = patch.get("artifacts", {})
        if isinstance(artifact_patch, dict) and PROTECTED_ARTIFACTS.intersection(artifact_patch):
            raise ValueError("Core artifact paths are immutable")
    _deep_merge(state, patch)
    _write_state(state)
    if state.get("status") == "completed":
        upsert_article(_history_entry(state))
    return state


def mark_step(step: str, status: str, run_id: str | None = None, error: str | None = None) -> dict:
    if status not in {"pending", "in_progress", "completed", "failed", "skipped"}:
        raise ValueError(f"Unknown step status: {status}")
    state = load_run(run_id)
    completed = state.get("status") == "completed"
    if completed and step not in POST_COMPLETION_STEPS:
        raise ValueError("Completed runs only accept visual or publish step updates.")
    patch = {"steps": {step: {"status": status, "updated": _now()}}}
    if error:
        patch["steps"][step]["error"] = error
        patch["last_error"] = error
    if completed:
        if status == "in_progress":
            patch["last_error"] = None
    elif status == "failed":
        patch["status"] = "failed"
    elif status == "in_progress":
        patch["status"] = "active"
        patch["last_error"] = None
    return update_run(patch, run_id, _control=True)


def list_runs() -> list[dict]:
    root = runs_dir()
    if not root.exists():
        return []
    runs = []
    for path in sorted(root.glob("*/state.yaml"), reverse=True):
        try:
            state = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            continue
        if state.get("run_id"):
            runs.append(state)
    return runs


def resume_run(run_id: str) -> dict:
    state = load_run(run_id)
    if state.get("status") == "completed":
        raise ValueError("Completed runs are immutable; start a new run to revise the article.")
    set_current_run(run_id)
    return update_run({"status": "active", "last_error": None}, run_id, _control=True)


def set_publish_permission(allow: bool, run_id: str | None = None) -> dict:
    """Record or revoke explicit permission to publish the current article."""
    state = load_run(run_id)
    state.setdefault("permissions", {})["publish"] = bool(allow)
    _write_state(state)
    if state.get("status") == "completed":
        upsert_article(_history_entry(state))
    return state


def _history_entry(state: dict) -> dict:
    topic = state.get("topic") or {}
    seo = state.get("seo") or {}
    publish = state.get("publish") or {}
    artifacts = state.get("artifacts") or {}
    return {
        "run_id": state["run_id"],
        "date": state.get("created", "")[:10],
        "title": seo.get("title") or topic.get("title") or "未命名文章",
        "topic_source": topic.get("source"),
        "topic_keywords": topic.get("keywords", []),
        "output_file": artifacts.get("article"),
        "draft_file": artifacts.get("draft"),
        "brief_file": artifacts.get("brief"),
        "review_file": artifacts.get("review_report"),
        "sources_file": artifacts.get("sources"),
        "framework": state.get("framework"),
        "enhance_strategy": state.get("enhance_strategy"),
        "word_count": state.get("word_count", 0),
        "media_id": publish.get("media_id"),
        "writing_persona": state.get("persona"),
        "dimensions": state.get("dimensions", []),
        "closing_type": state.get("closing_type"),
        "quality_score": seo.get("quality_score"),
        "editorial": state.get("editorial", {}),
        "provenance": state.get("provenance", {}),
        "status": state.get("status"),
        "stats": None,
    }


def finish_run(patch: dict | None = None, run_id: str | None = None) -> dict:
    state = load_run(run_id)
    if state.get("status") == "completed":
        return state
    if patch:
        blocked = PROTECTED_FIELDS.intersection(patch)
        if blocked:
            raise ValueError(
                "Protected run fields cannot be changed: " + ", ".join(sorted(blocked))
            )
        artifact_patch = patch.get("artifacts", {})
        if isinstance(artifact_patch, dict) and PROTECTED_ARTIFACTS.intersection(artifact_patch):
            raise ValueError("Core artifact paths are immutable")
        _deep_merge(state, patch)
    article_rel = (state.get("artifacts") or {}).get("article")
    article_path = home() / article_rel if article_rel else None
    if not article_path or not article_path.is_file() or not article_path.read_text(encoding="utf-8").strip():
        raise ValueError("Cannot finish run before a non-empty article is saved")
    draft_rel = (state.get("artifacts") or {}).get("draft")
    draft_path = home() / draft_rel if draft_rel else None
    if draft_path and draft_path.is_file() and draft_path.read_text(encoding="utf-8").strip():
        editorial = state.get("editorial") or {}
        report_rel = (state.get("artifacts") or {}).get("review_report")
        report_path = home() / report_rel if report_rel else None
        try:
            report = json.loads(report_path.read_text(encoding="utf-8")) if report_path else {}
        except (OSError, json.JSONDecodeError):
            report = {}
        if (
            editorial.get("decision") != "pass"
            or editorial.get("publishable") is not True
            or report.get("decision") != "pass"
            or report.get("publishable") is not True
        ):
            raise ValueError("Cannot finish a drafted article before editorial review passes")
    sources_file = run_dir(state["run_id"]) / "sources.yaml"
    if sources_file.exists():
        source_data = yaml.safe_load(sources_file.read_text(encoding="utf-8")) or {}
        sources = source_data.get("sources", []) if isinstance(source_data, dict) else []
        provenance = state.setdefault("provenance", {})
        provenance["verified_sources"] = sum(
            1 for item in sources if item.get("status") == "verified"
        )
        provenance["unverified_sources"] = sum(
            1 for item in sources if item.get("status") != "verified"
        )
    state["status"] = "completed"
    state["last_error"] = None
    _write_state(state)
    upsert_article(_history_entry(state))
    return state


def state_as_json(state: dict) -> str:
    return json.dumps(state, ensure_ascii=False, indent=2)
