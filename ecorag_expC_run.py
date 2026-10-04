# EcoRAG – Experiment C run (measurement only; nothing here may be changed during the run).
# Fixed: ecorag_ask.py UNCHANGED (v3 prompt, top-5 content/table retrieval, greedy, bf16, max 400 new tokens),
# Qwen2.5-3B-Instruct, the 27 frozen questions. Before EVERY question, the live top-5 is compared with the frozen
# retrieval snapshot (chunk ids and texts); any difference stops the run. Results are saved after every question.
# Usage: python ecorag_expC_run.py <model_dir>
import hashlib, io, json, os, sys, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
PROJECT = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT)
sys.path.insert(0, PROJECT)
EXP = os.path.join("ecorag_data", "expC")
RESULTS = os.path.join(EXP, "results.json")
model_dir = sys.argv[1]

src = open("ecorag_ask.py", encoding="utf-8").read()
src = "\n".join(l for l in src.splitlines() if not l.startswith("!"))      # drop the Colab pip line only
ns = {"__name__": "lib"}
exec(compile(src, "ecorag_ask.py", "exec"), ns)
assert ns["PROMPT_VERSION"] == "v3" and ns["TOP_K"] == 5 and ns["MAX_NEW_TOKENS"] == 400

questions = json.load(open(os.path.join(EXP, "questions_frozen.json"), encoding="utf-8"))["questions"]
snapshot = {q["id"]: q for q in json.load(open(os.path.join(EXP, "retrieval_snapshot.json"), encoding="utf-8"))["questions"]}
print(f"Experiment C run started {time.strftime('%Y-%m-%d %H:%M:%S')} | {len(questions)} questions | model {model_dir}")
print("ecorag_ask.py sha256:", hashlib.sha256(open("ecorag_ask.py", "rb").read()).hexdigest())
ns["load_llm"](model_dir)

results = json.load(open(RESULTS, encoding="utf-8")) if os.path.exists(RESULTS) else []
done = {r["id"] for r in results}
for q in questions:
    if q["id"] in done:
        print(f"{q['id']} already saved, skipping"); continue
    frozen = snapshot[q["id"]]["sources"]
    live = ns["retrieve"](q["question"])
    same = ([s["chunk_id"] for s in live] == [s["chunk_id"] for s in frozen] and
            [s["text"] for s in live] == [s["text"] for s in frozen])
    if not same:
        print(f"STOP: live top-5 for {q['id']} differs from the frozen snapshot")
        print("  frozen:", [s["chunk_id"] for s in frozen]); print("  live:  ", [s["chunk_id"] for s in live])
        sys.exit(2)
    result = ns["ask_ecorag"](q["question"], debug=True)
    used = [s["chunk_id"] for s in result["sources"]]
    if used != [s["chunk_id"] for s in frozen]:
        print(f"STOP: evidence given to the model for {q['id']} differs from the frozen snapshot"); sys.exit(2)
    result.update({"id": q["id"], "category": q["category"], "snapshot_match": True})
    results.append(result)
    json.dump(results, open(RESULTS, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"saved {q['id']} ({len(results)}/{len(questions)}) at {time.strftime('%H:%M:%S')}")
print(f"ALL QUESTIONS DONE {time.strftime('%Y-%m-%d %H:%M:%S')}")
