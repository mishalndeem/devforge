from fastapi import FastAPI

app = FastAPI(
    title="Rashid Dental AI Assistant",
    version="1.0.0"
)

print("After FastAPI:", app, type(app))

from app.rag.loader import load_markdown_files
print("After loader:", app, type(app))

from app.rag.chunker import chunk_all_documents
print("After chunker:", app, type(app))

from app.rag.vector_store import index_chunks, search
print("After vector_store:", app, type(app))

from app.routes.chat import router as chat_router
print("After chat:", app, type(app))


@app.get("/")
def home():
    return {
        "message": "Rashid Dental AI Assistant API is running!"
    }


@app.get("/documents")
def documents():

    docs = load_markdown_files()

    return {
        "total_documents": len(docs),
        "documents": docs
    }


@app.get("/chunks")
def chunks():

    docs = load_markdown_files()

    chunks = chunk_all_documents(docs)

    return {
        "total_chunks": len(chunks),
        "chunks": chunks
    }


@app.post("/index")
def build_index():

    docs = load_markdown_files()

    chunks = chunk_all_documents(docs)

    index_chunks(chunks)

    return {
        "message": "Knowledge base indexed successfully.",
        "chunks": len(chunks)
    }


@app.get("/search")
def semantic_search(query: str):

    results = search(query)

    return results


app.include_router(chat_router)

from app.database.database import Base, engine
print("After database:", app, type(app))

from app.database import models
print("After models:", app, type(app))

Base.metadata.create_all(bind=engine)

from app.routes.appointments import router as appointment_router
print("After appointments:", app, type(app))

app.include_router(appointment_router)