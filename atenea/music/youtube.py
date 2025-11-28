import yt_dlp

ytdl_opts = {
    "format": "bestaudio[protocol!=http_dash_segments]/bestaudio/best",
    "nocheckcertificate": True,
    "noplaylist": True,
    "default_search": "ytsearch",
    "quiet": True,
    "no_warnings": True,
    "source_address": "0.0.0.0",
    "extractor_args": {"youtube": {"player_client": ["default"]}},
}

ffmpeg_before = "-nostdin -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -loglevel error"

def ytdl_search(query):
    with yt_dlp.YoutubeDL(ytdl_opts) as ydl:
        info = ydl.extract_info(query, download=False)
        if "entries" in info:
            info = info["entries"][0]
        thumb = info.get("thumbnail")
        if not thumb:
            thumbs = info.get("thumbnails") or []
            if thumbs:
                thumb = thumbs[-1].get("url")
        return {
            "title": info.get("title"),
            "url": info.get("url"),
            "webpage_url": info.get("webpage_url") or info.get("url"),
            "thumbnail": thumb,
            "duration": info.get("duration"),
            "channel": info.get("uploader") or info.get("channel")
        }

def ytdl_suggest(term: str):
    try:
        opts = dict(ytdl_opts)
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"ytsearch10:{term}", download=False)
            entries = info.get("entries", [])
            res = []
            for e in entries:
                res.append({
                    "title": e.get("title"),
                    "webpage_url": e.get("webpage_url") or e.get("url"),
                    "channel": e.get("uploader") or e.get("channel"),
                    "duration": e.get("duration"),
                    "thumbnail": e.get("thumbnail")
                })
            return res
    except Exception:
        return []
