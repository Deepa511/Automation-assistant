"""Gradio chat app: answers questions only from the ingested documents."""
import os
from pathlib import Path

import chromadb
import gradio as gr
import ollama

DB_DIR = Path(__file__).resolve().parent / "chroma_db"
EMBED_MODEL = "nomic-embed-text"
CHAT_MODEL = os.environ.get("CHAT_MODEL", "qwen2.5:7b")
KEEP_ALIVE = "30m"   # keep models loaded between questions
NUM_PREDICT = 400    # max answer length in tokens (CPU generation is slow)
TOP_K = 3
MAX_DISTANCE = 0.6   # cosine distance; higher means less similar. Tune with tests/questions.md
RELATIVE_CUTOFF = 0.1  # drop chunks more than this farther away than the best chunk
HISTORY_FOR_REWRITE = 4  # exchanges (user + assistant) used to rewrite a follow-up question
HISTORY_FOR_ANSWER = 2   # exchanges passed to the answering call for conversational context
NOT_FOUND = "I couldn't find that in the document."

SYSTEM_PROMPT = (
    "You answer questions using ONLY the context provided. "
    f"If the context does not contain the answer, reply exactly: {NOT_FOUND} "
    "Earlier messages are only for conversational context; the answer must come from the context. "
    "Do not use outside knowledge. For procedures, give every step in order. "
    "Cite the section and page like [7.5 Replacing the camera, pages 13-14]."
)

collection = chromadb.PersistentClient(path=str(DB_DIR)).get_collection("docs")


def pages(m: dict) -> str:
    a, b = m["page_start"], m["page_end"]
    return f"page {a}" if a == b else f"pages {a}-{b}"


def label(m: dict) -> str:
    return f"{m['source']}, {m['heading']}, {pages(m)}"


def clean_history(history) -> list[dict]:
    """Gradio history -> [{"role", "content"}] with plain-text content."""
    out = []
    for m in history or []:
        content = m["content"]
        if isinstance(content, list):  # Gradio may send a list of parts
            content = " ".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in content)
        if m["role"] in ("user", "assistant") and content.strip():
            out.append({"role": m["role"], "content": content})
    return out


def standalone_question(question: str, history: list[dict]) -> str:
    """Rewrite a follow-up ("What must be done afterwards?") into a self-contained question."""
    if not history:
        return question
    # the "Sources:" list is noise for rewriting, so drop it from the assistant messages
    chat = "\n".join(f"{m['role']}: {m['content'].split('Sources:')[0].strip()}"
                     for m in history[-HISTORY_FOR_REWRITE * 2:])
    reply = ollama.chat(
        model=CHAT_MODEL,
        options={"temperature": 0, "num_predict": 80},
        keep_alive=KEEP_ALIVE,
        messages=[{"role": "user", "content": (
            "Rewrite the last user question as one standalone question that can be understood "
            "without the conversation. Replace words like it, that, this, them, afterwards or "
            "'the document' with what they refer to in the conversation. Keep all names, codes "
            "and numbers. Only return the question unchanged if it has no such references. "
            "Reply with the question only.\n\n"
            "Example:\n"
            "user: How do I replace the camera?\nassistant: (steps 1 to 7)\n"
            "Last user question: Which document is that from?\n"
            "Standalone question: Which document describes how to replace the camera?\n\n"
            f"Conversation:\n{chat}\n\nLast user question: {question}\nStandalone question:")}],
    )["message"]["content"].strip()
    return reply or question


def answer(question: str, history):
    """Generator: yields the growing answer so Gradio shows it while it is being written."""
    history = clean_history(history)
    search_question = standalone_question(question, history)
    q_emb = ollama.embed(model=EMBED_MODEL, input=search_question)["embeddings"]
    res = collection.query(query_embeddings=q_emb, n_results=TOP_K)
    hits = list(zip(res["documents"][0], res["metadatas"][0], res["distances"][0]))

    if not hits or hits[0][2] > MAX_DISTANCE:
        yield NOT_FOUND
        return
    # keep only chunks close to the best one: a shorter prompt is much faster on CPU
    hits = [h for h in hits if h[2] <= hits[0][2] + RELATIVE_CUTOFF]

    context = "\n\n".join(f"[{label(m)}]\n{d}" for d, m, _ in hits)
    stream = ollama.chat(
        model=CHAT_MODEL,
        options={"temperature": 0.1, "num_predict": NUM_PREDICT},
        keep_alive=KEEP_ALIVE,
        stream=True,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            *history[-HISTORY_FOR_ANSWER * 2:],
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
        ],
    )
    reply = ""
    for part in stream:
        reply += part["message"]["content"]
        yield reply

    if NOT_FOUND in reply:
        yield NOT_FOUND
        return
    sources = sorted({f"{m['source']} - {m['heading']} ({pages(m)})" for _, m, _ in hits})
    yield f"{reply}\n\nSources: {', '.join(sources)}"


if __name__ == "__main__":
    gr.ChatInterface(answer, title="Document Q&A (local RAG)").launch()
