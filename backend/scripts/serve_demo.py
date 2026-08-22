"""Serve the bundled demo website (safe, intentional issues only).

Usage (from backend/):  python -m scripts.serve_demo
Serves on http://localhost:8001
"""

import http.server
import os
import socketserver

ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "demo-site",
)
PORT = 8001


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def log_message(self, fmt, *args):  # noqa: ARG002
        pass


def main() -> None:
    with socketserver.ThreadingTCPServer(("", PORT), QuietHandler) as httpd:
        print(f"Demo site serving {ROOT} at http://localhost:{PORT}")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
