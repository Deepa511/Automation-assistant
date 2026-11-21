# Glossary

Plain-words definitions, in alphabetical order. "Explained in" points to the page that covers the idea in more depth.

| Term | Plain meaning | Explained in |
|---|---|---|
| **Answering model** | The AI model that writes the answers (here `qwen2.5:7b`) | [01](01-concepts-from-zero.md#1-the-ai-model-a-language-model) |
| **BM25 / keyword search** | A classic search that matches the actual words in your question against the text. Good at exact codes, weak at paraphrases. Built once as "hybrid search", then reverted | [04](04-design-decisions.md#tried-and-reversed) |
| **Chunk** | One small piece of a manual that is searched on its own (273 in this project) | [01](01-concepts-from-zero.md#6-chunks-cutting-manuals-into-pieces) |
| **Chunking** | Cutting the manuals into chunks. Where you cut decides whether a procedure stays whole | [04](04-design-decisions.md#section-aware-chunking) |
| **ChromaDB** | The small database that stores chunks and their coordinates and finds the nearest ones | [02](02-architecture.md#the-components) |
| **Context window** | How much text the model can hold in view at once (4,096 tokens here). Rules, history, passages, question and the answer must all fit | [01](01-concepts-from-zero.md#7-prompt-tokens-and-the-context-window) |
| **Cosine distance** | The number measuring how far apart two meanings are: 0 is the same, larger is less related | [01](01-concepts-from-zero.md#5-where-the-coordinates-are-kept-a-vector-database) |
| **CPU** | The computer's main processor. Here it runs the AI models, slowly | [01](01-concepts-from-zero.md#9-local-versus-cloud-cpu-versus-gpu) |
| **Distance gate** | The rule that refuses a question when even the best chunk is farther than 0.6 | [04](04-design-decisions.md#when-is-a-match-close-enough) |
| **Embedding** | Text converted into a list of numbers that acts as coordinates on a "map of meaning" | [01](01-concepts-from-zero.md#4-how-the-lookup-finds-the-right-passages-embeddings) |
| **Embedding model** | The small AI model that does that conversion (`nomic-embed-text`). It never writes answers | [02](02-architecture.md#the-components) |
| **Follow-up question** | A question that depends on the previous ones, like "What must be done afterwards?" | [04](04-design-decisions.md#rewriting-follow-up-questions) |
| **GPU** | A graphics card. Much faster than a CPU for running AI models. Not available on the development laptop | [01](01-concepts-from-zero.md#9-local-versus-cloud-cpu-versus-gpu) |
| **Gradio** | The Python toolkit that provides the chat web page | [04](04-design-decisions.md#gradio-for-the-screen) |
| **Hallucination** | When a model produces a confident but wrong or invented answer | [01](01-concepts-from-zero.md#2-why-models-make-things-up) |
| **History** | The earlier messages of the current chat | [04](04-design-decisions.md#how-much-chat-history-is-used) |
| **Hybrid search** | Combining meaning-based search with keyword search | [06](06-limits-and-future.md#quality) |
| **Ingest** | The offline job that prepares the library from the PDFs (`scripts/ingest.py`) | [02](02-architecture.md#job-1-ingest-prepare-the-library) |
| **Keep-alive** | How long Ollama keeps a model in memory after use (30 minutes here) | [04](04-design-decisions.md#streaming-answer-length-limit-and-keeping-the-model-loaded) |
| **Language model (LLM)** | A program trained on lots of text to continue text sensibly. The basis of chat assistants | [01](01-concepts-from-zero.md#1-the-ai-model-a-language-model) |
| **Local** | Running on your own computer rather than a company's servers | [01](01-concepts-from-zero.md#9-local-versus-cloud-cpu-versus-gpu) |
| **Ollama** | The program that downloads and runs the AI models locally | [04](04-design-decisions.md#ollama-to-run-the-models) |
| **Prompt** | Everything handed to the model for one answer: rules, recent chat, passages, question | [01](01-concepts-from-zero.md#7-prompt-tokens-and-the-context-window) |
| **qwen2.5:7b** | The answering model. "7b" is about 7 billion internal numbers (its size) | [04](04-design-decisions.md#the-answering-model-qwen257b) |
| **RAG** | Retrieval-augmented generation: look up the relevant passages first, then let the model answer from them. The "open-book exam" approach | [01](01-concepts-from-zero.md#3-rag-the-open-book-exam) |
| **Reading and writing (a model's two jobs)** | Reading processes the whole prompt; writing produces the answer token by token. Reading about 36 tokens/s, writing about 5 tokens/s on the development laptop | [01](01-concepts-from-zero.md#8-reading-versus-writing) |
| **Refusal** | The fixed reply "I couldn't find that in the document." | [04](04-design-decisions.md#the-answering-rules-and-the-refusal-sentence) |
| **Relative cutoff** | Dropping chunks more than 0.1 farther away than the best chunk | [04](04-design-decisions.md#when-is-a-match-close-enough) |
| **Retrieval** | Looking up the relevant chunks | [01](01-concepts-from-zero.md#3-rag-the-open-book-exam) |
| **Rewrite (of a question)** | Turning a follow-up into a question that stands on its own, before searching | [04](04-design-decisions.md#rewriting-follow-up-questions) |
| **Section-aware chunking** | Cutting along the manuals' numbered headings so a section can span pages | [04](04-design-decisions.md#section-aware-chunking) |
| **Streaming** | Showing the answer as it is produced, instead of all at once at the end | [01](01-concepts-from-zero.md#10-temperature-and-streaming) |
| **Temperature** | How adventurous the model is. Low (as here) means steady, factual answers | [01](01-concepts-from-zero.md#10-temperature-and-streaming) |
| **Token** | The small piece of text a model reads and writes. About three quarters of a word | [01](01-concepts-from-zero.md#7-prompt-tokens-and-the-context-window) |
| **Trace** | The progress display that shows each step while the system works | [03](03-life-of-a-question.md#what-you-see-on-screen) |
| **Vector / vector database** | A list of numbers (coordinates). A vector database stores them and finds the nearest ones | [01](01-concepts-from-zero.md#5-where-the-coordinates-are-kept-a-vector-database) |
