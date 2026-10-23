# URL Shortener

A URL shortening service with a web dashboard and click analytics. Built with Flask, SQLite and vanilla JavaScript, in a single Python file.



## Features
- Shorten any http(s) URL into a short code
- Redirects visitors to the original URL and counts every click
- Dashboard with the 20 most recent links, auto-refreshing click counts, one-click copy and delete
- Input validation: only valid http and https URLs are accepted
- Light and dark theme that follows your system setting

## Run it
Requires Python 3.9+.

```
pip install -r requirements.txt
python url_shortener.py
```

Open http://127.0.0.1:5000. Data is stored in `urls.db` next to the script.

## REST API
| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/shorten` | Create a short link (JSON: `{"url": "https://..."}`) |
| GET | `/<code>` | Redirect to the original URL and count a click |
| GET | `/api/links` | List recent links with click counts |
| GET | `/api/stats/<code>` | Stats for one link |
| DELETE | `/api/links/<code>` | Delete a link |

## Tech stack
Python, Flask, SQLite, HTML/CSS, JavaScript (fetch API).

## How it works
Each link is stored with an auto-incrementing integer ID. The short code is that ID converted to base62 (0-9, a-z, A-Z), so codes stay short and are unique without any collision checks. Opening a short link decodes the code back to the ID, increments the click counter and responds with a redirect.

## Ideas for improvement
- Custom aliases and link expiry
- Rate limiting
- Per-click analytics (time, referrer)
- Deploy with Docker or on a free host
