from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import typer

from cli.api import ApiError, SongApiClient
from cli.config import load_settings
from cli.utils import format_excerpts, format_songsheet, get_music, get_translation


YT_DESCRIPTION = """\
Download a song sheet with lyrics and chords
{song_url}


▬ Based on ▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬

{based_on}


▬ Translation ▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬

{translation}


▬ Lyrics & Chords ▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬

{song_sheet}


▬ Music ▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬

{music}


▬ Language ▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬

{language}


▬ About bahá'í song project ▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬

bahá’í song project was launched in 2011 by a group of friends who wanted to encourage others to sing and play Bahá’í songs in their communities. Over the years it has become a resource for people from all around the world who share the understanding that singing prayers and sacred verses can bring much joy and vibrancy to a community, and resources for learning to sing and play songs should be easily accessible.


▬ Links ▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬

► Facebook: https://www.facebook.com/bahaisongproject
► Instagram: https://www.instagram.com/bahaisongproject​
► Twitter: https://twitter.com/bahaisongp​
► PayPal: https://www.paypal.com/paypalme/bahaisongproject
► Website: https://www.bahaisongproject.com
"""


app = typer.Typer(help="Generate description text.")


def _validate_song(song: dict[str, Any], slug: str) -> None:
    missing_keys = [key for key in ("excerpts", "languages") if key not in song]
    if missing_keys:
        joined = ", ".join(missing_keys)
        raise ValueError(f"Invalid payload for slug '{slug}': missing key(s): {joined}")


def _normalize_excerpts(song: dict[str, Any], slug: str) -> list[dict[str, Any]]:
    excerpts = song.get("excerpts")
    if excerpts is None:
        return []
    if not isinstance(excerpts, list):
        raise ValueError(f"Invalid payload for slug '{slug}': 'excerpts' must be a list")

    for index, excerpt in enumerate(excerpts):
        if not isinstance(excerpt, dict):
            raise ValueError(
                f"Invalid payload for slug '{slug}': excerpts[{index}] must be an object"
            )
        missing_excerpt_keys = [key for key in ("language", "source") if key not in excerpt]
        if missing_excerpt_keys:
            joined = ", ".join(missing_excerpt_keys)
            raise ValueError(
                f"Invalid payload for slug '{slug}': excerpts[{index}] missing key(s): {joined}"
            )
        if not isinstance(excerpt["language"], dict) or "nameEn" not in excerpt["language"]:
            raise ValueError(
                f"Invalid payload for slug '{slug}': excerpts[{index}].language.nameEn is required"
            )
        if not isinstance(excerpt["source"], dict):
            raise ValueError(
                f"Invalid payload for slug '{slug}': excerpts[{index}].source must be an object"
            )
        missing_source_keys = [
            key for key in ("author", "description", "excerpts") if key not in excerpt["source"]
        ]
        if missing_source_keys:
            joined = ", ".join(missing_source_keys)
            raise ValueError(
                f"Invalid payload for slug '{slug}': excerpts[{index}].source missing key(s): {joined}"
            )
        nested_excerpts = excerpt["source"]["excerpts"]
        if not isinstance(nested_excerpts, list):
            raise ValueError(
                f"Invalid payload for slug '{slug}': excerpts[{index}].source.excerpts must be a list"
            )
        if excerpt.get("text") in (None, ""):
            current_language = excerpt["language"]["nameEn"]
            same_language_match = next(
                (
                    nested
                    for nested in nested_excerpts
                    if isinstance(nested, dict)
                    and isinstance(nested.get("language"), dict)
                    and nested["language"].get("nameEn") == current_language
                    and nested.get("text")
                ),
                None,
            )
            fallback_match = next(
                (
                    nested
                    for nested in nested_excerpts
                    if isinstance(nested, dict) and nested.get("text")
                ),
                None,
            )
            selected = same_language_match or fallback_match
            if not selected:
                raise ValueError(
                    f"Invalid payload for slug '{slug}': excerpts[{index}] missing text and no usable text found in source.excerpts"
                )
            excerpt["text"] = selected["text"]
    return excerpts


def _render_song_sheet(song_path: Path) -> str:
    if not song_path.exists():
        raise FileNotFoundError(f"Local song sheet not found: {song_path}")
    if shutil.which("chordpro") is None:
        raise RuntimeError("Missing required executable: chordpro")

    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".txt") as temp_file:
        temp_path = Path(temp_file.name)

    try:
        result = subprocess.run(
            [
                "chordpro",
                str(song_path),
                "--generate=Text",
                "--no-strict",
                f"--output={temp_path}",
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        lyrics = temp_path.read_text()
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr or "Unknown error"
        raise RuntimeError(f"chordpro failed with exit code {exc.returncode}: {stderr}") from exc
    finally:
        temp_path.unlink(missing_ok=True)

    if result.stderr:
        typer.echo("WARNINGS:\n" + result.stderr, err=True)
    return lyrics


@app.command("generate")
def generate(
    slug: str = typer.Option(..., "--slug", help="Generate a description for a single song slug."),
) -> None:
    """Generate description text for a song."""
    try:
        settings = load_settings()
        client = SongApiClient(settings.rest_api_base_url)
        song = client.fetch_song(slug)
        _validate_song(song, slug)
        excerpts = _normalize_excerpts(song, slug)
        lyrics = _render_song_sheet(settings.src_dir / f"{slug}.pro")
    except (ApiError, ValueError, FileNotFoundError, RuntimeError, KeyError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    based_on = "\n\n".join(format_excerpts(excerpts)) if excerpts else ""

    translations: list[dict[str, Any]] = []
    for excerpt in excerpts:
        if excerpt["language"]["nameEn"] != "English":
            translation = get_translation(excerpt)
            if translation:
                translations.append(translation)

    translation_text = "\n\n".join(format_excerpts(translations)) if translations else ""

    try:
        music = get_music(song)
    except KeyError as exc:
        typer.echo(
            f"Invalid payload for slug '{slug}': missing key required for music: {exc}",
            err=True,
        )
        raise typer.Exit(code=1) from exc

    if not music:
        music = "Do you know who composed this song? Please let us know!\n💌  https://bsp.app/contact"

    languages = song.get("languages")
    if not isinstance(languages, list):
        typer.echo(f"Invalid payload for slug '{slug}': 'languages' must be a list", err=True)
        raise typer.Exit(code=1)

    language_names: list[str] = []
    for index, language in enumerate(languages):
        if not isinstance(language, dict) or "nameEn" not in language:
            typer.echo(
                f"Invalid payload for slug '{slug}': languages[{index}].nameEn is required",
                err=True,
            )
            raise typer.Exit(code=1)
        language_names.append(language["nameEn"])

    typer.echo(
        YT_DESCRIPTION.format(
            song_url=f"https://www.bahaisongproject.com/{slug}",
            based_on=based_on,
            translation=translation_text,
            song_sheet=format_songsheet(lyrics),
            music=music,
            language=", ".join(language_names),
        )
    )
