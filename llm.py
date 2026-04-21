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

import requests
import os

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
    """You are a strict routing classifier for a distributed AI system.

Your task is to classify the user's request as either:
- SIMPLE
- COMPLEX

Return ONLY a valid JSON object:
{"mode": "SIMPLE"} 
or 
{"mode": "COMPLEX"}

Your response must be valid JSON parsable by json.loads() without preprocessing.
No explanation. No extra text.

---

Definitions:

SIMPLE:
- The final result of the user's query can be satisfied with a single, direct LLM response
- Does NOT require multi-step reasoning, planning, or tool use
- Does NOT require iterative refinement
- Does NOT require access or information from sources or tools other than your pretrained data.
  - Does not need access to email, internet, local files, communication, or terminal.
- Examples:
  - factual questions
  - short explanations
  - casual conversation
  - basic instructions
  - summarization

COMPLEX:
- Requires reasoning, planning, or multi-step thinking
- Would benefit from deeper analysis or structured thinking
- May require tools, decomposition, or multiple steps
- Examples:
  - requiring tangible interaction with the internet, local device, or cloud. 
  - Sending emails, accessing local or cloud files, intra-device and inter-device communication. 
  - designing systems or architectures
  - debugging non-trivial issues
  - strategy, optimization, or tradeoff analysis
  - long-form structured outputs

---

Rules:
- Ignore style, tone, or personality
- Focus ONLY on task complexity
- Do NOT consider latency or device constraints
- Always output valid JSON

---

User input will be provided next."""

)

def _chat(base_url, model, prompt, system_prompt):
    url = f"{base_url}/api/chat"

    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "options": {
            "temperature": 0.7
        }
    }

    r = requests.post(url, json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()

    return data["message"]["content"]


def generate_xenbook(prompt: str, system: str) -> str:
    print("xenbook:")
    return _chat(XENBOOK_URL, XENBOOK_MODEL, prompt, system)

def generate_phone(prompt: str, system: str) -> str:
    print("phone:")
    return _chat(PHONE_URL, PHONE_MODEL, prompt, system)

def generate_loq(prompt: str,  system: str) -> str:
    print("loq:")
    return _chat(LOQ_URL, LOQ_MODEL, prompt, system)

def generate_local(prompt: str,  system: str) -> str:
    print("local:")
    if DEVICE_ROLE == "xenbook":
        model = XENBOOK_MODEL
    else:
        model = PHONE_MODEL
    print(model)
    return _chat(LOCAL_URL, model, prompt, system)

import json
import re

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