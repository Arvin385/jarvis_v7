import webbrowser
from urllib.parse import parse_qs, quote_plus, urlparse, unquote

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

try:
    from playwright.sync_api import TargetClosedError as _TargetClosedError
except ImportError:  # pragma: no cover — version-specific
    _TargetClosedError = None

playwright = None
browser = None
context = None
page = None

def _direct_url_if_redirect(url: str) -> str:
    """Resolve DuckDuckGo lite /l/?uddg= shim links to the real target URL."""
    u = (url or "").strip()
    try:
        parsed = urlparse(u)
        host = (parsed.netloc or "").lower()
        if "duckduckgo.com" not in host:
            return u
        q = parse_qs(parsed.query).get("uddg")
        if q and q[0]:
            return unquote(q[0])
    except Exception:
        pass
    return u


_VERBS = frozenset(
    {"query", "get_links", "get_text", "click_text", "goto_url", "open_external"}
)


def _session_alive() -> bool:
    global page
    if page is None:
        return False
    try:
        if page.is_closed():
            return False
        br = page.context.browser
        return br is not None and br.is_connected()
    except Exception:
        return False


def _dispose_playwright_session() -> None:
    global playwright, browser, context, page
    try:
        if browser is not None:
            browser.close()
    except Exception:
        pass
    try:
        if playwright is not None:
            playwright.stop()
    except Exception:
        pass
    playwright = browser = context = page = None


def _playwright_connection_lost(exc: BaseException) -> bool:
    if _TargetClosedError is not None and isinstance(exc, _TargetClosedError):
        return True
    if isinstance(exc, PlaywrightError):
        msg = str(exc).lower()
        if any(
            s in msg
            for s in (
                "target closed",
                "browser has been closed",
                "browser closed",
                "connection closed",
            )
        ):
            return True
    return False


def ensure_browser() -> None:
    """Lazy launch: first Playwright use starts headed Chromium; reuse until it dies or user closes."""
    global playwright, browser, context, page

    if _session_alive():
        return

    _dispose_playwright_session()

    print("[Browser] launching...")
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    )
    page = context.new_page()
    print("[Browser] ready")


def _resolve_op(params, verb):
    """Pick browser operation from explicit verb first, then legacy param keys."""
    v = verb.strip() if isinstance(verb, str) else ""
    if v in _VERBS:
        return v
    if v:
        return None
    if "url" in params:
        return "url"
    if "query" in params:
        return "query"
    if "click_text" in params:
        return "click_text"
    if "get_text" in params:
        return "get_text"
    if "get_links" in params:
        return "get_links"
    return None


def run_browser(params, verb=None):
    if not isinstance(params, dict):
        params = {}

    op = _resolve_op(params, verb)
    if op is None:
        return {"error": "unknown browser action"}

    if op == "open_external":
        u = _direct_url_if_redirect((params.get("url") or "").strip())
        if not u.startswith(("http://", "https://")):
            return {
                "error": "open_external requires parameters.url (http:// or https://)",
            }
        webbrowser.open(u)
        print(f"[Browser] opened default browser: {u}")
        return {"status": "opened_default_browser", "url": u}

    def work():
        ensure_browser()

        if op in ("url", "goto_url"):
            target = _direct_url_if_redirect((params.get("url") or "").strip())
            # networkidle hangs on analytic-heavy pages and can stall the agent indefinitely
            page.goto(
                target,
                wait_until="domcontentloaded",
                timeout=60000,
            )
            try:
                page.wait_for_load_state("domcontentloaded", timeout=15000)
            except Exception:
                pass
            title = ""
            try:
                title = page.title()
            except Exception:
                pass
            return {
                "status": "opened_url",
                "url": target,
                "title": title,
            }

        if op == "query":
            query = params["query"]
            q_enc = quote_plus(query)
            page.goto(f"https://www.google.com/search?q={q_enc}")
            page.wait_for_load_state("domcontentloaded")
            final = page.url
            note = None
            if "google.com/sorry" in final or "/sorry/index" in final:
                page.goto(f"https://lite.duckduckgo.com/lite/?q={q_enc}")
                page.wait_for_load_state("domcontentloaded")
                final = page.url
                note = (
                    "Google showed a bot check page; same query was opened via "
                    "DuckDuckGo Lite instead."
                )
            out = {"status": "searched", "query": query, "url": final}
            if note:
                out["note"] = note
            return out

        if op == "click_text":
            page.click(f"text={params['click_text']}")
            return {"status": "clicked", "text": params["click_text"]}

        if op == "get_text":
            return {"text": page.inner_text("body")[:2000]}

        if op == "get_links":
            links = page.eval_on_selector_all(
                "a",
                "elements => elements.map(e => ({text: e.innerText, href: e.href})).slice(0, 15)",
            )
            return {"status": "links", "links": links}

        return {"error": "unknown browser action"}

    try:
        return work()
    except Exception as exc:
        if not _playwright_connection_lost(exc):
            raise
        print("[Browser] session closed; reopening and retrying once…")
        _dispose_playwright_session()
        try:
            return work()
        except Exception:
            _dispose_playwright_session()
            raise
