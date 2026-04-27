from memory_store import load_memories

def retrieve_relevant(query):
    memories = load_memories()
    
    # dumb version first
    results = []
    for m in memories:
        if any(word in m["content"] for word in query.split()):
            results.append(m)
    
    return results[:5]