# EcoRAG – documented manual review of every CITED claim in runs v2, v3 (1.5B) and v3-3b (3B).
# The verifier output is NOT changed. This file records a human decision per claim, plus a distinctive phrase
# that is searched in all 5 sources, so each decision can be re-checked against the evidence.
# Scope: claims that carry a citation (citation correctness). Uncited claims are counted by the verifier only.
# Output: ecorag_data/rag_manual_review.json
import json, re, sys, io
from collections import Counter
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
DATA = Path("ecorag_data")

# Manual statuses:
#   supported                   the cited source states the claim
#   supported_minor_distortion  the cited source holds the content, but the claim slightly changes its meaning
#   partially_supported         the cited source supports part of the claim
#   misattributed               the claim's content comes from a different source than the one cited
#   abstention                  not a factual claim (a correct "not enough information" line)
# (run, question number, claim_id, manual status, phrase located in the sources, note)
DECISIONS = [
    ("v2", 1, 1, "misattributed", "146 Mt", "146 Mt only in [2]; 42% in [2][4][5]; cited 'SOURCE [1]'"),
    ("v2", 3, 3, "supported_minor_distortion", "lengthening connection queues",
     "queues/service disruption are in [2]; 'competition among different types of energy sources' distorts "
     "'housing and industrial development competing with data centres and generation projects for scarce grid capacity'"),
    ("v2", 3, 8, "supported", "transformer loading", ""),

    ("v3", 1, 1, "misattributed", "with livestock and rice cultivation as the primary drivers",
     "sentence is verbatim from [5]; 42% also in [2][4]; cited [1]"),
    ("v3", 2, 1, "misattributed", "5,000 alerts", "5,000 in [1][3], 33 countries only in [3]; cited [2]; "
     "also says 'in 2025' where the source says 'By February 2026'"),
    ("v3", 2, 2, "misattributed", "12 per cent", "12% in [1][3]; cited [2]; 'of the alerts received' changes the scope"),
    ("v3", 3, 1, "misattributed", "lengthening connection queues", "queues / scarce capacity / service disruption are in [2]; cited [1]"),
    ("v3", 3, 2, "partially_supported", "within the thermal limits", "paraphrase of [2]; acceptable but loose"),
    ("v3", 3, 3, "supported", "inverter-based", ""),
    ("v3", 3, 4, "supported_minor_distortion", "unidirectional",
     "[3] says rooftop solar, batteries, EVs and flexible demand create two-way flows; data centres are a separate "
     "point (concentrated demand)"),
    ("v3", 4, 1, "misattributed", "energy-sector-specific interventions", "verbatim from [1]; cited [3]"),
    ("v3", 4, 2, "supported", "USD 150 billion", ""),
    ("v3", 4, 3, "supported", "USD 300 billion", ""),
    ("v3", 4, 4, "supported", "huge opportunity", "verbatim from [1]"),
    ("v3", 5, 3, "misattributed", "consistent signal across global markets", "verbatim from [1]; cited [3]"),
    ("v3", 5, 5, "supported", "one full tonne", "in [1]; [3] is cited as well but does not contain it (over-citation)"),
    ("v3", 6, 1, "misattributed", "Green Hydrogen Mission",
     "content from the policy table in [5], cited [4]; does not answer the question - should have abstained"),

    ("v3-3b", 1, 1, "misattributed", "almost 42 per cent in 2020",
     "verbatim from [5]; [4] states only '42 per cent' (no 'almost', no 2020) - a near miss"),
    ("v3-3b", 2, 1, "misattributed", "5,000 alerts", "5,000 in [1][3]; cited [2]; date now correct ('by February 2026')"),
    ("v3-3b", 2, 2, "misattributed", "12 per cent in 2025", "in [1][3]; cited [2]; wording now exact"),
    ("v3-3b", 3, 1, "supported", "lengthening connection queues", ""),
    ("v3-3b", 3, 2, "supported", "competing with data centres", ""),
    ("v3-3b", 3, 3, "supported", "service disruption", ""),
    ("v3-3b", 3, 4, "supported", "displace synchronous generators", ""),
    ("v3-3b", 3, 5, "supported", "fault current contribution", ""),
    ("v3-3b", 3, 6, "supported", "faster-moving and harder to observe", ""),
    ("v3-3b", 3, 7, "supported", "AI-based", ""),
    ("v3-3b", 3, 8, "supported", "rooftop solar", ""),
    ("v3-3b", 3, 9, "supported", "more concentrated form of generation and demand", ""),
    ("v3-3b", 3, 10, "supported", "feeder capacity", ""),
    ("v3-3b", 3, 11, "supported", "unidirectional systems", ""),
    ("v3-3b", 3, 12, "supported", "protection settings", "near-duplicate of claim 10"),
    ("v3-3b", 3, 13, "supported", "harder to observe and model than thermal limits", ""),
    ("v3-3b", 3, 14, "supported", "at the distribution level as much as at the transmission level", ""),
    ("v3-3b", 3, 15, "misattributed", "instantaneous disturbances", "only in the table in [5]; cited [2]"),
    ("v3-3b", 3, 16, "misattributed", "Evolving real-time conditions", "only in the table in [5]; cited [2]"),
    ("v3-3b", 3, 17, "supported", "connection studies", ""),
    ("v3-3b", 3, 18, "supported", "unplanned outages", ""),
    ("v3-3b", 4, 1, "supported", "USD 150 billion", ""),
    ("v3-3b", 4, 2, "supported", "USD 300 billion", ""),
    ("v3-3b", 4, 3, "supported", "different business models", ""),
    ("v3-3b", 4, 4, "supported", "dig into the features", ""),
    ("v3-3b", 4, 5, "supported", "extend well beyond the energy sector", ""),
    ("v3-3b", 4, 6, "supported", "tripling in international concessional funds", ""),
    ("v3-3b", 4, 7, "misattributed", "costs paid by consumers",
     "VERIFIER MISSED: verbatim from [5]; [1] only shares topic words (80% word coverage)"),
    ("v3-3b", 4, 8, "misattributed", "de-risking instruments", "verbatim from [5]; cited [1]"),
    ("v3-3b", 5, 1, "supported", "400-50 kg", ""),
    ("v3-3b", 5, 2, "supported", "125-40 kg", ""),
    ("v3-3b", 6, 1, "abstention", "electric", "correct abstention, but the line carries an unnecessary citation [5]"),
]

def norm(text):
    return " ".join(text.split()).lower()

records, problems = [], []
for run in ["v2", "v3", "v3-3b"]:
    verification = json.loads((DATA / f"rag_{run}_citation_verification.json").read_text(encoding="utf-8"))
    raw = {}
    for part in ("q1_q3", "q4_q6"):
        for r in json.loads((DATA / f"rag_{run}_results_{part}.json").read_text(encoding="utf-8")):
            raw[r["question"]] = r
    cited_ids = {(qi + 1, c["claim_id"]) for qi, res in enumerate(verification["results"])
                 for c in res["claims"] if c["citations"]}
    decided = {(q, cid) for r, q, cid, *_ in DECISIONS if r == run}
    if cited_ids != decided:
        problems.append(f"{run}: cited claims without a decision {sorted(cited_ids - decided)}, "
                        f"decisions without a cited claim {sorted(decided - cited_ids)}")
    for r, q, cid, status, phrase, note in DECISIONS:
        if r != run:
            continue
        res = verification["results"][q - 1]
        claim = next(c for c in res["claims"] if c["claim_id"] == cid)
        sources = raw[res["question"]]["sources"]
        found_in = [s["n"] for s in sources if norm(phrase) in norm(s["text"])]
        if status != "abstention" and not found_in:
            problems.append(f"{run} Q{q} c{cid}: phrase {phrase!r} not found in any source")
        records.append({"run": run, "question": q, "claim_id": cid, "claim": claim["claim"],
                        "cited": claim["citations"], "verifier_status": claim["citation_status"],
                        "manual_status": status, "evidence_phrase": phrase, "phrase_found_in": found_in,
                        "verifier_agrees": (claim["citation_status"] == "partially_supported" and status == "partially_supported")
                                           or (claim["citation_status"] == "supported" and status.startswith("supported"))
                                           or claim["citation_status"] == status,
                        "note": note})

def rates(run, exclude_q3=False):
    rs = [r for r in records if r["run"] == run and r["manual_status"] != "abstention"
          and not (exclude_q3 and r["question"] == 3)]
    m = Counter(r["manual_status"] for r in rs)
    v = Counter(r["verifier_status"] for r in rs)
    return {"cited_claims": len(rs),
            "verifier_misattributed": v["misattributed"], "manual_misattributed": m["misattributed"],
            "manual_supported": m["supported"], "manual_supported_minor_distortion": m["supported_minor_distortion"],
            "manual_partially_supported": m["partially_supported"],
            "verifier_misattribution_rate": round(v["misattributed"] / max(len(rs), 1), 3),
            "manual_misattribution_rate": round(m["misattributed"] / max(len(rs), 1), 3)}

summary = {run: {"overall": rates(run), "excluding_q3": rates(run, True),
                 "verifier_disagreements": [f"Q{r['question']} c{r['claim_id']}: verifier {r['verifier_status']} -> manual {r['manual_status']}"
                                            for r in records if r["run"] == run and not r["verifier_agrees"]]}
           for run in ["v2", "v3", "v3-3b"]}
(DATA / "rag_manual_review.json").write_text(json.dumps(
    {"scope": "every cited claim in runs v2, v3 (1.5B) and v3-3b (3B); verifier output unchanged",
     "statuses": ["supported", "supported_minor_distortion", "partially_supported", "misattributed", "abstention"],
     "summary": summary, "problems": problems, "claims": records}, ensure_ascii=False, indent=2), encoding="utf-8")

print("problems:", problems or "none")
for run, s in summary.items():
    for k in ("overall", "excluding_q3"):
        x = s[k]
        print(f"{run:6} {k:13} cited {x['cited_claims']:>2} | misattributed: verifier {x['verifier_misattributed']} "
              f"({x['verifier_misattribution_rate']:.0%}) -> manual {x['manual_misattributed']} ({x['manual_misattribution_rate']:.0%}) | "
              f"manual supported {x['manual_supported']} + minor distortion {x['manual_supported_minor_distortion']} "
              f"+ partial {x['manual_partially_supported']}")
    print(f"       verifier disagreements: {s['verifier_disagreements'] or 'none'}")
print("saved ecorag_data/rag_manual_review.json")
