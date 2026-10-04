# Side-by-side comparison of EcoRAG runs, rebuilt from the RAW answer files.
# 1. Re-runs the (unchanged) verifier in memory on rag_<run>_results_*.json and checks that it reproduces the
#    stored rag_<run>_citation_verification.json exactly (claim statuses and totals).
# 2. Prints one table, with each metric family in its own section, verifier and manual review kept separate.
# Usage: python ecorag_compare_runs.py v2 v3 v3-3b        (also saved to ecorag_data/rag_comparison_table.txt)
import json, re, sys, importlib.util
from pathlib import Path

DATA = Path("ecorag_data")
RUNS = sys.argv[1:] or ["v2", "v3", "v3-3b"]
MAX_NEW_TOKENS, MAX_LINES = 400, 8

# Same key-fact checklist as every earlier evaluation (importing it also sets up UTF-8 printing)
spec = importlib.util.spec_from_file_location("ev", "ecorag_eval_rag.py")
ev = importlib.util.module_from_spec(spec); spec.loader.exec_module(ev)
sys.path.insert(0, ".")
from ecorag_verify import verify_answer

manual = json.loads((DATA / "rag_manual_review.json").read_text(encoding="utf-8"))["summary"]

def load_raw(run):
    raw = []
    for part in ("q1_q3", "q4_q6"):
        raw += json.loads((DATA / f"rag_{run}_results_{part}.json").read_text(encoding="utf-8"))
    return raw

def pct(a, b):
    return f"{a}/{b} ({a / b:.0%})" if b else "0/0"

table, checks = {}, []
for run in RUNS:
    raw = load_raw(run)
    stored = json.loads((DATA / f"rag_{run}_citation_verification.json").read_text(encoding="utf-8"))
    fresh = [verify_answer(r["answer"], r["sources"]) for r in raw]
    same = all(f["summary"] == s["summary"] and
               [c["citation_status"] for c in f["claims"]] == [c["citation_status"] for c in s["claims"]] and
               r["answer"] == s["answer"]
               for f, s, r in zip(fresh, stored["results"], raw))
    checks.append(f"{run}: verifier re-run on raw answers reproduces the stored verification file: {'YES' if same else 'NO'}")

    per = [f["summary"] for f in fresh]
    def total(key, idx=range(6)):
        return sum(per[i][key] for i in idx)
    no_q3 = [0, 1, 3, 4, 5]
    complete, lines_over, truncated = 0, 0, 0
    for qi, r in enumerate(raw):
        if qi < 5:
            facts = {k: p for k, p in ev.KEY_FACTS[qi].items() if "optional" not in k}
            complete += all(re.search(p, r["answer"], re.I) for p in facts.values())
        lines_over += sum(l.strip().startswith("-") for l in r["answer"].splitlines()) > MAX_LINES
        truncated += r.get("answer_tokens", 0) >= MAX_NEW_TOKENS
    m_all, m_noq3 = manual[run]["overall"], manual[run]["excluding_q3"]
    table[run] = {
        "model": raw[0]["model"].replace("\\", "/").split("/")[-1].replace("Qwen2.5-", "").replace("-Instruct", ""),
        "prompt": raw[0].get("prompt_version", "?"),
        # citation coverage
        "factual claims": total("factual_claims"),
        "claims with a citation": pct(total("with_citation"), total("factual_claims")),
        "uncited, a source matches": total("uncited_but_matching_source"),
        "uncited, matching no source": total("uncited_and_unmatched"),
        # citation correctness: verifier
        "V: potentially supported": total("supported"),
        "V: partially supported": total("partially_supported"),
        "V: misattributed": total("misattributed"),
        "V: misattributed / cited": pct(total("misattributed"), total("with_citation")),
        "V: ... excluding Q3": pct(total("misattributed", no_q3), total("with_citation", no_q3)),
        # citation correctness: manual review
        "M: supported": m_all["manual_supported"],
        "M: supported, minor distortion": m_all["manual_supported_minor_distortion"],
        "M: partially supported": m_all["manual_partially_supported"],
        "M: misattributed": m_all["manual_misattributed"],
        "M: misattributed / cited": pct(m_all["manual_misattributed"], m_all["cited_claims"]),
        "M: ... excluding Q3": pct(m_noq3["manual_misattributed"], m_noq3["cited_claims"]),
        # factual accuracy & completeness
        "Q1-Q5 with complete key facts": f"{complete}/5",
        "claims with date/scope mismatch": total("date_scope_mismatches"),
        # abstention
        "Q6 abstained (out of scope)": "yes" if per[5]["abstained"] else "NO",
        # format compliance
        "non-standard citation format": total("non_standard_citation_format"),
        f"answers over {MAX_LINES} lines": lines_over,
        f"answers cut off at {MAX_NEW_TOKENS} tokens": truncated,
    }

SECTIONS = [
    ("RUN", ["model", "prompt"]),
    ("CITATION COVERAGE (is a citation present?)",
     ["factual claims", "claims with a citation", "uncited, a source matches", "uncited, matching no source"]),
    ("CITATION CORRECTNESS - VERIFIER (V, unchanged; 'supported' = word/number match only)",
     ["V: potentially supported", "V: partially supported", "V: misattributed", "V: misattributed / cited", "V: ... excluding Q3"]),
    ("CITATION CORRECTNESS - MANUAL REVIEW (M, every cited claim; see rag_manual_review.json)",
     ["M: supported", "M: supported, minor distortion", "M: partially supported", "M: misattributed",
      "M: misattributed / cited", "M: ... excluding Q3"]),
    ("FACTUAL ACCURACY & KEY-FACT COMPLETENESS", ["Q1-Q5 with complete key facts", "claims with date/scope mismatch"]),
    ("ABSTENTION", ["Q6 abstained (out of scope)"]),
    ("FORMAT COMPLIANCE", ["non-standard citation format", f"answers over {MAX_LINES} lines", f"answers cut off at {MAX_NEW_TOKENS} tokens"]),
]
width = max(len(k) for _, keys in SECTIONS for k in keys) + 2
col = max(14, max(len(str(v)) for r in table.values() for v in r.values()) + 3)
lines = []
for title, keys in SECTIONS:
    lines.append("")
    lines.append(title if title != "RUN" else f"{'':{width}}" + "".join(f"{run:>{col}}" for run in RUNS))
    for k in keys:
        lines.append(f"  {k:{width - 2}}" + "".join(f"{str(table[run][k]):>{col}}" for run in RUNS))
lines += ["", "EVIDENCE SUFFICIENCY (does the retrieved evidence collectively justify the answer?)",
          "  not measured in these runs - Experiment C", ""] + checks
report = "\n".join(lines)
print(report)
(DATA / "rag_comparison_table.txt").write_text(report + "\n", encoding="utf-8")
