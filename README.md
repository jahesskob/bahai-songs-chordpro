# Bahá'í Songs
![](https://github.com/bahaisongproject/bahai-songs/actions/workflows/deploy.yml/badge.svg)

A collection of songs inspired by the Bahá'í writings in ChordPro notation
- Learn more about the [Bahá'í Faith](https://www.bahai.org/)
- Learn more about [ChordPro](https://www.chordpro.org)
- Check out Bahá'í songs with lyrics, chords and videos on [bahaisongproject.com](https://www.bahaisongproject.com)


## Getting Started
1. Install requirements:
  - macOS
     -  ChordPro: [binary installation](https://www.chordpro.org/chordpro/install-macos-native/) or `sudo cpan chordpro` ([detailed instructions](https://www.chordpro.org/chordpro/chordpro-install-on-macos/))
     - exiftool: `brew install exiftool`
   - Linux:
     - ChordPro: `sudo cpan install chordpro`
     - exiftool: `sudo apt install libimage-exiftool-perl`
2. Install the CLI with `uv tool install .`
3. Use Makefile
  - Make song sheets with `make`
  - Make song book with `make songbook`
  - Empty public/ directory with `make clean`

## Updating song sheets with data from the bahá'í song project API
Use `bsp sheet enrich --all` to update local source files with data from the bahá'í song project API.
The matching of ChordPro source files with database records happens based on the file name.
If a database record is found for a ChordPro source file, the script will add/update:
- `{title: New Title}`
- `{music: Composer A, Composer B & Composer C}`
- `{words: Author A, Author B & Author C}`
- `{song_url: https://bsp.app/...}` (for creating a link to the song in the footer)

Use `bsp sheet enrich --slug some-song --dry-run` to preview the changes for a single song.

Use `bsp sheet upload --slug some-song` to update the database sheet from a local ChordPro file. Use `bsp sheet upload --all` to upload every file in the configured ChordPro directory.

The CLI uses the `dev` config by default. Pass `--prod` to use the `prod` config for any command that talks to Convex.

Configure local endpoints and upload secrets in `~/.bsp/bsp.jsonc` or `~/.bsp/bsp.json`:

```jsonc
{
  "chordproDir": "/absolute/path/to/bahai-songs-chordpro/src",
  "dev": {
    "baseUrl": "https://your-dev.convex.site",
    "shortUrl": "https://bsp.app/",
    "songSheetUpdateSecret": "dev-secret"
  },
  "prod": {
    "baseUrl": "https://your-prod.convex.site",
    "songSheetUpdateSecret": "prod-secret"
  }
}
```

Top-level `chordproDir` is required. Relative paths are resolved from the repository root, but an absolute path lets you run the CLI from anywhere. The upload command also requires `songSheetUpdateSecret`.

Use `bsp description generate --slug some-song` to print the current description text for a song.

## Deployment
Pushing to this repo triggers a build with GitHub Actions. The PDFs and additional deployment artifacts are deployed to Netlify. Song sheets are available at https://bahaisongproject.com/song-title.pdf.

## Contributing
Please submit pull requests to fix mistakes and add new songs

## Licenses
- **Songs** Copyrights belong to their respective owners
- **Makefile and CLI code** Copyright © 2020–2024 Dayyan Smith, [MIT License](https://opensource.org/licenses/MIT)
