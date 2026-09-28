#!/usr/bin/env python3
"""
No-cache HTTP server for development.
Adds Cache-Control: no-store to every response so browsers never cache files.
"""
import http.server
import socketserver

PORT = 3000

class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

import os
import functools

FRONTEND_DIR = os.path.dirname(os.path.abspath(__file__))
handler = functools.partial(NoCacheHandler, directory=FRONTEND_DIR)

with socketserver.TCPServer(("", PORT), handler) as httpd:
    print(f"Frontend serving from {FRONTEND_DIR} → http://localhost:{PORT}")
    httpd.serve_forever()
