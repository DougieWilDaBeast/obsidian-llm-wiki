#!/usr/bin/env python3
"""Minimal WHOOP v2 API client — stdlib only (urllib), no third-party deps.

Handles OAuth token lifecycle (refresh of a rotating refresh token), authenticated GETs
with one automatic re-auth on 401, simple 429 back-off, and cursor pagination over the
collection endpoints. Credentials come from the environment; tokens are persisted to a
0600 state file OUTSIDE the repo so they never land in git.

WHOOP rotates the refresh token on every refresh and invalidates the previous one, so the
new refresh_token from each response is persisted immediately.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API_BASE = "https://api.prod.whoop.com/developer"
TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
AUTH_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"

SCOPES = [
    "read:recovery", "read:cycles", "read:sleep", "read:workout",
    "read:profile", "read:body_measurement", "offline",
]

DEFAULT_STATE = Path(os.environ.get("WEARABLES_STATE_DIR", Path.home() / "whoop-pipeline")) / "state.json"
PAGE_LIMIT = 25            # WHOOP max per page
TOKEN_SKEW_S = 120        # refresh this many seconds before expiry
# WHOOP sits behind Cloudflare, which blocks the default "Python-urllib" UA (HTTP 403,
# Cloudflare error 1010). A normal browser UA string is required on every request.
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


class WhoopAuthError(RuntimeError):
    pass


class WhoopClient:
    def __init__(self, state_path: Path | None = None,
                 client_id: str | None = None, client_secret: str | None = None):
        self.state_path = Path(state_path or os.environ.get("WHOOP_STATE", DEFAULT_STATE))
        self.client_id = client_id or os.environ.get("WHOOP_CLIENT_ID", "")
        self.client_secret = client_secret or os.environ.get("WHOOP_CLIENT_SECRET", "")
        if not (self.client_id and self.client_secret):
            raise WhoopAuthError("WHOOP_CLIENT_ID / WHOOP_CLIENT_SECRET not set.")
        self.state = self._load_state()

    # -- token / state ---------------------------------------------------------------
    def _load_state(self) -> dict:
        if self.state_path.exists():
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        return {}

    def _save_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.state_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.state, indent=2, sort_keys=True), encoding="utf-8")
        os.chmod(tmp, 0o600)
        tmp.replace(self.state_path)
        os.chmod(self.state_path, 0o600)

    def _post_token(self, payload: dict) -> dict:
        data = urllib.parse.urlencode(payload).encode()
        req = urllib.request.Request(
            TOKEN_URL, data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded",
                     "User-Agent": USER_AGENT, "Accept": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            body = exc.read().decode(errors="replace")
            raise WhoopAuthError(f"Token request failed ({exc.code}): {body}") from exc

    def _store_tokens(self, tok: dict) -> None:
        self.state["access_token"] = tok["access_token"]
        if tok.get("refresh_token"):          # rotated each refresh — persist the new one
            self.state["refresh_token"] = tok["refresh_token"]
        self.state["expires_at"] = int(time.time()) + int(tok.get("expires_in", 3600))
        self.state["obtained_at"] = int(time.time())
        self._save_state()

    def exchange_code(self, code: str, redirect_uri: str) -> None:
        """One-time: swap an authorization code for the first access+refresh tokens."""
        self._store_tokens(self._post_token({
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }))

    def _refresh(self) -> None:
        refresh_token = self.state.get("refresh_token")
        if not refresh_token:
            raise WhoopAuthError(
                "No refresh_token in state — run whoop_oauth_bootstrap.py once first.")
        self._store_tokens(self._post_token({
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "offline",
        }))

    def _ensure_token(self) -> str:
        if (not self.state.get("access_token")
                or int(time.time()) >= int(self.state.get("expires_at", 0)) - TOKEN_SKEW_S):
            self._refresh()
        return self.state["access_token"]

    # -- requests --------------------------------------------------------------------
    def get(self, path: str, params: dict | None = None, _retried: bool = False) -> dict:
        token = self._ensure_token()
        url = f"{API_BASE}{path}"
        if params:
            url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}",
                                                   "User-Agent": USER_AGENT,
                                                   "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            if exc.code == 401 and not _retried:
                self._refresh()
                return self.get(path, params, _retried=True)
            if exc.code == 429:
                wait = int(exc.headers.get("Retry-After", "10"))
                time.sleep(min(wait, 60))
                return self.get(path, params, _retried=_retried)
            raise

    def paginate(self, path: str, params: dict | None = None):
        """Yield every record across all pages of a collection endpoint."""
        params = dict(params or {})
        params.setdefault("limit", PAGE_LIMIT)
        while True:
            page = self.get(path, params)
            for record in page.get("records", []):
                yield record
            token = page.get("next_token")
            if not token:
                break
            params["nextToken"] = token

    # -- typed collection helpers ----------------------------------------------------
    def cycles(self, start: str, end: str):
        return self.paginate("/v2/cycle", {"start": start, "end": end})

    def recoveries(self, start: str, end: str):
        return self.paginate("/v2/recovery", {"start": start, "end": end})

    def sleeps(self, start: str, end: str):
        return self.paginate("/v2/activity/sleep", {"start": start, "end": end})

    def workouts(self, start: str, end: str):
        return self.paginate("/v2/activity/workout", {"start": start, "end": end})
