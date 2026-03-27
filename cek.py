import yt_dlp
import sys
import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS # Allows the browser to talk to the server

from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TCON, TRCK, APIC, ID3NoHeaderError
from mutagen.mp3 import MP3


def get_deezer_metadata(title, artist):
    try:
        query = f"{title} {artist}"
        r = requests.get(f"https://api.deezer.com/search?q={requests.utils.quote(query)}&limit=1", timeout=10)
        data = r.json()
        tracks = data.get("data", [])
        if not tracks:
            print("No Deezer match found, using YouTube metadata.")
            return None

        track = tracks[0]
        album_id = track["album"]["id"]
        album_data = requests.get(
            f"https://api.deezer.com/album/{album_id}",
            timeout=10
        ).json()

        year = album_data.get("release_date", "")[:4]
        return {
            "title": track["title"],
            "artist": track["artist"]["name"],
            "album": track["album"]["title"],
            "year": year,  
            "track_number": "",
            "thumbnail": track["album"]["cover_xl"],  # high quality cover art
        }
    except Exception as e:
        print(f"Deezer error: {e}")
        return None

def embed_metadata(filepath, meta):
    try:
        audio = MP3(filepath, ID3=ID3)
    except ID3NoHeaderError:
        audio = MP3(filepath)
        audio.add_tags()

    tags = audio.tags

    # Clear any existing tags first to avoid conflicts
    tags.delall("APIC")
    tags.delall("TIT2")
    tags.delall("TPE1")
    tags.delall("TALB")
    tags.delall("TDRC")
    tags.delall("TRCK")

    tags.add(TIT2(encoding=3, text=meta.get("title", "")))
    tags.add(TPE1(encoding=3, text=meta.get("artist", "")))
    tags.add(TALB(encoding=3, text=meta.get("album", "")))
    tags.add(TDRC(encoding=3, text=meta.get("year", "")))
    tags.add(TRCK(encoding=3, text=meta.get("track_number", "")))

    thumb_url = meta.get("thumbnail")
    if thumb_url:
        try:
            img_data = requests.get(thumb_url, timeout=10).content
            tags.add(APIC(
                encoding=0,        # 0 = Latin-1, more compatible
                mime="image/jpeg",
                type=3,            # 3 = Cover (front)
                desc="",           # empty desc is more compatible
                data=img_data,
            ))
            print("Album art embedded.")
        except Exception as e:
            print(f"Could not embed thumbnail: {e}")

    audio.save(v2_version=3)  # Save as ID3v2.3 — most compatible with Windows/Spotify
    print(f"Metadata embedded: {os.path.basename(filepath)}")

def download_music(url, output_dir="downloads"):
    os.makedirs(output_dir, exist_ok=True)

    downloaded_files = []

    def capture_filename(d):
        if d["status"] == "finished":
            downloaded_files.append(d["filename"])

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": f"{output_dir}/%(title)s.%(ext)s",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "quiet": False,
        "progress_hooks": [capture_filename],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = yt_dlp.YoutubeDL({"quiet": True}).extract_info(url, download=False)
        ydl.download([url])

        entries = info.get("entries", [info])
        for i, entry in enumerate(entries):
            yt_title = entry.get("title", "unknown")
            yt_artist = entry.get("artist") or entry.get("uploader", "")


            if i < len(downloaded_files):
                base = os.path.splitext(downloaded_files[i])[0]
                mp3_path = base + ".mp3"
            else:
                mp3_path = os.path.join(output_dir, f"{yt_title}.mp3")

            meta = get_deezer_metadata(yt_title, yt_artist) or {
                "title": yt_title,
                "artist": yt_artist,
                "album": entry.get("album", ""),
                "year": entry.get("upload_date", "")[:4],
                "track_number": "",
                "thumbnail": entry.get("thumbnail"),
            }

            if os.path.exists(mp3_path):
                embed_metadata(mp3_path, meta)
            else:
                print(f"File not found for tagging: {mp3_path}")



app = Flask(__name__)
CORS(app) 

@app.route('/data', methods=['POST'])
def receive_data():
    content = request.json
    user_text = content.get('message')
    
    print(f"Received from HTML: {user_text}")
    
    # Do whatever you want with user_text here (save to file, AI processing, etc.)
    url = user_text
    clean = url.split("&") [0]
    download_music(clean)

    return jsonify({"status": "Success", "received": user_text})

print("Done! Check the 'downloads' folder.")


if __name__ == '__main__':
    app.run(port=5000)

# if __name__ == "__main__":
    # if len(sys.argv) < 2:
    #     print("Usage: python cek.py <YouTube Music URL>")
    #     sys.exit(1)

    # print(f"Downloading: {sys.argv[1]}")
    # # download_music(sys.argv[1])
