from app.rag.vector_store import search

SIMILARITY_THRESHOLD = 1.2


def retrieve(question):

    results = search(question)

    retrieved = []

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    for document, metadata, distance in zip(
        documents,
        metadatas,
        distances
    ):

        if distance > SIMILARITY_THRESHOLD:
            continue

        retrieved.append(
            {
                "source": metadata["source"],
                "heading": metadata["heading"],
                "content": document,
                "distance": distance
            }
        )

    return retrieved