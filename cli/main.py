from __future__ import annotations

import typer

from cli.description import app as description_app
from cli.sheet import app as sheet_app


root_app = typer.Typer(help="Bahá'í songs project CLI.")
root_app.add_typer(sheet_app, name="sheet")
root_app.add_typer(description_app, name="description")


def app() -> None:
    root_app()
