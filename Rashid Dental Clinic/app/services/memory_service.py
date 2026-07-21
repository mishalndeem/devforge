from collections import defaultdict

# session_id -> conversation history
conversation_store = defaultdict(list)

MAX_HISTORY = 10


def get_history(session_id: str):

    return conversation_store[session_id]


def add_message(session_id: str, role: str, content: str):

    conversation_store[session_id].append(
        {
            "role": role,
            "content": content
        }
    )

    # Keep only recent messages
    if len(conversation_store[session_id]) > MAX_HISTORY:
        conversation_store[session_id] = conversation_store[session_id][-MAX_HISTORY:]


def clear_history(session_id: str):

    conversation_store.pop(session_id, None)