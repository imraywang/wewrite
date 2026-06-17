"""环境配置 —— 平台密钥池、模型、路径等都从环境变量读取。"""
from __future__ import annotations

import os
import tempfile
from functools import lru_cache
from pathlib import Path


def _repo_root_guess() -> Path:
    # 本文件位于 <repo>/web/backend/app/config.py → 上溯 3 层即仓库根
    return Path(__file__).resolve().parents[3]


class Settings:
    def __init__(self) -> None:
        self.anthropic_api_key: str = os.environ.get("ANTHROPIC_API_KEY", "")
        self.model: str = os.environ.get("WEWRITE_MODEL", "claude-opus-4-8")

        # 平台图片密钥池
        self.image_provider: str = os.environ.get("WEWRITE_IMAGE_PROVIDER", "")
        self.image_api_key: str = os.environ.get("WEWRITE_IMAGE_API_KEY", "")
        self.image_secret_key: str = os.environ.get("WEWRITE_IMAGE_SECRET_KEY", "")
        # 自定义图片服务（如 Sub2API 网关）的 base_url 与模型
        self.image_base_url: str = os.environ.get("WEWRITE_IMAGE_BASE_URL", "")
        self.image_model: str = os.environ.get("WEWRITE_IMAGE_MODEL", "")

        self.app_secret_key: str = os.environ.get("APP_SECRET_KEY", "")

        # 小红书：xiaohongshu-mcp 的 MCP 端点（如 http://localhost:18060/mcp）
        self.xhs_mcp_url: str = os.environ.get("XHS_MCP_URL", "")

        skill_dir = os.environ.get("WEWRITE_SKILL_DIR", "")
        self.skill_dir: Path = Path(skill_dir).resolve() if skill_dir else _repo_root_guess()

        ws_root = os.environ.get("WEWRITE_WORKSPACE_ROOT", "")
        self.workspace_root: Path = Path(ws_root).resolve() if ws_root else None  # None → 系统临时目录

        # 任务产物（生成的图片）持久化目录 —— 工作区清理后仍保留，供预览与发布使用。
        # NOTE(生产): 换成对象存储（S3/OSS）+ CDN，而非本机磁盘。
        art_root = os.environ.get("WEWRITE_ARTIFACT_ROOT", "")
        self.artifact_root: Path = (
            Path(art_root).resolve()
            if art_root
            else Path(tempfile.gettempdir()) / "wewrite-artifacts"
        )
        # 拼绝对 URL 用的公开基址（可选）。留空则产物用相对路径 /artifacts/...
        self.public_base_url: str = os.environ.get("WEWRITE_PUBLIC_BASE_URL", "").rstrip("/")

        self.max_turns: int = int(os.environ.get("WEWRITE_MAX_TURNS", "120"))
        self.cors_origins: list[str] = [
            o.strip()
            for o in os.environ.get("WEWRITE_CORS_ORIGINS", "http://localhost:3000").split(",")
            if o.strip()
        ]

    def image_config(self) -> dict | None:
        """构造写入工作区 config.yaml 的 image 段（平台统一出 key）。"""
        if not self.image_provider or not self.image_api_key:
            return None
        cfg: dict = {"provider": self.image_provider, "api_key": self.image_api_key}
        if self.image_base_url:
            cfg["base_url"] = self.image_base_url
        if self.image_model:
            cfg["model"] = self.image_model
        if self.image_secret_key:
            cfg["secret_key"] = self.image_secret_key
        return cfg


@lru_cache
def get_settings() -> Settings:
    return Settings()
