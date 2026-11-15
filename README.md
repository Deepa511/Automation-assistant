# automation-rag-assistant

## Overview
Prototype RAG chatbot for an assembly/fastening process (torque tightening). Runs fully locally and for free.

## Features (planned)
- Question answering over fictional process documents
- Local retrieval with citations to source documents

## Tech stack
- Ollama: qwen2.5:7b (chat), nomic-embed-text (embeddings)
- ChromaDB, Gradio, pandas, Jinja2, Pydantic

## Setup
TBD

## Usage
TBD

## Project structure
```
app.py              # Gradio app
scripts/            # small helper scripts (e.g. download_data.py)
data/docs/          # fictional documents
data/templates/     # Jinja2 templates
tests/questions.md  # test questions
```

## Data and licenses
See [DATA_SOURCES.md](DATA_SOURCES.md). Raw data is downloaded by `scripts/download_data.py` and is not committed.

## Disclaimer
Only open data and fictional documents are used. No company data, names or part numbers.

## License
TBD
