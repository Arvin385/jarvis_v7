import json
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests

CONFIG_PATH = Path.home() / ".config" / "jarvis" / "gmail_oauth.json"
REDIRECT_URI = "http://127.0.0.1:8765/callback"
SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"


class CallbackHandler(BaseHTTPRequestHandler):
    auth_code = None
    auth_error = None
    state = None

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        code = (params.get("code") or [None])[0]
        err = (params.get("error") or [None])[0]
        state = (params.get("state") or [None])[0]

        if state != self.state:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"State mismatch. You can close this tab.")
            type(self).auth_error = "state_mismatch"
            return

        if err:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(f"OAuth error: {err}".encode("utf-8"))
            type(self).auth_error = err
            return

        if code:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(
                b"Gmail authorization complete. Return to terminal."
            )
            type(self).auth_code = code
            return

        self.send_response(400)
        self.end_headers()
        self.wfile.write(b"Missing code. You can close this tab.")
        type(self).auth_error = "missing_code"

    def log_message(self, fmt, *args):  # silence default logs
        return


def _ask(label):
    return input(f"{label}: ").strip()


def _start_server(state):
    CallbackHandler.auth_code = None
    CallbackHandler.auth_error = None
    CallbackHandler.state = state
    server = HTTPServer(("127.0.0.1", 8765), CallbackHandler)
    t = threading.Thread(target=server.handle_request, daemon=True)
    t.start()
    return server, t


def main():
    print("Gmail OAuth one-time setup")
    print("This will save credentials to ~/.config/jarvis/gmail_oauth.json")
    client_id = _ask("Enter Google OAuth Client ID")
    client_secret = _ask("Enter Google OAuth Client Secret")
    if not client_id or not client_secret:
        raise SystemExit("Client ID/secret are required.")

    state = secrets.token_urlsafe(24)
    query = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    auth_link = f"{AUTH_URL}?{urlencode(query)}"

    server, thread = _start_server(state)
    print("\nOpening browser for Google consent...")
    print(auth_link)
    webbrowser.open(auth_link)

    print("Waiting for OAuth callback on 127.0.0.1:8765 ...")
    thread.join(timeout=300)
    server.server_close()

    if CallbackHandler.auth_error:
        raise SystemExit(f"OAuth failed: {CallbackHandler.auth_error}")
    if not CallbackHandler.auth_code:
        raise SystemExit("Did not receive OAuth code (timeout).")

    token_payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": CallbackHandler.auth_code,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    r = requests.post(TOKEN_URL, data=token_payload, timeout=30)
    if r.status_code >= 400:
        raise SystemExit(f"Token exchange failed: {r.status_code} {r.text[:500]}")
    data = r.json()
    refresh_token = (data.get("refresh_token") or "").strip()
    access_token = (data.get("access_token") or "").strip()
    expires_in = int(data.get("expires_in", 3600))

    if not refresh_token:
        raise SystemExit(
            "No refresh_token returned. Revoke prior consent and retry (prompt=consent is already set)."
        )

    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(
            {
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "access_token": access_token,
                "expires_at": 0,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print("\nSaved OAuth config to:")
    print(CONFIG_PATH)
    print("Done. Gmail tool will auto-refresh tokens from this file.")


if __name__ == "__main__":
    main()
