# 🎵 YouTube Music Downloader

A command-line tool that downloads audio from YouTube/YouTube Music, converts it to MP3, and automatically fetches high-quality metadata (title, artist, album, cover art) from the Deezer API.

---

## Features

- Downloads audio from any YouTube or YouTube Music URL
- Converts to MP3 at 192kbps
- Fetches accurate metadata from Deezer (title, artist, album, cover art)
- Embeds ID3v2.3 tags — compatible with Windows, Spotify, and most media players
- Falls back to YouTube metadata if no Deezer match is found
- Supports playlists

---

## Requirements

### Python packages

Install all dependencies with:

```bash
pip install -r requirements.txt
```

### FFmpeg (required)

FFmpeg is required for audio extraction. Install it for your OS:

| OS      | Command                        |
|---------|--------------------------------|
| Windows | `winget install ffmpeg`        |
| macOS   | `brew install ffmpeg`          |
| Linux   | `sudo apt install ffmpeg`      |

---

## Installation

```bash
git clone https://github.com/yourname/yourrepo.git
cd yourrepo
pip install -r requirements.txt
```

---

## Usage

```bash
python cek.py <YouTube or YouTube Music URL>
```

### Examples

```bash
# Single track
python cek.py "https://music.youtube.com/watch?v=..."

```

Downloaded MP3s are saved to a `downloads/` folder in the current directory.

---

## How It Works

1. `yt-dlp` fetches and downloads the best available audio stream from the URL.
2. FFmpeg converts the audio to MP3 at 192kbps.
3. The script queries the **Deezer API** using the track title and artist to find matching metadata.
4. Metadata (title, artist, album, cover art) is embedded into the MP3 as ID3 tags using `mutagen`.
5. If no Deezer match is found, YouTube metadata is used as a fallback.

---

## Output

```
downloads/
└── Track Title.mp3   ← MP3 with embedded metadata and cover art
```

---

## Notes

- Cover art is sourced from Deezer at the highest available resolution (`cover_xl`).
- Tags are saved as **ID3v2.3** for maximum compatibility.
- Year metadata is taken from the YouTube upload date when Deezer doesn't provide it.

---

## License

MIT
