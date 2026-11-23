# Project: Automation Assistant

Prototype RAG chatbot for an assembly/fastening process (torque tightening).
Public GitHub repo.

## Rules
- Use only open data and fictional documents. No company data, names or part numbers.
- Free and local only: Ollama (qwen2.5:7b, nomic-embed-text), ChromaDB, Gradio, pandas, Jinja2, Pydantic.
- Never commit data/raw/, .venv/, chroma_db/ or .env.
- Raw data is downloaded by scripts/download_data.py, not committed.
- Every data source must be listed in DATA_SOURCES.md with license and credit.
- Keep code simple: one app.py plus small scripts. No extra frameworks.
- Commit after each working milestone with a clear message.

## Structure
app.py, scripts/, data/docs/, data/templates/, tests/questions.md