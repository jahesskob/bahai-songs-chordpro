from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote

import requests


class ApiError(RuntimeError):
    """Raised when the REST API cannot be queried or validated."""


class SongApiClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def fetch_songs(self) -> dict[str, dict[str, Any]]:
        payload = self._get_json(f"{self.base_url}/api/v0/songs")
        songs = payload.get("songs")
        if not isinstance(songs, list):
            raise ApiError(
                f"Invalid payload from {self.base_url}/api/v0/songs: expected a top-level 'songs' array"
            )

        song_map: dict[str, dict[str, Any]] = {}
        for item in songs:
            if not isinstance(item, dict):
                raise ApiError(
                    f"Invalid payload from {self.base_url}/api/v0/songs: each item in 'songs' must be an object"
                )
            slug = item.get("slug")
            if not slug:
                raise ApiError(
                    f"Invalid payload from {self.base_url}/api/v0/songs: each song must include 'slug'"
                )
            song_map[slug] = item
        return song_map

    def fetch_song(self, slug: str) -> dict[str, Any]:
        url = f"{self.base_url}/api/v0/songs/{slug}"
        payload = self._get_json(url, slug=slug)
        song = payload.get("song")
        if not isinstance(song, dict):
            raise ApiError(
                f"Invalid payload from {url}: expected a top-level 'song' object"
            )
        return song

    def _get_json(self, url: str, slug: str | None = None) -> dict[str, Any]:
        try:
            response = requests.get(url, timeout=30)
        except requests.RequestException as exc:
            raise ApiError(f"REST request failed for {url}: {exc}") from exc

        if response.status_code == 404 and slug:
            raise ApiError(f"No song with slug: {slug}")
        if not response.ok:
            raise ApiError(
                f"REST request failed for {url}: HTTP {response.status_code} - {response.text[:500]}"
            )

        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise ApiError(f"Invalid JSON response from {url}") from exc

        if not isinstance(payload, dict):
            raise ApiError(f"Invalid payload from {url}: expected a JSON object")
        return payload


class SheetUploadClient:
    def __init__(self, site_url: str, secret: str) -> None:
        self.site_url = site_url.rstrip("/")
        self.secret = secret

    def upload_sheet(self, slug: str, sheet: str) -> None:
        encoded_slug = quote(slug, safe="")
        url = f"{self.site_url}/api/v0/songs/{encoded_slug}/sheet"

        try:
            response = requests.put(
                url,
                headers={
                    "Authorization": f"Bearer {self.secret}",
                    "Content-Type": "application/json",
                },
                json={"sheet": sheet},
                timeout=30,
            )
        except requests.RequestException as exc:
            raise ApiError(f"REST request failed for {url}: {exc}") from exc

        if response.status_code == 204:
            return

        error = self._extract_error(response)
        raise ApiError(error)

    def _extract_error(self, response: requests.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return f"HTTP {response.status_code} - {response.text[:500]}"

        if isinstance(payload, dict) and isinstance(payload.get("error"), str):
            return payload["error"]
        return f"HTTP {response.status_code} - {response.text[:500]}"
