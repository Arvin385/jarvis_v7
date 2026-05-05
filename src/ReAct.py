# Reason Action Loop

# flow:
#   while not done:
#       reason _result = reason_call (prompt, state)
#       if done:
#           finish
#       
#       action = reason_result["action"]
#       action_result = act_call(action)
#       
#       state["history"].append(observe(action_result))

import json
import re

from llm import generate_loq, parse_agent_json
from act import act_call


def _browser_intent_for_empty_history_done(t: str, original: str) -> bool:
    if t.startswith(
        (
            "open ",
            "visit ",
            "go to ",
            "goto ",
            "launch ",
            "navigate to ",
        )
    ):
        return True
    if "http://" in original or "https://" in original:
        return True
    if re.search(r"\bwww\.[a-z0-9.-]+\.[a-z]{2,}\b", t):
        return True
    if re.search(r"\bopen\s+[a-z0-9.-]+\.[a-z]{2,}\b", t):
        return True
    return False


def _terminal_intent_for_empty_history_done(t: str) -> bool:
    if "in my terminal" in t or "in the terminal" in t or "my terminal" in t:
        return True
    if re.search(r"\b(create|make)\b.*\b(folder|directory|dir)\b", t):
        return True
    if re.search(r"\b(create|make|write)\b.*\b(file|text file)\b", t):
        return True
    if re.search(r"\b(copy|move|delete|remove)\b.*\b(file|folder|directory)\b", t):
        return True
    if any(
        k in t
        for k in (
            "mkdir",
            "rmdir",
            "touch ",
            "chmod ",
            "chown ",
            "run command",
            "shell command",
            "run a command",
            "execute ",
            "powershell",
            "apt install",
            "apt-get ",
            "dnf ",
            "yum ",
            "pacman ",
            "brew ",
            "git clone",
            "pip install",
            "nano ",
            "vim ",
        )
    ):
        return True
    if re.match(
        r"^(ls|dir|pwd|whoami|id|uname|df|free|ps|jobs|uptime|env|cat|grep|sed|awk|curl|wget|scp|ssh)\b",
        t,
    ):
        return True
    if t in ("ls", "pwd", "whoami"):
        return True
    return False


def _gmail_intent_for_empty_history_done(t: str) -> bool:
    if "email" in t or "gmail" in t:
        return True
    if re.search(r"\b(send|draft|compose|reply|forward)\b.*\b(email|mail)\b", t):
        return True
    if re.search(r"\b(inbox|unread|thread|message id)\b", t):
        return True
    return False


def _empty_history_done_blocked_reason(user_prompt: str) -> str | None:
    """If truthy: model must NOT emit done:true with zero tool observations for this prompt."""
    p = (user_prompt or "").strip()
    if not p:
        return None
    t = p.lower()

    if _browser_intent_for_empty_history_done(t, p):
        return (
            "User request needs the browser tool. Use done:false with a concrete browser "
            "action (query, get_links, goto_url, open_external). Use done:true only after "
            "real tool observations appear in history."
        )
    if _terminal_intent_for_empty_history_done(t):
        return (
            "User request needs the terminal tool. Use done:false with tool=terminal, "
            "action=run_command, parameters.command as one shell string (&& ok). "
            "Use done:true only after stdout/stderr from executed commands appear "
            "in history; never fabricate command output."
        )
    if _gmail_intent_for_empty_history_done(t):
        return (
            "User request needs the gmail tool. Use done:false with tool=gmail and "
            "one of actions: send_email, list_messages, get_message. "
            "Use done:true only after gmail observations appear in history."
        )
    return None


def agent_call(prompt, state):
    system_prompt = """
You are an autonomous agent operating a tool-based system.

Your job is to solve the user’s request step-by-step using tools. You must reason, take actions, observe results, and continue until completion.

You control a real Playwright browser window plus the OS default browser: `query` opens search results, `get_links` reads links from the page, `click_text` clicks visible text in Playwright. Use `open_external` when the user should get the chosen URL in their normal desktop browser (default app). Never pass a bare `https://...` URL as `query`—always use `goto_url` or `open_external` with `parameters.url`. Every turn you must output only the JSON schema below.

---

# AVAILABLE TOOLS

1. terminal
- runs shell commands

2. browser (persistent headed browser)
- used for all web interaction

3. gmail
- used for sending and reading Gmail via Gmail API

---

# TERMINAL CAPABILITIES (`tool` MUST be `"terminal"`)

Use the terminal whenever the user wants **shell commands** executed: filesystem (mkdir, mv, cd, …),
package managers, git/builds/scripts, piping, text search (`grep`), networking (`curl`/`wget` to inspect),
or phrases like **“in my terminal”**, **“run ls”**, **“create a folder/file”**.

There is exactly one verb: **`run_command`**. Provide the full shell line as **`parameters.command`** (a string).
You may combine steps with **`&&`** in that one string.

**Never answer with `"done": true` and pretend you ran commands** unless the history already contains
successful terminal observations (`stdout` / `stderr` / `returncode`) after each required step.

**Example — run `ls`:**
```
{"done": false, "thought": "User asked to list the current directory.", "action": {"tool": "terminal", "action": "run_command", "parameters": {"command": "ls -la"}}}
```

**Example — create folder and write a UTF-8 line (POSIX):**
```
{"done": false, "thought": "Need directory then file with greeting.", "action": {"tool": "terminal", "action": "run_command", "parameters": {"command": "mkdir -p test-created-folder && echo 'hello Arvin' > test-created-folder/hello.txt"}}}
```

Prefer **multiple** `done: false` + `run_command` steps when that is clearer (mkdir, then verify, then write).

---

# BROWSER CAPABILITIES

You MUST use exactly one of the following actions:

- query
  {"query": "..."}
  → Playwright opens a Google search in the browser; if Google blocks automation, the tool reloads the same query on DuckDuckGo Lite so links are still obtainable

- get_links
  {}
  → returns list of links from current page

- get_text
  {}
  → returns visible page text

- click_text
  {"click_text": "..."}
  → clicks a visible element in the Playwright window

- goto_url
  {"url": "https://..."}
  → navigates the Playwright tab to that exact URL (use after you know the link from get_links)

- open_external
  {"url": "https://..."}
  → opens that URL in the user’s default system browser (xdg-open / OS handler), not only inside Playwright

---

# GMAIL CAPABILITIES (`tool` MUST be `"gmail"`)

- send_email
  {"to": "name@example.com", "subject": "...", "body": "...", "cc": "...", "bcc": "..."}
  → sends an email from the authenticated Gmail account

- list_messages
  {"query": "in:inbox is:unread", "max_results": 10}
  → lists message ids matching query

- get_message
  {"message_id": "..."}
  → returns metadata/snippet for one message

Never claim you sent/read email unless a gmail tool result confirms it.
If gmail returns `gmail_not_configured`, guide user to run:
`python src/tools/gmail_oauth_setup.py` once, then retry.

---

# CRITICAL STATE TRANSITION RULES (VERY IMPORTANT)

You must follow these rules strictly:

1. After using "query":
   → you MUST use either "get_links" or "get_text" next
   → you are NOT allowed to repeat "query" immediately again

2. After "get_links":
   → use "goto_url" or "open_external" with the chosen href when you have a URL; or "click_text" on its title; or "get_text"

3. When the user asks to actually open / visit / show the website in their browser:
   → prefer `"action": "open_external"` with the exact `href` you picked from observations

4. After "click_text":
   → use "get_text" or continue navigation if needed

5. You MUST NOT repeat the same action twice in a row unless the previous action failed.

6. If an action fails, you may retry once with a modified approach.

7. "goto_url" may be used back-to-back for navigation across different pages.
   → do NOT repeat "goto_url" to the same URL unless the previous goto_url returned an error.

---

# DECISION RULES

- Break tasks into small steps
- If the task changes the machine (files, dirs, installs, builds, repos) or invokes a shell, use **terminal**.
- Use **browser** for fetching web pages / search SERPs / links the user cares about visually.
- Use **gmail** for email operations (send/list/read); do not use browser/terminal for those unless asked.
- For setup/install requests: use browser only to fetch instructions, then switch to terminal `run_command` to execute setup steps.
- Do not invent command output—read it from observation history (`stdout`, `stderr`, `returncode`).
- NEVER assume information you have not observed

---

# REASONING RULE

Think briefly about what information you already have and what is missing.
Then choose the next single best action.

---

# OUTPUT FORMAT (STRICT JSON ONLY)

Your entire reply must be a single JSON object. Do not prepend or append prose, markdown, apologies, or clarifying questions.

Hard rule (browser): never set `"done": true` for open/visit/navigate until AFTER a matching browser action ran and observations exist in history.

Hard rule (terminal): never set `"done": true` for create/run/install/build tasks until AFTER the matching `terminal`/`run_command` steps ran and observations exist in history. Do **not** put the shell command alone in `"final_answer"` instead of invoking `run_command`.

If the user gives a hostname without scheme (example: `open oneclique.us`), assume `https://` in `parameters.url`.

If unsure for purely conversational asks with **no tools needed**, `"done": true` with a brief `final_answer` is acceptable.

Browser step — not finished (tool is exactly `"browser"`; `action` is one browser verb):

{
  "done": false,
  "thought": "brief reasoning about what is needed next",
  "action": {
    "tool": "browser",
    "action": "query",
    "parameters": {"query": "ACM UMD site"}
  }
}

Terminal step — not finished (tool is exactly `"terminal"`; `action` must be `"run_command"`):

{
  "done": false,
  "thought": "User wants a listing of the cwd.",
  "action": {
    "tool": "terminal",
    "action": "run_command",
    "parameters": {"command": "ls -la"}
  }
}

Gmail step — not finished (tool is exactly `"gmail"`):

{
  "done": false,
  "thought": "User asked to send email.",
  "action": {
    "tool": "gmail",
    "action": "send_email",
    "parameters": {"to": "person@example.com", "subject": "Hi", "body": "Hello"}
  }
}

If finished:

{
  "done": true,
  "final_answer": "final answer to the user"
}

---

# PARAMETER RULES

- parameters must ALWAYS be a JSON object
- never pass raw strings
- Browser GOOD: `"parameters": {"query": "ACM UMD"}` BAD: `"parameters": "ACM UMD"`
- Terminal GOOD: `"parameters": {"command": "mkdir -p d && echo hi > d/f.txt"}`
- Terminal BAD: missing `command`; BAD: quoting the wrapper object as a string instead of nested JSON.

---

# EXECUTION PRINCIPLE

You are not allowed to “stall” or repeat the same action without new information.
Every step must move closer to the final answer.

Never fabricate tool outcomes—if nothing has run yet, your next reply must set `"done": false` with a concrete `action`.
---
"""

    user_message = {
        "prompt": prompt,
        "history": state["history"],
    }

    _serialized = json.dumps(user_message)

    def _valid_step_shape(obj):
        if not isinstance(obj, dict):
            return False
        if "done" not in obj:
            return False
        if obj.get("done") is True:
            return isinstance(obj.get("final_answer"), str)
        if obj.get("done") is False:
            act = obj.get("action")
            return (
                isinstance(act, dict)
                and isinstance(act.get("tool"), str)
                and isinstance(act.get("action"), str)
                and isinstance(act.get("parameters"), dict)
            )
        return False

    def _normalize_step_shape(obj):
        """Coerce common near-valid forms into the strict schema."""
        if not isinstance(obj, dict):
            return obj
        if obj.get("done") is False and isinstance(obj.get("action"), dict):
            act = obj["action"]
            if "parameters" not in act or act.get("parameters") is None:
                act["parameters"] = {}
        return obj

    # ---- LLM CALL ----
    response = generate_loq(_serialized, system_prompt, temperature=0.35, trace_label="loq:")

    # ---- PARSE ----
    try:
        parsed = parse_agent_json(response)
    except ValueError:
        repair_prompt = (
            "Your previous output was invalid for this step.\n\n"
            "Continue the SAME task using the same prompt/history context below.\n\n"
            f"Current task context JSON:\n{_serialized}\n\n"
            f"Invalid output was:\n{response}\n\n"
            "Return ONLY one valid JSON object matching exactly one of these schemas:\n"
            '1) {"done": false, "thought": "...", "action": {"tool": "browser", '
            '"action": "query | get_links | get_text | click_text | goto_url | open_external", '
            '"parameters": {...}}}\n'
            '2) {"done": false, "thought": "...", "action": {"tool": "terminal", '
            '"action": "run_command", "parameters": {"command": "..."}}}\n'
            '3) {"done": false, "thought": "...", "action": {"tool": "gmail", '
            '"action": "send_email | list_messages | get_message", "parameters": {...}}}\n'
            '4) {"done": true, "final_answer": "..."}\n'
            'Choose "terminal" only for system/shell tasks and always include parameters.command.\n'
            'Choose "browser" only for web-navigation tasks.\n'
            'Choose "gmail" only for email tasks.\n'
            "No markdown. No prose. No explanation."
        )
        repaired = generate_loq(
            repair_prompt,
            system_prompt,
            temperature=0.1,
            trace_label="loq(repair):",
        )
        try:
            parsed = parse_agent_json(repaired)
        except ValueError as exc:
            raise Exception(
                f"{exc}\n\nRaw agent output:\n{response}\n\nRepair output:\n{repaired}"
            ) from exc

    parsed = _normalize_step_shape(parsed)
    if not _valid_step_shape(parsed):
        shape_repair_prompt = (
            "Your previous JSON was parsed but had an invalid schema for this agent.\n\n"
            "Continue the SAME task using the same prompt/history context below.\n\n"
            f"Current task context JSON:\n{_serialized}\n\n"
            f"Invalid parsed object:\n{json.dumps(parsed, ensure_ascii=False)}\n\n"
            "Return ONLY one valid JSON object in exactly one schema:\n"
            '1) {"done": false, "thought": "...", "action": {"tool": "browser", '
            '"action": "query | get_links | get_text | click_text | goto_url | open_external", '
            '"parameters": {...}}}\n'
            '2) {"done": false, "thought": "...", "action": {"tool": "terminal", '
            '"action": "run_command", "parameters": {"command": "..."}}}\n'
            '3) {"done": false, "thought": "...", "action": {"tool": "gmail", '
            '"action": "send_email | list_messages | get_message", "parameters": {...}}}\n'
            '4) {"done": true, "final_answer": "..."}\n'
            "No extra keys like tool_calls/content. No markdown. No prose."
        )
        repaired_shape = generate_loq(
            shape_repair_prompt,
            system_prompt,
            temperature=0.1,
            trace_label="loq(shape-repair):",
        )
        try:
            parsed = parse_agent_json(repaired_shape)
        except ValueError as exc:
            raise Exception(
                f"{exc}\n\nRaw agent output:\n{response}\n\nShape repair output:\n{repaired_shape}"
            ) from exc
        parsed = _normalize_step_shape(parsed)
        if not _valid_step_shape(parsed):
            raise Exception(
                "Agent returned structurally invalid step after repair.\n\n"
                f"Step: {parsed}"
            )

    return parsed



def run_agent(prompt, max_steps=10):
    state = {
        "history": []
    }

    for i in range(max_steps):
        # 1. AGENT STEP (reason + observe combined)
        step = agent_call(prompt, state)
        print(f"step {i}: {step}")
        # expected:
        # {
        #   "done": bool,
        #   "final_answer": str (if done),
        #   "action": {...}
        # }

        if step["done"]:
            _block_reason = _empty_history_done_blocked_reason(prompt)
            if _block_reason and not state["history"]:
                print(f"result {i}: rejected premature done:true (tools required first)")
                state["history"].append(
                    {
                        "action": {
                            "tool": "none",
                            "action": "(none)",
                            "parameters": {},
                        },
                        "result": {
                            "error": (
                                "You emitted done:true with no executed tools in history.\n\n"
                                + _block_reason
                            ),
                        },
                        "status": "error",
                        "success": False,
                    }
                )
                continue

            return step["final_answer"]

        _act_raw = step.get("action")
        if not isinstance(_act_raw, dict):
            result = {
                "error": (
                    "invalid action schema from agent: expected object with "
                    "tool/action/parameters"
                ),
                "received_action": _act_raw,
            }
            status = "error"
            print(f"result {i}: {result['error']}")
            state["history"].append(
                {
                    "action": {
                        "tool": "none",
                        "action": "(invalid-action)",
                        "parameters": {},
                    },
                    "result": result,
                    "status": status,
                    "success": False,
                }
            )
            continue

        _act = _act_raw
        if (
            _act.get("tool") == "browser"
            and _act.get("action") == "goto_url"
            and state["history"]
        ):
            _prev = state["history"][-1]
            _prev_action = _prev.get("action") or {}
            _prev_result = _prev.get("result") or {}
            same_prev_url = (
                _prev_action.get("tool") == "browser"
                and _prev_action.get("action") == "goto_url"
                and (_prev_action.get("parameters") or {}).get("url")
                == (_act.get("parameters") or {}).get("url")
            )
            prev_failed = isinstance(_prev_result, dict) and "error" in _prev_result
            if same_prev_url and not prev_failed:
                result = {
                    "error": (
                        "blocked: repeated goto_url to the same URL after success; "
                        "use get_text or get_links on the current page first"
                    )
                }
                status = "error"
                print(f"result {i}: {result['error']}")
                state["history"].append(
                    {
                        "action": step["action"],
                        "result": result,
                        "status": status,
                        "success": False,
                    }
                )
                continue

        if (
            _act.get("tool") == "browser"
            and _act.get("action") == "query"
            and state["history"]
        ):
            _prev = state["history"][-1].get("action") or {}
            if _prev.get("tool") == "browser" and _prev.get("action") == "query":
                result = {
                    "error": (
                        "blocked: do not run browser query immediately after another query; "
                        "use get_links or get_text on the current page first"
                    )
                }
                status = "error"
                print(f"result {i}: {result['error']}")
                state["history"].append(
                    {
                        "action": step["action"],
                        "result": result,
                        "status": status,
                        "success": False,
                    }
                )
                continue

        # 2. ACT
        try:
            result = act_call(step["action"])
            if isinstance(result, dict):
                summary = (
                    result.get("error")
                    or result.get("status")
                    or ", ".join(f"{k}=…" for k in list(result)[:3])
                )
            else:
                summary = repr(result)
            print(f"result {i}: {summary}")

            if isinstance(result, dict) and "error" in result:
                status = "error"
            else:
                status = "success"
        except Exception as e:
            result = {"error": str(e)}
            status = "error"

        # 3. UPDATE STATE (CRITICAL)
        state["history"].append({
            "action": step["action"],
            "result": result,
            "status": status,
            "success": status == "success"
        })

    return "Agent stopped: max steps reached."