#!/usr/bin/env python3
"""
Movie tracker CLI — search movies, get links, log as watched/to-watch.

Usage:
  python movies.py search <movie name>
  python movies.py list
  python movies.py watched <movie name>
  python movies.py towatch <movie name>

Set your OMDB API key (free at https://www.omdbapi.com/apikey.aspx):
  Windows:  set OMDB_API_KEY=your_key
  Linux/Mac: export OMDB_API_KEY=your_key
"""

import sys
import json
import os
import urllib.request
import urllib.parse
import re

try:
    from config.keys import OMDB_API_KEY as _cfg_key
except ImportError:
    _cfg_key = ""
OMDB_API_KEY = os.environ.get("OMDB_API_KEY") or _cfg_key
WATCHLIST_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "movies_watchlist.json")


def load_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_watchlist(data):
    with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def fetch_movie(title):
    params = urllib.parse.urlencode({"t": title, "apikey": OMDB_API_KEY, "plot": "short"})
    url = f"http://www.omdbapi.com/?{params}"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read())
    except Exception as e:
        print(f"  Network error: {e}")
        return None
    if data.get("Response") == "False":
        print(f"  Not found: {data.get('Error', 'Unknown error')}")
        return None
    return data


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
    imdb_id = data.get("imdbID", "")
    title = data.get("Title", "")
    year = data.get("Year", "")
    slug = urllib.parse.quote_plus(title)
    imdb = f"https://www.imdb.com/title/{imdb_id}/" if imdb_id else f"https://www.imdb.com/find?q={slug}"
    lb_slug = re.sub(r"[^a-z0-9\s]", "", title.lower()).strip()
    lb_slug = re.sub(r"\s+", "-", lb_slug)
    letterboxd = f"https://letterboxd.com/film/{lb_slug}/"
    douban = fetch_douban_direct(title, year)
    return imdb, letterboxd, douban


def display_movie(data):
    title    = data.get("Title", "N/A")
    year     = data.get("Year", "N/A")
    genre    = data.get("Genre", "N/A")
    director = data.get("Director", "N/A")
    actors   = data.get("Actors", "N/A")
    runtime  = data.get("Runtime", "N/A")
    rating   = data.get("imdbRating", "N/A")
    plot     = data.get("Plot", "N/A")

    imdb, letterboxd, douban = make_links(data)

    line = "─" * 62
    print(f"\n  {line}")
    print(f"  {title}  ({year})  |  {runtime}  |  IMDb {rating}/10")
    print(f"  {line}")
    print(f"  Genre    : {genre}")
    print(f"  Director : {director}")
    print(f"  Cast     : {actors}")
    print(f"  Plot     : {plot}")
    print(f"\n  Links")
    print(f"  IMDb       : {imdb}")
    print(f"  Letterboxd : {letterboxd}")
    print(f"  Douban     : {douban}")
    print(f"  {line}\n")


def make_entry(data, status):
    imdb, letterboxd, douban = make_links(data)
    return {
        "title":      data["Title"],
        "year":       data.get("Year", ""),
        "imdbID":     data.get("imdbID", ""),
        "status":     status,
        "imdb":       imdb,
        "letterboxd": letterboxd,
        "douban":     douban,
    }


def cmd_search(args):
    if not args:
        print("Usage: python movies.py search <movie name>")
        return
    title = " ".join(args)
    print(f"\n  Searching for \"{title}\"...")
    data = fetch_movie(title)
    if not data:
        return

    display_movie(data)

    watchlist = load_watchlist()
    key = data.get("imdbID") or data["Title"]
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
        print(f"Usage: python movies.py {cmd} <movie name>")
        return
    title = " ".join(args)
    print(f"\n  Searching for \"{title}\"...")
    data = fetch_movie(title)
    if not data:
        return

    watchlist = load_watchlist()
    key = data.get("imdbID") or data["Title"]
    watchlist[key] = make_entry(data, status)
    save_watchlist(watchlist)

    label = "watched" if status == "watched" else "to-watch"
    print(f"  ✓ \"{data['Title']}\" marked as {label}.\n")


def check_api_key():
    if not OMDB_API_KEY:
        print("\n  Error: OMDB_API_KEY not set.")
        print("  1. Get a free key at https://www.omdbapi.com/apikey.aspx")
        print("  2. Set it:  set OMDB_API_KEY=your_key  (Windows)")
        print("              export OMDB_API_KEY=your_key  (Linux/Mac)\n")
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
