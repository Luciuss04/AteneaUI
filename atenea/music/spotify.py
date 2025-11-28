import os
import re

def is_spotify_url(s: str) -> bool:
    return bool(re.search(r"https?://open\.spotify\.com/", s))

def spotify_id_and_type(url: str):
    m = re.search(r"open\.spotify\.com/(track|playlist|album)/([A-Za-z0-9]+)", url)
    if not m:
        return None, None
    return m.group(2), m.group(1)

def build_search_string(name: str, artists: list[str]) -> str:
    return f"{name} {' '.join(artists)}"

def resolve_spotify_items(spotify_client, url: str):
    if not spotify_client:
        return []
    sid, typ = spotify_id_and_type(url)
    if not sid:
        return []
    items = []
    max_items = os.getenv("SPOTIFY_MAX_ITEMS")
    try:
        max_items = int(max_items) if max_items else 10
    except Exception:
        max_items = 10
    if typ == "track":
        t = spotify_client.track(sid)
        name = t.get("name")
        artists = [a.get("name") for a in t.get("artists", [])]
        items.append(build_search_string(name, artists))
    elif typ == "playlist":
        results = spotify_client.playlist_items(sid, additional_types=("track",), limit=max_items)
        for entry in results.get("items", [])[:max_items]:
            tr = entry.get("track")
            if not tr:
                continue
            name = tr.get("name")
            artists = [a.get("name") for a in tr.get("artists", [])]
            items.append(build_search_string(name, artists))
    elif typ == "album":
        results = spotify_client.album_tracks(sid, limit=max_items)
        for tr in results.get("items", [])[:max_items]:
            name = tr.get("name")
            artists = [a.get("name") for a in tr.get("artists", [])]
            items.append(build_search_string(name, artists))
    return items
