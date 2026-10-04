# ============================================================
# EcoRAG - Stage 4: build the Chroma vector database (no LLM, no answer generation)
# ============================================================
# Input : ecorag_data/embeddings/  (embeddings.npy + records.jsonl + manifest.json)
# Output: ecorag_data/chroma/       (persistent Chroma database, one collection)
# The chunks are NOT embedded again: the saved vectors are passed to Chroma directly.
# Only the test QUESTIONS are embedded (with the BGE query prefix) for the retrieval check.

# --- 0. Install (Colab) ---
!pip install -q chromadb sentence-transformers

import json
from pathlib import Path

import chromadb
import numpy as np


# --- 1. Settings ---
DATA_DIR = Path("ecorag_data")    # Colab tip: Path("/content/drive/MyDrive/ecorag_data") keeps files
EMBEDDINGS_DIR = DATA_DIR / "embeddings"
CHROMA_DIR = DATA_DIR / "chroma"
COLLECTION_NAME = "ecorag_knowledge_base"
BATCH_SIZE = 500                  # chunks added per collection.add() call
TOP_K = 5                         # results per test question

TEST_QUESTIONS = [
    "What share of global anthropogenic methane emissions comes from agriculture?",
    "How many methane alerts did the satellite-based Methane Alert and Response System send, and how often do operators respond?",
    "What are the main challenges in modernising electricity grids?",
    "How can the cost of capital for clean energy projects in emerging and developing economies be reduced?",
    "How are near-zero emissions steel and cement defined?",
]


# --- 2. Load the saved embeddings, records and manifest ---
manifest = json.loads((EMBEDDINGS_DIR / "manifest.json").read_text(encoding="utf-8"))
embeddings = np.load(EMBEDDINGS_DIR / "embeddings.npy")
with open(EMBEDDINGS_DIR / "records.jsonl", encoding="utf-8") as f:
    records = [json.loads(line) for line in f]

# Sanity checks before touching the database
assert embeddings.shape == (manifest["num_chunks"], manifest["embedding_dimension"]), \
    f"embeddings.npy shape {embeddings.shape} does not match the manifest"
assert len(records) == embeddings.shape[0], "records.jsonl and embeddings.npy have different lengths"
assert all(r["row"] == i for i, r in enumerate(records)), "records are not in row order"
ids = [r["id"] for r in records]
assert len(set(ids)) == len(ids), "chunk IDs are not unique"
print(f"Loaded {len(records)} records and {embeddings.shape} embeddings "
      f"({manifest['model']}, {manifest['num_documents']} documents)")


# --- 3. Create the persistent database and (re)build the collection ---
client = chromadb.PersistentClient(path=str(CHROMA_DIR))
if COLLECTION_NAME in [c.name for c in client.list_collections()]:
    client.delete_collection(COLLECTION_NAME)      # rebuild from scratch so re-runs stay in sync

collection = client.create_collection(
    name=COLLECTION_NAME,
    embedding_function=None,                       # we always provide our own BGE vectors
    configuration={"hnsw": {"space": "cosine"}},   # distance = 1 - cosine similarity
    metadata={                                     # remembered with the collection
        "embedding_model": manifest["model"],
        "embedding_dimension": manifest["embedding_dimension"],
        "query_instruction": manifest["query_instruction"],
        "num_documents": manifest["num_documents"],
        "embeddings_created_at": manifest["created_at"],
    },
)

for start in range(0, len(records), BATCH_SIZE):
    batch = records[start:start + BATCH_SIZE]
    collection.add(
        ids=[r["id"] for r in batch],
        embeddings=embeddings[start:start + BATCH_SIZE],   # the saved vectors, no re-embedding
        documents=[r["document"] for r in batch],
        metadatas=[r["metadata"] for r in batch],
    )
print(f"Added {collection.count()} chunks to collection '{COLLECTION_NAME}' in {CHROMA_DIR}/")


# --- 4. Verify the collection ---
checks = {}
checks["count matches (1 per chunk)"] = collection.count() == len(records)

stored_ids = collection.get(include=[])["ids"]
checks["stored IDs unique and complete"] = len(set(stored_ids)) == len(stored_ids) == len(records) \
    and set(stored_ids) == set(ids)

sample_rows = sorted({0, len(records) // 2, len(records) - 1})
sample = collection.get(ids=[ids[i] for i in sample_rows], include=["documents", "metadatas", "embeddings"])
by_id = {i: k for k, i in enumerate(sample["ids"])}
checks["known IDs retrievable"] = len(sample["ids"]) == len(sample_rows)
checks["documents and metadata present"] = all(
    sample["documents"][by_id[ids[i]]] == records[i]["document"]
    and sample["metadatas"][by_id[ids[i]]]["document_id"] == records[i]["metadata"]["document_id"]
    for i in sample_rows)
checks["stored vectors = saved embeddings"] = all(
    np.allclose(sample["embeddings"][by_id[ids[i]]], embeddings[i], atol=1e-6) for i in sample_rows)

reopened = chromadb.PersistentClient(path=str(CHROMA_DIR)).get_collection(COLLECTION_NAME)
checks["reopened database count matches"] = reopened.count() == len(records)

print("\n" + "=" * 70)
print("EcoRAG CHROMA BUILD REPORT")
print("=" * 70)
print(f"Database:    {CHROMA_DIR}/   collection: {COLLECTION_NAME}")
print(f"Count:       {collection.count()} (expected {len(records)}); after reopening: {reopened.count()}")
print(f"Distance:    cosine   |   embedding model: {manifest['model']} ({manifest['embedding_dimension']} dims)")
for name, ok in checks.items():
    print(f"  [{'OK' if ok else 'FAIL'}] {name}")
print("Known IDs retrieved:")
for i in sample_rows:
    m = sample["metadatas"][by_id[ids[i]]]
    print(f"  {ids[i]}  | {m['document_title'][:45]} | pages {m['page_numbers']} | {m['content_type']}")
if not all(checks.values()):
    raise ValueError(f"Chroma verification failed: {checks}")


# --- 5. Retrieval tests (question -> BGE query vector -> nearest chunks) ---
from sentence_transformers import SentenceTransformer

query_model = SentenceTransformer(manifest["model"])
prefix = manifest["query_instruction"]      # BGE: questions get this prefix, passages do not

print("\n" + "=" * 70)
print("RETRIEVAL TESTS (top results, no LLM)")
print("=" * 70)
for question in TEST_QUESTIONS:
    query_vector = query_model.encode(prefix + question, normalize_embeddings=True)
    result = reopened.query(query_embeddings=[query_vector], n_results=TOP_K,
                            include=["documents", "metadatas", "distances"])
    print(f"\nQ: {question}")
    for rank, (cid, doc, meta, dist) in enumerate(zip(result["ids"][0], result["documents"][0],
                                                      result["metadatas"][0], result["distances"][0]), 1):
        print(f"  {rank}. {cid}   similarity {1 - dist:.3f} (distance {dist:.3f})")
        print(f"     {meta['document_title']} | {meta['section']} | pages {meta['page_numbers']} | {meta['content_type']}")
        print(f"     \"{' '.join(doc.split())[:200]}...\"")
