"""Static file server for local dev that disables browser caching.

`python3 -m http.server` sends no Cache-Control headers at all, so browsers
fall back to heuristic caching and can silently serve a stale index.html/
app.js pairing after an edit (e.g. an old app.js referencing DOM ids that no
longer exist in the current index.html) - causing runtime errors that look
like a code bug but are actually a stale-cache mismatch. This wrapper adds
Cache-Control: no-store so every request always hits disk.

Usage:
    python3 scripts/dev_server.py [port]   # defaults to 4173
"""

import sys
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class NoCacheHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
        super().end_headers()


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 4173
    handler = partial(NoCacheHandler, directory=str(PROJECT_ROOT))
    server = HTTPServer(("", port), handler)
    print(f"Serving {PROJECT_ROOT} at http://localhost:{port} (Cache-Control: no-store)")
    server.serve_forever()


if __name__ == "__main__":
    main()
