from __future__ import annotations

import re
from typing import Any


METADATA_PREFIXES = ("{title:", "{words:", "{music:", "{song_url:")


def get_music(song: dict[str, Any]) -> str:
    """Artists who intoned the text."""
    contributors = song.get("contributors")
    if not isinstance(contributors, list):
        raise KeyError("contributors")

    artists = [
        contributor["name"]
        for contributor in contributors
        if isinstance(contributor, dict) and contributor.get("name") is not None
    ]
    artists.sort()

    description = song.get("description")
    if not artists and description:
        return description
    if len(artists) > 2:
        return " & ".join([", ".join(artists[:-1]), artists[-1]])
    return " & ".join(artists)


def format_songsheet(song_sheet: str) -> str:
    """Format the songsheet to make sense in non-monospace fonts."""
    chord_pattern = re.compile(
        r"^[A-G](b|#)?(add|maj|min|m|M|\+|-|dim|aug)?[0-9]*(sus)?[0-9]*(/[A-G](b|#)?)?$"
    )

    trimmed_parts = re.compile(r"\n+").split(song_sheet, 1)
    if len(trimmed_parts) > 1:
        song_sheet = trimmed_parts[1]

    result_lines: list[str] = []
    for line in song_sheet.splitlines():
        chord_candidates = line.split()
        chord_flags = [bool(chord_pattern.match(candidate)) for candidate in chord_candidates]
        if chord_flags.count(False) >= chord_flags.count(True):
            result_lines.append(line)
        else:
            result_lines.append(" | ".join(chord_candidates))
    return "\n".join(result_lines)


def format_excerpts(excerpts: list[dict[str, Any]]) -> list[str]:
    formatted: list[str] = []
    for excerpt in excerpts:
        excerpt_text = excerpt["text"]
        excerpt_from = "{author}, {source}".format(
            author=excerpt["source"]["author"],
            source=excerpt["source"]["description"],
        )
        formatted.append(f"{excerpt_text}\n\n—{excerpt_from}")
    return formatted


def get_translation(excerpt: dict[str, Any], language: str = "English") -> dict[str, Any] | None:
    """Return translation excerpt if available."""
    source = excerpt.get("source")
    if not isinstance(source, dict):
        return None

    nested_excerpts = source.get("excerpts")
    if not isinstance(nested_excerpts, list):
        return None

    for nested in nested_excerpts:
        if (
            isinstance(nested, dict)
            and isinstance(nested.get("language"), dict)
            and nested["language"].get("nameEn") == language
        ):
            return nested
    return None


def build_metadata_lines(song: dict[str, Any], short_url: str) -> list[str]:
    missing_keys = [key for key in ("title", "words", "music", "slug") if key not in song]
    if missing_keys:
        joined = ", ".join(missing_keys)
        raise ValueError(
            f"Invalid payload for slug '{song.get('slug', '<unknown>')}': missing key(s): {joined}"
        )

    return [
        f"{{title: {song['title']}}}\n",
        f"{{words: {song['words']}}}\n",
        f"{{music: {song['music'] or ''}}}\n",
        f"{{song_url: {short_url}{song['slug']}}}\n",
    ]


def apply_metadata(content: str, metadata_lines: list[str]) -> str:
    body_lines = [
        line
        for line in content.splitlines(keepends=True)
        if not line.startswith(METADATA_PREFIXES)
    ]
    return "".join(metadata_lines + body_lines)
