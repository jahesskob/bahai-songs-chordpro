from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PACKAGE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SHORT_URL = "https://bsp.app/"


@dataclass(frozen=True)
class Settings:
    root_dir: Path
    site_url: str
    rest_api_base_url: str
    short_url: str
    chordpro_dir: Path
    song_sheet_update_secret: str | None


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


def _strip_jsonc_comments(content: str) -> str:
    result: list[str] = []
    index = 0
    in_string = False
    escape = False

    while index < len(content):
        char = content[index]
        next_char = content[index + 1] if index + 1 < len(content) else ""

        if in_string:
            result.append(char)
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            index += 1
            continue

        if char == '"':
            in_string = True
            result.append(char)
            index += 1
            continue

        if char == "/" and next_char == "/":
            index += 2
            while index < len(content) and content[index] not in "\r\n":
                index += 1
            continue

        if char == "/" and next_char == "*":
            index += 2
            while index + 1 < len(content) and content[index : index + 2] != "*/":
                index += 1
            index += 2
            continue

        result.append(char)
        index += 1

    without_comments = "".join(result)
    return re.sub(r",(\s*[}\]])", r"\1", without_comments)


def _config_paths() -> tuple[Path, Path]:
    config_dir = Path.home() / ".bsp"
    return (config_dir / "bsp.jsonc", config_dir / "bsp.json")


def _load_user_config() -> dict[str, Any]:
    config_path = next((path for path in _config_paths() if path.exists()), None)
    if config_path is None:
        return {}

    try:
        content = config_path.read_text(encoding="utf-8")
        if config_path.suffix == ".jsonc":
            content = _strip_jsonc_comments(content)
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {config_path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError(f"Invalid config in {config_path}: expected a JSON object")
    return payload


def _get_env_config(config: dict[str, Any], env_name: str) -> dict[str, Any]:
    env_config = config.get(env_name, {})
    if env_config is None:
        return {}
    if not isinstance(env_config, dict):
        raise ValueError(f"Invalid BSP config: '{env_name}' must be an object")
    return env_config


def _get_config_string(config: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = config.get(key)
        if value is not None:
            if not isinstance(value, str):
                raise ValueError(f"Invalid BSP config: '{key}' must be a string")
            return value
    return None


def _resolve_config_path(root_dir: Path, value: str) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return root_dir / path


def load_settings(prod: bool = False) -> Settings:
    root_dir = _find_workspace_root()

    user_config = _load_user_config()
    env_name = "prod" if prod else "dev"
    env_config = _get_env_config(user_config, env_name)

    configured_site_url = _get_config_string(env_config, "baseUrl", "base_url", "siteUrl", "site_url")
    if not configured_site_url:
        raise ValueError(
            "Missing baseUrl for '{env}' in ~/.bsp/bsp.jsonc or ~/.bsp/bsp.json".format(
                env=env_name
            )
        )

    configured_secret = _get_config_string(
        env_config,
        "songSheetUpdateSecret",
        "song_sheet_update_secret",
        "secret",
    )
    configured_chordpro_dir = _get_config_string(
        user_config,
        "chordproDir",
        "chordpro_dir",
        "chordProDir",
    )
    if not configured_chordpro_dir:
        raise ValueError(
            "Missing top-level chordproDir in ~/.bsp/bsp.jsonc or ~/.bsp/bsp.json"
        )

    short_url = _get_config_string(env_config, "shortUrl", "short_url") or DEFAULT_SHORT_URL

    return Settings(
        root_dir=root_dir,
        site_url=configured_site_url.rstrip("/"),
        rest_api_base_url=configured_site_url.rstrip("/"),
        short_url=short_url,
        chordpro_dir=_resolve_config_path(root_dir, configured_chordpro_dir),
        song_sheet_update_secret=configured_secret,
    )
