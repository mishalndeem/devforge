from fastapi import FastAPI

from app.rag.loader import load_markdown_files

from app.rag.chunker import chunk_all_documents

from app.rag.vector_store import index_chunks, search

from app.routes.chat import router as chat_router

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Rashid Dental AI Assistant",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

from app.database.database import Base
from app.database.database import engine

#import app.database.models
from app.database import models

Base.metadata.create_all(bind=engine)

from app.routes.appointments import router as appointment_router


app.include_router(appointment_router)

