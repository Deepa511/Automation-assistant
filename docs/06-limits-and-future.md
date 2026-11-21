# 06 Limits and future

An honest list of what does not work well today, followed by ideas for what to do next.

## Known limits

| # | Limit | What it looks like | Evidence |
|---|---|---|---|
| 1 | **Slow on a CPU-only laptop** | 20 to 60 seconds per answer | Measured: about 36 tokens/s reading, about 5 tokens/s writing (a token is a small piece of text) |
| 2 | **Tables are misread** | The manuals' tables are split into one line per cell and the header row is not repeated, so the model can pair a row with the wrong column. Example: "Who does that?" (about nutrunner calibration) was answered with the wrong team, although the right table was retrieved | Measured, during the hybrid-search test |
| 3 | **Exact codes can be missed** | With meaning-based search alone, "What does event 4012 mean?" did not retrieve the chunk containing 4012 | Measured. Fixed by hybrid search, which was reverted |
| 4 | **The refusal gate is weak** | "What is the capital of France?" scored 0.59 against a limit of 0.6, so it is refused by the model after a full model call, not instantly. Off-topic questions that sound on-topic ("How much does a new camera cost?") also pass the gate and rely on the model to refuse | Measured |
| 5 | **The rewrite step runs on every follow-up** | Costs 7 to 11 seconds, and can add words the user did not type (it added a document number to a standalone question). It also depends heavily on how the previous answer is worded: when answers became shorter in a test, it picked the wrong topic for "What must be done afterwards?" | Measured |
| 6 | **"Sources" lists what the model was given** | It can list a section the answer did not actually use (identical entries are shown only once, grouped per manual) | Observed |
| 7 | **Answers are capped at 400 tokens** | A very long answer may be cut off | By design |
| 8 | **Limited reasoning across documents** | A question that needs facts from several manuals, or a chain of facts, works only if all the right passages land in the top three | General property of this design. Not systematically tested |
| 9 | **No automated tests** | Quality is checked by hand with `tests/questions.md` | The file lists 16 questions. The follow-up sequences were reverted together with hybrid search |
| 10 | **Built around these manuals' layout** | The cleaning and chunking assume numbered headings, a repeated page header, and dotted contents pages | By design. Other layouts may need adjustments |
| 11 | **Single user, local only** | One person on one laptop, no login | By design |
| 12 | **No model comparison was ever done** | `qwen2.5:7b` was chosen by project rule | **Not tested** |

## Future notes

Ideas, roughly in the order we would consider them. "Effort" is a rough guess (small = under an hour, medium = a few hours, large = a project).

### Version 2

| Idea | Why | Effort | Notes |
|---|---|---|---|
| **Exact step labels** | The "Generating answer…" label hides a long silent phase where the model reads the prompt. Replace it with exact steps: rewriting the question, embedding the question, searching N chunks, *reading* the prompt (with the number of tokens), *writing* the answer (with tokens per second) | Small | **Designed and agreed, then postponed to version 2.** Ollama's final message already provides the exact reading and writing times and token counts, so the numbers can be real, not estimates |

### Quality

| Idea | Why | Effort | Notes |
|---|---|---|---|
| **Hybrid search (keyword + meaning)** | Finds exact terms such as "event 4012" and "result code 12" reliably | Small (about 25 lines) | Already built. Restore with `git revert 7f533a1`. Test it against the answers you prefer before keeping it |
| **Skip the rewrite when not needed** | Saves about 10 seconds and stops the rewrite from adding words. Only rewrite when the question contains reference words ("it", "that", "afterwards") or is very short | Small | Proposed, not built |
| **Table-aware chunking** | Keep each table together and repeat its header row, so the model reads rows correctly | Medium | Would address limit 2 |
| **Tighter refusal gate** | A limit of about 0.5 would refuse clearly off-topic questions instantly | Small | Collect more test questions first so valid ones are not refused |
| **Show only the sources actually cited** | Cleaner and more honest "Sources" line | Small | Parse the `[section, pages]` citations from the answer |
| **Concise-answer instruction** | A "be concise" line in the rules shortens answers and the wait | Small | Trade-off: less detail |

### Speed

| Idea | Why | Effort | Notes |
|---|---|---|---|
| **A machine with a graphics card, or a smaller model** | Writing is limited by the CPU. A graphics card could be many times faster; a 3B model is about twice as fast but weaker | Hardware / small | Try with `CHAT_MODEL`. Untested for this task |
| **Fewer or shorter chunks** | A shorter prompt means a shorter reading phase | Small | Costs completeness |

### Testing and evaluation

| Idea | Why | Effort |
|---|---|---|
| **Automated test script** | Run all test questions through the app, record answers, times and whether refusals happen, so changes (model, chunking, settings) can be compared objectively | Medium |
| **Model comparison** | Try other models of similar size on the same questions and compare accuracy and speed | Medium |
| **Restore the follow-up test sequences** | Multi-turn cases (camera → afterwards → which document, out-of-scope follow-ups) | Small. `git revert 8135a67` |

### Bigger ideas

The long-term idea for this project is to treat this index as a **knowledge layer for an automation cell**: one knowledge base with several front ends on top (chat assistant, an operator-panel assistant, engineering search, alarm diagnostics, commissioning help, automatic documentation, change-impact analysis). The chat assistant described here is the first of those.

| Idea | Why | Effort |
|---|---|---|
| **A knowledge graph** | Store the relations between things (a device, its alarms, the manuals that mention it) so multi-step questions across manuals can be answered | Large |
| **More document types** | PLC programs, robot programs, recipes, simulation data, beyond PDFs | Large |
| **Other front ends** | Alarm diagnostics, operator-panel help, engineering search | Medium to large |
| **Many users** | A server-class vector database and a faster model server | Large |

## Before changing the design

Read [04 Design decisions](04-design-decisions.md) first: several "obvious" improvements were already tried, and the reasons they were reversed matter. After any change to the model, the chunking or the settings, re-run the questions in `tests/questions.md` and compare against the answers you liked before.
