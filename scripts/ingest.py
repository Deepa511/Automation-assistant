"""Read PDFs from data/raw/, split them into sections, embed with Ollama, store in ChromaDB.

Section-aware chunking: a numbered heading (e.g. "7.5 Replacing the camera") starts a new
section, and a section may span several pages. Sections longer than MAX_CHARS are split on
line boundaries and every piece repeats the heading.

Run with --dry-run to see the sections and chunks without calling Ollama.
"""
import re
import sys
from collections import Counter
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
DB_DIR = ROOT / "chroma_db"
EMBED_MODEL = "nomic-embed-text"
MAX_CHARS = 1500
HEAD_LINES, FOOT_LINES = 6, 3  # where repeated page headers/footers are looked for

# "7 Maintenance", "7.5 Replacing the camera" (not "1. Stop the cell", not TOC lines)
HEADING_RE = re.compile(r"^(\d{1,2}(?:\.\d{1,2}){0,2})\s+([A-Z][^.]{2,80})$")
DOT_LEADER_RE = re.compile(r"^(\.\s*){3,}")


def norm(line: str) -> str:
    return re.sub(r"\d+", "#", line.strip())


def page_lines(reader: PdfReader) -> list[list[str]]:
    """Text lines per page, without headers/footers that repeat on most pages."""
    pages = [[l.strip() for l in (p.extract_text() or "").splitlines() if l.strip()] for p in reader.pages]
    counts = Counter()
    for lines in pages:
        counts.update({norm(l) for l in lines[:HEAD_LINES] + lines[-FOOT_LINES:]})
    repeated = {k for k, c in counts.items() if c >= max(3, len(pages) / 2)}
    cleaned = []
    for lines in pages:
        n = len(lines)
        cleaned.append([l for i, l in enumerate(lines)
                        if not ((i < HEAD_LINES or i >= n - FOOT_LINES) and norm(l) in repeated)])
    # table-of-contents pages are full of ". . . . 14" dot leaders; they would only add duplicate headings
    return [[] if sum(bool(DOT_LEADER_RE.match(l)) for l in lines) >= 5 else lines for lines in cleaned]


def is_heading(line: str) -> bool:
    return bool(HEADING_RE.match(line)) and "...." not in line


def split_sections(pages: list[list[str]]) -> list[dict]:
    """Each section: {"heading": str, "lines": [(page_no, text), ...]}."""
    sections = [{"heading": "Front matter", "lines": []}]
    for page_no, lines in enumerate(pages, start=1):
        for line in lines:
            if is_heading(line):
                sections.append({"heading": line, "lines": []})
            else:
                sections[-1]["lines"].append((page_no, line))
    return [s for s in sections if s["lines"]]


def make_chunks(section: dict) -> list[dict]:
    chunks, cur, size = [], [], 0

    def flush():
        if cur:
            pages = [p for p, _ in cur]
            text = section["heading"] + "\n" + "\n".join(t for _, t in cur)
            chunks.append({"text": text, "heading": section["heading"],
                           "page_start": min(pages), "page_end": max(pages)})

    for item in section["lines"]:
        if cur and size + len(item[1]) > MAX_CHARS:
            flush()
            cur, size = [], 0
        cur.append(item)
        size += len(item[1]) + 1
    flush()
    return chunks


def build_chunks(pdf: Path) -> list[dict]:
    pages = page_lines(PdfReader(pdf))
    return [c for s in split_sections(pages) for c in make_chunks(s)]


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    pdfs = sorted(RAW_DIR.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"No PDFs found in {RAW_DIR}")

    if not dry_run:
        import chromadb
        import ollama
        client = chromadb.PersistentClient(path=str(DB_DIR))
        try:
            client.delete_collection("docs")
        except Exception:
            pass
        collection = client.create_collection("docs", metadata={"hnsw:space": "cosine"})

    total = 0
    for pdf in pdfs:
        chunks = build_chunks(pdf)
        total += len(chunks)
        print(f"{pdf.name}: {len(chunks)} chunks")
        if dry_run:
            for c in chunks:
                print(f"  p.{c['page_start']}-{c['page_end']} {len(c['text']):5d} chars  {c['heading']}")
            continue
        for i in range(0, len(chunks), 32):
            batch = chunks[i:i + 32]
            embeddings = ollama.embed(model=EMBED_MODEL, input=[c["text"] for c in batch])["embeddings"]
            collection.add(
                ids=[f"{pdf.name}-{i + j}" for j in range(len(batch))],
                documents=[c["text"] for c in batch],
                embeddings=embeddings,
                metadatas=[{"source": pdf.name, "heading": c["heading"],
                            "page_start": c["page_start"], "page_end": c["page_end"]} for c in batch],
            )
    print(f"{'Would store' if dry_run else 'Stored'} {total} chunks" + ("" if dry_run else f" in {DB_DIR}"))


if __name__ == "__main__":
    main()
