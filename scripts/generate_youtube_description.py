#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["requests", "dotenv"]
# ///
import argparse
import json
import os
import subprocess
import sys
import tempfile

import requests
from dotenv import load_dotenv
from utils import format_excerpts, format_songsheet, get_music, get_translation

# Load environment variables from a .env file in the parent directory
dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path)

CHORDPRO_DIR = "src"
REST_API_BASE_URL = os.getenv("REST_API_BASE_URL")

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


def main(args):
    if not REST_API_BASE_URL:
        sys.exit("Missing required environment variable: REST_API_BASE_URL")

    song_url = "{base}/api/v0/songs/{slug}".format(
        base=REST_API_BASE_URL.rstrip("/"),
        slug=args.slug,
    )
    try:
        r = requests.get(song_url, timeout=30)
    except requests.RequestException as exc:
        sys.exit("REST request failed for {url}: {error}".format(url=song_url, error=exc))
    if r.status_code == 404:
        sys.exit("No song with slug: {slug}".format(slug=args.slug))
    if not r.ok:
        sys.exit(
            "REST request failed for {url}: HTTP {status} - {body}".format(
                url=song_url,
                status=r.status_code,
                body=r.text[:500],
            )
        )

    try:
        json_data = r.json()
    except json.JSONDecodeError:
        sys.exit("Invalid JSON response from {url}".format(url=song_url))

    if "song" not in json_data or not isinstance(json_data["song"], dict):
        sys.exit(
            "Invalid payload from {url}: expected a top-level 'song' object".format(
                url=song_url
            )
        )
    song_data = json_data["song"]

    required_song_keys = ["excerpts", "languages"]
    missing_song_keys = [key for key in required_song_keys if key not in song_data]
    if missing_song_keys:
        sys.exit(
            "Invalid payload for slug '{slug}': missing key(s): {keys}".format(
                slug=args.slug,
                keys=", ".join(missing_song_keys),
            )
        )

    yt_description_data = {}
    yt_description_data["based_on"] = ""
    yt_description_data["translation"] = ""

    # Song URL
    yt_description_data["song_url"] = "https://www.bahaisongproject.com/{slug}".format(
        slug=args.slug
    )

    # Based on
    if song_data["excerpts"] is not None:
        if not isinstance(song_data["excerpts"], list):
            sys.exit(
                "Invalid payload for slug '{slug}': 'excerpts' must be a list".format(
                    slug=args.slug
                )
            )
        for i, excerpt in enumerate(song_data["excerpts"]):
            if not isinstance(excerpt, dict):
                sys.exit(
                    "Invalid payload for slug '{slug}': excerpts[{index}] must be an object".format(
                        slug=args.slug,
                        index=i,
                    )
                )
            missing_excerpt_keys = [key for key in ["language", "source"] if key not in excerpt]
            if missing_excerpt_keys:
                sys.exit(
                    "Invalid payload for slug '{slug}': excerpts[{index}] missing key(s): {keys}".format(
                        slug=args.slug,
                        index=i,
                        keys=", ".join(missing_excerpt_keys),
                    )
                )
            if not isinstance(excerpt["language"], dict) or "nameEn" not in excerpt["language"]:
                sys.exit(
                    "Invalid payload for slug '{slug}': excerpts[{index}].language.nameEn is required".format(
                        slug=args.slug,
                        index=i,
                    )
                )
            if not isinstance(excerpt["source"], dict):
                sys.exit(
                    "Invalid payload for slug '{slug}': excerpts[{index}].source must be an object".format(
                        slug=args.slug,
                        index=i,
                    )
                )
            missing_source_keys = [
                key
                for key in ["author", "description", "excerpts"]
                if key not in excerpt["source"]
            ]
            if missing_source_keys:
                sys.exit(
                    "Invalid payload for slug '{slug}': excerpts[{index}].source missing key(s): {keys}".format(
                        slug=args.slug,
                        index=i,
                        keys=", ".join(missing_source_keys),
                    )
                )
            if not isinstance(excerpt["source"]["excerpts"], list):
                sys.exit(
                    "Invalid payload for slug '{slug}': excerpts[{index}].source.excerpts must be a list".format(
                        slug=args.slug,
                        index=i,
                    )
                )

            # REST payload parity fallback:
            # if top-level excerpt text is omitted/null, derive from source.excerpts.
            if "text" not in excerpt or excerpt["text"] in (None, ""):
                current_lang = excerpt["language"]["nameEn"]
                same_language_match = next(
                    (
                        nested
                        for nested in excerpt["source"]["excerpts"]
                        if isinstance(nested, dict)
                        and isinstance(nested.get("language"), dict)
                        and nested["language"].get("nameEn") == current_lang
                        and nested.get("text")
                    ),
                    None,
                )
                fallback_match = next(
                    (
                        nested
                        for nested in excerpt["source"]["excerpts"]
                        if isinstance(nested, dict) and nested.get("text")
                    ),
                    None,
                )
                selected = same_language_match or fallback_match
                if not selected:
                    sys.exit(
                        "Invalid payload for slug '{slug}': excerpts[{index}] missing text and no usable text found in source.excerpts".format(
                            slug=args.slug,
                            index=i,
                        )
                    )
                excerpt["text"] = selected["text"]
        all_excerpts_formatted = format_excerpts(song_data["excerpts"])
        yt_description_data["based_on"] = "\n\n".join(all_excerpts_formatted)

    # Translation
    if song_data["excerpts"] is not None:
        all_translations = []
        for excerpt in song_data["excerpts"]:
            # Look up translation if excerpt is not in English
            if excerpt["language"]["nameEn"] != "English":
                translation = get_translation(excerpt)
                if translation:
                    all_translations.append(translation)
        if all_translations:
            all_translations_formatted = format_excerpts(all_translations)
            all_translations_joined = "\n\n".join(all_translations_formatted)
        yt_description_data["translation"] = (
            all_translations_joined if all_translations else ""
        )

    # Create temporary file with explicit cleanup
    with tempfile.NamedTemporaryFile(
        mode="w+", delete=False, suffix=".txt"
    ) as temp_file:
        temp_path = temp_file.name

    try:
        # Verify chordpro installation
        subprocess.run(
            ["which", "chordpro"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Generate lyrics to temporary file
        cmd = [
            "chordpro",
            f"{CHORDPRO_DIR}/{args.slug}.pro",
            "--generate=Text",
            "--no-strict",
            f"--output={temp_path}",
        ]

        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True
        )

        # Read generated content
        with open(temp_path, "r") as f:
            lyrics = f.read()

        if result.stderr:
            print("WARNINGS:\n" + result.stderr)

    except subprocess.CalledProcessError as e:
        print(f"Error {e.returncode}: {e.stderr or 'Unknown error'}")

    finally:
        # Cleanup temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)

    song_sheet_formatted = format_songsheet(lyrics)
    yt_description_data["song_sheet"] = song_sheet_formatted

    # Music
    try:
        music = get_music(song_data)
    except KeyError as exc:
        sys.exit(
            "Invalid payload for slug '{slug}': missing key required for music: {key}".format(
                slug=args.slug,
                key=exc,
            )
        )
    if not music:
        music = "Do you know who composed this song? Please let us know!\n💌  https://bsp.app/contact"
    yt_description_data["music"] = music

    # Language
    if not isinstance(song_data["languages"], list):
        sys.exit(
            "Invalid payload for slug '{slug}': 'languages' must be a list".format(
                slug=args.slug
            )
        )
    for i, language in enumerate(song_data["languages"]):
        if not isinstance(language, dict) or "nameEn" not in language:
            sys.exit(
                "Invalid payload for slug '{slug}': languages[{index}].nameEn is required".format(
                    slug=args.slug,
                    index=i,
                )
            )
    languages = [language["nameEn"] for language in song_data["languages"]]
    yt_description_data["language"] = ", ".join(languages)

    yt_description_formatted = YT_DESCRIPTION.format(
        song_url=yt_description_data["song_url"],
        based_on=yt_description_data["based_on"],
        song_sheet=yt_description_data["song_sheet"],
        music=yt_description_data["music"],
        language=yt_description_data["language"],
        translation=yt_description_data["translation"],
    )
    print(yt_description_formatted)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate YouTube description for bsp videos"
    )
    parser.add_argument(
        "--slug", metavar="S", type=str, required=True, help="slug of song"
    )
    args = parser.parse_args()
    main(args)
