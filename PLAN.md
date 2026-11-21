# Plan: Phase 1 demo (chat assistant with follow-up memory)

Goal: a basic local chat assistant that retrieves from the knowledge source (fictional manuals) and answers follow-up questions using conversation context.

Long-term idea: RAG as a digital twin knowledge layer for an ACP cell (PLC, safety manuals, robot and simulation data, process, customer input). One knowledge base, many front ends: chat assistant, HMI assistant, engineering search, alarm diagnostics, commissioning assistant, auto documentation, change-impact analysis. This plan covers only the first front end.

Rules stay as in CLAUDE.md (free and local only, one app.py plus small scripts, fictional data only).

## Tasks (do in order, commit after each)

1. **Follow-up memory in app.py** (DONE)
   - `answer(question, history)` currently ignores `history`.
   - Before retrieval, if history is not empty, call the chat model to rewrite the question into a standalone question using the last 4 turns. Use the rewritten question for embedding and search.
   - Keep the original question for the final answer prompt, and include the last 2 turns in the messages for conversational context.
   - Keep the NOT_FOUND refusal behavior.

2. **Follow-up test cases** (TRIED, THEN REVERTED: not kept in the repo; can be restored with `git revert 8135a67`)
   - Add a section "Follow-up questions" to tests/questions.md with 3 to 4 multi-turn sequences, for example:
     - "How do I replace the camera?" then "What must be done afterwards?" then "Which document is that from?"
     - "What does vision result code 12 mean?" then "What should the robot do in that case?"
   - Add a short out-of-scope follow-up (should still refuse).

3. **Hybrid search** (TRIED, THEN REVERTED: it fixed exact-term lookups such as "event 4012", but the previous answers were preferred; can be restored with `git revert 7f533a1`)
   - Add BM25 (rank_bm25) over the chunk texts and merge with the vector results (reciprocal rank fusion).
   - Goal: exact terms such as "event 4012" and "result code 12" are found reliably.
   - Add rank_bm25 to requirements.txt.

4. **Docs cleanup** (DONE)
   - Fill in README Setup and Usage (install Ollama, pull qwen2.5:7b and nomic-embed-text, pip install, place PDFs in data/raw/, run scripts/ingest.py, run app.py).
   - Fix structure mismatch: README lists data/docs/ but the code reads data/raw/.
   - Make scripts/download_data.py either do something or state clearly that the PDFs are supplied locally.

## Also done (not in the original plan)
- Section-aware chunking (sections can span pages), speed-ups (streaming, shorter prompt), and a live progress trace with response time (`TRACE_STYLE=bubble|status`).

## Demo script
1. "How do I replace the camera?"
2. "What must be done afterwards?"
3. "Which document is that from?"
4. "What is the capital of France?" (must refuse)
