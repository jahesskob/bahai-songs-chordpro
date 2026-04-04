from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PACKAGE_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    root_dir: Path
    rest_api_base_url: str
    short_url: str
    src_dir: Path


def _find_workspace_root() -> Path:
    cwd = Path.cwd().resolve()
    candidates = [cwd, *cwd.parents]

    for candidate in candidates:
        has_src = (candidate / "src").is_dir()
        has_repo_marker = any(
            (candidate / marker).exists()
            for marker in (".env", "pyproject.toml", "Makefile", ".git")
        )
        if has_src and has_repo_marker:
            return candidate

    return cwd


def load_settings() -> Settings:
    root_dir = _find_workspace_root()
    load_dotenv(root_dir / ".env")

    rest_api_base_url = os.getenv("REST_API_BASE_URL")
    if not rest_api_base_url:
        raise ValueError("Missing required environment variable: REST_API_BASE_URL")

    short_url = os.getenv("SHORT_URL") or "https://www.bahaisongproject.com/"

    return Settings(
        root_dir=root_dir,
        rest_api_base_url=rest_api_base_url.rstrip("/"),
        short_url=short_url,
        src_dir=root_dir / "src",
    )
