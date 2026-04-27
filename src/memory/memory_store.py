import json

MEMORY_FILE = "memory.json"

def load_memories():
    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_memory(memory):
    data = load_memories()
    data.append(memory)
    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f, indent=2)