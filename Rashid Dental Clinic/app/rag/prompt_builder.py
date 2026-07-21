def build_prompt(question, chunks, history):

    context = ""

    sources = []

    for chunk in chunks:

        context += f"""
Source: {chunk['source']}
Heading: {chunk['heading']}

{chunk['content']}

-------------------------
"""

        sources.append(chunk["source"])

    conversation = ""

    for message in history:

        conversation += (
            f"{message['role'].capitalize()}: "
            f"{message['content']}\n"
        )

    prompt = f"""
You are Rashid Dental Clinic's AI Assistant.

IMPORTANT RULES

- Answer ONLY using the provided context.
- Never invent information.
- Never diagnose.
- Never prescribe medication.
- If information is unavailable, say so.
- Keep answers concise and professional.
- If the user refers to something mentioned earlier (e.g. "it", "that", "them"), use the conversation history to understand the reference.

Conversation History

{conversation}

Knowledge Base

{context}

Current Question

{question}

Answer:
"""

    return prompt, list(set(sources))

