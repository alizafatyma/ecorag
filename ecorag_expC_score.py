# EcoRAG – Experiment C scoring. Applies the frozen rubric/metric spec to results.json + gold.json + manual_review.json.
# Reads only; writes ecorag_data/expC/scores.json and report.txt. Every aggregate is printed as numerator/denominator.
# Primary analysis = FROZEN gold. Sensitivity analysis = gold_erratum.json overlay (Q10, Q18, Q22), reported separately.
import copy, json, re, sys, io
from collections import Counter
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, ".")
from ecorag_verify import verify_answer

EXP = Path("ecorag_data/expC")
results = {r["id"]: r for r in json.loads((EXP / "results.json").read_text(encoding="utf-8"))}
GOLD = {g["id"]: g for g in json.loads((EXP / "gold.json").read_text(encoding="utf-8"))["questions"]}
MR = json.loads((EXP / "manual_review.json").read_text(encoding="utf-8"))
MQ, MCLAIMS = MR["questions"], MR["claims"]
ERR = json.loads((EXP / "gold_erratum.json").read_text(encoding="utf-8"))
IDS = sorted(results)
VER = {q: verify_answer(results[q]["answer"], results[q]["sources"]) for q in IDS}
OUTLIERS = [q for q in IDS if sum(l.strip().startswith("-") for l in results[q]["answer"].splitlines()) > 8
            or results[q]["answer_tokens"] >= 400]
SCORE = {"justified": 1, "partial": 0.5, "not": 0}
EXPECTED = {"sufficient": "FULL", "partial": "PARTIAL+GAP", "insufficient": "ABSTAIN"}

def frac(a, b): return f"{a}/{b} = {a / b:.0%}" if b else f"{a}/0 = n/a"
def mean(xs): return f"{sum(xs):.2f}/{len(xs)} = {sum(xs) / len(xs):.2f}" if xs else "n/a"

def sensitivity_gold_and_manual():
    """Overlay the erratum: corrected unit statuses -> recomputed sufficiency; rubric rules re-applied to the
    gold-dependent fields (S3b 'insufficient' rule, taxonomy priority) for Q10, Q18, Q22 only."""
    gold, mq = copy.deepcopy(GOLD), copy.deepcopy(MQ)
    for c in ERR["corrections"]:
        g = gold[c["qid"]]
        for u in g["units"]:
            if u["id"] == c["unit"]: u["status"] = c["corrected_status"]
        g["retrieval_sufficiency"] = c["corrected_sufficiency"]
        mq[c["qid"]]["units"][c["unit"]]["failure"] = "correct"          # stated correctly with a supporting citation
    mq["Q10"]["S3b"] = "justified"     # claim supported by top-5 [1]
    mq["Q18"]["S3b"] = "partial"       # 0.029% supported; salary substituted (O2)
    mq["Q22"]["S3b"] = "justified"     # 8.5 million in top-5 [1]
    return gold, mq

def evaluate(qs, gold, mq):
    o = {}
    # ---- S1
    lab = Counter(gold[q]["retrieval_sufficiency"] for q in qs)
    req = [u for q in qs for u in gold[q]["units"] if u["required"]]
    exist = [u for u in req if u["status"] in ("top5", "corpus")]
    o["S1 labels (suff/partial/insuff)"] = f"{lab['sufficient']}/{lab['partial']}/{lab['insufficient']} of {len(qs)}"
    o["S1 share sufficient"] = frac(lab["sufficient"], len(qs))
    o["S1 unit retrieval recall"] = frac(sum(u["status"] == "top5" for u in exist), len(exist))
    # ---- S2
    gn = gd = en = ed = 0; pg, pe = [], []
    for q in qs:
        units = [u for u in gold[q]["units"] if u["required"]]
        cov = [u for u in units if mq[q]["units"][u["id"]]["covered"]]
        t5 = [u for u in units if u["status"] == "top5"]
        ct5 = sum(mq[q]["units"][u["id"]]["covered"] for u in t5)
        gn += ct5; gd += len(t5); en += len(cov); ed += len(units)
        if t5: pg.append(ct5 / len(t5))
        pe.append(len(cov) / len(units))
    o["S2-gen pooled"] = frac(gn, gd); o["S2-gen per-question avg"] = mean(pg)
    o["S2-e2e pooled"] = frac(en, ed); o["S2-e2e per-question avg"] = mean(pe)
    # ---- S3
    for k in ("S3a", "S3b"):
        labs = [mq[q][k] for q in qs if mq[q][k] != "n/a"]
        c = Counter(labs)
        o[f"{k} justified/partial/not (n answering)"] = f"{c['justified']}/{c['partial']}/{c['not']} (n={len(labs)})"
        o[f"{k} mean score"] = mean([SCORE[l] for l in labs])
    # ---- S4
    ok = [q for q in qs if mq[q]["behaviour"] == EXPECTED[gold[q]["retrieval_sufficiency"]]]
    ins = [q for q in qs if gold[q]["retrieval_sufficiency"] == "insufficient"]
    suf = [q for q in qs if gold[q]["retrieval_sufficiency"] == "sufficient"]
    par = [q for q in qs if gold[q]["retrieval_sufficiency"] == "partial"]
    o["S4 calibration accuracy"] = frac(len(ok), len(qs))
    o["S4 correct | sufficient (FULL)"] = frac(sum(mq[q]["behaviour"] == "FULL" for q in suf), len(suf))
    o["S4 correct | partial (PARTIAL+GAP)"] = frac(sum(mq[q]["behaviour"] == "PARTIAL+GAP" for q in par), len(par))
    o["S4 abstention recall | insufficient"] = frac(sum(mq[q]["behaviour"] == "ABSTAIN" for q in ins), len(ins))
    o["S4 false abstention | sufficient"] = frac(sum(mq[q]["behaviour"] == "ABSTAIN" for q in suf), len(suf))
    o["S4 matrix"] = dict(Counter(f"{gold[q]['retrieval_sufficiency']}->{mq[q]['behaviour']}" for q in qs))
    # ---- S5
    over = [x for q in qs for x in mq[q]["overreach"]]
    fact = sum(mq[q]["manual_factual_claims"] for q in qs)
    ans = [q for q in qs if mq[q]["behaviour"] != "ABSTAIN"]
    o["S5 over-reach claims / factual claims"] = frac(len(over), fact)
    o["S5 answering questions with >=1 over-reach"] = frac(sum(bool(mq[q]["overreach"]) for q in ans), len(ans))
    o["S5 by type"] = dict(Counter(x["type"] for x in over))
    # ---- S6
    s6 = [mq[q]["units"][u]["s6"] for q in qs for u in mq[q]["units"] if mq[q]["units"][u]["s6"] is not None]
    o["S6 covered units with a supporting cited chunk"] = frac(sum(x["cited_chunks"] > 0 for x in s6), len(s6))
    o["S6 mean distinct origins per covered unit"] = mean([x["distinct_origins"] for x in s6])
    o["S6 dependent multi-citations"] = sum(x["cited_chunks"] >= 2 and x["distinct_origins"] == 1 for x in s6)
    o["S6 false corroborations"] = sum(x["false_corroboration"] for x in s6)
    # ---- failure taxonomy (per required unit)
    f = Counter(mq[q]["units"][u["id"]]["failure"] for q in qs for u in gold[q]["units"] if u["required"])
    tot = sum(f.values())
    for k in ("retrieval", "calibration", "generation", "citation", "correct"):
        o[f"taxonomy {k}"] = frac(f[k], tot)
    # ---- citation correctness (separate dimension)
    vt = Counter()
    for q in qs: vt.update({k: v for k, v in VER[q]["summary"].items() if not isinstance(v, bool)})
    o["CIT verifier: cited / factual claims"] = frac(vt["with_citation"], vt["factual_claims"])
    o["CIT verifier: misattributed / cited"] = frac(vt["misattributed"], vt["with_citation"])
    o["CIT verifier: potentially supported / cited"] = frac(vt["supported"], vt["with_citation"])
    mc = [c for c in MCLAIMS if c["qid"] in qs]
    m = Counter(c["manual_status"] for c in mc)
    o["CIT manual: cited claims"] = len(mc)
    o["CIT manual: supported (incl. minor distortion) / cited"] = frac(m["supported"] + m["supported_minor_distortion"], len(mc))
    o["CIT manual: misattributed / cited"] = frac(m["misattributed"], len(mc))
    o["CIT manual: unsupported / cited"] = frac(m["unsupported"], len(mc))
    o["CIT manual: partially supported / cited"] = frac(m["partially_supported"], len(mc))
    o["CIT manual: incorrect (misattributed+unsupported) / cited"] = frac(m["misattributed"] + m["unsupported"], len(mc))
    per = [sum(c["manual_status"] in ("misattributed", "unsupported") for c in mc if c["qid"] == q) /
           sum(c["qid"] == q for c in mc) for q in qs if any(c["qid"] == q for c in mc)]
    o["CIT manual: incorrect rate, per-question avg"] = mean(per)
    # ---- descriptive (NOT pre-registered): overall answer correctness ignoring citations
    good = [q for q in qs if mq[q]["behaviour"] == EXPECTED[gold[q]["retrieval_sufficiency"]] and not mq[q]["overreach"]
            and all(mq[q]["units"][u["id"]]["covered"] for u in gold[q]["units"] if u["required"] and u["status"] == "top5")
            and mq[q]["S3b"] in ("justified", "n/a")]
    good_cit = [q for q in good if all(c["manual_status"] in ("supported", "supported_minor_distortion")
                                       for c in mc if c["qid"] == q)]
    o["DESC answer content fully correct (S4 ok, S3b ok, no over-reach, all top-5 units covered)"] = frac(len(good), len(qs))
    o["DESC ... and every citation correct"] = frac(len(good_cit), len(qs))
    o["_good"] = good; o["_good_cit"] = good_cit
    return o

def views(gold, mq):
    v = {"POOLED (27)": IDS,
         f"EXCLUDING LENGTH OUTLIERS {OUTLIERS} (secondary)": [q for q in IDS if q not in OUTLIERS]}
    for lab in ("sufficient", "partial", "insufficient"):
        v[f"GOLD = {lab}"] = [q for q in IDS if gold[q]["retrieval_sufficiency"] == lab]
    for cat, name in (("a", "single chunk"), ("b", "multi-chunk"), ("c", "partially answerable"), ("d", "unanswerable"), ("e", "dependent-source")):
        v[f"TYPE {cat} ({name})"] = [q for q in IDS if gold[q]["category"] == cat]
    v["CONTINUITY Q01-Q06"] = ["Q01", "Q02", "Q03", "Q04", "Q05", "Q06"]
    return {k: (qs, evaluate(qs, gold, mq)) for k, qs in v.items()}

primary = views(GOLD, MQ)
sgold, smq = sensitivity_gold_and_manual()
sens = {"POOLED (27) - erratum labels": (IDS, evaluate(IDS, sgold, smq))}

# Experiment B (same 6 answers) from its own files
b_manual = json.loads(Path("ecorag_data/rag_manual_review.json").read_text(encoding="utf-8"))["summary"]["v3-3b"]["overall"]
b_ver = json.loads(Path("ecorag_data/rag_v3-3b_citation_verification.json").read_text(encoding="utf-8"))["totals"]

lines = [f"EcoRAG Experiment C - scores (frozen gold = primary). Outliers (pre-registered rule): {OUTLIERS}", ""]
for name, (qs, o) in list(primary.items()) + list(sens.items()):
    lines.append("=" * 100); lines.append(f"{name}  [{', '.join(qs)}]")
    for k, val in o.items():
        if not k.startswith("_"): lines.append(f"   {k:<72} {val}")
c = primary["CONTINUITY Q01-Q06"][1]
lines += ["", "=" * 100, "EXPERIMENT B vs C (same 6 answers, byte-identical)",
          f"   B verifier: cited/factual {b_ver['with_citation']}/{b_ver['factual_claims']}, misattributed/cited {b_ver['misattributed']}/{b_ver['with_citation']}",
          f"   C verifier: {c['CIT verifier: cited / factual claims']}, misattributed/cited {c['CIT verifier: misattributed / cited']}",
          f"   B manual: misattributed/cited {b_manual['manual_misattributed']}/{b_manual['cited_claims']}",
          f"   C manual: misattributed/cited {c['CIT manual: misattributed / cited']}"]
report = "\n".join(lines)
(EXP / "report.txt").write_text(report + "\n", encoding="utf-8")
(EXP / "scores.json").write_text(json.dumps({"outliers": OUTLIERS, "primary": {k: v[1] for k, v in primary.items()},
                                             "sensitivity": {k: v[1] for k, v in sens.items()}}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
print(report)
