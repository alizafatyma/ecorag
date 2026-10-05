#!/usr/bin/env python3
"""Test script for EcoRAG - skips Colab syntax"""

import json
import re
import time
from pathlib import Path

import chromadb
import torch
from sentence_transformers import SentenceTransformer
from transformers import AutoModelForCausalLM, AutoTokenizer

# --- Settings ---
DATA_DIR = Path("ecorag_data")
COLLECTION_NAME = "ecorag_knowledge_base"
TOP_K = 5
EVIDENCE_TYPES = ["content", "table"]

LLM_GPU = "Qwen/Qwen2.5-3B-Instruct"
LLM_CPU = "Qwen/Qwen2.5-1.5B-Instruct"
MAX_NEW_TOKENS = 400

# --- Load retrieval setup ---
print("Loading Chroma database...")
manifest = json.loads((DATA_DIR / "embeddings" / "manifest.json").read_text(encoding="utf-8"))
QUERY_PREFIX = manifest["query_instruction"]

client = chromadb.PersistentClient(path=str(DATA_DIR / "chroma"))
collection = client.get_collection(COLLECTION_NAME)

embedder = SentenceTransformer(manifest["model"])
print(f"[OK] Chroma collection: {collection.count()} chunks")
print(f"[OK] Embedding model: {manifest['model']} ({manifest['embedding_dimension']} dims)")

# --- Retrieval ---
def retrieve(question, top_k=TOP_K, content_types=EVIDENCE_TYPES):
    query_vector = embedder.encode(QUERY_PREFIX + question, normalize_embeddings=True)
    where = {"content_type": {"$in": list(content_types)}} if content_types else None
    result = collection.query(query_embeddings=[query_vector], n_results=top_k, where=where,
                              include=["documents", "metadatas", "distances"])
    sources = []
    for n, (chunk_id, text, meta, distance) in enumerate(
            zip(result["ids"][0], result["documents"][0], result["metadatas"][0], result["distances"][0]), 1):
        sources.append({
            "n": n,
            "chunk_id": chunk_id,
            "document": meta["document_title"],
            "section": meta["section"],
            "similarity": round(1 - distance, 3),
            "text": text[:300],
        })
    return sources

# --- Test ---
print("\n" + "="*80)
print("TESTING: 'What share of global anthropogenic methane emissions comes from agriculture?'")
print("="*80)

sources = retrieve("What share of global anthropogenic methane emissions comes from agriculture?")

print(f"\n[OK] Retrieved {len(sources)} sources:")
for s in sources:
    print(f"  [{s['n']}] {s['document']} (similarity: {s['similarity']})")
    print(f"      {s['text']}...")

if all(s["similarity"] < 0.2 for s in sources):
    print("\n[WARN] All similarities < 0.2 (might indicate empty/irrelevant database)")
elif not sources:
    print("\n[ERROR] No sources retrieved at all!")
else:
    print(f"\n[OK] System is working - retrieved relevant sources")
