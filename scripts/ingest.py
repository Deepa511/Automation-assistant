"""Read PDFs from data/raw/, chunk them, embed with Ollama, store in ChromaDB."""
from pathlib import Path

import chromadb
import ollama
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
DB_DIR = ROOT / "chroma_db"
EMBED_MODEL = "nomic-embed-text"
CHUNK_SIZE = 800
OVERLAP = 100


def chunk_text(text: str) -> list[str]:
    text = " ".join(text.split())
    step = CHUNK_SIZE - OVERLAP
    return [text[i:i + CHUNK_SIZE] for i in range(0, len(text), step) if text[i:i + CHUNK_SIZE].strip()]


def main() -> None:
    pdfs = sorted(RAW_DIR.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"No PDFs found in {RAW_DIR}")

    client = chromadb.PersistentClient(path=str(DB_DIR))
    try:
        client.delete_collection("docs")
    except Exception:
        pass
    collection = client.create_collection("docs", metadata={"hnsw:space": "cosine"})

    total = 0
    for pdf in pdfs:
        reader = PdfReader(pdf)
        empty_pages = []
        for page_no, page in enumerate(reader.pages, start=1):
            chunks = chunk_text(page.extract_text() or "")
            if not chunks:
                empty_pages.append(page_no)
                continue
            embeddings = ollama.embed(model=EMBED_MODEL, input=chunks)["embeddings"]
            collection.add(
                ids=[f"{pdf.name}-p{page_no}-c{i}" for i in range(len(chunks))],
                documents=chunks,
                embeddings=embeddings,
                metadatas=[{"source": pdf.name, "page": page_no}] * len(chunks),
            )
            total += len(chunks)
        print(f"{pdf.name}: {len(reader.pages)} pages, pages without text: {empty_pages or 'none'}")
    print(f"Stored {total} chunks in {DB_DIR}")


if __name__ == "__main__":
    main()
