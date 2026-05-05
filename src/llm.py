# from ollama import Client

# # Set the IP address for the synchronous client
# client_xenbook = Client(host='http://100.100.22.99:11434')
# client_phone = Client(host='http://100.97.33.1:11434')
# client_loq = Client(host='http://100.69.245.107:11434')



# def generate_xenbook(prompt):
#     response = client_xenbook.chat(
#         model='gemma2:2b',
#         messages=[{'role': 'user', 'content': prompt}],
#     )
#     print("\nxenbook:")
#     print(response['message']['content'])   

# def generate_phone(prompt):
#     response = client_phone.chat(
#         model='llama3.2:1b',
#         messages=[{'role': 'user', 'content': prompt}],
#     )
#     print("\nphone:")
#     print(response['message']['content'])   
    

# def generate_loq(prompt):
#     response = client_loq.chat(
#         model='gemma4:e2b',
#         messages=[{'role': 'user', 'content': prompt}],
#     )

#     print("\nloq:")
#     print(response['message']['content'])   

import json
import os
import re

import requests

XENBOOK_URL = os.getenv("XENBOOK_URL", "http://100.100.22.99:11434")
PHONE_URL = os.getenv("PHONE_URL", "http://100.97.33.1:11434")
LOQ_URL = os.getenv("LOQ_URL", "http://100.69.245.107:11434")
DEVICE_ROLE = os.getenv("DEVICE_ROLE", "phone")
LOCAL_URL = "http://localhost:11434"

XENBOOK_MODEL = "gemma2:2b"
PHONE_MODEL = "llama3.2:1b"
LOQ_MODEL = "gemma4:e2b"

SYSTEM_PROMPT = (
    """
    You are Jarvis, a highly capable personal AI assistant.

Your role is to provide clear, accurate, and efficient responses to the user.

---

Core behavior:

- Be concise by default
- Prioritize clarity and correctness
- Answer directly—do not ramble
- Expand only when necessary or explicitly requested
- Maintain a calm, confident, and intelligent tone

---

Response style:

- If the input is simple → respond in 1–3 sentences
- If the input requires depth → provide structured, well-organized output
- Avoid filler, repetition, or unnecessary disclaimers
- Do not mention internal system design, routing, or models

---

Interaction rules:

- If the request is ambiguous → make a reasonable assumption and proceed
- If critical information is missing → ask a short clarifying question
- If uncertain → state uncertainty briefly and give best possible answer
- Never hallucinate specific facts when unsure

---

Output modality:

- Your response will be converted to either text or speech depending on input
- Avoid formatting that does not translate well to speech unless necessary

---

You are efficient, precise, and reliable.
Respond to the user now.
"""
)

CLASSIFIER_PROMPT = (
"""You are a strict routing classifier for an AI agent system.

Your task is to classify the user's request into exactly one of two modes:

- SIMPLE
- COMPLEX

Return ONLY valid JSON in one of these formats:
{"mode": "SIMPLE"}
{"mode": "COMPLEX"}

No explanation. No extra text. Must be directly parsable by json.loads().

---

# CORE PRINCIPLE

Classify based on whether the request requires:
(1) deep multi-step reasoning OR
(2) external tool execution OR
(3) interactive system/browser control

---

# SIMPLE

Use SIMPLE if the request can be answered directly in a single LLM response without:
- planning or decomposition
- tool usage
- external interaction
- iterative steps
- system manipulation

Examples:
- factual questions ("What is recursion?")
- definitions and explanations
- summarization
- rewriting text
- casual conversation
- basic instructions or advice
- simple comparisons that do not require tools or computation

---

# COMPLEX

Use COMPLEX if ANY of the following are required:

## 1. Deep reasoning
- multi-step problem solving
- debugging
- planning or decomposition
- optimization or tradeoffs
- system design or architecture

## 2. Terminal execution (system interaction)
- running shell commands
- file system operations
- code execution or environment manipulation
- debugging runtime/system issues

## 3. Browser automation (Playwright tool)
- searching the web
- navigating websites
- clicking, scraping, or interacting with pages
- retrieving live or dynamic information

## 4. Any multi-step task that may require:
- chaining actions across tools
- maintaining state across steps
- iterative refinement

Examples:
- "open a website and extract information"
- "run a command to check system status"
- "debug why my code is failing"
- "find and summarize information from the web"
- "send an email"
- "compare live prices or current data"

---

# RULES

- If uncertain → choose COMPLEX
- Never consider tone, length, or writing style
- Do NOT assume tool availability for SIMPLE
- COMPLEX = anything that goes beyond single-response generation
- Output MUST be valid JSON only
"""
)

def _chat(base_url, model, prompt, system_prompt, temperature=0.7):
    url = f"{base_url}/api/chat"

    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "options": {
            "temperature": temperature,
        },
    }

    r = requests.post(url, json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()

    return data["message"]["content"]

def _chat_stream(base_url, model, prompt, system_prompt):
    url = f"{base_url}/api/chat"

    payload = {
        "model": model,
        "stream": True,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "options": {
            "temperature": 0.7
        }
    }

    with requests.post(url, json=payload, stream=True, timeout=120) as r:
        r.raise_for_status()

        for line in r.iter_lines(decode_unicode=True):
            if not line:
                continue

            try:
                import json
                data = json.loads(line)

                if "message" in data and "content" in data["message"]:
                    token = data["message"]["content"]
                    if token:
                        yield token

            except Exception:
                continue

    print()  

def generate_xenbook(prompt: str, system: str) -> str:
    print("xenbook:")
    return _chat(XENBOOK_URL, XENBOOK_MODEL, prompt, system)

def generate_phone(prompt: str, system: str) -> str:
    print("phone:")
    return _chat(PHONE_URL, PHONE_MODEL, prompt, system)

def generate_loq(
    prompt: str,
    system: str,
    temperature: float | None = None,
    trace_label: str = "loq:",
) -> str:
    if trace_label:
        print(trace_label)
    t = 0.7 if temperature is None else temperature
    return _chat(LOQ_URL, LOQ_MODEL, prompt, system, temperature=t)


def _first_balanced_brace_block(text: str) -> str | None:
    """Return substring from first '{' through its matching '}', respecting strings."""
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escape = False
    i = start
    while i < len(text):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
        i += 1
    return None


def _json_quote_body_as_string(body: str) -> str:
    """Decode a substring that came from inside a JSON string (JSON escape rules)."""
    if not body:
        return ""
    try:
        return json.loads(f'"{body}"')
    except json.JSONDecodeError:
        return body


def _fallback_parse_agent_payload(stripped: str) -> dict | None:
    """
    Recover agent steps when JSON is truncated (common under load) or sloppy.
    """
    dm = re.search(r'"done"\s*:\s*(true|false)\b', stripped, re.I)
    if not dm:
        return None
    done = dm.group(1).lower() == "true"
    if done:
        fm = re.search(
            r'"final_answer"\s*:\s*"((?:[^"\\]|\\.)*)"\s*',
            stripped,
            re.DOTALL,
        )
        fa = ""
        if fm:
            fa = _json_quote_body_as_string(fm.group(1))
        return {"done": True, "final_answer": fa}

    verbs = "|".join(
        (
            "query",
            "get_links",
            "get_text",
            "click_text",
            "goto_url",
            "open_external",
            "run_command",
            "send_email",
            "list_messages",
            "get_message",
        )
    )
    verb_iters = list(
        re.finditer(rf'"action"\s*:\s*"({verbs})"', stripped, flags=re.I)
    )
    inner_verb = verb_iters[-1].group(1).lower() if verb_iters else None

    tm = re.search(r'"tool"\s*:\s*"([^"]+)"', stripped)
    gmail_verbs = {"send_email", "list_messages", "get_message"}
    if tm:
        raw_tool = tm.group(1).strip().lower()
        if "terminal" in raw_tool or raw_tool.startswith("shell"):
            tool = "terminal"
        elif "gmail" in raw_tool:
            tool = "gmail"
        else:
            tool = "browser"
    else:
        tool = "browser"

    params: dict = {}

    qm = re.search(r'"query"\s*:\s*"((?:[^"\\]|\\.)*)"', stripped, re.DOTALL)
    if qm:
        params["query"] = _json_quote_body_as_string(qm.group(1))

    xm = re.search(r'"click_text"\s*:\s*"((?:[^"\\]|\\.)*)"', stripped, re.DOTALL)
    if xm:
        params["click_text"] = _json_quote_body_as_string(xm.group(1))

    um = re.search(r'"url"\s*:\s*"((?:[^"\\]|\\.)*)"', stripped, re.DOTALL)
    if not um:
        um = re.search(r'"url"\s*:\s*"([^"\n]*)', stripped)
    if um:
        params["url"] = um.group(1)

    cm = re.search(r'"command"\s*:\s*"((?:[^"\\]|\\.)*)"', stripped, re.DOTALL)
    if cm:
        params["command"] = _json_quote_body_as_string(cm.group(1))

    thought = ""
    thm = re.search(
        r'"thought"\s*:\s*"((?:[^"\\]|\\.)*)"',
        stripped,
        re.DOTALL,
    )
    if thm:
        thought = _json_quote_body_as_string(thm.group(1))

    if inner_verb is None:
        if "query" in params:
            inner_verb = "query"
        elif "url" in params:
            inner_verb = "goto_url"
        elif "click_text" in params:
            inner_verb = "click_text"
        elif "command" in params:
            inner_verb = "run_command"
            tool = "terminal"
        else:
            # Avoid silently forcing browser/get_text when salvage has no real action.
            return None

    if inner_verb == "run_command" and tool != "terminal":
        tool = "terminal"
    if inner_verb in gmail_verbs and tool != "gmail":
        tool = "gmail"

    return {
        "done": False,
        "thought": thought,
        "action": {
            "tool": tool,
            "action": inner_verb,
            "parameters": params,
        },
    }


def parse_agent_json(raw: str) -> dict:
    """Parse agent step JSON when the model wraps it in prose or markdown fences."""
    if not raw or not str(raw).strip():
        raise ValueError("Agent returned empty response")

    stripped = raw.strip()

    blobs: list[str] = []

    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", stripped)
    if fenced:
        blobs.append(fenced.group(1).strip())
    blobs.append(stripped)

    for blob in blobs:
        fragment = _first_balanced_brace_block(blob)
        if fragment is None:
            continue
        try:
            obj = json.loads(fragment)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and "done" in obj:
            return obj

    salvage = _fallback_parse_agent_payload(stripped)
    if salvage is not None:
        return salvage

    raise ValueError(f"No valid agent JSON object (expected key 'done'): {stripped[:500]!r}…")

def generate_cli(prompt: str,  system: str) -> str:
    return _chat(LOQ_URL, LOQ_MODEL, prompt, system)

def generate_local(prompt: str,  system: str) -> str:
    print("local:")
    if DEVICE_ROLE == "xenbook":
        model = XENBOOK_MODEL
    else:
        model = PHONE_MODEL
    print(model)
    return _chat(LOCAL_URL, model, prompt, system)

def generate_stream(prompt: str, system: str):
    print("Stream:")

    print(XENBOOK_MODEL)

    yield from _chat_stream(LOQ_URL, XENBOOK_MODEL, prompt, system)


def parse_classifier_output(raw: str) -> str:
    """
    Extracts SIMPLE or COMPLEX from messy LLM output.
    Handles:
    - ```json { ... } ```
    - raw JSON
    - extra text before/after JSON
    """

    if not raw:
        return "SIMPLE"

    text = raw.strip()

    # 1. Try to extract JSON block inside ``` ```
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fence_match:
        text = fence_match.group(1)

    # 2. Fallback: extract first JSON object anywhere
    if not text.startswith("{"):
        match = re.search(r"\{.*\}", text, re.S)
        if match:
            text = match.group(0)

    # 3. Parse JSON safely
    try:
        obj = json.loads(text)
        mode = obj.get("mode", "SIMPLE").upper()
    except Exception:
        # 4. Final fallback: keyword scan
        upper = raw.upper()
        if "COMPLEX" in upper:
            return "COMPLEX"
        return "SIMPLE"

    # 5. Normalize output
    if mode not in ("SIMPLE", "COMPLEX"):
        return "SIMPLE"

    return mode