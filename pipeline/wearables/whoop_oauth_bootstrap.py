#!/usr/bin/env python3
"""One-time WHOOP OAuth bootstrap — mint the first refresh token.

Run this ONCE, interactively, on a machine with a browser (e.g. your laptop). It performs
the authorization-code flow against your registered WHOOP app, capturing the redirect on a
local loopback server, and writes the resulting access+refresh tokens into the pipeline
state file. After this, whoop_pull.py refreshes tokens unattended on the server.

Prerequisites (WHOOP Developer Dashboard):
  * an App with a Client ID + Client Secret,
  * a registered Redirect URL EXACTLY matching --redirect (default http://localhost),
  * the `offline` scope enabled/requested, or WHOOP returns no refresh token.

Usage:
  set WHOOP_CLIENT_ID / WHOOP_CLIENT_SECRET in the environment, then:
    python whoop_oauth_bootstrap.py
    python whoop_oauth_bootstrap.py --redirect http://localhost --state ~/whoop-pipeline/state.json

The state file holds secrets (refresh token) — keep it 0600 and never commit it.
"""
from __future__ import annotations

import argparse
import secrets
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from whoop_client import AUTH_URL, SCOPES, WhoopClient

_captured: dict[str, str] = {}


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 - http.server API
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        _captured.update({k: v[0] for k, v in params.items()})
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        ok = "code" in _captured
        msg = "Authorization captured — you can close this tab." if ok else \
              f"Authorization failed: {_captured.get('error', 'unknown error')}"
        self.wfile.write(f"<html><body><h3>{msg}</h3></body></html>".encode())

    def log_message(self, *_):  # silence the default stderr logging
        return


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--redirect", default="http://localhost",
                    help="Redirect URL — must match the one registered in the WHOOP dashboard.")
    ap.add_argument("--state", type=Path, default=None, help="Path to write the token state file.")
    args = ap.parse_args()

    client = WhoopClient(state_path=args.state)
    state = secrets.token_urlsafe(8)[:16]
    auth_url = f"{AUTH_URL}?" + urllib.parse.urlencode({
        "response_type": "code",
        "client_id": client.client_id,
        "redirect_uri": args.redirect,
        "scope": " ".join(SCOPES),
        "state": state,
    })

    parsed = urllib.parse.urlparse(args.redirect)
    host, port = parsed.hostname or "localhost", parsed.port or 80

    print("Opening the WHOOP authorization page in your browser…")
    print(f"If it doesn't open, visit:\n  {auth_url}\n")
    webbrowser.open(auth_url)

    print(f"Waiting for the redirect on {host}:{port} …")
    server = HTTPServer((host, port), _CallbackHandler)
    while "code" not in _captured and "error" not in _captured:
        server.handle_request()

    if "code" not in _captured:
        print(f"Authorization failed: {_captured.get('error')}")
        return 1
    if _captured.get("state") != state:
        print("State mismatch — aborting (possible CSRF).")
        return 1

    client.exchange_code(_captured["code"], args.redirect)
    print(f"Success. Tokens written to {client.state_path} (chmod 600).")
    if client.state.get("refresh_token"):
        print("Refresh token received — whoop_pull.py can now run unattended.")
    else:
        print("WARNING: no refresh_token returned. The access token will expire in ~1h and\n"
              "         cannot be refreshed. Enable/request the 'offline' scope in the WHOOP\n"
              "         dashboard, then re-run this bootstrap.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
