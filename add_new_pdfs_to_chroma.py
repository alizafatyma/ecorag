"""
Add new PDFs to EcoRAG Chroma database
Chunks, embeds, and integrates new documents
"""

import json
import os
from pathlib import Path
import chromadb
from sentence_transformers import SentenceTransformer
import fitz  # PyMuPDF

# Configuration
DATA_DIR = Path("ecorag_data")
COLLECTION_NAME = "ecorag_knowledge_base"
CHUNK_SIZE = 500  # words per chunk
OVERLAP = 50  # overlap between chunks

# Load existing collection
client = chromadb.PersistentClient(path=str(DATA_DIR / "chroma"))
collection = client.get_collection(COLLECTION_NAME)

# Load embedder
manifest = json.loads((DATA_DIR / "embeddings" / "manifest.json").read_text(encoding="utf-8"))
embedder = SentenceTransformer(manifest["model"])
QUERY_PREFIX = manifest["query_instruction"]

print(f"Existing collection: {collection.count()} chunks")

# New PDFs to add
NEW_PDFS = [
    {
        "path": "ecorag_data/pdfs/UNEP_Sudan_PCEA_2007.pdf",
        "title": "UNEP Sudan Post-Conflict Environmental Assessment 2007",
        "scope": "REGIONAL",
        "year": 2007
    },
    {
        "path": "ecorag_data/pdfs/Youth-for-food-not-waste.pdf",
        "title": "Youth for Food Not Waste - UNEP Initiative",
        "scope": "GLOBAL",
        "year": 2024
    },
    {
        "path": "ecorag_data/pdfs/Hidden-assets.pdf",
        "title": "Hidden Assets - Environmental & Economic Value",
        "scope": "GLOBAL",
        "year": 2023
    },
    {
        "path": "ecorag_data/pdfs/Spotlighting Opportunity_130726.pdf",
        "title": "Spotlighting Opportunity - Sustainable Development",
        "scope": "GLOBAL",
        "year": 2013
    }
]

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF"""
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page_num in range(len(doc)):
            page = doc[page_num]
            text += f"\n[Page {page_num + 1}]\n"
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        print(f"Error extracting {pdf_path}: {e}")
        return ""

def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=OVERLAP):
    """Split text into overlapping chunks"""
    words = text.split()
    chunks = []

    for i in range(0, len(words), chunk_size - overlap):
        chunk_words = words[i:i + chunk_size]
        if chunk_words:
            chunks.append(" ".join(chunk_words))

    return chunks

# Process new PDFs
total_new_chunks = 0

for pdf_info in NEW_PDFS:
    pdf_path = pdf_info["path"]

    if not Path(pdf_path).exists():
        print(f"Skipping {pdf_path} - not found")
        continue

    print(f"\nProcessing: {pdf_info['title']}")
    print(f"  File: {pdf_path}")

    # Extract text
    text = extract_text_from_pdf(pdf_path)
    if not text:
        print(f"  Failed to extract text")
        continue

    # Chunk
    chunks = chunk_text(text)
    print(f"  Extracted: {len(text.split())} words, {len(chunks)} chunks")

    # Prepare for Chroma
    chunk_ids = []
    documents = []
    metadatas = []
    embeddings = []

    for i, chunk in enumerate(chunks):
        chunk_id = f"{Path(pdf_path).stem}_{i}"
        chunk_ids.append(chunk_id)
        documents.append(chunk)

        # Metadata
        metadatas.append({
            "document_title": pdf_info["title"],
            "source_file": Path(pdf_path).name,
            "chunk_index": i,
            "total_chunks": len(chunks),
            "year": pdf_info["year"],
            "scope": pdf_info["scope"],
            "content_type": "content"
        })

        # Embed
        embedding = embedder.encode(QUERY_PREFIX + chunk, normalize_embeddings=True)
        embeddings.append(embedding.tolist())

    # Add to Chroma
    try:
        collection.add(
            ids=chunk_ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings
        )
        print(f"  Added {len(chunks)} chunks to Chroma")
        total_new_chunks += len(chunks)
    except Exception as e:
        print(f"  Error adding to Chroma: {e}")

print(f"\n" + "="*60)
print(f"Total new chunks added: {total_new_chunks}")
print(f"Collection size: {collection.count()} chunks")
print(f"="*60)

# Update manifest
manifest["num_documents"] = len(NEW_PDFS)
manifest["num_chunks_added"] = total_new_chunks
manifest["last_updated"] = "2026-10-06"

print("\nNew PDFs successfully added to Chroma database!")
print(f"Ready for deployment with {collection.count()} total chunks")
