# Mechanical checks for EcoRAG answers (v1 vs v2). The final judgement is still made by reading
# each answer against its evidence; this script only gathers the facts consistently.
import json, re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
D = r"C:\Users\HP\Desktop\chakor last day\ecorag_data"

def norm(t): return " ".join(t.split()).lower()

def load_v1():
    """v1 answers: Q1-4 from the debug text output, Q5-6 from json."""
    runs = []
    txt = open(D + r"\rag_test_output.txt", encoding="utf-8").read()
    for b in txt.split("=" * 80 + "\nQUESTION: ")[1:]:
        if "STEP 5" not in b: continue
        q = b.split("\n")[0]
        prompt = b.split("--- STEP 4")[1].split("--- STEP 5")[0]
        parts = re.split(r"\[SOURCE (\d+)\]", prompt)
        sources = {int(parts[i]): parts[i + 1] for i in range(1, len(parts) - 1, 2)}
        m = re.search(r"--- STEP 5: GENERATED ANSWER \(.*?, (\d+) tokens, ([\d.]+)s\) ---\n(.*?)\n\n--- STEP 6", b, re.S)
        runs.append({"question": q, "answer": m.group(3), "sources": sources, "seconds": float(m.group(2))})
    for r in json.load(open(D + r"\rag_test_results_q5_q6.json", encoding="utf-8")):
        runs.append({"question": r["question"], "answer": r["answer"], "seconds": r["timing"]["generation_s"],
                     "sources": {s["n"]: s["text"] for s in r["sources"]}})
    return runs

def load_v2():
    runs = []
    for name in ["rag_v2_results_q1_q3.json", "rag_v2_results_q4_q6.json"]:
        try:
            for r in json.load(open(D + "\\" + name, encoding="utf-8")):
                runs.append({"question": r["question"], "answer": r["answer"], "seconds": r["timing"]["generation_s"],
                             "sources": {s["n"]: s["text"] for s in r["sources"]}})
        except FileNotFoundError:
            pass
    return runs

# Key facts a complete answer should contain (all present in the retrieved evidence)
KEY_FACTS = {
    0: {"42% / 42 per cent": r"\b42\b", "146 Mt (optional)": r"146"},
    1: {"5,000 alerts": r"5[,.]?000", "12 per cent response rate (2025)": r"\b12\s*(per ?cent|%)",
        "1 per cent in 2024 (optional)": r"\b(one|1)\s*(per ?cent|%)"},
    2: {"demand outpacing grid expansion / queues": r"keep pace|outpac|queue|expansion",
        "distributed resources / two-way flows": r"distributed|rooftop|two-way",
        "digital tools / AI": r"digital|\bai\b"},
    3: {"tripling of concessional funds": r"concessional", "policy/regulation & de-risking": r"de-risk|risk management|policy framework|regulat",
        "sector-specific risks": r"sector|off-taker|transmission", "1 pp -> USD 150 bn": r"150 billion"},
    4: {"steel threshold 400-50 kg CO2-eq/t": r"400", "cement threshold 125-40 kg CO2-eq/t": r"125",
        "depends on scrap share / clinker ratio": r"scrap|clinker"},
    5: {"abstains": r"do not contain enough information|not contain enough|no information|cannot be answered"},
}

def citations_in(sentence):
    nums = set()
    for g in re.findall(r"\[(\d+(?:\s*[,–-]\s*\d+)*)\]", sentence):
        nums.update(int(n) for n in re.findall(r"\d+", g))
    nums.update(int(n) for n in re.findall(r"\bsources?\s+(\d+)", sentence, re.I))
    return nums

def numbers_in(sentence):
    s = re.sub(r"\[\d+(?:\s*[,–-]\s*\d+)*\]", "", sentence)          # drop citation markers
    s = re.sub(r"\bsources?\s+\d+", "", s, flags=re.I)
    return set(re.findall(r"\d[\d,.]*\d|\d", s))

def evaluate(run, qi):
    ans, sources = run["answer"], run["sources"]
    print(f"   runtime {run['seconds']:.0f}s | {len(ans.split())} words")
    for name, pat in KEY_FACTS[qi].items():
        print(f"   key fact {'YES' if re.search(pat, ans, re.I) else 'no ':3}  {name}")
    all_cited = citations_in(ans)
    print(f"   citations used: {sorted(all_cited) or 'NONE'}"
          f"{'  (written as SOURCE n)' if re.search(r'source\s+\d', ans, re.I) else ''}")
    # per-sentence number check: is each number in the cited source, another source, or none?
    for sent in re.split(r"(?<=[.!?])\s+|\n+", ans):
        nums, cited = numbers_in(sent), citations_in(sent)
        for num in sorted(nums):
            if num in {"1", "2", "3", "4", "5"} and len(nums) == 1 and not re.search(r"\d\s*(%|per)", sent):
                continue
            found = [n for n, t in sources.items() if num.lower() in norm(t)]
            status = ("in cited source" if cited & set(found) else
                      "UNCITED" if not cited and found else
                      f"WRONG SOURCE (cited {sorted(cited)}, found in {found})" if found else
                      "NOT IN ANY SOURCE")
            print(f"      number {num!r:12} -> {status}")

if __name__ == "__main__":
    v1, v2 = load_v1(), load_v2()
    for qi in range(6):
        q = v1[qi]["question"]
        print("\n" + "=" * 90 + f"\nQ{qi+1}: {q}")
        for label, runs in (("v1 (old prompt)", v1), ("v2 (fixed prompt)", v2)):
            run = next((r for r in runs if r["question"] == q), None)
            print(f"\n  {label}:")
            if run is None:
                print("   (not run yet)"); continue
            print("   ANSWER: " + run["answer"].replace("\n", "\n           "))
            evaluate(run, qi)
