# Documentation

This folder explains the document chatbot from the basics. You do not need a machine-learning background. Every technical word is explained the first time it appears, and the [glossary](glossary.md) collects them all.

## How to read it

| You have | Read | What you get |
|---|---|---|
| **5 minutes** | [00 Overview](00-overview.md) | What the chatbot does, a picture of how it works, three real examples |
| **30 minutes** | [01 Concepts from zero](01-concepts-from-zero.md), [02 Architecture](02-architecture.md), [03 Life of a question](03-life-of-a-question.md), [04 Design decisions](04-design-decisions.md) | Why it is built this way, and exactly what happens when you ask something |
| **When you need it** | [05 Running and troubleshooting](05-running-and-troubleshooting.md), [06 Limits and future](06-limits-and-future.md), [Glossary](glossary.md) | Commands, settings, fixes, known weaknesses, and ideas for next steps |

## What "measured" means in these pages

Numbers about speed and quality come from this project's development laptop: an 11th-generation Intel Core i7 with 4 cores, 15.7 GB of memory and no usable graphics card. They are **measured examples, not promises**. On other hardware they will differ.

When something was never tested, the text says **not tested**. For example, we never compared different AI models side by side, and the pages say so.

## The project in one paragraph

A chat assistant that answers questions about technical manuals (here: five fictional manuals about a tightening controller, robot vision and a fastening cell). It finds the relevant passages in the manuals, lets a locally running AI model write an answer from only those passages, and shows where the answer came from. If the manuals do not contain the answer, it says so. Everything runs on one laptop, for free, with no cloud AI service involved (the small print is in [Design decisions](04-design-decisions.md#local-and-free-only)).
