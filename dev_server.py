#!/usr/bin/env python3
"""
Dev server: watches content/, templates/, and static/ for changes,
rebuilds automatically, and serves dist/ locally.

Usage:
    python3 dev_server.py           # serves on port 9405
    python3 dev_server.py 8080      # custom port
    python3 dev_server.py --drafts  # include draft posts
"""
import http.server
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).parent
WATCH_DIRS = [ROOT / "content", ROOT / "templates", ROOT / "static"]
PORT = int(next((a for a in sys.argv[1:] if a.isdigit()), "9405"))
INCLUDE_DRAFTS = "--drafts" in sys.argv


def rebuild():
    args = ["python3", str(ROOT / "build.py")]
    if INCLUDE_DRAFTS:
        args.append("--drafts")
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        print("[build] FAILED\n" + result.stderr.strip())
        return False
    return True


def get_mtimes():
    mtimes = {}
    for watch_dir in WATCH_DIRS:
        if not watch_dir.exists():
            continue
        for path in watch_dir.rglob("*"):
            if path.is_file():
                try:
                    mtimes[path] = path.stat().st_mtime
                except OSError:
                    pass
    return mtimes


def watch_loop():
    prev = get_mtimes()
    while True:
        time.sleep(1)
        curr = get_mtimes()
        changed = [p for p in curr if curr[p] != prev.get(p)] + \
                  [p for p in prev if p not in curr]
        if changed:
            names = ", ".join(p.name for p in changed[:3])
            suffix = " ..." if len(changed) > 3 else ""
            print("[watch] changed: %s%s — rebuilding" % (names, suffix))
            ok = rebuild()
            if ok:
                print("[build] OK")
        prev = curr


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "dist"), **kwargs)

    def log_message(self, fmt, *args):
        pass  # suppress per-request noise

    def log_error(self, fmt, *args):
        print("[serve] error: " + (fmt % args))


def main():
    print("[build] initial build...")
    ok = rebuild()
    if ok:
        print("[build] OK")

    watcher = threading.Thread(target=watch_loop, daemon=True)
    watcher.start()

    draft_note = "  (draft mode ON)" if INCLUDE_DRAFTS else ""
    print("[serve] http://localhost:%d%s" % (PORT, draft_note))
    print("[watch] %s" % ", ".join(str(d.relative_to(ROOT)) for d in WATCH_DIRS))

    with http.server.ThreadingHTTPServer(("127.0.0.1", PORT), QuietHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[serve] stopped")


if __name__ == "__main__":
    main()
