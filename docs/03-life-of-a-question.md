# 03 Life of a question

Follow one conversation from the first keystroke to the finished answer, and see exactly what the progress display means.

The example:

1. **"How do I replace the camera?"** (first question)
2. **"What must be done afterwards?"** (follow-up)

## What you see on screen

The chat shows a progress bubble while the system works, then the answer, then a time line. With the default display (`TRACE_STYLE=bubble`) the follow-up looks like this when finished:

```
Done in 33.7 s            (collapsible bubble)
  ✓ Rewriting question (6.9 s)
     → "What must be done after replacing the camera?"
  ✓ Retrieving chunks (0.1 s)
     → 7.5 Replacing the camera (pages 13-14)
  ✓ Generating answer (26.7 s)

After mounting the new camera and setting the IP address, the following steps must be done:
1. Run the hand-eye calibration and teach the reference position.
2. Run 30 reference parts and check the match score.
[7.5 Replacing the camera, pages 13-14]

Sources: FC-200 Operating and Service Manual - 7.5 Replacing the camera (pages 13-14)

⏱ 33.7 s
```

(Values are a measured example from the development laptop.)

## Step by step

### Step 0: your message arrives
A stopwatch starts. The page also sends the earlier messages of this chat. Before anything else, the app cleans that history: it removes the old progress bubbles and the `⏱` lines so the AI only sees real conversation.

### Step 1: rewrite the question (only if there is earlier chat)
Display: **Rewriting question**.

"What must be done afterwards?" cannot be searched: *afterwards* after what? The AI model is asked to rewrite it using the last four exchanges of the chat, giving "What must be done after replacing the camera?". The first question of a chat skips this step.

Cost: one extra AI call, **about 7 to 11 seconds** in our measurements. See [Rewriting follow-up questions](04-design-decisions.md#rewriting-follow-up-questions) for why, and for its weakness.

### Step 2: turn the question into coordinates
Part of **Retrieving chunks**. The embedding model converts the (rewritten) question into its 768 numbers. Very fast (a tenth of a second or less).

### Step 3: find the nearest chunks
Also part of **Retrieving chunks**. ChromaDB compares those coordinates with all 273 stored chunks and returns the three nearest, each with a distance. Typically about 0.1 to 0.9 seconds in total for steps 2 and 3.

Two checks follow:
- **Close enough?** If even the best chunk is farther than 0.6, the chatbot answers "I couldn't find that in the document." immediately. The display shows "✗ No close match in the documents".
- **Keep the close ones.** Chunks that are more than 0.1 farther away than the best chunk are dropped. This shortens the prompt, which matters a lot for speed (next step).

The remaining chunks are listed under the step, for example "→ 7.5 Replacing the camera (pages 13-14)". This is what the search found, not yet what the AI will use.

### Step 4: build the prompt
Not shown on screen. The app assembles one long piece of text:

1. **The rules**: use only the context below; if the answer is not there, reply exactly "I couldn't find that in the document."; give procedures in full and in order; cite the section and page.
2. **The last two exchanges** of the chat (for context only).
3. **The chunks**, each labelled with its source.
4. **Your question** (the original wording, not the rewrite).

### Step 5: the model reads, then writes
Display: **Generating answer…** This label covers two different phases:

| Phase | What happens | Visible? | Measured speed |
|---|---|---|---|
| **Reading** | The model processes the whole prompt (often 500 to 1,500 tokens; a token is a small piece of text, about three quarters of a word) | No: the screen shows "Generating answer…" and nothing else | About 36 tokens per second, so around 15 to 40 seconds |
| **Writing** | The model produces the answer token by token; you see it appear | Yes | About 5 tokens per second |

This explains the quiet gap between the "Generating answer…" label and the first word. It is the model reading. A more precise label is planned (see [06 Limits and future](06-limits-and-future.md)).

The answer is capped at 400 tokens (roughly 300 words) so a runaway answer cannot take minutes.

### Step 6: finish
When the model stops, the app:
- replaces the answer with just "I couldn't find that in the document." if the model produced that sentence,
- otherwise appends a **Sources** line listing the section and pages of the chunks it was given,
- adds the **⏱ total time**, and closes the progress bubble ("Done in 33.7 s").

## Where the time goes

Measured examples on the development laptop (CPU only):

| Question | Rewrite | Search | Reading + writing | Total |
|---|---|---|---|---|
| First question, camera replacement | none | 0.1-0.2 s | about 20 s | about 20 s |
| Follow-up, "What must be done afterwards?" | 7 s | 0.1 s | about 27 s | about 34 s |
| A slow run (one of the user's runs, when free memory was very low) | 6.5 s | 0.0 s | 51.8 s | 58.4 s |

Almost all of the time is the AI model working on the CPU. Searching is negligible. When free memory is low, the computer slows down further, so closing other programs helps.

## The two display styles

| Setting | What you see while waiting |
|---|---|
| `TRACE_STYLE=bubble` (default) | A collapsible bubble listing each step as it happens. It stays above the answer so you can reopen it later |
| `TRACE_STYLE=status` | A plain status text that is replaced by the answer once the first word arrives. Per-step times appear in the line below the answer |

Both exist because we wanted to compare them in use. See [Design decisions](04-design-decisions.md#progress-trace-and-timing).

Next: [04 Design decisions](04-design-decisions.md), the reasons behind each choice.
