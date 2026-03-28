import yt_dlp
import sys
import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS # Allows the browser to talk to the server
import musicbrainzngs
# import ytmusicapi

from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TCON, TRCK, APIC, ID3NoHeaderError
from mutagen.mp3 import MP3

# from ytmusicapi import YTMusic

# yt = YTMusic()  # no auth needed for search

# def get_ytmusic_metadata(title, artist):
#     try:
#         results = yt.search(f"{title} {artist}", filter="songs", limit=1)
#         if not results:
#             return None
        
#         track = results[0]
#         return {
#             "title": track.get("title", title),
#             "artist": track["artists"][0]["name"] if track.get("artists") else artist,
#             "album": track["album"]["name"] if track.get("album") else "",
#             "year": track.get("year", ""),
#             "track_number": "",
#             "thumbnail": track["thumbnails"][-1]["url"] if track.get("thumbnails") else None,
#         }
#     except Exception as e:
#         print(f"YTMusic error: {e}")
#         return None



# def get_itunes_metadata(title, artist):
#     try:
#         query = f"{title} {artist}"
#         r = requests.get(
#             f"https://itunes.apple.com/search?term={requests.utils.quote(query)}&media=music&limit=1",
#             timeout=10
#         )
#         data = r.json()
#         results = data.get("results", [])
#         if not results:
#             print("No iTunes match found, using YouTube metadata.")
#             return None

#         track = results[0]
#         return {
#             "title": track.get("trackName", title),
#             "artist": track.get("artistName", artist),
#             "album": track.get("collectionName", ""),
#             "year": track.get("releaseDate", "")[:4],
#             "track_number": str(track.get("trackNumber", "")),
#             "thumbnail": track.get("artworkUrl100", "").replace("100x100", "600x600"),  # get higher res
#         }

#     except Exception as e:
#         print(f"iTunes error: {e}")
#         return None


musicbrainzngs.set_useragent("YTMusicDownloader", "1.0", "your@email.com")

def get_musicbrainz_metadata(title, artist):
    try:
        result = musicbrainzngs.search_recordings(
            recording=title,
            artist=artist,
            limit=1
        )

        recordings = result.get("recording-list", [])
        if not recordings:
            print("No MusicBrainz match found, using YouTube metadata.")
            return None

        rec = recordings[0]
        track_title = rec.get("title", title)
        artist_name = rec["artist-credit"][0]["artist"]["name"] if rec.get("artist-credit") else artist

        release = rec.get("release-list", [{}])[0]
        album = release.get("title", "")
        year = release.get("date", "")[:4]
        track_number = release.get("track-count", "")

        # Get cover art from Cover Art Archive (free, no API key needed)
        thumbnail = None
        release_id = release.get("id")
        if release_id:
            try:
                cover_url = f"https://coverartarchive.org/release/{release_id}/front"
                r = requests.head(cover_url, timeout=5, allow_redirects=True)
                if r.status_code == 200:
                    thumbnail = cover_url
            except:
                pass

        return {
            "title": track_title,
            "artist": artist_name,
            "album": album,
            "year": year,
            "track_number": str(track_number),
            "thumbnail": thumbnail,
        }

    except Exception as e:
        print(f"MusicBrainz error: {e}")
        return None


# def get_deezer_metadata(title, artist):
#     try:
#         query = f"{title} {artist}"
#         r = requests.get(f"https://api.deezer.com/search?q={requests.utils.quote(query)}&limit=1", timeout=10)
#         data = r.json()
#         tracks = data.get("data", [])
#         if not tracks:
#             print("No Deezer match found, using YouTube metadata.")
#             return None

#         track = tracks[0]
#         album_id = track["album"]["id"]
#         album_data = requests.get(
#             f"https://api.deezer.com/album/{album_id}",
#             timeout=10
#         ).json()

#         year = album_data.get("release_date", "")[:4]
#         return {
#             "title": track["title"],
#             "artist": track["artist"]["name"],
#             "album": track["album"]["title"],
#             "year": year,  
#             "track_number": "",
#             "thumbnail": track["album"]["cover_xl"],  # high quality cover art
#         }
#     except Exception as e:
#         print(f"Deezer error: {e}")
#         return None

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
            # meta = get_ytmusic_metadata(yt_title, yt_artist) or {
            # meta = get_itunes_metadata(yt_title, yt_artist) or {
            meta = get_musicbrainz_metadata(yt_title, yt_artist) or {
            # meta = get_deezer_metadata(yt_title, yt_artist) or {
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
