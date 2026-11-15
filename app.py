"""Gradio chat app: answers questions only from the ingested documents."""
from pathlib import Path

import chromadb
import gradio as gr
import ollama

DB_DIR = Path(__file__).resolve().parent / "chroma_db"
EMBED_MODEL = "nomic-embed-text"
CHAT_MODEL = "qwen2.5:7b"
TOP_K = 4
MAX_DISTANCE = 0.6  # cosine distance; higher means less similar. Tune with tests/questions.md
NOT_FOUND = "I couldn't find that in the document."

SYSTEM_PROMPT = (
    "You answer questions using ONLY the context provided. "
    f"If the context does not contain the answer, reply exactly: {NOT_FOUND} "
    "Do not use outside knowledge. Cite the page like [page 12]."
)

collection = chromadb.PersistentClient(path=str(DB_DIR)).get_collection("docs")


def answer(question: str, history) -> str:
    q_emb = ollama.embed(model=EMBED_MODEL, input=question)["embeddings"]
    res = collection.query(query_embeddings=q_emb, n_results=TOP_K)
    docs, metas, dists = res["documents"][0], res["metadatas"][0], res["distances"][0]

    if not docs or min(dists) > MAX_DISTANCE:
        return NOT_FOUND

    context = "\n\n".join(f"[page {m['page']}] {d}" for d, m in zip(docs, metas))
    reply = ollama.chat(
        model=CHAT_MODEL,
        options={"temperature": 0.1},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
        ],
    )["message"]["content"]

    if NOT_FOUND in reply:
        return NOT_FOUND
    sources = sorted({f"{m['source']} p.{m['page']}" for m in metas})
    return f"{reply}\n\nSources: {', '.join(sources)}"


if __name__ == "__main__":
    gr.ChatInterface(answer, title="Document Q&A (local RAG)").launch()
