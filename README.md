# FilmFetch

As a movie lover, you can easily use this repo to get movie URLs for Douban, IMDb, and Letterboxd — then mark them as watched or add them to your watchlist.

---

## Two Scripts

| File | API | Language Support |
|---|---|---|
| `movies_omdb.py` | [OMDB](https://www.omdbapi.com/) | English titles only |
| `movies_tmdb.py` | [TMDB](https://www.themoviedb.org/) | English **and** Chinese titles |

Both scripts share the same `movies_watchlist.json` file, so your saved movies carry over between the two.

---

## Setup

### 1. Get API keys

- **OMDB** (for `movies_omdb.py`): https://www.omdbapi.com/apikey.aspx
- **TMDB** (for `movies_tmdb.py`): https://www.themoviedb.org/settings/api

### 2. Add your keys

Copy the example config and fill in your keys:

```
config/keys.example.py  →  config/keys.py
```

Edit `config/keys.py`:

```python
OMDB_API_KEY = "your_omdb_key"
TMDB_API_KEY = "your_tmdb_key"
```

`config/keys.py` is gitignored and will never be committed.

Alternatively, set keys as environment variables:

```
# Windows
set OMDB_API_KEY=your_key
set TMDB_API_KEY=your_key

# Linux / Mac
export OMDB_API_KEY=your_key
export TMDB_API_KEY=your_key
```

---

## Usage

```
python movies_omdb.py search <movie name>      # English titles
python movies_tmdb.py search <movie name>      # English or Chinese titles
python movies_tmdb.py search 飞驰人生

python movies_omdb.py list                     # show your watchlist
python movies_omdb.py watched <movie name>     # mark as watched directly
python movies_omdb.py towatch <movie name>     # add to watch list directly
```

After a search, you'll be prompted to save the movie:

```
Save as: [w]atched  [t]o-watch  [enter to skip]  >
```

---

## Links returned

Each search returns direct links to:

- **IMDb** — exact movie page (via IMDb ID)
- **Letterboxd** — direct film page
- **Douban** — direct movie page (scraped from search; falls back to search page if unavailable)
