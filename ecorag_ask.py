# ============================================================
# EcoRAG - Stage 5: question -> retrieval -> evidence -> LLM answer with citations
# ============================================================
# A small layer ON TOP of the existing, validated pipeline. It does not re-chunk, re-embed
# or rebuild anything. It only READS:
#   ecorag_data/embeddings/manifest.json  (embedding model name + BGE query prefix)
#   ecorag_data/chroma/                   (the existing collection "ecorag_knowledge_base")
#
#   question --(BGE + query prefix)--> query vector --(Chroma, content/table only)--> top-k chunks
#            --> numbered evidence block --> local instruction-tuned LLM --> answer with [n] citations
#
# No paid API, no LangChain, no UI.

# --- 0. Install (Colab; most of these are already present) ---
!pip install -q chromadb sentence-transformers transformers accelerate

import json
import re
import time
from pathlib import Path

import chromadb
import torch
from sentence_transformers import SentenceTransformer


# --- 1. Settings ---
DATA_DIR = Path("ecorag_data")    # Colab tip: Path("/content/drive/MyDrive/ecorag_data")
COLLECTION_NAME = "ecorag_knowledge_base"
TOP_K = 5                                   # chunks given to the LLM
EVIDENCE_TYPES = ["content", "table"]       # never front_matter / references by default

# The LLM is chosen by the hardware it runs on (see the report for why):
LLM_GPU = "Qwen/Qwen2.5-3B-Instruct"        # Colab T4 GPU (16 GB): fp16, ~6 GB
LLM_CPU = "Qwen/Qwen2.5-1.5B-Instruct"      # CPU-only machines: 3B is too slow / too big
MAX_NEW_TOKENS = 400                        # maximum length of the generated answer


# --- 2. Load the existing retrieval setup (no LLM needed for this part) ---
manifest = json.loads((DATA_DIR / "embeddings" / "manifest.json").read_text(encoding="utf-8"))
QUERY_PREFIX = manifest["query_instruction"]   # "Represent this sentence for searching relevant passages: "

client = chromadb.PersistentClient(path=str(DATA_DIR / "chroma"))
collection = client.get_collection(COLLECTION_NAME)
if collection.metadata.get("embedding_model") != manifest["model"]:
    raise ValueError("The Chroma collection was built with a different embedding model than the manifest.")

embedder = SentenceTransformer(manifest["model"])   # the SAME model that embedded the chunks
print(f"Chroma collection '{COLLECTION_NAME}': {collection.count()} chunks | "
      f"query embeddings: {manifest['model']} ({manifest['embedding_dimension']} dims)")


# --- 3. Small helpers for readable source labels ---
def format_pages(page_numbers):
    """'11,12' -> 'pp. 11–12', '7' -> 'p. 7', '4,7' -> 'pp. 4, 7'."""
    pages = [int(p) for p in str(page_numbers).split(",") if p.strip().isdigit()]
    if not pages:
        return "page unknown"
    if len(pages) == 1:
        return f"p. {pages[0]}"
    if pages == list(range(pages[0], pages[-1] + 1)):
        return f"pp. {pages[0]}–{pages[-1]}"
    return "pp. " + ", ".join(str(p) for p in pages)

def short_title(title):
    """'GLOBAL METHANE STATUS REPORT 2025' -> 'Global Methane Status Report 2025';
    text after a colon (a subtitle) is dropped."""
    title = title.split(":")[0].strip()
    return title.title() if title.isupper() else title


# --- 4. Retrieval: question -> BGE query vector -> top-k content/table chunks ---
def retrieve(question, top_k=TOP_K, content_types=EVIDENCE_TYPES):
    """Return the top-k chunks for a question as a list of numbered sources."""
    # BGE embeds QUESTIONS with the query prefix (the chunks were embedded without it)
    query_vector = embedder.encode(QUERY_PREFIX + question, normalize_embeddings=True)
    where = {"content_type": {"$in": list(content_types)}} if content_types else None
    result = collection.query(query_embeddings=[query_vector], n_results=top_k, where=where,
                              include=["documents", "metadatas", "distances"])
    sources = []
    for n, (chunk_id, text, meta, distance) in enumerate(
            zip(result["ids"][0], result["documents"][0], result["metadatas"][0], result["distances"][0]), 1):
        pages = format_pages(meta["page_numbers"])
        sources.append({
            "n": n,                                        # the number the LLM cites as [n]
            "chunk_id": chunk_id,
            "document": meta["document_title"],
            "section": meta["section"],
            "chapter": meta["chapter"],
            "pages": pages,
            "page_start": meta["page_start"],
            "page_end": meta["page_end"],
            "content_type": meta["content_type"],
            "similarity": round(1 - distance, 3),           # cosine similarity
            "distance": round(distance, 3),
            "label": f"[{n}] {short_title(meta['document_title'])}, {pages}",
            "text": text,
        })
    return sources


# --- 5. Evidence block + prompt ---
# v1: blocks labelled [SOURCE n] | v2: labelled [n] + explicit citation/key-fact rules |
# v3: same evidence as v2, but a rigid answer format: one claim per line, each ending with its citation
PROMPT_VERSION = "v3"

def build_evidence(sources):
    """The numbered evidence exactly as the LLM sees it (similarity scores are NOT
    included, so the model judges the text itself rather than our ranking).
    Blocks are labelled [1], [2], ... so the label is exactly the citation the model should write."""
    return "\n\n".join(
        f"[{s['n']}]\n"
        f"Document: {s['document']}\n"
        f"Section: {s['section']}\n"
        f"Pages: {s['pages']}\n"
        f"Chunk ID: {s['chunk_id']}\n"
        f"TEXT:\n{s['text']}"
        for s in sources)

SYSTEM_PROMPT_V2 = """You are EcoRAG, an assistant that answers questions about environmental and sustainability reports.

You are given numbered SOURCES, labelled [1], [2], [3], and so on. Follow these rules strictly:
1. Answer using ONLY information stated in the SOURCES. Do not use your general knowledge, even if you think it is correct.
2. Citations: write the source number in square brackets right after the claim it supports. [2] means the second source block, the one labelled [2].
   Example: Wind power capacity doubled between 2015 and 2020 [3].
   - Cite the source whose text actually states that specific claim. If a number comes from source [4], cite [4], not another source.
   - Never cite a source just because it is about the same topic. If two sources both state the claim, cite both: [2][4].
   - Every factual sentence needs at least one citation. Write citations only as [n], never as "SOURCE n".
3. Make sure your answer includes the specific numbers, thresholds, percentages, dates, or definitions that directly answer the question when those facts are present in the supplied evidence. Do not replace a specific answer with a vague summary.
4. If the SOURCES do not contain enough information to answer the question, or part of it, say so explicitly: "The provided sources do not contain enough information to answer this." Do not guess or fill gaps.
5. If sources disagree, describe the disagreement and cite each side. Do not silently pick one.
6. Copy numbers, units, percentages and years exactly as they appear in the SOURCES.
7. Be concise: a short paragraph or a few bullet points."""

USER_INSTRUCTION_V2 = (
    "Answer the question using only the SOURCES above. Put the number of the supporting "
    "source in square brackets, like [1], right after each claim, and include the specific "
    "numbers, thresholds or definitions that answer the question. "
    "If the SOURCES do not contain enough information, say so.")

SYSTEM_PROMPT_V3 = """You are EcoRAG, an assistant that answers questions about environmental and sustainability reports.

You are given numbered SOURCES, labelled [1], [2], [3], and so on.

Write your answer in this exact format:
- One factual claim per line. Start each line with "- ".
- End EVERY line with the number of the source that states that claim, in square brackets: [2]. If two sources state it, write [2][4].
- Use only the numbers of the SOURCES you were given.
- If no source states a claim, do not write that claim.
- No introduction and no concluding summary: only the claim lines.

Example of the format (made-up content):
- Wind power capacity doubled between 2015 and 2020 [3].
- Most of the new capacity was built offshore [1][3].

Rules:
1. Use ONLY information stated in the SOURCES. Do not use your general knowledge, even if you think it is correct.
2. Cite the source whose text actually states that specific claim. If a number comes from source [4], cite [4]. A source about the same topic is not enough.
3. Include the specific numbers, thresholds, percentages, dates, or definitions that directly answer the question when those facts are present in the SOURCES.
4. If the SOURCES do not contain enough information to answer the question, write only this line: "The provided sources do not contain enough information to answer this." If they answer only part of it, add a line: "- The provided sources do not contain enough information about <the missing part>."
5. If sources disagree, write one line for each side, each with its own citation.
6. Copy numbers, units, percentages and years exactly as they appear in the SOURCES.
7. Write at most 8 lines."""

USER_INSTRUCTION_V3 = (
    "Answer the question using only the SOURCES above, in the required format: one claim per line, "
    "each line ending with the number of the source that states it, in square brackets.")

PROMPTS = {"v2": (SYSTEM_PROMPT_V2, USER_INSTRUCTION_V2),
           "v3": (SYSTEM_PROMPT_V3, USER_INSTRUCTION_V3)}

def build_messages(question, sources, prompt_version=None):
    system_prompt, instruction = PROMPTS[prompt_version or PROMPT_VERSION]
    user_message = (
        f"SOURCES:\n\n{build_evidence(sources)}\n\n"
        f"QUESTION: {question}\n\n"
        f"{instruction}")
    return [{"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}]


# --- 6. The LLM (loaded separately, only when first needed) ---
LLM = {"model": None, "tokenizer": None, "name": None, "device": None}

def load_llm(model_name=None):
    """Load the instruction-tuned LLM once. Retrieval works without calling this."""
    if LLM["model"] is not None:
        return
    from transformers import AutoModelForCausalLM, AutoTokenizer
    device = "cuda" if torch.cuda.is_available() else "cpu"
    name = model_name or (LLM_GPU if device == "cuda" else LLM_CPU)
    dtype = torch.float16 if device == "cuda" else torch.bfloat16   # bf16 halves CPU memory
    print(f"Loading {name} on {device} ({str(dtype).replace('torch.', '')})...")
    start = time.time()
    tokenizer = AutoTokenizer.from_pretrained(name)
    model = AutoModelForCausalLM.from_pretrained(name, dtype=dtype).to(device).eval()
    LLM.update(model=model, tokenizer=tokenizer, name=name, device=device)
    print(f"Loaded in {time.time() - start:.0f}s")

def generate(messages, max_new_tokens=MAX_NEW_TOKENS):
    """Run the chat-formatted prompt through the LLM (greedy decoding = reproducible)."""
    tokenizer, model = LLM["tokenizer"], LLM["model"]
    prompt_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(prompt_text, return_tensors="pt").to(model.device)
    with torch.no_grad():
        output = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False,
                                temperature=None, top_p=None, top_k=None,
                                pad_token_id=tokenizer.eos_token_id)
    new_tokens = output[0][inputs["input_ids"].shape[1]:]
    answer = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
    return answer, prompt_text, inputs["input_ids"].shape[1], len(new_tokens)


# --- 7. Citations: which [n] did the answer use? (a simple check, not a parser) ---
def check_citations(answer, sources):
    cited = set()
    for group in re.findall(r"\[(\d+(?:\s*[,–-]\s*\d+)*)\]", answer):     # [1], [2, 3], [1-2]
        cited.update(int(n) for n in re.findall(r"\d+", group))
    # small models often write "SOURCE 2" / "Source 2" instead of [2]: count those too
    cited.update(int(n) for n in re.findall(r"\bsources?\s+(\d+)", answer, re.IGNORECASE))
    valid = sorted(n for n in cited if 1 <= n <= len(sources))
    return {
        "cited": [sources[n - 1]["label"] for n in valid],          # what the answer cites
        "invalid": sorted(cited - set(valid)),                      # numbers with no source
        "not_cited": [s["label"] for s in sources if s["n"] not in valid],
    }


# Optional post-generation verifier (ecorag_verify.py): checks each claim's citations against
# the sources. It never changes the answer. In Colab, run the ecorag_verify cell first.
if "verify_answer" not in globals():
    try:
        from ecorag_verify import verify_answer
    except ImportError:
        verify_answer = None


# --- 8. ask_ecorag(): the whole question -> answer pipeline ---
def ask_ecorag(question, top_k=TOP_K, content_types=EVIDENCE_TYPES, debug=False):
    timing = {}
    start = time.time()
    sources = retrieve(question, top_k, content_types)
    timing["retrieval_s"] = round(time.time() - start, 2)

    if debug:
        print("=" * 80)
        print(f"QUESTION: {question}")
        print("=" * 80)
        print(f"\n--- STEP 1-3: RETRIEVAL (top {top_k}, types {content_types}) ---")
        for s in sources:
            print(f"[{s['n']}] {s['chunk_id']}  similarity {s['similarity']} (distance {s['distance']})")
            print(f"    {s['document']} | {s['section']} | {s['pages']} | {s['content_type']}")
            print(f"    \"{' '.join(s['text'].split())[:300]}...\"")

    load_llm()
    messages = build_messages(question, sources)
    start = time.time()
    answer, prompt_text, prompt_tokens, answer_tokens = generate(messages)
    timing["generation_s"] = round(time.time() - start, 1)
    citations = check_citations(answer, sources)
    verification = verify_answer(answer, sources) if verify_answer else None

    if debug:
        print("\n--- STEP 4: FINAL PROMPT SENT TO THE LLM (chat template applied) ---")
        print(prompt_text)
        print(f"--- STEP 5: GENERATED ANSWER ({LLM['name']}, {answer_tokens} tokens, "
              f"{timing['generation_s']}s) ---")
        print(answer)
        print("\n--- STEP 6: CITATIONS ---")
        print("Cited:      ", citations["cited"] or "none")
        print("Not cited:  ", citations["not_cited"] or "none")
        if citations["invalid"]:
            print("INVALID (no such source):", citations["invalid"])
        if verification:
            print("\n--- STEP 7: CLAIM-BY-CLAIM VERIFICATION (deterministic, answer unchanged) ---")
            for c in verification["claims"]:
                print(f"[{c['citation_status']}] {c['claim'][:110]}")
                if c["problem"]:
                    print(f"    problem: {c['problem']}")
            print("Summary:", verification["summary"])

    return {
        "question": question,
        "answer": answer,
        "citations": citations,
        "verification": verification,        # claim-level citation check (None if verifier not loaded)
        "sources": sources,                  # exactly the evidence the LLM received
        "prompt": prompt_text,
        "model": LLM["name"],
        "prompt_version": PROMPT_VERSION,
        "prompt_tokens": prompt_tokens,
        "answer_tokens": answer_tokens,
        "timing": timing,
    }


# --- 9. Test questions ---
TEST_QUESTIONS = [
    "What share of global anthropogenic methane emissions comes from agriculture?",
    "How many alerts did the Methane Alert and Response System send, and how often do operators respond?",
    "What are the main challenges in modernising electricity grids?",
    "How can the cost of capital for clean energy projects in emerging and developing economies be reduced?",
    "How are near-zero emissions steel and cement defined?",
    # Not covered by the 9 PDFs: the right behaviour is to say the sources are insufficient
    "How many electric cars were sold in India in 2023?",
]

if __name__ == "__main__":
    results = [ask_ecorag(q, debug=True) for q in TEST_QUESTIONS]
    with open(DATA_DIR / "rag_test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nSaved all results (answers, sources, prompts) to {DATA_DIR / 'rag_test_results.json'}")
