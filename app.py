"""Gradio chat app: answers questions only from the ingested documents."""
import os
import re
import time
from pathlib import Path

import chromadb
import gradio as gr
import ollama

DB_DIR = Path(__file__).resolve().parent / "chroma_db"
EMBED_MODEL = "nomic-embed-text"
CHAT_MODEL = os.environ.get("CHAT_MODEL", "qwen2.5:7b")
KEEP_ALIVE = "30m"  # keep models loaded between questions
NUM_PREDICT = 400    # max answer length in tokens (CPU generation is slow)
TOP_K = 3
MAX_DISTANCE = 0.6   # cosine distance; higher means less similar. Tune with tests/questions.md
RELATIVE_CUTOFF = 0.1  # drop chunks more than this farther away than the best chunk
HISTORY_FOR_REWRITE = 4  # exchanges (user + assistant) used to rewrite a follow-up question
HISTORY_FOR_ANSWER = 2   # exchanges passed to the answering call for conversational context
NOT_FOUND = "I couldn't find that in the document."
SOURCES_MARK = "\n\n**Sources**"  # starts the sources block the app appends to every answer

WELCOME = ("I'm the Automation Assistant. I have knowledge about tightening, vision and cell control, "
           "including setup, calibration, alarms and codes. Feel free to ask me anything related. "
           "How can I help you?")

# Whole-message patterns answered instantly, without searching or calling the model
SMALL_TALK = [
    (r"(hi|hello|hey|hiya|howdy|greetings|good (morning|afternoon|evening))( there| assistant| everyone)?", "greet"),
    (r"(thanks|thank you|thx|cheers)( a lot| very much| assistant)?", "You're welcome! Feel free to ask me anything else."),
    (r"(bye|goodbye|see you|see ya|good night)( assistant)?", "Goodbye! Come back any time."),
    (r"(how are you|how are you doing|how is it going|how's it going|what's up|whats up)", "I'm doing well, thank you! How can I help you?"),
    (r"(who are you|what are you|what can you do|what do you know|what can i ask( you)?|help)", "about"),
]


def small_talk(question: str, name: str = "") -> str | None:
    """Instant reply to greetings, thanks and "what can you do"; None for real questions."""
    text = " ".join(re.sub(r"[^a-z' ]", " ", question.lower()).split())
    who = name.strip() or "there"
    for pattern, reply in SMALL_TALK:
        if re.fullmatch(pattern, text):
            if reply == "greet":
                return f"Hi {who}! How can I help you?"
            return f"Hi {who}! {WELCOME}" if reply == "about" else reply
    return None


SYSTEM_PROMPT = (
    "You answer questions using ONLY the context provided. "
    f"If the topic of the question does not appear in the context, reply exactly: {NOT_FOUND} "
    "If the context covers the topic but gives no step-by-step instructions, say what the context does state "
    "about it and cite it; do not refuse in that case, and do not add steps that are not in the context. "
    "Earlier messages are only for conversational context; the answer must come from the context. "
    "Do not use outside knowledge. For procedures, give every step in order. "
    "Do not repeat the same information within one answer, but always include every fact the question "
    "asks for, even if an earlier message mentioned it. "
    "Cite the section and page like [7.5 Replacing the camera, pages 13-14]."
)

collection = chromadb.PersistentClient(path=str(DB_DIR)).get_collection("docs")


def pages(m: dict) -> str:
    a, b = m["page_start"], m["page_end"]
    return f"page {a}" if a == b else f"pages {a}-{b}"


def label(m: dict) -> str:
    return f"{m['source']}, {m['heading']}, {pages(m)}"


def format_sources(hits) -> str:
    """Sources block: identical (document, section, pages) entries appear once, grouped by document."""
    unique = {(m["source"], m["page_start"], m["page_end"], m["heading"]): m for _, m in hits}
    by_doc: dict[str, list[str]] = {}
    for key in sorted(unique):
        m = unique[key]
        by_doc.setdefault(m["source"], []).append(f"{m['heading']} ({pages(m)})")
    lines = [f"- *{Path(doc).stem.replace('_', ' ')}*: {', '.join(parts)}" for doc, parts in by_doc.items()]
    return f"{SOURCES_MARK}\n\n" + "\n".join(lines)


def without_sources(text: str) -> str:
    """Cut a "Sources: ..." list the model wrote itself; the app adds its own."""
    m = re.search(r"(?im)^\W*sources?\W*:", text)
    return text[:m.start()].rstrip() if m else text


def clean_history(history) -> list[dict]:
    """Gradio history -> [{"role", "content"}] with plain-text content."""
    out = []
    for m in history or []:
        if (m.get("metadata") or {}).get("title"):  # progress-trace bubble, not part of the conversation
            continue
        content = m["content"]
        if isinstance(content, list):  # Gradio may send a list of parts
            content = " ".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in content)
        content = content.split("\n\n⏱")[0].split(SOURCES_MARK)[0]  # drop the timing footer and the sources block
        if m["role"] == "assistant" and WELCOME in content:  # the welcome message is not part of the conversation
            continue
        if m["role"] in ("user", "assistant") and content.strip():
            out.append({"role": m["role"], "content": content})
    return out


def standalone_question(question: str, history: list[dict]) -> str:
    """Rewrite a follow-up ("What must be done afterwards?") into a self-contained question.
    Only called when there is history."""
    chat = "\n".join(f"{m['role']}: {m['content'].strip()}" for m in history[-HISTORY_FOR_REWRITE * 2:])
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


def retrieve(query: str, k: int = TOP_K, where_document: dict | None = None, where: dict | None = None) -> list[dict]:
    """The one place that searches the documents. Returns up to k chunks, nearest first, each a dict with
    text, source, system, heading, page_start, page_end, codes and distance (cosine; lower is closer).
    where_document is an optional ChromaDB text filter, for example {"$contains": "4012"};
    where filters on metadata, for example {"system": "CCP"}."""
    emb = ollama.embed(model=EMBED_MODEL, input=query, keep_alive=KEEP_ALIVE)["embeddings"]
    extra = {**({"where_document": where_document} if where_document else {}), **({"where": where} if where else {})}
    res = collection.query(query_embeddings=emb, n_results=k, **extra)
    return [{**meta, "id": chunk_id, "text": doc, "distance": dist}
            for chunk_id, doc, meta, dist in zip(res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0])]


def with_neighbours(hits: list) -> list:
    """Adds the chunk before and the chunk after the best hit when they belong to the same section, in reading
    order, so a procedure that continues in the next chunk is not cut off. Other hits stay as they are."""
    first = hits[0][1]
    prefix, number = first["id"].rsplit("-", 1)
    wanted = [f"{prefix}-{int(number) - 1}", f"{prefix}-{int(number) + 1}"]
    have = {m["id"] for _, m in hits}
    got = collection.get(ids=[i for i in wanted if i not in have], include=["documents", "metadatas"])
    near = [(doc, {**meta, "id": i}) for i, doc, meta in zip(got["ids"], got["documents"], got["metadatas"])
            if (meta["source"], meta["heading"]) == (first["source"], first["heading"])]
    before = [h for h in near if int(h[1]["id"].rsplit("-", 1)[1]) < int(number)]
    after = [h for h in near if int(h[1]["id"].rsplit("-", 1)[1]) > int(number)]
    return before + [hits[0]] + after + hits[1:]


def cited(hits: list, reply: str) -> list:
    """The retrieved sections that the answer names (by section title). If it names none, all of them."""
    text = reply.lower()
    used = [h for h in hits if h[1]["heading"].lower() in text]
    return used or hits


def working(label: str):
    """A one-line progress bubble. The next yield replaces it, so it disappears when the answer starts."""
    return [gr.ChatMessage(content="", metadata={"title": label, "status": "pending"})]


def footer(total: float) -> str:
    return f"\n\n⏱ {total:.1f} s"


def answer(question: str, history, name: str = ""):
    """Generator: yields a one-line progress bubble per step, then the growing answer, then the final answer with sources and time."""
    quick = small_talk(question, name)
    if quick:
        yield quick
        return
    t0 = time.perf_counter()
    history = clean_history(history)

    search_question = question
    if history:
        yield working("Rewriting question…")
        search_question = standalone_question(question, history)

    yield working("Retrieving chunks…")
    candidates = retrieve(search_question)

    if not candidates or candidates[0]["distance"] > MAX_DISTANCE:
        yield NOT_FOUND + footer(time.perf_counter() - t0)
        return
    # keep only chunks close to the best one: a shorter prompt is much faster on CPU
    best = candidates[0]["distance"]
    hits = [(c["text"], c) for c in candidates if c["distance"] <= best + RELATIVE_CUTOFF]
    hits = with_neighbours(hits)
    yield working("Generating answer…")

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
        yield without_sources(reply)  # the first text replaces the progress bubble
    total = time.perf_counter() - t0

    # a pure refusal is shown as the exact standard sentence; a real answer that merely contains the sentence
    # (for example for one part of the question) is kept, it must not be wiped out
    if NOT_FOUND in reply and len(reply.replace(NOT_FOUND, "").strip()) < 40:
        yield NOT_FOUND + footer(total)
        return
    yield without_sources(reply) + format_sources(cited(hits, reply)) + footer(total)


if __name__ == "__main__":
    TITLE = "Automation Assistant"
    CSS = """
    #name-modal { position: fixed; inset: 0; z-index: 1000; background: rgba(0,0,0,.55);
                  display: flex; align-items: center; justify-content: center; }
    .chat-area, .chat-area .bubble-wrap { background: #ECEFEA !important; }
    .gradio-container { --color-accent: #2F855A; }
    /* full-screen layout: sizes follow the browser window, so zooming out shows more of the conversation */
    .gradio-container, .gradio-container .main { width: 96vw !important; max-width: 96vw !important; margin: 0 auto !important; }
    .chat-area { height: calc(100vh - 230px) !important; min-height: 300px; }
    #start-btn { background: #2F855A !important; border-color: #2F855A !important; color: #fff !important; }
    #start-btn:hover { background: #22543D !important; border-color: #22543D !important; }
    #name-card { max-width: 380px; width: 90vw; padding: 24px; border-radius: 16px; gap: 12px;
                 flex: 0 0 auto !important; height: fit-content !important; min-height: 0 !important;
                 background: var(--background-fill-primary); box-shadow: 0 10px 40px rgba(0,0,0,.35); }
    """

    def start_chat(name: str):
        """Pop-up submitted: remember the name, show the welcome message, close the pop-up."""
        name = name.strip() or "there"
        welcome = [{"role": "assistant", "content": f"Hi {name}! {WELCOME}"}]
        return welcome, name, gr.update(visible=False)

    with gr.Blocks(title="Automation Assistant") as demo:
        gr.HTML(
            '<div style="display:flex;flex-direction:column;align-items:center;gap:10px">'
            f'<h1 style="margin:0;font-size:1.6rem;text-align:center">{TITLE}</h1>'
            '</div>'
        )
        user_name = gr.State("")
        avatars = (None, "assets/assistant.svg")
        chat = gr.ChatInterface(answer, chatbot=gr.Chatbot(avatar_images=avatars, show_label=False, elem_classes="chat-area"),
                                additional_inputs=[user_name])
        with gr.Column(elem_id="name-modal") as modal:
            with gr.Column(elem_id="name-card"):
                gr.HTML('<div style="text-align:center"><img src="/gradio_api/file=assets/assistant.svg" '
                        'style="height:64px;display:block;margin:0 auto"><h2 style="margin:8px 0 0">Hi! I\'m the Automation Assistant.</h2>'
                        '<p style="margin:4px 0 0">What\'s your name?</p></div>')
                name_in = gr.Textbox(show_label=False, placeholder="Enter your name", autofocus=True)
                start = gr.Button("Start", variant="primary", elem_id="start-btn")
        for trigger in (start.click, name_in.submit):
            trigger(start_chat, name_in, [chat.chatbot_value, user_name, modal])
    demo.launch(allowed_paths=["assets"], css=CSS)
