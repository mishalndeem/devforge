from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

# Folder where ChromaDB will store its data
DB_PATH = Path("chroma_db")

# Embedding model
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# Persistent ChromaDB client
client = chromadb.PersistentClient(path=str(DB_PATH))

# Create (or load) a collection
collection = client.get_or_create_collection(
    name="rashid_dental_kb"
)

def index_chunks(chunks):
    """
    Store chunks in ChromaDB.
    """

    ids = []
    documents = []
    metadatas = []
    embeddings = []

    for chunk in chunks:

        text = f"{chunk['heading']}\n\n{chunk['content']}"

        vector = embedding_model.encode(text).tolist()

        ids.append(chunk["id"])
        documents.append(text)

        metadatas.append(
            {
                "source": chunk["source"],
                "heading": chunk["heading"]
            }
        )

        embeddings.append(vector)

    # Avoid duplicates if rerunning
    existing = collection.get()

    if existing["ids"]:
        collection.delete(ids=existing["ids"])

    collection.add(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas
    )

def search(query, top_k=3):

    query_embedding = embedding_model.encode(query).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=[
            "documents",
            "metadatas",
            "distances"
        ]
    )

    return results