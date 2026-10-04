# EcoRAG – Experiment C manual review (single reviewer: Claude), written AFTER the run from saved files only.
# Reads results.json / gold.json / retrieval_snapshot.json (never modified). Writes ecorag_data/expC/manual_review.json.
#
# Scoring decisions taken at the manual-review stage (user-approved; frozen rubric not altered):
#   A1  extra citation status "unsupported": the cited source does not support the claim (meaning-changing claim using a
#       related figure, or claimed information absent from the cited source and not supportable from it).
#   A2  bare-value lines are factual claims for the manual analysis and the S5 denominator:
#       Q08 c1 "12% [1]", Q08 c2 "40% [1]", Q22 c1 "8500000 [1]", Q14 c2 "These actions are to be delivered by 2030 [1]".
#       The verifier's own classification is left unchanged.
# Applied literally (flagged earlier): Q12 unit coverage is binary; Q10/Q18/Q22 scored on the FROZEN gold.
import json, re, sys, io
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, ".")
from ecorag_verify import verify_answer
EXP = Path("ecorag_data/expC")

# claim statuses: S supported, D supported_minor_distortion, P partially_supported, M misattributed, U unsupported
STATUS = {"S": "supported", "D": "supported_minor_distortion", "P": "partially_supported", "M": "misattributed", "U": "unsupported"}
A2_LINES = {("Q08", 1), ("Q08", 2), ("Q22", 1), ("Q14", 2)}

# Per question: cited-claim statuses {claim_id: (code, evidence note)}, covered units, S3a, S3b, behaviour,
# over-reach [(claim_id, type, note)], S6 {unit: cited chunks containing it}, failures {unit: category}, note.
R = {
 "Q01": dict(claims={1: ("M", "sentence verbatim from [5] ('almost 42 per cent in 2020'); cited [4] says only '42 per cent', no 2020 (= Exp B)")},
             covered=["U1", "U2"], S3a="partial", S3b="justified", behaviour="FULL", overreach=[],
             s6={"U1": 1, "U2": 1}, failures={"U1": "correct", "U2": "correct"},
             note="Unit facts (largest source, 42%) are in cited [4]; the claim's 'almost ... in 2020' is only in [5]."),
 "Q02": dict(claims={1: ("M", "5,000 only in [1][3]; cited [2]"), 2: ("M", "12 per cent only in [1][3]; cited [2]")},
             covered=["U1", "U2"], S3a="not", S3b="justified", behaviour="FULL", overreach=[],
             s6={"U1": 0, "U2": 0}, failures={"U1": "citation", "U2": "citation"},
             note="Figures and dates exact ('by February 2026', '12 per cent in 2025'); cited [2] contains neither."),
 "Q03": dict(claims={**{i: ("S", "Exp B manual review: verbatim/close to cited source") for i in (1,2,3,4,5,6,7,8,9,10,11,12,13,14,17,18)},
                     15: ("M", "'evolving real-time conditions' only in table [5]; cited [2]"),
                     16: ("M", "'instantaneous disturbances' only in table [5]; cited [2]")},
             covered=["U1", "U2", "U3"], S3a="partial", S3b="justified", behaviour="FULL", overreach=[],
             s6={"U1": 1, "U2": 1, "U3": 1}, failures={"U1": "correct", "U2": "correct", "U3": "correct"},
             note="Queues and stability in cited [2]; two-way flows in cited [3]; c15-c16 misattributed; c19 truncated, uncited."),
 "Q04": dict(claims={1: ("S", "USD 150 bn in [1]"), 2: ("S", "USD 300 bn in [1]"), 3: ("S", "'different business models' [2]"),
                     4: ("S", "'dig into the features' [2]"), 5: ("S", "'extend well beyond the energy sector' [3]"),
                     6: ("S", "'tripling in international concessional funds' [5]"),
                     7: ("M", "'costs paid by consumers' verbatim from [5]; cited [1] (verifier missed)"),
                     8: ("M", "'de-risking instruments' verbatim from [5]; cited [1]")},
             covered=["U1", "U2", "U3"], S3a="partial", S3b="justified", behaviour="FULL", overreach=[],
             s6={"U1": 1, "U2": 0, "U3": 1}, failures={"U1": "correct", "U2": "citation", "U3": "correct"},
             note="U2 (policy/de-risking) stated but cited [1]; the text is in [5]."),
 "Q05": dict(claims={1: ("S", "400-50 kg in [4], values in [3]"), 2: ("S", "125-40 kg in [4], values in [3]")},
             covered=["U1", "U2"], S3a="justified", S3b="justified", behaviour="FULL", overreach=[],
             s6={"U1": 2, "U2": 2}, failures={"U1": "correct", "U2": "correct"},
             note="Both thresholds exact; [3][4] are the same report (dependent multi-citation)."),
 "Q06": dict(claims={}, covered=[], S3a="n/a", S3b="n/a", behaviour="ABSTAIN", overreach=[], s6={},
             failures={"U1": "correct"}, note="Correct abstention; abstention line carries [5] (format)."),
 "Q07": dict(claims={1: ("S", "330 GW in [1]; [2] over-cited"), 2: ("S", "USD 100 billion in [1]")},
             covered=["U1", "U2"], S3a="justified", S3b="justified", behaviour="FULL", overreach=[],
             s6={"U1": 1, "U2": 1}, failures={"U1": "correct", "U2": "correct"}, note="Fully answered from [1]."),
 "Q08": dict(claims={1: ("S", "A2 bare value: '12% of global electricity supply in 2023' [1]"), 2: ("S", "A2 bare value: 'rise to 40% by 2030' [1]")},
             covered=["U1", "U2"], S3a="justified", S3b="justified", behaviour="FULL", overreach=[],
             s6={"U1": 1, "U2": 1}, failures={"U1": "correct", "U2": "correct"}, note="Bare values in question order; both in [1]."),
 "Q09": dict(claims={1: ("S", "'(IEA, 2024a)' in [2]"), 2: ("S", "six chains in [2]")},
             covered=["U1"], S3a="justified", S3b="justified", behaviour="FULL", overreach=[],
             s6={"U1": 1}, failures={"U1": "correct"}, note="Six supply chains listed exactly."),
 "Q10": dict(claims={1: ("S", "Bay Area cluster in [1]"), 2: ("S", "'11.1% of the country's solar online job postings' [1]"),
                     3: ("S", "'almost onefourth of the US online solar vacancies between 2019 and 2024' [1]")},
             covered=["U1"], S3a="justified", S3b="not", behaviour="FULL", overreach=[],
             s6={"U1": 1}, failures={"U1": "retrieval"},
             note="Answer is supported by cited [1]. FROZEN gold says not retrieved (erratum): S3b set by the "
                  "'insufficient -> not justified' rule; taxonomy priority 1 = retrieval failure."),
 "Q11": dict(claims={1: ("S", "'Spain and Finland' [1]"), 2: ("S", "'November 2025' [1]")},
             covered=["U1", "U2"], S3a="justified", S3b="justified", behaviour="FULL", overreach=[],
             s6={"U1": 1, "U2": 1}, failures={"U1": "correct", "U2": "correct"}, note="Fully answered from [1]."),
 "Q12": dict(claims={1: ("S", "[1]: concessional support helps remove barriers, mobilise capital"),
                     2: ("S", "[2]: 'tax credits and concessional finance are important in developing economies, where upfront costs...'"),
                     3: ("D", "[4]: lowering cost of capital saves ~USD 150 bn; link to concessional finance is an inference"),
                     4: ("U", "[2]: accelerator was 'jointly launched' joint funding, not concessional finance"),
                     5: ("U", "[2]: 'ensuring funding reaches the local level' is about funding generally, not concessional finance"),
                     6: ("M", "'seek technology transfer and concessional finance' only in [5]; cited [2] (verifier missed)"),
                     7: ("U", "[3]: 'near-term climate win' refers to methane action, not concessional finance"),
                     8: ("U", "[3]: 53% reduction via controls + system change; no statement that concessional finance is necessary")},
             covered=[], S3a="partial", S3b="partial", behaviour="FULL",
             overreach=[(4, "O2", "joint funding presented as concessional finance"), (5, "O2", "general funding presented as concessional finance"),
                        (7, "O3", "unsupported generalisation"), (8, "O3", "unsupported generalisation")],
             s6={}, failures={"U1": "generation", "U2": "generation"},
             note="Never states U1 ('tripling', USD 90-110 bn) or U2 ('scale up highly concessional donor funding'); binary coverage applied."),
 "Q13": dict(claims={1: ("S", "'over 80% in Europe' [1]"), 2: ("S", "'2.5 times in India' [1]"), 3: ("S", "'3 times in Indonesia' [1]"),
                     4: ("S", "'at least 30%' [4]"), 5: ("S", "'1 700 GW ... 600 GW' [4]")},
             covered=["U1", "U2", "U3", "U4"], S3a="justified", S3b="justified", behaviour="FULL", overreach=[],
             s6={"U1": 1, "U2": 1, "U3": 1, "U4": 1}, failures={"U1": "correct", "U2": "correct", "U3": "correct", "U4": "correct"},
             note="All four figures correct and correctly cited."),
 "Q14": dict(claims={1: ("S", "'nine priority actions' [1]"), 2: ("S", "A2 bare claim: actions delivered by 2030 [1]"),
                     3: ("S", "fossil fuel, agriculture and waste sectors [1]"), 4: ("S", "'Fix leaks' [2]"),
                     5: ("S", "'food waste', 'Reform incentives' [5]"),
                     6: ("U", "'improve waste management practices' not in [1] or any top-5 source"),
                     7: ("S", "'the Secretary-General is endorsing nine priority actions' [1]")},
             covered=["A1", "A5", "A6"], S3a="partial", S3b="partial", behaviour="FULL",
             overreach=[(6, "O3", "unsupported generalisation about the waste sector")],
             s6={"A1": 1, "A5": 1, "A6": 1},
             failures={"A1": "correct", "A2": "retrieval", "A3": "retrieval", "A4": "retrieval", "A5": "correct",
                       "A6": "correct", "A7": "retrieval", "A8": "retrieval", "A9": "retrieval"},
             note="Gives 3 of 9 actions, states no gap (gold partial -> expected PARTIAL+GAP)."),
 "Q15": dict(claims={}, covered=[], S3a="n/a", S3b="n/a", behaviour="ABSTAIN", overreach=[], s6={},
             failures={"U1": "generation", "U2": "correct"},
             note="Only an aluminium gap line (cited [1]); omits the steel threshold that is in the top-5."),
 "Q16": dict(claims={1: ("S", "'USD 1.8 trillion in 2023' [1]"),
                     2: ("U", "[3] says 'USD 270 billion invested in clean energy in EMDE in 2023', not Africa 2024")},
             covered=["U1"], S3a="partial", S3b="partial", behaviour="FULL",
             overreach=[(2, "O2", "EMDE 2023 figure presented as Africa 2024")],
             s6={"U1": 1}, failures={"U1": "correct", "U2": "calibration"}, note="Answers the missing part with a substituted figure."),
 "Q17": dict(claims={1: ("S", "'global electricity demand in 2050 is more than double its 2022 level' [4]"),
                     2: ("U", "no source mentions household prices"),
                     **{i: ("S", "flexibility/peak-demand statements present in cited source (word-level match, verifier supported)")
                        for i in (3, 4, 5, 6, 7, 8, 9, 10, 11)}},
             covered=[], S3a="not", S3b="not", behaviour="FULL",
             overreach=[(2, "O4", "household price rise not in any source")],
             s6={}, failures={"U1": "retrieval", "U2": "calibration"},
             note="Gives global (not Europe) demand and flexibility facts; asserts household price rise. 11 lines (> 8)."),
 "Q18": dict(claims={1: ("S", "'Austria (0.029%)' [1]"),
                     2: ("U", "[5] 'German Professionals (USD 36 800)', not Austria")},
             covered=["U1"], S3a="partial", S3b="not", behaviour="FULL",
             overreach=[(2, "O2", "German salary presented as Austrian")],
             s6={"U1": 1}, failures={"U1": "retrieval", "U2": "calibration"},
             note="U1 correct and cited (FROZEN gold says not retrieved: erratum); salary substituted."),
 "Q19": dict(claims={1: ("S", "'USD 12 billion in the United States' [2]")}, covered=["U1"], S3a="justified", S3b="justified",
             behaviour="PARTIAL+GAP", overreach=[], s6={"U1": 1}, failures={"U1": "correct", "U2": "correct"},
             note="US figure plus explicit Japan gap line (gap line carries [2], format)."),
 "Q20": dict(claims={}, covered=[], S3a="n/a", S3b="n/a", behaviour="ABSTAIN", overreach=[], s6={},
             failures={"U1": "correct"}, note="Correct abstention (line carries [2])."),
 "Q21": dict(claims={}, covered=[], S3a="n/a", S3b="n/a", behaviour="ABSTAIN", overreach=[], s6={},
             failures={"U1": "correct"}, note="Correct abstention (line carries [1])."),
 "Q22": dict(claims={1: ("S", "A2 bare value: '8.5 million people' in [1]")}, covered=["U1"], S3a="justified", S3b="not",
             behaviour="FULL", overreach=[], s6={"U1": 1}, failures={"U1": "calibration"},
             note="Supported by cited [1]. FROZEN gold says absent (erratum): S3b rule and taxonomy priority 2 applied literally."),
 "Q23": dict(claims={}, covered=[], S3a="n/a", S3b="n/a", behaviour="ABSTAIN", overreach=[], s6={},
             failures={"U1": "correct"}, note="Correct abstention (line carries [2])."),
 "Q24": dict(claims={1: ("M", "'164 Mt per year in 2050, 53 per cent' only in [2]; cited [4]"),
                     2: ("U", "[4]: 'a 2.3-2.5°C rise ... even if current NDCs are implemented' is projected warming, not avoided warming")},
             covered=[], S3a="not", S3b="not", behaviour="FULL",
             overreach=[(2, "O2", "projected warming presented as avoided warming")],
             s6={}, failures={"U1": "retrieval"}, note="Avoided-warming figure not retrieved; answers with other facts."),
 "Q25": dict(claims={1: ("S", "'USD 98 billion' [4]"), 2: ("S", "'two to four per cent of the sector's USD 2.4 trillion net income in 2023' [4]")},
             covered=["U1", "U2"], S3a="justified", S3b="justified", behaviour="FULL", overreach=[],
             s6={"U1": 1, "U2": 1}, failures={"U1": "correct", "U2": "correct"}, note="Both units correct; GMSR origin via cited [4]."),
 "Q26": dict(claims={1: ("M", "'1,942 parts per billion' only in [2][3]; cited [4]")}, covered=["U1"], S3a="not", S3b="justified",
             behaviour="FULL", overreach=[], s6={"U1": 0}, failures={"U1": "citation"}, note="Correct fact, wrong source."),
 "Q27": dict(claims={1: ("M", "'roughly 90 per cent' only in [1][5]; cited [2]")}, covered=["U1"], S3a="not", S3b="justified",
             behaviour="FULL", overreach=[], s6={"U1": 0}, failures={"U1": "citation"}, note="Correct fact, wrong source."),
}

results = {r["id"]: r for r in json.loads((EXP / "results.json").read_text(encoding="utf-8"))}
gold = {g["id"]: g for g in json.loads((EXP / "gold.json").read_text(encoding="utf-8"))["questions"]}
problems, claims_out, questions_out = [], [], {}
for qid, d in R.items():
    v = verify_answer(results[qid]["answer"], results[qid]["sources"])
    vclaims = {c["claim_id"]: c for c in v["claims"]}
    cited_ids = {c["claim_id"] for c in v["claims"] if c["citations"] and c["kind"] != "abstention"
                 and (c["kind"] == "factual" or (qid, c["claim_id"]) in A2_LINES)}
    if cited_ids != set(d["claims"]):
        problems.append(f"{qid}: decided {sorted(d['claims'])} vs cited claims {sorted(cited_ids)}")
    factual_manual = [c for c in v["claims"] if c["kind"] == "factual" or (qid, c["claim_id"]) in A2_LINES]
    for cid, (code, note) in d["claims"].items():
        c = vclaims[cid]
        claims_out.append({"qid": qid, "claim_id": cid, "claim": c["claim"], "cited": c["citations"],
                           "verifier_kind": c["kind"], "verifier_status": c["citation_status"],
                           "manual_status": STATUS[code], "evidence": note, "a2_line": (qid, cid) in A2_LINES})
    req = [u["id"] for u in gold[qid]["units"] if u["required"]]
    if set(d["failures"]) != set(req):
        problems.append(f"{qid}: failure categories {sorted(d['failures'])} vs required units {req}")
    units = {u: {"covered": u in d["covered"], "failure": d["failures"][u],
                 "s6": ({"cited_chunks": d["s6"][u], "distinct_origins": 1 if d["s6"][u] else 0, "false_corroboration": False}
                        if u in d["s6"] else None)} for u in req}
    questions_out[qid] = {"behaviour": d["behaviour"], "S3a": d["S3a"], "S3b": d["S3b"],
                          "overreach": [{"claim_id": c, "type": t, "note": n} for c, t, n in d["overreach"]],
                          "manual_factual_claims": len(factual_manual), "units": units, "note": d["note"]}

out = {"reviewer": "single reviewer (Claude); no second review completed",
       "decisions": {"A1": "added citation status 'unsupported' (manual-review stage decision, user-approved)",
                     "A2": "bare-value lines counted as factual claims: " + ", ".join(f"{q} c{c}" for q, c in sorted(A2_LINES))},
       "problems": problems, "claims": claims_out, "questions": questions_out}
(EXP / "manual_review.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print("problems:", problems or "none", "| cited claims reviewed:", len(claims_out), "| questions:", len(questions_out))
