#!/usr/bin/env python3
"""
Movie tracker CLI (TMDB) — supports Chinese & English titles.

Usage:
  python movies_tmdb.py search <movie name>
  python movies_tmdb.py list
  python movies_tmdb.py watched <movie name>
  python movies_tmdb.py towatch <movie name>

Get a free TMDB API key at https://www.themoviedb.org/settings/api
  Windows:  set TMDB_API_KEY=your_key
  Linux/Mac: export TMDB_API_KEY=your_key
"""

import sys
import json
import os
import urllib.request
import urllib.parse
import re

try:
    from config.keys import TMDB_API_KEY as _cfg_key
except ImportError:
    _cfg_key = ""
TMDB_API_KEY = os.environ.get("TMDB_API_KEY") or _cfg_key
WATCHLIST_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "movies_watchlist.json")
TMDB_BASE = "https://api.themoviedb.org/3"


def load_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_watchlist(data):
    with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def tmdb_get(path, params):
    params["api_key"] = TMDB_API_KEY
    url = f"{TMDB_BASE}{path}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"  Network error: {e}")
        return None


def has_chinese(text):
    return bool(re.search(r'[\u4e00-\u9fff]', text))


def fetch_movie(title):
    # Search — TMDB searches across all languages automatically
    lang = "zh-CN" if has_chinese(title) else "en-US"
    data = tmdb_get("/search/movie", {"query": title, "language": lang})
    if not data or not data.get("results"):
        print(f"  Not found.")
        return None

    movie_id = data["results"][0]["id"]

    # Get full details in the detected language
    details_zh = tmdb_get(f"/movie/{movie_id}", {"language": lang, "append_to_response": "credits"})
    # Also fetch English details for Letterboxd slug
    details_en = tmdb_get(f"/movie/{movie_id}", {"language": "en-US"})

    if not details_zh:
        return None

    # Store English title alongside for link generation
    details_zh["_en_title"] = details_en.get("title", "") if details_en else ""
    return details_zh


def fetch_douban_direct(title, year=""):
    query = urllib.parse.quote_plus(f"{title} {year}".strip())
    search_url = f"https://search.douban.com/movie/subject_search?search_text={query}&cat=1002"
    try:
        req = urllib.request.Request(search_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            html = r.read().decode("utf-8", errors="ignore")
        match = re.search(r'https://movie\.douban\.com/subject/(\d+)/', html)
        if match:
            return f"https://movie.douban.com/subject/{match.group(1)}/"
    except Exception:
        pass
    return search_url


def make_links(data):
    imdb_id = data.get("imdb_id", "")
    en_title = data.get("_en_title") or data.get("title", "")
    year = (data.get("release_date") or "")[:4]
    display_title = data.get("title", "")

    slug = urllib.parse.quote_plus(en_title)
    imdb = f"https://www.imdb.com/title/{imdb_id}/" if imdb_id else f"https://www.imdb.com/find?q={slug}"

    lb_slug = re.sub(r"[^a-z0-9\s]", "", en_title.lower()).strip()
    lb_slug = re.sub(r"\s+", "-", lb_slug)
    if year:
        lb_slug = f"{lb_slug}-{year}"
    letterboxd = f"https://letterboxd.com/film/{lb_slug}/"

    douban = fetch_douban_direct(display_title, year)
    return imdb, letterboxd, douban


def display_movie(data):
    title    = data.get("title", "N/A")
    en_title = data.get("_en_title", "")
    year     = (data.get("release_date") or "N/A")[:4]
    genres   = ", ".join(g["name"] for g in data.get("genres", []))
    runtime  = f"{data.get('runtime', 'N/A')} min"
    rating   = data.get("vote_average", "N/A")
    plot     = data.get("overview") or "N/A"
    cast     = ", ".join(
        c["name"] for c in (data.get("credits") or {}).get("cast", [])[:5]
    )

    crew     = (data.get("credits") or {}).get("crew", [])
    director = next((c["name"] for c in crew if c.get("job") == "Director"), "N/A")

    imdb, letterboxd, douban = make_links(data)

    line = "─" * 62
    header = f"{title}  ({year})  |  {runtime}  |  TMDB {rating}/10"
    if en_title and en_title != title:
        header = f"{title} / {en_title}  ({year})  |  {runtime}  |  TMDB {rating}/10"

    print(f"\n  {line}")
    print(f"  {header}")
    print(f"  {line}")
    print(f"  Genre    : {genres or 'N/A'}")
    print(f"  Director : {director}")
    print(f"  Cast     : {cast or 'N/A'}")
    print(f"  Plot     : {plot}")
    print(f"\n  Links")
    print(f"  IMDb       : {imdb}")
    print(f"  Letterboxd : {letterboxd}")
    print(f"  Douban     : {douban}")
    print(f"  {line}\n")


def make_entry(data, status):
    imdb, letterboxd, douban = make_links(data)
    year = (data.get("release_date") or "")[:4]
    return {
        "title":      data.get("title", ""),
        "year":       year,
        "imdbID":     data.get("imdb_id", ""),
        "tmdbID":     str(data.get("id", "")),
        "status":     status,
        "imdb":       imdb,
        "letterboxd": letterboxd,
        "douban":     douban,
    }


def cmd_search(args):
    if not args:
        print("Usage: python movies_tmdb.py search <movie name>")
        return
    title = " ".join(args)
    print(f"\n  Searching for \"{title}\"...")
    data = fetch_movie(title)
    if not data:
        return

    display_movie(data)

    watchlist = load_watchlist()
    key = data.get("imdb_id") or str(data.get("id")) or data["title"]
    current = watchlist.get(key, {}).get("status")
    if current:
        print(f"  Already saved as: {current}")
    print("  Save as: [w]atched  [t]o-watch  [enter to skip]  > ", end="", flush=True)
    choice = input().strip().lower()

    if choice in ("w", "watched"):
        watchlist[key] = make_entry(data, "watched")
        save_watchlist(watchlist)
        print(f"  Saved as watched.\n")
    elif choice in ("t", "to-watch", "towatch"):
        watchlist[key] = make_entry(data, "to-watch")
        save_watchlist(watchlist)
        print(f"  Added to watch list.\n")
    else:
        print("  Not saved.\n")


def cmd_list(_args):
    watchlist = load_watchlist()
    if not watchlist:
        print("\n  Watchlist is empty.\n")
        return

    to_watch = [v for v in watchlist.values() if v["status"] == "to-watch"]
    watched  = [v for v in watchlist.values() if v["status"] == "watched"]

    if to_watch:
        print(f"\n  TO WATCH ({len(to_watch)})")
        print("  " + "─" * 50)
        for m in to_watch:
            print(f"  [ ] {m['title']} ({m['year']})")
            print(f"      IMDb       : {m['imdb']}")
            print(f"      Letterboxd : {m['letterboxd']}")
            print(f"      Douban     : {m['douban']}")

    if watched:
        print(f"\n  WATCHED ({len(watched)})")
        print("  " + "─" * 50)
        for m in watched:
            print(f"  [x] {m['title']} ({m['year']})")

    print()


def cmd_mark(args, status):
    cmd = "watched" if status == "watched" else "towatch"
    if not args:
        print(f"Usage: python movies_tmdb.py {cmd} <movie name>")
        return
    title = " ".join(args)
    print(f"\n  Searching for \"{title}\"...")
    data = fetch_movie(title)
    if not data:
        return

    watchlist = load_watchlist()
    key = data.get("imdb_id") or str(data.get("id")) or data["title"]
    watchlist[key] = make_entry(data, status)
    save_watchlist(watchlist)

    label = "watched" if status == "watched" else "to-watch"
    print(f"  \"{data['title']}\" marked as {label}.\n")


def check_api_key():
    if not TMDB_API_KEY:
        print("\n  Error: TMDB_API_KEY not set.")
        print("  1. Get a free key at https://www.themoviedb.org/settings/api")
        print("  2. Set it:  set TMDB_API_KEY=your_key  (Windows)")
        print("              export TMDB_API_KEY=your_key  (Linux/Mac)\n")
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1].lower()
    args = sys.argv[2:]

    if cmd in ("search", "watched", "towatch"):
        check_api_key()

    if cmd == "search":
        cmd_search(args)
    elif cmd == "list":
        cmd_list(args)
    elif cmd == "watched":
        cmd_mark(args, "watched")
    elif cmd == "towatch":
        cmd_mark(args, "to-watch")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
