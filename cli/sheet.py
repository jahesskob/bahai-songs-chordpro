from __future__ import annotations

from pathlib import Path

import typer

from cli.api import ApiError, SongApiClient
from cli.config import load_settings
from cli.utils import apply_metadata, build_metadata_lines


app = typer.Typer(help="Work with local song sheets.")


def _enrich_file(
    sheet_path: Path,
    song: dict,
    short_url: str,
    dry_run: bool,
) -> bool:
    original = sheet_path.read_text()
    updated = apply_metadata(original, build_metadata_lines(song, short_url))
    changed = updated != original

    if dry_run:
        status = "Would update" if changed else "No change"
        typer.echo(f"{status}: {sheet_path.name}")
        return changed

    if changed:
        sheet_path.write_text(updated)
        typer.echo(f"Updated: {sheet_path.name}")
    else:
        typer.echo(f"No change: {sheet_path.name}")
    return changed


@app.command("enrich")
def enrich(
    slug: str | None = typer.Option(None, "--slug", help="Enrich a single song sheet by slug."),
    all_sheets: bool = typer.Option(False, "--all", help="Enrich all local song sheets."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview changes without writing files."),
) -> None:
    """Enrich local ChordPro song sheets with API metadata."""
    if bool(slug) == all_sheets:
        raise typer.BadParameter("Specify exactly one of --slug or --all.")

    try:
        settings = load_settings()
        client = SongApiClient(settings.rest_api_base_url)
        remote_songs = client.fetch_songs()
    except (ApiError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    if slug:
        sheet_path = settings.src_dir / f"{slug}.pro"
        if not sheet_path.exists():
            typer.echo(f"Local song sheet not found: {sheet_path}", err=True)
            raise typer.Exit(code=1)

        song = remote_songs.get(slug)
        if song is None:
            typer.echo(f"No song with slug: {slug}", err=True)
            raise typer.Exit(code=1)

        try:
            _enrich_file(sheet_path, song, settings.short_url, dry_run)
        except ValueError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(code=1) from exc
        return

    warnings: list[str] = []
    changed_count = 0
    for sheet_path in sorted(settings.src_dir.glob("*.pro")):
        song_slug = sheet_path.stem
        song = remote_songs.get(song_slug)
        if song is None:
            warnings.append(song_slug)
            continue

        try:
            if _enrich_file(sheet_path, song, settings.short_url, dry_run):
                changed_count += 1
        except ValueError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(code=1) from exc

    if warnings:
        typer.echo(
            "Warnings: skipped local sheets with no matching API song: "
            + ", ".join(warnings),
            err=True,
        )

    action = "would change" if dry_run else "changed"
    typer.echo(f"Summary: {changed_count} sheet(s) {action}.")
