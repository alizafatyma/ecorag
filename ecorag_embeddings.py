# ============================================================
# EcoRAG - Stage 3: embed the chunks of ALL documents into one dataset
# ============================================================
# Folder layout (works the same for 1, 10 or 100 PDFs):
#   ecorag_data/pdfs/        <- the PDFs (input of the chunking stage)
#   ecorag_data/chunks/      <- one chunks JSON file per PDF (output of the chunking stage)
#   ecorag_data/embeddings/  <- ONE combined, Chroma-ready embedding dataset (output of this stage)
# Adding PDFs later = put their chunk files in ecorag_data/chunks/ and re-run this cell.
# No vector database, retrieval or LLM yet.

# --- 0. Install (already present in most Colab runtimes) ---
!pip install -q sentence-transformers

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import transformers
from sentence_transformers import SentenceTransformer

transformers.logging.set_verbosity_error()   # we check chunk lengths ourselves


# --- 1. Settings ---
DATA_DIR = Path("ecorag_data")   # tip for Colab: Path("/content/drive/MyDrive/ecorag_data") keeps files
CHUNKS_DIR = DATA_DIR / "chunks"
OUTPUT_DIR = DATA_DIR / "embeddings"

MODEL_NAME = "BAAI/bge-small-en-v1.5"
# bge models embed PASSAGES as-is, but QUESTIONS need this prefix (used in the retrieval stage)
QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "
TEXT_FIELD = "embed_text"   # context header + chunk text, built for embedding by the chunker
BATCH_SIZE = 32


# --- 2. Find all chunk files ---
CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
chunk_files = sorted(CHUNKS_DIR.glob("*.json"))
if not chunk_files:
    try:
        from google.colab import files
        print(f"No chunk files in {CHUNKS_DIR}/ - please upload one or more chunk JSON files...")
        for name, data in files.upload().items():
            (CHUNKS_DIR / name).write_bytes(data)
        chunk_files = sorted(CHUNKS_DIR.glob("*.json"))
    except ImportError:
        pass
if not chunk_files:
    raise FileNotFoundError(f"No chunk files found in {CHUNKS_DIR}/")


# --- 3. Load every chunk and group the chunks by document ---
def make_document_id(source_filename):
    """Stable, readable ID from the PDF file name: 'UN Report 2025.pdf' -> 'un-report-2025'."""
    return re.sub(r"[^a-z0-9]+", "-", Path(source_filename).stem.lower()).strip("-")

documents = {}   # document_id -> {"source_filename", "chunk_files", "chunks"}
for path in chunk_files:
    data = json.loads(path.read_text(encoding="utf-8"))
    raw_chunks = data["chunks"] if isinstance(data, dict) else data   # a list, or {"chunks": [...]}
    for raw in raw_chunks:
        source = raw.get("source_filename") or raw.get("source") or f"{path.stem}.pdf"
        doc_id = raw.get("document_id") or make_document_id(source)
        doc = documents.setdefault(doc_id, {"source_filename": source, "chunk_files": set(), "chunks": []})
        if doc["source_filename"] != source:
            raise ValueError(f"Different files map to the same document_id '{doc_id}': "
                             f"{doc['source_filename']!r} and {source!r}. Rename one of the PDFs.")
        doc["chunk_files"].add(path.name)
        doc["chunks"].append(raw)

# A document must come from exactly ONE chunk file, otherwise it would be embedded twice
duplicated = {d: sorted(v["chunk_files"]) for d, v in documents.items() if len(v["chunk_files"]) > 1}
if duplicated:
    raise ValueError(f"These documents appear in more than one chunk file: {duplicated}. "
                     "Keep one chunk file per document.")


# --- 4. Build one record per chunk with globally unique IDs ---
# Chunk numbers restart at 0 in every PDF, so the global ID = document_id + local chunk number.
records = []
for doc_id in sorted(documents):
    doc = documents[doc_id]
    local_ids = [c["chunk_id"] for c in doc["chunks"]]
    if len(set(local_ids)) != len(local_ids):
        raise ValueError(f"Duplicate chunk_id values inside document '{doc_id}'.")
    for raw in sorted(doc["chunks"], key=lambda c: c["chunk_id"]):
        local_id = raw["chunk_id"]
        text = (raw.get("text") or "").strip()
        records.append({
            "id": f"{doc_id}::{local_id:04d}" if isinstance(local_id, int) else f"{doc_id}::{local_id}",
            "document_id": doc_id,
            "source_filename": doc["source_filename"],
            "document_title": raw.get("document_title") or Path(doc["source_filename"]).stem,
            "chapter": raw.get("chapter") or "",
            "section": raw.get("section") or "",
            "page_numbers": raw.get("page_numbers") or [],
            "content_type": raw.get("content_type") or "content",
            "text": text,
            "embed_text": (raw.get(TEXT_FIELD) or text).strip(),
            "references": raw.get("references") or [],
            "local_chunk_id": local_id,
        })

empty = [r["id"] for r in records if not r["text"] or not r["embed_text"]]
if empty:
    raise ValueError(f"These chunks have no text to embed: {empty}")

id_counts = Counter(r["id"] for r in records)
duplicate_ids = [i for i, n in id_counts.items() if n > 1]
if duplicate_ids:
    raise ValueError(f"Chunk IDs are not globally unique: {duplicate_ids[:10]}")


# --- 5. Load the model and check that no chunk is too long for it ---
model = SentenceTransformer(MODEL_NAME)
model_max_tokens = min(model.max_seq_length,
                       model.tokenizer.model_max_length,
                       model[0].auto_model.config.max_position_embeddings)
embedding_dim = model.get_sentence_embedding_dimension()

texts = [r["embed_text"] for r in records]
token_counts = [len(ids) for ids in model.tokenizer(texts)["input_ids"]]   # incl. [CLS] and [SEP]
for r, n in zip(records, token_counts):
    r["tokens"] = n
too_long = [(r["id"], n) for r, n in zip(records, token_counts) if n > model_max_tokens]
if too_long:
    raise ValueError(f"{len(too_long)} chunks are longer than the model's {model_max_tokens}-token "
                     f"limit and would be cut off: {too_long[:10]}. Re-chunk these documents.")


# --- 6. Generate one embedding per chunk (row i = records[i]) ---
embeddings = model.encode(
    texts,
    batch_size=BATCH_SIZE,
    show_progress_bar=True,
    convert_to_numpy=True,
    normalize_embeddings=True,     # length 1 -> cosine similarity = dot product
).astype(np.float32)

norms = np.linalg.norm(embeddings, axis=1)
invalid_rows = [records[i]["id"] for i in range(len(embeddings))
                if not np.isfinite(embeddings[i]).all() or norms[i] < 1e-6]
if embeddings.shape != (len(records), embedding_dim) or invalid_rows:
    raise ValueError(f"Invalid embeddings: shape {embeddings.shape}, bad rows {invalid_rows[:10]}")


# --- 7. Save in a Chroma-ready structure ---
# Chroma needs:  ids (str), embeddings (list of vectors), documents (str), metadatas (dict)
# Chroma metadata values must be str / int / float / bool, so lists are stored as text.
def chroma_metadata(r):
    pages = r["page_numbers"]
    return {
        "document_id": r["document_id"],
        "source_filename": r["source_filename"],
        "document_title": r["document_title"],
        "chapter": r["chapter"],
        "section": r["section"],
        "content_type": r["content_type"],
        "page_numbers": ",".join(str(p) for p in pages),     # e.g. "4,5"
        "page_start": min(pages) if pages else -1,
        "page_end": max(pages) if pages else -1,
        "references": json.dumps(r["references"], ensure_ascii=False),
        "num_references": len(r["references"]),
        "local_chunk_id": r["local_chunk_id"],
        "tokens": r["tokens"],
    }

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
np.save(OUTPUT_DIR / "embeddings.npy", embeddings)
with open(OUTPUT_DIR / "records.jsonl", "w", encoding="utf-8") as f:
    for row, r in enumerate(records):
        f.write(json.dumps({"row": row, "id": r["id"], "document": r["text"],
                            "metadata": chroma_metadata(r)}, ensure_ascii=False) + "\n")

chunks_per_document = Counter(r["document_id"] for r in records)
manifest = {
    "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "model": MODEL_NAME,
    "embedding_dimension": embedding_dim,
    "model_max_tokens": model_max_tokens,
    "normalized": True,
    "embedded_field": TEXT_FIELD,
    "query_instruction": QUERY_INSTRUCTION,
    "num_documents": len(documents),
    "num_chunks": len(records),
    "files": {"embeddings": "embeddings.npy", "records": "records.jsonl"},
    "documents": [{"document_id": d,
                   "source_filename": documents[d]["source_filename"],
                   "document_title": next(r["document_title"] for r in records if r["document_id"] == d),
                   "chunk_file": sorted(documents[d]["chunk_files"])[0],
                   "num_chunks": chunks_per_document[d]} for d in sorted(documents)],
}
(OUTPUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


# --- 8. Re-load the saved files and prove rows and metadata line up ---
saved_embeddings = np.load(OUTPUT_DIR / "embeddings.npy")
with open(OUTPUT_DIR / "records.jsonl", encoding="utf-8") as f:
    saved_records = [json.loads(line) for line in f]
rows_match = (len(saved_records) == saved_embeddings.shape[0]
              and all(s["row"] == i and s["id"] == r["id"]
                      for i, (s, r) in enumerate(zip(saved_records, records))))
# Re-embed a few chunks from scratch: each must match the vector stored in its row
check_rows = sorted({0, len(records) // 2, len(records) - 1})
fresh = model.encode([records[i]["embed_text"] for i in check_rows], normalize_embeddings=True)
alignment_ok = all(float(saved_embeddings[i] @ v) > 0.999 for i, v in zip(check_rows, fresh))


# --- 9. Report ---
print("\n" + "=" * 70)
print("EcoRAG EMBEDDING REPORT")
print("=" * 70)
print(f"Model:                        {MODEL_NAME}")
print(f"Model maximum input length:   {model_max_tokens} tokens")
print(f"Documents processed:          {len(documents)}")
print(f"Chunks processed:             {len(records)}")
print("Chunks per document:")
for d in sorted(documents):
    print(f"  {chunks_per_document[d]:>5}  {d}  ({documents[d]['source_filename']})")
print(f"Chunk types:                  {dict(Counter(r['content_type'] for r in records))}")
print(f"Embedding dimension:          {embedding_dim}")
print(f"Embedding array shape:        {embeddings.shape}  (dtype {embeddings.dtype})")
print(f"Tokens per chunk:             min {min(token_counts)}, "
      f"avg {sum(token_counts) / len(token_counts):.0f}, max {max(token_counts)}")
print(f"Chunks exceeding the limit:   {len(too_long)}")
print(f"Missing/invalid embeddings:   {len(invalid_rows)}")
print(f"IDs globally unique:          {'YES' if not duplicate_ids else 'NO'} "
      f"({len(id_counts)} unique IDs for {len(records)} chunks)")
print(f"Rows <-> metadata aligned:    {'YES' if rows_match and alignment_ok else 'NO'} "
      f"(re-embedded rows {check_rows} match the saved vectors)")

example = records[min(20, len(records) - 1)]
row = records.index(example)
print("\nExample record:")
print(f"  row {row}  id: {example['id']}")
print(f"  {example['document_title']} | {example['section']} | pages {example['page_numbers']} "
      f"| {example['content_type']}")
print(f"  text: {example['text'][:200]}...")
print(f"  embedding[:8]: {[round(float(x), 4) for x in embeddings[row][:8]]}")
print(f"\nSaved to {OUTPUT_DIR}/: embeddings.npy, records.jsonl, manifest.json")

# Next stage (NOT run now) - loading into Chroma will look like:
#   collection.add(ids=[r["id"] for r in saved_records],
#                  embeddings=saved_embeddings.tolist(),
#                  documents=[r["document"] for r in saved_records],
#                  metadatas=[r["metadata"] for r in saved_records])
