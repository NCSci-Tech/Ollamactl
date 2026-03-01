#!/usr/bin/env python3
"""
rag.py — Local RAG pipeline using llama-index + Ollama
Indexes your zsh history and nvim config, then queries codellama with context.

Usage:
    python rag.py "what neovim plugins do I have"
    python rag.py "what commands do I use most"
    python rag.py  (interactive mode)
"""

import sys
import os
from pathlib import Path

# ─── Config ────────────────────────────────────────────────────────────────────
MODEL        = "codellama:7b"
EMBED_MODEL  = "nomic-embed-text"   # lightweight embedding model via Ollama
OLLAMA_URL   = "http://localhost:11434"

FILES = [
    Path.home() / ".zsh_history",
    Path.home() / ".config/nvim/init.lua",
    Path.home() / ".config/nvim/lazy-lock.json",
]

# ─── Imports ───────────────────────────────────────────────────────────────────
try:
    from llama_index.core import VectorStoreIndex, Document, Settings
    from llama_index.llms.ollama import Ollama
    from llama_index.embeddings.ollama import OllamaEmbedding
except ImportError:
    print("[ERR] llama-index not found. Run: ai-env && pip install llama-index llama-index-llms-ollama llama-index-embeddings-ollama")
    sys.exit(1)

# ─── Check Ollama is running ───────────────────────────────────────────────────
import urllib.request
try:
    urllib.request.urlopen(OLLAMA_URL, timeout=2)
except Exception:
    print("[ERR] Ollama is not running. Start it with: ollamactl start")
    sys.exit(1)

# ─── Load files ────────────────────────────────────────────────────────────────
def load_documents():
    docs = []
    for path in FILES:
        if not path.exists():
            print(f"[WARN] File not found, skipping: {path}")
            continue
        try:
            text = path.read_text(errors="ignore")
            # Label each document so the model knows what it's reading
            doc = Document(
                text=text,
                metadata={"source": str(path), "filename": path.name}
            )
            docs.append(doc)
            print(f"[OK]  Loaded: {path} ({len(text)} chars)")
        except Exception as e:
            print(f"[WARN] Could not read {path}: {e}")
    return docs

# ─── Setup ─────────────────────────────────────────────────────────────────────
def setup():
    print(f"\n[INFO] Setting up RAG pipeline...")
    print(f"[INFO] LLM     : {MODEL}")
    print(f"[INFO] Embedder: {EMBED_MODEL}")
    print()

    # Check embedding model is pulled
    try:
        import urllib.request, json
        req = urllib.request.urlopen(f"{OLLAMA_URL}/api/tags")
        data = json.loads(req.read())
        model_names = [m["name"] for m in data.get("models", [])]
        if not any(EMBED_MODEL in m for m in model_names):
            print(f"[INFO] Pulling embedding model: {EMBED_MODEL}")
            os.system(f"ollama pull {EMBED_MODEL}")
    except Exception:
        pass

    # Configure llama-index to use local Ollama
    Settings.llm = Ollama(
        model=MODEL,
        base_url=OLLAMA_URL,
        request_timeout=120.0
    )
    Settings.embed_model = OllamaEmbedding(
        model_name=EMBED_MODEL,
        base_url=OLLAMA_URL
    )

    # Load and index documents
    docs = load_documents()
    if not docs:
        print("[ERR] No documents loaded. Check file paths.")
        sys.exit(1)

    print(f"\n[INFO] Indexing {len(docs)} document(s) — this may take a moment...")
    index = VectorStoreIndex.from_documents(docs, show_progress=True)
    print("[OK]  Index built.\n")
    return index

# ─── Query ─────────────────────────────────────────────────────────────────────
def query(index, question):
    engine = index.as_query_engine(
        similarity_top_k=5,  # retrieve 5 most relevant chunks
        streaming=False
    )
    print(f"\n[YOU] {question}")
    print(f"[AI]  ", end="", flush=True)
    response = engine.query(question)
    print(response)
    print()

# ─── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("  RAG — Local AI with your files")
    print("  Files: zsh history + nvim config")
    print("  Model: codellama:7b via Ollama")
    print("=" * 55)

    index = setup()

    # Command line mode — single question
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        query(index, question)
        return

    # Interactive mode
    print("Interactive mode — type your question or 'exit' to quit\n")
    while True:
        try:
            question = input(">>> ").strip()
            if not question:
                continue
            if question.lower() in ("exit", "quit", "bye", "/bye"):
                print("Bye.")
                break
            query(index, question)
        except (KeyboardInterrupt, EOFError):
            print("\nBye.")
            break

if __name__ == "__main__":
    main()
