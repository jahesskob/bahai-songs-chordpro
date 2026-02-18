#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["requests", "dotenv"]
# ///

import os
import requests
import json
import sys
from dotenv import load_dotenv

# Load environment variables from a .env file in the parent directory
dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path)

CHORDPRO_DIR = "src"
REST_API_BASE_URL = os.getenv("REST_API_BASE_URL")
SHORT_URL = os.getenv("SHORT_URL")

if not REST_API_BASE_URL:
    sys.exit("Missing required environment variable: REST_API_BASE_URL")
if not SHORT_URL:
    sys.exit("Missing required environment variable: SHORT_URL")

list_url = "{base}/api/v0/songs".format(base=REST_API_BASE_URL.rstrip("/"))
try:
    r = requests.get(list_url, timeout=30)
except requests.RequestException as exc:
    sys.exit("REST request failed for {url}: {error}".format(url=list_url, error=exc))
if not r.ok:
    sys.exit(
        "REST request failed for {url}: HTTP {status} - {body}".format(
            url=list_url,
            status=r.status_code,
            body=r.text[:500],
        )
    )

try:
    json_data = r.json()
except json.JSONDecodeError:
    sys.exit("Invalid JSON response from {url}".format(url=list_url))

if "songs" not in json_data or not isinstance(json_data["songs"], list):
    sys.exit(
        "Invalid payload from {url}: expected a top-level 'songs' array".format(
            url=list_url
        )
    )

songs = {}
for song in json_data["songs"]:
    if not isinstance(song, dict):
        sys.exit("Invalid payload from {url}: each item in 'songs' must be an object".format(url=list_url))
    slug = song.get("slug")
    if not slug:
        sys.exit("Invalid payload from {url}: each song must include 'slug'".format(url=list_url))
    songs[slug] = song

def get_title(song):
    """Tite of song"""
    return song['title']

def get_words(song):
    """Authors of the text the song is based on"""
    return song["words"]

def get_music(song):
    """Artists who intoned the text"""
    return song["music"] or ""

def get_song_url(song):
    """Get URL of song"""
    return SHORT_URL + song['slug']

chordpro_file_names = os.listdir(CHORDPRO_DIR)

for file_name in chordpro_file_names:
    if not file_name.startswith("."):
        slug = file_name[:-4]
        song = songs[slug]
        missing_keys = [key for key in ["title", "words", "music", "slug"] if key not in song]
        if missing_keys:
            sys.exit(
                "Invalid payload for slug '{slug}': missing key(s): {keys}".format(
                    slug=slug,
                    keys=", ".join(missing_keys),
                )
            )
        title = get_title(song)
        words = get_words(song)
        music = get_music(song)
        song_url = get_song_url(song)
        title_line = f"{{title: {title}}}\n"
        words_line = f"{{words: {words}}}\n"
        music_line = f"{{music: {music}}}\n"
        song_url_line = f"{{song_url: {song_url}}}\n"
        new_lines = [title_line, words_line, music_line, song_url_line]
        with open(os.path.join(CHORDPRO_DIR, file_name), 'r') as f:
            lines = f.readlines()
            for line in lines:
                if line.startswith("{title:") or line.startswith("{words:") or line.startswith("{music:") or line.startswith("{song_url:"):
                    pass
                else:
                    new_lines.append(line)
        with open(os.path.join(CHORDPRO_DIR, file_name), 'w') as f:
            for line in new_lines:
                f.write(line)
