# 05 Running and troubleshooting

Commands are for Windows PowerShell, run from the project folder.

## Set up (once)

1. Install [Ollama](https://ollama.com), then download the two models:
   ```powershell
   ollama pull qwen2.5:7b
   ollama pull nomic-embed-text
   ```
2. Create the project's Python environment and install the dependencies (Python 3.12):
   ```powershell
   py -3.12 -m venv .venv
   .venv\Scripts\python -m pip install -r requirements.txt
   ```
3. Put the PDF manuals in `data/raw/`.
4. Build the searchable library:
   ```powershell
   .venv\Scripts\python scripts\ingest.py
   ```
   This rebuilds `chroma_db/` from scratch. Run it again only when the PDFs or `scripts/ingest.py` change. `scripts\ingest.py --dry-run` lists the sections and chunks without calling Ollama.

## Run

```powershell
.venv\Scripts\python app.py
```

Open http://127.0.0.1:7860 in a browser. Stop the app with `Ctrl+C`. After changing `app.py`, stop and start it again, then refresh the page.

## Settings

Two settings are read from environment variables when the app starts:

| Setting | Values | Default | Example |
|---|---|---|---|
| `TRACE_STYLE` | `bubble` or `status` | `bubble` | `$env:TRACE_STYLE="status"` |
| `CHAT_MODEL` | any model name in `ollama list` | `qwen2.5:7b` | `$env:CHAT_MODEL="qwen2.5:3b"` |

Set the variable, then start the app in the **same PowerShell window**. A setting made in another window has no effect.

Optional privacy settings (see the small print in [04](04-design-decisions.md#local-and-free-only)): `$env:ANONYMIZED_TELEMETRY="False"` and `$env:GRADIO_ANALYTICS_ENABLED="False"` switch off the anonymous usage statistics that ChromaDB and Gradio may send by default.

The other tuning values are constants at the top of `app.py` (and `scripts/ingest.py` for chunking):

| Constant | Now | What it controls | Effect of raising it |
|---|---|---|---|
| `TOP_K` | 3 | Chunks fetched per question | More complete answers, slower reading |
| `MAX_DISTANCE` | 0.6 | Refusal gate (see [04](04-design-decisions.md#when-is-a-match-close-enough)) | Fewer refusals, more risk of weak answers |
| `RELATIVE_CUTOFF` | 0.1 | How much farther than the best chunk another chunk may be and still be kept | More chunks in the prompt |
| `NUM_PREDICT` | 400 | Maximum answer length in tokens | Longer answers allowed, longer waits |
| `HISTORY_FOR_REWRITE` | 4 | Exchanges used to rewrite a follow-up | Better understanding of references, slower |
| `HISTORY_FOR_ANSWER` | 2 | Exchanges given to the answering call | More context, longer prompt |
| `KEEP_ALIVE` | 30 minutes | How long models stay in memory | Avoids reloads, holds about 5 GB |
| `MAX_CHARS` (ingest) | 1,500 | Largest chunk size | Fewer, bigger chunks (**re-run ingest after changing**) |

## Trying it out

`tests/questions.md` lists 12 questions the manuals can answer and 4 that must be refused. Try them by hand and check each answer against the cited pages.

## Troubleshooting

**Answers take a minute or more.**
The models run on the CPU, which is slow. Close other programs, especially browsers with many tabs (low free memory slowed one run from about 20 s to 58 s), and make sure only one copy of the app is running. See [03 Life of a question](03-life-of-a-question.md#where-the-time-goes).

**There is a long quiet gap after "Generating answer…".**
Normal. The model is reading the prompt before writing. See [03](03-life-of-a-question.md#step-5-the-model-reads-then-writes).

**"I couldn't find that in the document" for a question that should be answerable.**
- Rephrase using words from the manual; exact codes and names help.
- Exact codes (for example an event number) are the weak spot of meaning-based search. See [06](06-limits-and-future.md).
- Check the trace: if the retrieved sections look unrelated, the search missed.

**The answer is wrong or incomplete.**
Check the cited section and pages in the PDF. Tables are the most likely cause (see [06](06-limits-and-future.md)). An answer cut off in mid-sentence reached the 400-token limit.

**The page looks the same after I changed a setting or the code.**
The old copy of the app is probably still running. Stop it (`Ctrl+C`), check nothing else uses port 7860, start it again, then refresh the browser (`Ctrl+F5`). The page title shows the trace style in use ("trace style: bubble" or "status").

**A new copy starts on another port, or the old page keeps showing.**
Gradio quietly picks another port if 7860 is busy, while your browser tab stays on the old one. Stop the old copy first.

**Errors mentioning a connection or `localhost:11434`.**
Ollama is not running. Start the Ollama application, then check with `ollama list`.

**An error at start-up about a missing collection.**
The library has not been built. Run `.venv\Scripts\python scripts\ingest.py` first.

**Ingest finds no PDFs.**
Put them in `data/raw/`.

## What not to commit to git

`data/raw/`, `chroma_db/`, `.venv/` and `.env` are in `.gitignore` and must stay out of the repository. Every data source must be listed in `DATA_SOURCES.md` with its license and credit.
