"""Gradio chat app: answers questions only from the ingested documents."""
import os
import re
from pathlib import Path

import chromadb
import gradio as gr
import ollama
from rank_bm25 import BM25Okapi

DB_DIR = Path(__file__).resolve().parent / "chroma_db"
EMBED_MODEL = "nomic-embed-text"
CHAT_MODEL = os.environ.get("CHAT_MODEL", "qwen2.5:7b")
KEEP_ALIVE = "30m"   # keep models loaded between questions
NUM_PREDICT = 400    # max answer length in tokens (CPU generation is slow)
TOP_K = 3            # chunks sent to the model (a short prompt is much faster on CPU)
CANDIDATES = 10      # results taken from each search (vector, BM25) before merging
RRF_K = 60           # reciprocal rank fusion constant
MAX_DISTANCE = 0.6   # cosine distance; higher means less similar. Tune with tests/questions.md
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

# Keyword index (BM25) over the same chunks, so exact terms like "event 4012" are found reliably
STOPWORDS = {"a", "an", "the", "is", "are", "of", "to", "in", "on", "for", "and", "or", "what", "does",
             "do", "how", "which", "that", "this", "it", "be", "must", "can", "i", "with", "by", "at"}


def tokens(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOPWORDS]


_chunks = collection.get()
CHUNK_IDS, CHUNK_DOCS, CHUNK_METAS = _chunks["ids"], _chunks["documents"], _chunks["metadatas"]
CHUNK_POS = {cid: i for i, cid in enumerate(CHUNK_IDS)}
bm25 = BM25Okapi([tokens(d) for d in CHUNK_DOCS])


def retrieve(question: str, q_emb) -> tuple[list[tuple[str, dict]], float]:
    """Hybrid search: vector top results + BM25 top results, merged with reciprocal rank fusion.
    Returns ([(text, metadata), ...], best vector distance)."""
    res = collection.query(query_embeddings=q_emb, n_results=CANDIDATES)
    scores = bm25.get_scores(tokens(question))
    bm25_ids = [CHUNK_IDS[i] for i in sorted(range(len(scores)), key=lambda i: -scores[i])[:CANDIDATES]
                if scores[i] > 0]
    fused: dict[str, float] = {}
    for ranking in (res["ids"][0], bm25_ids):
        for rank, cid in enumerate(ranking):
            fused[cid] = fused.get(cid, 0) + 1 / (RRF_K + rank + 1)
    top = sorted(fused, key=fused.get, reverse=True)[:TOP_K]
    return [(CHUNK_DOCS[CHUNK_POS[c]], CHUNK_METAS[CHUNK_POS[c]]) for c in top], res["distances"][0][0]


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
    hits, best_distance = retrieve(search_question, q_emb)

    if not hits or best_distance > MAX_DISTANCE:
        yield NOT_FOUND
        return

    context = "\n\n".join(f"[{label(m)}]\n{d}" for d, m in hits)
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
    sources = sorted({f"{m['source']} - {m['heading']} ({pages(m)})" for _, m in hits})
    yield f"{reply}\n\nSources: {', '.join(sources)}"


if __name__ == "__main__":
    gr.ChatInterface(answer, title="Document Q&A (local RAG)").launch()
