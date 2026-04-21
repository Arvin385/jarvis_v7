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
    "You are a helpful assistant. Be concise and accurate."
)


def _chat(base_url, model, prompt):
    url = f"{base_url}/api/chat"

    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
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


def generate_xenbook(prompt: str, use_remote: bool = True) -> str:
    print("xenbook:")
    return _chat(XENBOOK_URL, XENBOOK_MODEL, prompt)

def generate_phone(prompt: str, use_remote: bool = True) -> str:
    print("phone:")
    return _chat(PHONE_URL, PHONE_MODEL, prompt)

def generate_loq(prompt: str, use_remote: bool = True) -> str:
    print("loq:")
    return _chat(LOQ_URL, LOQ_MODEL, prompt)