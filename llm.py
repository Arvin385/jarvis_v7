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

No explanation. No extra text.

---

Definitions:

SIMPLE:
- Can be answered with a single, direct LLM response
- Does NOT require multi-step reasoning, planning, or tool use
- Does NOT require iterative refinement
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
  - designing systems or architectures
  - debugging non-trivial issues
  - strategy, optimization, or tradeoff analysis
  - long-form structured outputs

---

Rules:
- Be conservative: prefer SIMPLE unless clearly COMPLEX
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
    if system == "jarvis":
        SYSTEM = SYSTEM_PROMPT
    elif system == "classifier":
        SYSTEM = CLASSIFIER_PROMPT
    else:
        print("ERROR: Select a System Prompt")

    return _chat(XENBOOK_URL, XENBOOK_MODEL, prompt, SYSTEM)

def generate_phone(prompt: str, system: str) -> str:
    print("phone:")
    if system == "jarvis":
        SYSTEM = SYSTEM_PROMPT
    elif system == "classifier":
        SYSTEM = CLASSIFIER_PROMPT
    else:
        print("ERROR: Select a System Prompt")

    return _chat(PHONE_URL, PHONE_MODEL, prompt, SYSTEM)

def generate_loq(prompt: str,  system: str) -> str:
    print("loq:")
    if system == "jarvis":
        SYSTEM = SYSTEM_PROMPT
    elif system == "classifier":
        SYSTEM = CLASSIFIER_PROMPT
    else:
        print("ERROR: Select a System Prompt")

    return _chat(LOQ_URL, LOQ_MODEL, prompt, SYSTEM)