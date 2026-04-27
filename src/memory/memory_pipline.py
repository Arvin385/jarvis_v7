from llm import generate_local

def process_input(user_input):
    if not is_important(user_input):
        return None

    memory = {
        "type": classify(user_input),
        "content": summarize(user_input)
    }

    return memory

def is_important(text):
    system_prompt = f"""
You are a strict memory filter for an AI system.

Your job is to decide whether a piece of information is worth storing as long-term memory.

Store ONLY information that is:
- about the user's identity, preferences, or habits
- related to ongoing projects or goals
- useful for future reasoning or actions

Do NOT store:
- trivial questions or casual conversation
- one-time requests with no future relevance
- generic knowledge

You must be conservative. Only store high-value information.

Output rules:
- Respond with ONLY "YES" or "NO"
- No explanation
- No extra text
"""

    prompt = f"""
Text:
\"\"\"{text}\"\"\"

Should this be stored as long-term memory?
"""

    response = generate_local(prompt, system_prompt).strip().upper()

    if "YES" in response:
        return True
    elif "NO" in response:
        return False
    else:
        print("Error: LLM returned did not give a proper yes or no when deciding importance of memory.")
        return False

    return "YES" in response

def summarize(text):
    system_prompt = f"""
You are a memory compressor for an AI system.

Your job is to convert input into a short, reusable memory.

Rules:
- Maximum 20 words
- Preserve important meaning
- Remove unnecessary detail
- Make it general enough to be reused later
- Do NOT include filler or conversational language

Write it as a clean factual statement.

Output rules:
- Output ONLY the summary
- No explanation
- No extra text
"""

    prompt = f"""
Text:
\"\"\"{text}\"\"\"

Summary:
"""

    response = generate_local(prompt, system_prompt).strip()

    return response

def classify(text):
    system_prompt = f"""
You are a strict memory classifier for an AI system.

Classify the input into exactly ONE category:

- semantic → facts about the user (identity, preferences, long-term info)
- episodic → events or actions that happened
- procedural → rules, behaviors, or automation logic

Definitions:
- semantic: stable, reusable knowledge about the user
- episodic: something that happened at a specific time
- procedural: instructions or "if X then Y" behavior

Output rules:
- Respond with ONLY one word:
  semantic
  episodic
  procedural
- No explanation
- No extra text
"""

    prompt = f"""
Text:
\"\"\"{text}\"\"\"

Category:
"""

    response = generate_local(prompt, system_prompt).strip().lower()

    # safety cleanup
    if "semantic" in response:
        return "semantic"
    elif "episodic" in response:
        return "episodic"
    elif "procedural" in response:
        return "procedural"

    return "episodic"  # fallback



def build_prompt(user_prompt, memory_context):
    context_text = ""

    if memory_context:
        context_text = "\n".join(
            [f"- {m['content']}" for m in memory_context]
        )

    return f"""
You are Jarvis.

Relevant memory:
{context_text if context_text else "None"}

User request:
{user_prompt}

Respond using memory when helpful.
"""