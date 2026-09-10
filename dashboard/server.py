"""
dashboard/server.py
===================
Simple HTTP Server runner hosting AIRINDEX Government Dashboard on port 3000.
"""

import http.server
import os
import socketserver

PORT = 3000
DIRECTORY = os.path.dirname(__file__)


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)


def run_dashboard_server():
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"🚀 AIRINDEX Government Dashboard UI live at: http://127.0.0.1:{PORT}")
        httpd.serve_forever()


if __name__ == "__main__":
    run_dashboard_server()
