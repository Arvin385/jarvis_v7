# prompt is recieved from any device (xenbook, phone, or loq)
# All prompts are routed to be classifed on the xenbook with a specific prompt asking for SIMPLE or COMPLEX
# Definition of COMPLEX is one that requires additional Reasoning or Action taken by an LLM or tools, and
# cannot give the user a superb result with a one-time LLM text generation response (even with memory).  
# Definition of SIMPLE is one that does not require additional R/A and can be reach a supurb result 
# through a one-time LLM text generation (including the use of memory).
# All responses are to be returned to the original client in the same form in which the prompt was recieved:
# If through STT-> return with TTS. If through plain text-> return with plain text.

from llm import generate_local, generate_loq, generate_phone, generate_xenbook, SYSTEM_PROMPT, CLASSIFIER_PROMPT, parse_classifier_output
import json

#print(generate_xenbook("hi whats up?"))
#print(generate_loq("hi whats up?"))
#print(generate_phone("hi whats up?"))

print("Jarvis Initialized.")

while True:
    prompt = input(">> ")
    
    raw = generate_xenbook(prompt, CLASSIFIER_PROMPT)
    print(raw)
    parsed = parse_classifier_output(raw)
    print(parsed)
    mode = parsed
    
    if mode == "SIMPLE":
        print(generate_local(prompt, SYSTEM_PROMPT))
    else:
        print(generate_loq(prompt, SYSTEM_PROMPT))
