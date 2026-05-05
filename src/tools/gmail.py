import base64
import json
import os
import time
from email.message import EmailMessage
from pathlib import Path

import requests

_GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"
_GOOGLE_OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
_DEFAULT_CONFIG_PATH = Path.home() / ".config" / "jarvis" / "gmail_oauth.json"

_VERBS = frozenset({"send_email", "list_messages", "get_message"})
_TOKEN_CACHE = {"access_token": "", "expires_at": 0}


def _resolve_verb(params, verb):
    v = verb.strip() if isinstance(verb, str) else ""
    if v in _VERBS:
        return v
    if v:
        return None
    if "to" in params and "subject" in params and "body" in params:
        return "send_email"
    if "message_id" in params:
        return "get_message"
    return "list_messages"


def _refresh_config():
    file_cfg = _load_config_file()
    return {
        "client_id": (
            os.getenv("GMAIL_CLIENT_ID", "").strip()
            or str(file_cfg.get("client_id", "")).strip()
        ),
        "client_secret": (
            os.getenv("GMAIL_CLIENT_SECRET", "").strip()
            or str(file_cfg.get("client_secret", "")).strip()
        ),
        "refresh_token": (
            os.getenv("GMAIL_REFRESH_TOKEN", "").strip()
            or str(file_cfg.get("refresh_token", "")).strip()
        ),
        "access_token": (
            os.getenv("GMAIL_ACCESS_TOKEN", "").strip()
            or str(file_cfg.get("access_token", "")).strip()
        ),
        "expires_at": int(file_cfg.get("expires_at", 0) or 0),
    }


def _load_config_file():
    path = Path(os.getenv("GMAIL_OAUTH_FILE", str(_DEFAULT_CONFIG_PATH))).expanduser()
    if not path.exists():
        return {}
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _save_config_file(updates):
    path = Path(os.getenv("GMAIL_OAUTH_FILE", str(_DEFAULT_CONFIG_PATH))).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    current = _load_config_file()
    current.update(updates)
    path.write_text(json.dumps(current, indent=2), encoding="utf-8")


def _refresh_access_token():
    cfg = _refresh_config()
    if not (cfg["client_id"] and cfg["client_secret"] and cfg["refresh_token"]):
        return {"error": "gmail_refresh_not_configured"}

    payload = {
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
        "refresh_token": cfg["refresh_token"],
        "grant_type": "refresh_token",
    }
    r = requests.post(_GOOGLE_OAUTH_TOKEN_URL, data=payload, timeout=30)
    if r.status_code >= 400:
        return {
            "error": "gmail_token_refresh_failed",
            "status_code": r.status_code,
            "details": (r.text or "")[:500],
        }
    data = r.json()
    token = (data.get("access_token") or "").strip()
    if not token:
        return {"error": "gmail_token_refresh_failed", "details": "missing access_token"}
    expires_in = int(data.get("expires_in", 3600))
    # refresh a bit early for safety
    expires_at = int(time.time()) + max(60, expires_in - 30)
    _TOKEN_CACHE["access_token"] = token
    _TOKEN_CACHE["expires_at"] = expires_at
    _save_config_file({"access_token": token, "expires_at": expires_at})
    return {"access_token": token}


def _access_token(force_refresh=False):
    cfg = _refresh_config()
    now = int(time.time())
    if (
        not force_refresh
        and _TOKEN_CACHE["access_token"]
        and _TOKEN_CACHE["expires_at"] > now
    ):
        return {"access_token": _TOKEN_CACHE["access_token"]}

    # Optional direct token path for quick/manual testing.
    if cfg["access_token"] and not force_refresh:
        expires_at = int(cfg["expires_at"] or 0)
        if expires_at > now:
            _TOKEN_CACHE["access_token"] = cfg["access_token"]
            _TOKEN_CACHE["expires_at"] = expires_at
            return {"access_token": cfg["access_token"]}
        # If expiry unknown, try it briefly and let 401 trigger refresh.
        if expires_at == 0:
            _TOKEN_CACHE["access_token"] = cfg["access_token"]
            _TOKEN_CACHE["expires_at"] = now + 60
            return {"access_token": cfg["access_token"]}

    return _refresh_access_token()


def _request(method, path, token, **kwargs):
    url = f"{_GMAIL_API}{path}"
    headers = {"Authorization": f"Bearer {token}"}
    headers.update(kwargs.pop("headers", {}))
    r = requests.request(method, url, headers=headers, timeout=30, **kwargs)
    if r.status_code >= 400:
        out = {
            "error": "gmail_api_error",
            "status_code": r.status_code,
            "details": (r.text or "")[:500],
        }
        if r.status_code == 401:
            out["unauthorized"] = True
        return out
    if r.text:
        try:
            return r.json()
        except ValueError:
            return {"status": "ok", "text": r.text}
    return {"status": "ok"}


def _build_raw_email(params):
    msg = EmailMessage()
    msg["To"] = params["to"]
    msg["Subject"] = params["subject"]
    if params.get("cc"):
        msg["Cc"] = params["cc"]
    if params.get("bcc"):
        msg["Bcc"] = params["bcc"]
    msg.set_content(params["body"])
    raw_bytes = base64.urlsafe_b64encode(msg.as_bytes())
    return raw_bytes.decode("utf-8")


def run_gmail(params, verb=None):
    if not isinstance(params, dict):
        params = {}

    token_result = _access_token()
    if "access_token" not in token_result:
        if token_result.get("error") == "gmail_refresh_not_configured":
            return {
                "error": (
                    "gmail_not_configured: set either GMAIL_ACCESS_TOKEN, or "
                    "GMAIL_CLIENT_ID + GMAIL_CLIENT_SECRET + GMAIL_REFRESH_TOKEN."
                )
            }
        return token_result
    token = token_result["access_token"]

    op = _resolve_verb(params, verb)
    if op is None:
        return {"error": "unknown gmail action"}

    def gmail_request(method, path, **kwargs):
        nonlocal token
        data = _request(method, path, token, **kwargs)
        if isinstance(data, dict) and data.get("unauthorized"):
            refreshed = _access_token(force_refresh=True)
            if "access_token" not in refreshed:
                return refreshed
            token = refreshed["access_token"]
            data = _request(method, path, token, **kwargs)
        return data

    if op == "send_email":
        for k in ("to", "subject", "body"):
            if not params.get(k):
                return {"error": f"missing required field: {k}"}
        raw = _build_raw_email(params)
        payload = {"raw": raw}
        data = gmail_request("POST", "/messages/send", json=payload)
        if "error" in data:
            return data
        return {
            "status": "sent",
            "id": data.get("id"),
            "thread_id": data.get("threadId"),
            "to": params.get("to"),
            "subject": params.get("subject"),
        }

    if op == "list_messages":
        q = params.get("query") or params.get("q") or "in:inbox"
        max_results = int(params.get("max_results", 10))
        max_results = max(1, min(max_results, 50))
        data = gmail_request(
            "GET",
            "/messages",
            params={"q": q, "maxResults": max_results},
        )
        if "error" in data:
            return data
        return {
            "status": "messages",
            "query": q,
            "messages": data.get("messages", []),
            "result_size_estimate": data.get("resultSizeEstimate", 0),
        }

    # op == "get_message"
    message_id = params.get("message_id")
    if not message_id:
        return {"error": "missing required field: message_id"}
    data = gmail_request(
        "GET",
        f"/messages/{message_id}",
        params={"format": "metadata", "metadataHeaders": ["From", "To", "Subject", "Date"]},
    )
    if "error" in data:
        return data

    headers = {}
    for h in data.get("payload", {}).get("headers", []):
        name = h.get("name")
        value = h.get("value")
        if name and value:
            headers[name] = value

    return {
        "status": "message",
        "id": data.get("id"),
        "thread_id": data.get("threadId"),
        "snippet": data.get("snippet", ""),
        "headers": headers,
    }