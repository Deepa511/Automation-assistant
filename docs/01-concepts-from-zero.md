# 01 Concepts from zero

This page explains the ideas behind the chatbot with everyday comparisons. Read it once and the rest of the documentation will make sense. Terms are also in the [glossary](glossary.md).

## 1. The AI model (a "language model")

A language model is a program trained on an enormous amount of text to do one thing very well: **continue a piece of text sensibly**. Give it "The capital of France is" and it continues "Paris". Chat assistants are language models arranged so that the "continuation" is an answer to your question.

Think of a very well-read assistant who has read a huge library but has **never seen your company's manuals** and has no memory of past conversations.

The model in this project is called `qwen2.5:7b`. The "7b" means roughly 7 billion adjustable numbers inside it (its "size"). Bigger usually means more capable, but also slower and hungrier for memory.

## 2. Why models make things up

A language model predicts likely text. It has no built-in sense of "I don't know". If you ask about something it never saw, it will often produce a fluent, confident, **wrong** answer. This is called **hallucination**.

For manuals that is dangerous: a wrong torque value or a missing safety step looks just as convincing as a correct one.

## 3. RAG: the open-book exam

**RAG** stands for *retrieval-augmented generation*:

- **Retrieval**: look up relevant passages from your documents.
- **Augmented generation**: let the model write its answer *with those passages in front of it*.

Compare a closed-book exam (the model answers from memory and may bluff) with an open-book exam (the student is handed the right pages and must answer from them). RAG turns the first into the second.

Two things make it work well here:
1. The lookup must find the *right* passages.
2. The model must be told to **stay inside** those passages and to admit when the answer is missing.

Both are discussed in [Design decisions](04-design-decisions.md).

## 4. How the lookup finds the right passages: embeddings

Searching for exact words is fragile. "Swap the camera" and "replace the camera" mean the same thing but share few words. We want to search by **meaning**.

An **embedding** converts a piece of text into a list of numbers (for our embedding model, 768 of them) that acts like **coordinates on a map of meaning**. Texts with similar meaning land close together; unrelated texts land far apart. Think of a library where books are shelved by *what they are about* instead of alphabetically.

A separate small model, `nomic-embed-text`, does this conversion. It does not write answers. It only turns text into coordinates.

## 5. Where the coordinates are kept: a vector database

A list of numbers is called a **vector**, so a **vector database** stores vectors and quickly finds the ones nearest to a given point. We use **ChromaDB**. It is just a folder on disk (`chroma_db/`), with no server to run.

To search: convert your question into coordinates, then ask the database for the three nearest passages.

**Distance.** "Nearest" is measured as a number (here *cosine distance*): 0 means identical meaning, bigger means less related. In our tests, questions that the manuals can answer had a best-match distance of about 0.23 to 0.41, while an off-topic question was around 0.6. The chatbot uses these numbers in two places, described in [Design decisions](04-design-decisions.md#when-is-a-match-close-enough).

## 6. Chunks: cutting manuals into pieces

The manuals total 109 pages. We cannot hand all of that to the model for every question (it would be far too slow and exceed what it can read at once). So each manual is cut into **chunks**, small pieces that are each searched separately, and only the best few are used.

How you cut matters a lot. Cut in the wrong place and a procedure gets split in half, so the model sees only half of it. Our chunks follow the manuals' own **sections** (for example "7.5 Replacing the camera"), which keeps procedures together. See [Section-aware chunking](04-design-decisions.md#section-aware-chunking).

## 7. Prompt, tokens and the context window

The **prompt** is everything we hand the model for one answer: the rules ("use only this text"), the last few chat messages, the retrieved passages, and your question.

Models do not read letters or words but **tokens**, small pieces of text. As a rule of thumb, one token is about three quarters of a word, so 100 words is around 130 tokens. Speed is measured in tokens per second.

The **context window** is how much text the model can hold in view at once, like the size of its desk. In this setup it is 4,096 tokens. Everything (rules, history, passages, question *and* the answer being written) must fit on that desk. That is one reason we send only the top 3 passages.

## 8. Reading versus writing

When you ask a question the model does two different jobs:

1. **Read the prompt.** It processes all the text it was given. It cannot start answering before this is finished.
2. **Write the answer.** It produces the answer one token at a time.

On a normal graphics card both are fast. On this laptop they are not: we measured roughly **36 tokens per second for reading** and **about 5 tokens per second for writing**. That is why a 1,000-token prompt can take around half a minute before the first word of the answer appears.

## 9. Local versus cloud, CPU versus GPU

- **Cloud**: the model runs on a company's servers (like ChatGPT). Fast and capable, but your questions and passages are sent to them and you pay per use.
- **Local**: the model runs on your own computer. Free and private, but limited by your hardware.
- **CPU versus GPU**: a **GPU** (graphics card) can do the huge amount of arithmetic a model needs far faster than the **CPU** (the computer's main processor). The development laptop has no usable GPU, so everything runs on the CPU, which is slow. This single fact explains most of the waiting.

## 10. Temperature and streaming

- **Temperature** controls how adventurous the model is. High values give creative variety, low values give steady, repeatable answers. We use a low value (0.1 for answers, 0 for question rewriting) because we want facts, not creativity.
- **Streaming** means showing the answer piece by piece as it is produced, instead of waiting for the whole thing. It does **not** make the answer finish sooner; it only lets you start reading earlier.

## What to remember

- The model is a well-read assistant that has not seen your manuals and can bluff.
- RAG = look up the right pages first, then answer from them only.
- Search works by meaning, using embeddings stored in a vector database.
- Manuals are cut into chunks; where you cut decides whether answers are complete.
- On this laptop the waiting is dominated by the CPU reading and writing text.

Next: [02 Architecture](02-architecture.md).
