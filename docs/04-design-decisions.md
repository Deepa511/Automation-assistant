# 04 Design decisions

Every significant choice, with the reasoning, the price paid, and what else could have been done. Each entry has the same four parts:

- **Decision**: what we chose
- **Why**: the reason
- **Trade-off**: what it costs us
- **Alternatives**: what else we could have chosen

A note on honesty: where a choice was made by a project rule or by convenience rather than by comparing options, this page says so. In particular, **no side-by-side comparison of AI models was ever run**.

Contents: [Local and free only](#local-and-free-only) · [Ollama](#ollama-to-run-the-models) · [The answering model](#the-answering-model-qwen257b) · [The embedding model](#the-embedding-model-nomic-embed-text) · [ChromaDB](#chromadb-for-search-storage) · [Gradio](#gradio-for-the-screen) · [Section-aware chunking](#section-aware-chunking) · [Cleaning the PDF text](#cleaning-the-pdf-text) · [How many chunks to use](#how-many-chunks-to-use) · [When is a match close enough?](#when-is-a-match-close-enough) · [The answering rules](#the-answering-rules-and-the-refusal-sentence) · [Rewriting follow-up questions](#rewriting-follow-up-questions) · [How much chat history](#how-much-chat-history-is-used) · [Streaming, answer limit, keep-alive](#streaming-answer-length-limit-and-keeping-the-model-loaded) · [Progress trace and timing](#progress-trace-and-timing) · [Tried and reversed](#tried-and-reversed)

---

## Local and free only

- **Decision:** everything runs on the user's own laptop with free software. No paid or online AI service.
- **Why:** it is a rule of the project (see `CLAUDE.md`). The manuals in a real setting would be confidential, so keeping all text on the machine avoids sending it to a third party. It also keeps the prototype free and usable offline.
- **Trade-off:** speed and quality. A laptop without a graphics card writes at about 5 tokens per second (a token is a small piece of text, about three quarters of a word), and a small local model is less capable than the largest online ones.
- **Alternatives:** an online model API (fast and strong, but costs money per use and sends text to the provider); a local model on a machine with a good graphics card (fast, but not available here). Switching to an online model would change two functions in `app.py`, but would break the "free and local" rule.
- **Small print:** "local" means the AI models and the documents stay on the machine. It does **not** mean "100% safe" or "never touches the internet":
  - Installing software and downloading models needs the internet.
  - Some libraries used here (ChromaDB and Gradio) may send anonymous usage statistics by default. They do not send the documents. This was **not checked on this machine**. They can be switched off with the environment variables `ANONYMIZED_TELEMETRY=False` (ChromaDB) and `GRADIO_ANALYTICS_ENABLED=False` (Gradio).
  - Ollama can also offer optional cloud-hosted models. This project uses only local ones.
  - The manuals' text sits unencrypted on disk in `data/raw/` and `chroma_db/`. Do not use the app's "share" option, which would create a public link.
  - Before using real company documents, check your organisation's policy: this prototype was built and tested only with fictional manuals.

## Ollama to run the models

- **Decision:** use Ollama to download and run the AI models.
- **Why:** it installs with one program and one command per model (`ollama pull ...`), runs both the answering model and the embedding model, and offers a simple way for Python code to call them. It is free and local, so it fits the rules.
- **Trade-off:** it is built for convenience, not maximum speed. On this laptop both models ran entirely on the CPU (`ollama ps` showed "100% CPU"), because the integrated graphics are too small to help.
- **Alternatives:** other local runners exist (for example llama.cpp directly, or LM Studio). **Not tested.**

## The answering model: qwen2.5:7b

- **Decision:** `qwen2.5:7b` writes the answers and rewrites follow-up questions.
- **Why:**
  - It is the model named in the project rules from the start, so it was a given rather than a result of testing.
  - At about 4.7 GB it fits comfortably in the laptop's 15.7 GB of memory next to everything else.
  - In our tests it followed the "use only this text" rule well and wrote complete step-by-step procedures (for example all seven camera-replacement steps).
- **Trade-off:**
  - Speed: about 5 tokens per second for writing on this CPU (measured).
  - It sometimes misreads tables: asked "Who does that?" about nutrunner calibration, it named the wrong team although the right table was in front of it (measured, with hybrid search enabled; see [Tried and reversed](#tried-and-reversed)).
  - It does not always obey "return the question unchanged" in the rewrite step.
- **Alternatives (not tested):**
  - Smaller models such as `qwen2.5:3b` (about 2 GB) would be roughly twice as fast but weaker. We downloaded it once to test as a rewriting helper, then dropped the idea at the owner's request and kept a single model.
  - Models of similar size from other families (for example `qwen3:8b`, `llama3.1:8b`, `granite3.3:8b`) might be better or worse for this task. This is a guess from general knowledge, not a result.
  - Bigger models (12B and up) would be noticeably slower on this laptop and some would not fit in memory.
  - If better answers matter more than speed, the cheapest experiment is to set the `CHAT_MODEL` environment variable to another model and rerun the questions in `tests/questions.md`.

## The embedding model: nomic-embed-text

- **Decision:** `nomic-embed-text` converts text to coordinates for both the manuals and the questions.
- **Why:** small (about 0.3 GB), fast, runs under Ollama, and is a commonly used general-purpose choice for this job.
- **Trade-off:** one general model for everything. It can miss exact codes: in an early test, vector search alone (search by meaning, using the coordinates) did not return the chunk containing "event 4012" for the question "What does event 4012 mean?" (measured). Meaning-based search is weaker on exact numbers and codes.
- **Alternatives:** other embedding models (not tested); adding a keyword search next to it (tried, see [Tried and reversed](#tried-and-reversed)).
- **Must match:** the same embedding model must be used for ingest and for questions.

## ChromaDB for search storage

- **Decision:** ChromaDB stores the chunks and their coordinates and finds the nearest ones.
- **Why:** it runs inside the Python program and saves to a plain folder, so there is no database server to install or keep running. Perfect for a prototype with a few hundred chunks. Closeness is measured as *cosine distance* (a standard way to compare two meanings, set when the library is created).
- **Trade-off:** not meant for many users or millions of chunks.
- **Alternatives:** dedicated vector servers (for example Qdrant) or a search engine such as OpenSearch. They add a server to run and only pay off with much more data or many users.

## Gradio for the screen

- **Decision:** Gradio provides the chat page.
- **Why:** a working chat screen in one line of Python, with built-in support for streaming text and for showing a collapsible "thinking" bubble. The progress bubble was built and tested with Gradio 6, so `requirements.txt` asks for `gradio>=6`.
- **Trade-off:** a functional but generic look; the app has little control over the page.
- **Alternatives:** a custom web front end (much more work), or a command-line interface.

## Section-aware chunking

- **Decision:** cut each manual along its numbered section headings (such as "7.5 Replacing the camera"), letting a section run across page breaks. If a section is longer than 1,500 characters, split it on line boundaries and repeat the section heading on each piece.
- **Why:** the first version cut each page separately into 800-character pieces. A question about replacing the camera got only steps 1 to 5, because steps 6 and 7 were on the next page and never retrieved. Cutting along sections keeps a whole procedure together.
- **Result (measured):** 273 chunks from 109 pages. Typical chunk is about 430 characters (the median), the largest about 1,500. The camera procedure is now one chunk covering pages 13-14.
- **Trade-off:**
  - Relies on the manuals having numbered headings. Documents without them end up as one block per document ("Front matter").
  - A long **table** is cut into line-by-line pieces, and the header row is not repeated, so the model can misread which row belongs to which column.
- **Alternatives:** fixed-size cuts with overlap (simple, but it splits procedures); cutting by sentences or paragraphs; keeping each table together (not done yet, see [06 Limits and future](06-limits-and-future.md)).

## Cleaning the PDF text

- **Decision:** before cutting, remove (a) the page header and footer lines that repeat on most pages and (b) table-of-contents pages.
- **Why:** each page started with the same four header lines. Left in, they would sit in the middle of a section that spans pages, and clutter every chunk. Table-of-contents pages list every heading, so they would create fake, nearly empty chunks that compete with the real ones in search (they roughly doubled the chunk count: 576 before, 273 after).
- **Trade-off:** the detection is built around these manuals' layout (a repeated header, dotted lines in the contents page). A manual laid out differently may need adjusting.

## How many chunks to use

- **Decision:** retrieve the top 3 chunks.
- **Why:** the model's *reading* time grows with the prompt, at about 36 tokens per second here. More chunks means a longer silent wait. Three is a balance between covering the answer and waiting less. The context window (how much text the model can read at once, 4,096 tokens here) is also limited.
- **Trade-off:** a question whose answer is spread over four or more chunks (for example across several manuals) may be answered only partly.
- **Alternatives:** a larger number (slower, more complete); fewer (faster, riskier).

## When is a match close enough?

Two distance rules, both based on the cosine distance (0 = same meaning, higher = less related):

1. **The refusal gate (`MAX_DISTANCE = 0.6`).** If even the best chunk is farther than 0.6, the chatbot refuses straight away, without calling the model.
   - *Measured:* questions the manuals could answer had a best distance of about 0.23 to 0.41. The off-topic question "What is the capital of France?" scored 0.59, **barely under the limit**, so it passed the gate and was refused by the model instead (after about half a minute).
   - So this gate is a weak safety net. Lowering it to around 0.5 would refuse such questions instantly, but we want more test questions before changing it.
2. **The relative cutoff (`RELATIVE_CUTOFF = 0.1`).** Chunks that are more than 0.1 farther away than the best chunk are dropped. This shortens the prompt (faster) and keeps the "Sources" line focused.
   - *Trade-off:* a useful second chunk that happens to be a bit farther away can be dropped.

## The answering rules and the refusal sentence

- **Decision:** the model gets strict rules: answer **only** from the provided passages; if the answer is not there, reply exactly "I couldn't find that in the document."; give procedures in full and in order; cite section and pages; earlier chat messages are context only.
- **Why:** this is what turns a general chatbot into a trustworthy "answers from the document" tool. A fixed refusal sentence lets the app recognise a refusal reliably: if the reply contains that sentence, the app shows only the sentence and no sources.
- **Settings:** temperature 0.1 for answers (steady and factual).
- **Trade-off:**
  - The rules are a request, not a guarantee. A model can still err.
  - The "Sources" line lists the sections the model was *given*, not only the ones it actually used.
  - Answers are capped at 400 tokens, so a very long answer may be cut off.

## Rewriting follow-up questions

- **Decision:** when the chat already has earlier messages, an AI call first rewrites the new question so that it stands on its own. The rewritten version is used for **searching**; the model's final answer still receives your original wording (plus the last two exchanges).
- **Why:** search looks at one question at a time and has no memory. "What must be done afterwards?" contains no words about cameras, so searching it directly returns unrelated chunks. After the rewrite it becomes "What must be done after replacing the camera?", which finds the right section. "Which document is that from?" becomes "Which document describes what must be done after replacing the camera?".
- **How:** the last four exchanges (up to eight messages) are shown to the model, with the sources lists removed, along with an example. Temperature is 0 (no randomness), and the result is capped at 80 tokens.
- **Trade-offs (measured):**
  - **Time:** it adds one extra AI call to every follow-up, about 7 to 11 seconds.
  - **Runs even when not needed:** it triggers whenever the chat is not empty, not only for vague questions. In one case a standalone question ("Summarize the declaration of conformity") came back with an added document number the user never typed, which can steer the search.
  - It can fail to rewrite: an early version left "Which document is that from?" unchanged, which was fixed by a clearer instruction and an example.
- **Alternatives:**
  - Skip the rewrite when the question has no reference words ("it", "that", "afterwards", ...) or is long enough to stand alone. This was **proposed but not implemented**. It would save about 10 seconds on standalone questions.
  - Accept a rewrite only if it keeps the user's words (still costs the time).
  - Send the whole chat to search (poor results, long prompts).

## How much chat history is used

- **Decision:** four exchanges feed the rewrite step; two exchanges go into the final answering prompt.
- **Why:** the rewrite needs enough context to resolve "that" and "afterwards", while the answering prompt must stay short because reading is slow. The answering step gets its facts from the retrieved passages, not from history.
- **Trade-off:** a reference to something more than four exchanges back may not be understood.

## Streaming, answer-length limit and keeping the model loaded

- **Streaming:** the answer is shown word by word as produced. It does **not** make the answer finish sooner (the total time is the same), but you can start reading immediately, and the display is more honest than a blank screen. Considered and not added: a setting to show the whole answer at once; the owner decided against it.
- **Answer limit (`NUM_PREDICT = 400` tokens):** protects against very long or rambling output at about 5 tokens per second. Trade-off: very long answers can be cut off.
- **Keep-alive (30 minutes):** the models stay in memory between questions. Without it, they would unload after 5 minutes and the next question would pay a loading delay. Trade-off: uses about 5 GB of memory while idle.

## Progress trace and timing

- **Decision:** while the system works, show which step is running with the time each took, and show the total time under every answer.
- **Why:** on this laptop a question takes about 20 to 60 seconds. With nothing on screen, a user cannot tell a working system from a frozen one, and cannot tell *which part* is slow. The trace also helps debugging: it shows the rewritten question and which sections were retrieved.
- **Two styles, on purpose:** the owner wanted to compare them in real use.
  - **Bubble (default):** a collapsible "Working..." bubble that lists the steps and stays above the answer.
  - **Status:** a plain status text that disappears when the answer starts, with per-step times in the line under the answer.
  - Switch with the `TRACE_STYLE` setting.
- **Implementation detail that matters:** the trace bubbles and the `⏱` line are stripped from the chat history before it is used again, so they never leak into the AI's prompts.
- **Known imprecision:** the "Generating answer…" label covers both the silent *reading* phase and the visible *writing* phase. A more exact set of labels is planned for a later version (see [06 Limits and future](06-limits-and-future.md)).

## Tried and reversed

These were built and tested, then deliberately removed. They can be restored.

| Experiment | What it did | Result | Status |
|---|---|---|---|
| **Hybrid search** | Added a keyword search (BM25) next to the meaning-based search and merged both result lists | Fixed exact-code questions: "What does event 4012 mean?" now found the right chunk (vector-only did not). But the follow-up "Who does that?" went from a refusal to a wrong answer (the right table was retrieved, the model misread it), and the project owner said they preferred the earlier version's answers | Reverted. Restore with `git revert 7f533a1` |
| **Follow-up test questions** | A test file with multi-turn sequences | Was added with hybrid search and reverted together | Reverted. Restore with `git revert 8135a67` |
| **Smaller model for the rewrite step** | Use `qwen2.5:3b` just for rewriting follow-ups, to save time | Never used: the owner chose to keep one model | Not kept |
| **Show whole answer at once** | A setting to disable streaming | Would not shorten the wait | Declined |

Next: [05 Running and troubleshooting](05-running-and-troubleshooting.md).
