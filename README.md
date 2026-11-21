# automation-rag-assistant

## Overview
Prototype RAG chatbot for an assembly/fastening process (torque tightening). It answers questions only from the PDF manuals you give it, runs fully locally, and is free to use.

## Features
- Answers only from the documents; replies "I couldn't find that in the document." otherwise
- Section-aware chunking: a section can span several pages, so procedures are not cut off at a page break
- Citations with document, section and page range
- Follow-up questions ("What must be done afterwards?") using conversation context
- Live progress steps while it works, and the total response time under every answer

## Tech stack
- Ollama: qwen2.5:7b (chat), nomic-embed-text (embeddings)
- ChromaDB (vector store), Gradio (chat UI), pypdf (PDF text)

## Setup
Windows PowerShell, from the project folder.

1. Install [Ollama](https://ollama.com), then pull the two models:
   ```powershell
   ollama pull qwen2.5:7b
   ollama pull nomic-embed-text
   ```
2. Create the virtual environment and install the dependencies (Python 3.12):
   ```powershell
   py -3.12 -m venv .venv
   .venv\Scripts\python -m pip install -r requirements.txt
   ```
3. Put your PDF manuals in `data/raw/` (not committed).
4. Build the index (rebuilds `chroma_db/`; only needed when the PDFs or `scripts/ingest.py` change):
   ```powershell
   .venv\Scripts\python scripts\ingest.py
   ```

## Usage
```powershell
.venv\Scripts\python app.py
```
Open http://127.0.0.1:7860. Restart the app after changing `app.py`.

Optional settings (environment variables, read at start-up):
- `TRACE_STYLE`: `bubble` (default, collapsible trace bubble) or `status` (status line that disappears), for example `$env:TRACE_STYLE="status"`.
- `CHAT_MODEL`: another Ollama model, default `qwen2.5:7b`.

Other:
- `.venv\Scripts\python scripts\ingest.py --dry-run` lists the sections and chunks without calling Ollama.
- `tests/questions.md` has questions to try by hand, including ones that must be refused.

## Project structure
```
app.py              # Gradio chat app (retrieval, answering, progress trace)
scripts/ingest.py   # PDFs in data/raw/ -> chunks -> embeddings -> chroma_db/
scripts/download_data.py  # placeholder: the PDFs are supplied locally, nothing is downloaded
data/raw/           # your input PDFs (not committed)
data/docs/          # reserved, currently unused
data/templates/     # reserved, currently unused
tests/questions.md  # test questions
chroma_db/          # generated index (not committed)
```

## Data and licenses
See [DATA_SOURCES.md](DATA_SOURCES.md). Raw data in `data/raw/` and the generated `chroma_db/` are not committed.

## Disclaimer
Only open data and fictional documents are used. No company data, names or part numbers.

## License
TBD
