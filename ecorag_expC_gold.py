# EcoRAG – Experiment C gold labels (written BEFORE any Experiment C generation).
# Built only from: the frozen questions, the frozen top-5 retrieval snapshot, and the full corpus text.
# Every answer unit has an annotated expected status and a regex locating it; the script verifies the annotation
# against the snapshot and the corpus and FAILS if they disagree. Sufficiency labels are computed, not hand-picked.
# Output: ecorag_data/expC/gold.json and gold.txt (fingerprint appended to FREEZE_LOG.txt)
import hashlib, json, re, sys, io, time
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
EXP = Path("ecorag_data/expC")

# Unit fields: id, text (what a complete answer must state), required, status, locate (regex), answer (regex(es)
# for the mechanical S2 pre-check; all must match), origin (where the fact originates), dependency (how repeats relate)
#   status: "top5"       - stated by at least one of the question's top-5 chunks
#           "corpus"     - in the corpus but NOT in the top-5  -> retrieval failure if required
#           "absent"     - nowhere in the 1,242 chunks
GOLD = {
 "Q01": {"units": [
    dict(id="U1", text="Agriculture is the largest source of anthropogenic methane emissions", required=True, status="top5",
         locate=r"largest source of (global )?(anthropogenic|biogenic) methane|biggest single contributor to anthropogenic methane",
         answer=[r"largest|biggest"], origin="GMSR 2025", dependency="UN SG chunk restates GMSR (footnote [67])"),
    dict(id="U2", text="It accounts for about 42% of the global total (GMSR: almost 42 per cent in 2020)", required=True, status="top5",
         locate=r"42 per cent", answer=[r"\b42\b"], origin="GMSR 2025",
         dependency="3 chunks: 2 GMSR + 1 UN SG restating GMSR -> 1 independent origin"),
    dict(id="U3", text="146 Mt per year (2020)", required=False, status="top5", locate=r"146 Mt", answer=[r"146"],
         origin="GMSR 2025", dependency="single chunk")],
   "boundary": "Supports agriculture ~42% (2020) of anthropogenic methane. One GMSR chunk says 'biogenic' for the same figure; "
               "the UN SG chunk gives 42% without a year. All repeats trace to GMSR 2025: one origin, not corroboration."},
 "Q02": {"units": [
    dict(id="U1", text="MARS had sent over 5,000 alerts by February 2026 (cumulative)", required=True, status="top5",
         locate=r"5,000 alerts", answer=[r"5[,.]?000"], origin="IMEO/UNEP MARS data",
         dependency="2 UN SG chunks (same report) -> 1 origin"),
    dict(id="U2", text="Global response rate was 12% in 2025 (up from 1% in 2024)", required=True, status="top5",
         locate=r"12 per cent", answer=[r"\b12\s*(per ?cent|%)"], origin="IMEO/UNEP MARS data",
         dependency="2 UN SG chunks (same report) -> 1 origin"),
    dict(id="U3", text="Response rates grew nearly tenfold since the end of 2024", required=False, status="top5",
         locate=r"nearly tenfold", answer=[r"tenfold|ten-fold|10.fold"], origin="IMEO/UNEP MARS data", dependency="GMSR")],
   "boundary": "5,000 is cumulative to February 2026, not a 2025 figure. 12% is a global response rate for 2025, not a share "
               "of all alerts. No per-operator or per-country rates beyond 'only 11 countries above 70%'."},
 "Q03": {"units": [
    dict(id="U1", text="Demand growth outpaces grid expansion: connection queues, competition for scarce capacity, service disruption",
         required=True, status="top5", locate=r"connection queues", answer=[r"queue|keep pace|congestion|expansion"],
         origin="IEA Modernising Grids", dependency="single document"),
    dict(id="U2", text="Stability / system strength as converter-connected resources displace synchronous generators", required=True,
         status="top5", locate=r"converter-connected resources displace synchronous generators",
         answer=[r"stabil|system strength|inertia|converter"], origin="IEA Modernising Grids", dependency="single document"),
    dict(id="U3", text="Distributed resources and two-way flows create voltage, transformer loading, feeder and protection challenges",
         required=True, status="top5", locate=r"two-way flows", answer=[r"two-way|bidirectional|distributed|rooftop"],
         origin="IEA Modernising Grids", dependency="single document")],
   "boundary": "Challenges are qualitative in the top-5; no quantified costs (e.g. congestion costs, 330 GW) are retrieved."},
 "Q04": {"units": [
    dict(id="U1", text="At least a tripling of international concessional funds (USD 90-110 billion a year) to improve risk-return",
         required=True, status="top5", locate=r"tripling in international concessional funds", answer=[r"concessional"],
         origin="IEA Reducing the Cost of Capital", dependency="single chunk"),
    dict(id="U2", text="Better risk management: strong policy frameworks and regulation, and de-risking instruments", required=True,
         status="top5", locate=r"de-risking instruments", answer=[r"de-risk|risk management|policy framework|regulat"],
         origin="IEA Reducing the Cost of Capital", dependency="single chunk"),
    dict(id="U3", text="Address sector-specific risks (different business models, project scales, prevalent risks)", required=True,
         status="top5", locate=r"different business models", answer=[r"sector|business model|off-taker|transmission"],
         origin="IEA Reducing the Cost of Capital", dependency="single chunk"),
    dict(id="U4", text="A 1 percentage point reduction saves about USD 150 billion a year (impact, not a 'how')", required=False,
         status="top5", locate=r"150 billion", answer=[r"150 billion"], origin="IEA Reducing the Cost of Capital",
         dependency="2 chunks, same report")],
   "boundary": "Top-5 supports the 'how' (concessional funds, policy/regulation, de-risking, sector-specific risks) and the size of "
               "the benefit. It does not give country-specific measures."},
 "Q05": {"units": [
    dict(id="U1", text="Steel: 400-50 kg CO2-eq per tonne of crude steel, depending on scrap share", required=True, status="top5",
         locate=r"400-50 kg|100% iron: 400 kg", answer=[r"400"], origin="IEA near-zero definitions",
         dependency="exec summary restates section 3 (same report)"),
    dict(id="U2", text="Cement: 125-40 kg CO2-eq per tonne of cement, depending on clinker ratio", required=True, status="top5",
         locate=r"125-40 kg|100% clinker: 125 kg", answer=[r"125"], origin="IEA near-zero definitions",
         dependency="exec summary restates section 3 (same report)")],
   "boundary": "Supports the IEA-derived near-zero thresholds and that they slide with scrap share / clinker ratio."},
 "Q06": {"units": [
    dict(id="U1", text="Number of electric cars sold in India in 2023", required=True, status="absent",
         locate=r"India[^.]{0,120}(electric car|EV)[^.]{0,80}(sold|sales)|(electric car|EV) sales[^.]{0,80}India",
         answer=[r"\d"], origin="-", dependency="-")],
   "boundary": "Top-5: US EV/battery job postings, Norway EV update, India industrial policy list. No Indian EV sales figure."},
 "Q07": {"units": [
    dict(id="U1", text="Up to 330 GW of additional generation, storage and demand", required=True, status="top5",
         locate=r"330 GW", answer=[r"330"], origin="IEA Modernising Grids", dependency="single chunk"),
    dict(id="U2", text="Connecting the same volume via expansion would need around USD 100 billion of investment", required=True,
         status="top5", locate=r"USD 100 billion", answer=[r"100 billion"], origin="IEA Modernising Grids", dependency="single chunk")],
   "boundary": "Fully answered by one chunk."},
 "Q08": {"units": [
    dict(id="U1", text="Wind and solar PV were 12% of global electricity supply in 2023", required=True, status="top5",
         locate=r"12% of global electricity supply", answer=[r"\b12\s*(%|per ?cent)"], origin="IEA Seasonal Variability",
         dependency="single chunk"),
    dict(id="U2", text="They rise to 40% by 2030 on the path to net zero", required=True, status="top5",
         locate=r"rise to 40% by 2030", answer=[r"\b40\s*(%|per ?cent)"], origin="IEA Seasonal Variability", dependency="single chunk")],
   "boundary": "Another chunk gives a different metric (EMDE share 6% in 2022 -> 23% by 2035, STEPS): not the global figure."},
 "Q09": {"units": [
    dict(id="U1", text="Six supply chains: solar PV, wind turbines, electric cars, batteries, electrolysers, heat pumps",
         required=True, status="top5", locate=r"six key clean energy technology supply chains",
         answer=[r"solar", r"wind", r"electric car|\bEVs?\b", r"batter", r"electrolys", r"heat pump"],
         origin="IEA MaT documentation", dependency="single chunk")],
   "boundary": "A retrieved chunk notes ETP-2024 also modelled aluminium, steel and ammonia in the same framework; those are not "
               "among the six clean energy technology supply chains."},
 "Q10": {"units": [
    dict(id="U1", text="25% of US solar online job postings are in California", required=True, status="corpus",
         locate=r"California \(25% of solar", answer=[r"\b25\s*(%|per ?cent)"], origin="IEA Mapping Jobs", dependency="-")],
   "boundary": "Top-5 says California, Texas and Florida have the most solar vacancies, without a share. The 25% figure is in "
               "the executive summary chunk, which was not retrieved (retrieval failure)."},
 "Q11": {"units": [
    dict(id="U1", text="Peer experts from Spain and Finland", required=True, status="top5", locate=r"Spain and Finland",
         answer=[r"Spain", r"Finland"], origin="IEA CMR Norway", dependency="single chunk"),
    dict(id="U2", text="The review team visited Norway in November 2025", required=True, status="top5", locate=r"November 2025",
         answer=[r"November 2025"], origin="IEA CMR Norway", dependency="single chunk")],
   "boundary": "Fully answered by one chunk."},
 "Q12": {"units": [
    dict(id="U1", text="Clean energy: at least a tripling of international concessional funds (USD 90-110 bn/yr) to improve "
                       "risk-return and mobilise private capital", required=True, status="top5",
         locate=r"tripling in international concessional funds|tripling of concessional funding",
         answer=[r"concessional", r"tripl"], origin="IEA Reducing the Cost of Capital", dependency="2 chunks, same report"),
    dict(id="U2", text="Methane: grants and highly concessional donor funding should scale up and coordinate to fill gaps",
         required=True, status="top5", locate=r"highly concessional donor funding", answer=[r"methane|grant|donor"],
         origin="UN SG call to action", dependency="single chunk"),
    dict(id="U3", text="Emerging economies seek technology transfer and concessional finance to bridge capacity gaps", required=False,
         status="top5", locate=r"seek technology transfer and concessional finance", answer=[r"technology transfer|capacity gap"],
         origin="GMSR 2025", dependency="single chunk")],
   "boundary": "Two separate literatures: IEA (clean energy, quantified) and UNEP/UN (methane, qualitative). No single figure "
               "for methane-specific concessional finance is retrieved."},
 "Q13": {"units": [
    dict(id="U1", text="Europe: electricity demand +80% or more, 2022-2050", required=True, status="top5",
         locate=r"over 80% in Europe", answer=[r"\b80\s*(%|per ?cent)"], origin="IEA Seasonal Variability", dependency="single chunk"),
    dict(id="U2", text="India: more than 2.5 times", required=True, status="top5", locate=r"2\.5 times in India",
         answer=[r"2\.5"], origin="IEA Seasonal Variability", dependency="single chunk"),
    dict(id="U3", text="Indonesia: 3 times", required=True, status="top5", locate=r"3 times in Indonesia",
         answer=[r"\b(3|three)\s*times|threefold"], origin="IEA Seasonal Variability", dependency="single chunk"),
    dict(id="U4", text="Global grid capacity must increase by at least 30% by 2035 (25 million km of lines)", required=True,
         status="top5", locate=r"at least 30%", answer=[r"\b30\s*(%|per ?cent)"], origin="IEA Modernising Grids",
         dependency="single chunk")],
   "boundary": "Demand figures are 2022-2050 (Seasonal Variability); grid figure is to 2035 (Modernising Grids): different "
               "reports and horizons, which should not be merged into one timeline."},
 "Q14": {"units": [
    dict(id="A1", text="Action 1: Fix leaks and eliminate routine flaring and cold venting", required=True, status="top5",
         locate=r"Fix leaks", answer=[r"leak"], origin="UN SG call to action", dependency="-"),
    dict(id="A2", text="Action 2: Make methane measurable, reportable and verifiable", required=True, status="corpus",
         locate=r"measurable, reportable and verifiable", answer=[r"measurable|reportable|verifiable"], origin="UN SG call to action", dependency="-"),
    dict(id="A3", text="Action 3: Science-based global methane standard / near-zero-methane marketplace", required=True,
         status="corpus", locate=r"science.based global methane standard", answer=[r"standard|marketplace"], origin="UN SG call to action", dependency="-"),
    dict(id="A4", text="Action 4: Produce food more efficiently with less methane", required=True, status="corpus",
         locate=r"Produce food more efficiently", answer=[r"food more efficiently|livestock|rice"], origin="UN SG call to action", dependency="-"),
    dict(id="A5", text="Action 5: Halve per-capita food waste and reduce food loss", required=True, status="top5",
         locate=r"Halve per.capita food waste", answer=[r"food waste|food loss"], origin="UN SG call to action", dependency="-"),
    dict(id="A6", text="Action 6: Reform incentives and redirect finance and subsidies", required=True, status="top5",
         locate=r"Reform incentives", answer=[r"incentive|subsid"], origin="UN SG call to action", dependency="-"),
    dict(id="A7", text="Action 7: Phase out open dumping and uncontrolled landfills", required=True, status="corpus",
         locate=r"open dumping", answer=[r"dumping|landfill"], origin="UN SG call to action", dependency="-"),
    dict(id="A8", text="Action 8: Capture methane from waste and wastewater", required=True, status="corpus",
         locate=r"Capture methane from waste", answer=[r"wastewater|capture methane from waste"], origin="UN SG call to action", dependency="-"),
    dict(id="A9", text="Action 9: Build circular, low-methane urban waste systems", required=True, status="corpus",
         locate=r"circular, low.methane urban waste", answer=[r"circular"], origin="UN SG call to action", dependency="-")],
   "boundary": "Top-5 contains only Actions 1, 5 and 6 (+ general text). Six actions are in the corpus but not retrieved."},
 "Q15": {"units": [
    dict(id="U1", text="Steel near-zero threshold 400-50 kg CO2-eq/t crude steel, by scrap share", required=True, status="top5",
         locate=r"400-50 kg|100% iron: 400 kg", answer=[r"400"], origin="IEA near-zero definitions", dependency="same report"),
    dict(id="U2", text="Aluminium near-zero threshold", required=True, status="absent",
         locate=r"alumin[^.]{0,80}(threshold|near-zero)|(threshold|near-zero)[^.]{0,80}alumin", answer=[r"alumin[^.]*\d"],
         origin="-", dependency="-")],
   "boundary": "Steel supported; another retrieved proposal gives 380-400 kg CO2-eq/t hot-rolled steel by 2045 (different "
               "proposal and metric). Nothing on aluminium anywhere in the corpus."},
 "Q16": {"units": [
    dict(id="U1", text="Global clean energy investment reached about USD 1.8 trillion in 2023", required=True, status="top5",
         locate=r"USD 1\.8 trillion in 2023", answer=[r"1\.8 trillion"], origin="IEA Reducing the Cost of Capital", dependency="single chunk"),
    dict(id="U2", text="Clean energy spending in Africa in 2024", required=True, status="absent",
         locate=r"Africa[^.]{0,120}2024|2024[^.]{0,120}Africa", answer=[r"Africa[^.]*\d"], origin="-", dependency="-")],
   "boundary": "2024 Africa figure absent from the corpus. The corpus has a 2023 Africa figure (USD 35 billion) but it was not "
               "retrieved; presenting a 2023 figure as 2024 would be a date/scope error."},
 "Q17": {"units": [
    dict(id="U1", text="Europe electricity demand +80% or more, 2022-2050", required=True, status="corpus",
         locate=r"over 80% in Europe", answer=[r"\b80\s*(%|per ?cent)"], origin="IEA Seasonal Variability", dependency="-"),
    dict(id="U2", text="Rise in household electricity prices", required=True, status="absent",
         locate=r"household[^.]{0,60}\b(electricity )?(prices?|bills?|tariffs?)\b", answer=[r"household[^.]*\d"], origin="-", dependency="-")],
   "boundary": "Top-5 gives Europe flexibility needs (+50% by 2030, doubling by 2050), not demand growth: using it as demand "
               "growth would be over-reach. Household prices appear nowhere in the corpus."},
 "Q18": {"units": [
    dict(id="U1", text="Heat pump OJPs reached about 0.03% of all online postings in Austria", required=True, status="corpus",
         locate=r"0\.03% of the total online postings in Austria", answer=[r"0\.03"], origin="IEA Mapping Jobs", dependency="-"),
    dict(id="U2", text="Average advertised salary of Austrian heat pump postings", required=True, status="absent",
         locate=r"Austria[^.]{0,120}heat pump[^.]{0,120}salar", answer=[r"(USD|EUR|€|\$)\s?\d"], origin="-", dependency="-")],
   "boundary": "Top-5 states that salary information on heat pump OJPs is very scarce; that supports saying the salary is not "
               "available. A Europe-wide solar salary range exists in the corpus but is for solar, not heat pumps."},
 "Q19": {"units": [
    dict(id="U1", text="Grid congestion cost USD 12 billion in the United States in 2024", required=True, status="top5",
         locate=r"USD 12 billion", answer=[r"12 billion"], origin="IEA Modernising Grids", dependency="2 chunks, same report"),
    dict(id="U2", text="Grid congestion cost in Japan", required=True, status="absent",
         locate=r"Japan[^.]{0,120}congestion|congestion[^.]{0,120}Japan", answer=[r"Japan[^.]*\d"], origin="-", dependency="-")],
   "boundary": "US supported (EU EUR 4.3 billion also given). Nothing on Japan."},
 "Q20": {"units": [
    dict(id="U1", text="Norway's lithium production in 2024 (tonnes)", required=True, status="absent",
         locate=r"lithium[^.]{0,100}(produc|tonnes|output)[^.]{0,60}Norway|Norway[^.]{0,100}lithium[^.]{0,60}(produc|tonnes)",
         answer=[r"\d[\d,.]*\s*(tonnes|t\b|kt)"], origin="-", dependency="-")],
   "boundary": "Top-5 lists lithium among critical raw materials; no production data."},
 "Q21": {"units": [
    dict(id="U1", text="Average wholesale electricity price in Indonesia in 2023", required=True, status="absent",
         locate=r"Indonesia[^.]{0,120}wholesale|wholesale[^.]{0,120}Indonesia", answer=[r"(USD|\$)\s?\d|/MWh|per MWh"],
         origin="-", dependency="-")],
   "boundary": "Top-5 covers Indonesia's power system evolution; no wholesale price."},
 "Q22": {"units": [
    dict(id="U1", text="Number of people working in the global grid sector", required=True, status="absent",
         locate=r"(million|thousand)[^.]{0,40}(workers|employees)[^.]{0,60}grid|grid[^.]{0,60}(million|thousand)[^.]{0,20}(workers|employees)",
         answer=[r"\d[\d,.]*\s*(million|thousand)?\s*(people|workers|employees)"], origin="-", dependency="-")],
   "boundary": "Top-5 describes skills shortages, an ageing workforce and job postings; no headcount."},
 "Q23": {"units": [
    dict(id="U1", text="Cost of carbon capture for cement plants (USD per tonne CO2)", required=True, status="absent",
         locate=r"(carbon capture|CCS|CCUS)[^.]{0,120}(USD|cost)[^.]{0,40}(tonne|t CO2)",
         answer=[r"(USD|\$)\s?\d[^.]*(tonne|/t)"], origin="-", dependency="-")],
   "boundary": "Top-5 has CCUS definitions only; no cost."},
 "Q24": {"units": [
    dict(id="U1", text="About 0.1-0.2°C of warming avoided by 2050", required=True, status="corpus", locate=r"0\.1\W0\.2",
         answer=[r"0\.1\W0\.2"], origin="GMSR 2025 / CCAC", dependency="UN SG restates in 3 chunks (footnotes [26,27])")],
   "boundary": "Top-5 has overshoot context only (1.5°C, a 2.3-2.5°C projected rise). The avoided-warming figure is in the corpus "
               "but not retrieved (retrieval failure). Any number given would be over-reach."},
 "Q25": {"units": [
    dict(id="U1", text="About USD 98 billion a year (accounting for the value of recovered gas)", required=True, status="top5",
         locate=r"98 billion", answer=[r"98 billion"], origin="GMSR 2025",
         dependency="3 chunks: GMSR + 2 UN SG chunks restating GMSR (footnote [23]) -> 1 independent origin"),
    dict(id="U2", text="Equal to 2-4% of the sector's USD 2.4 trillion net income in 2023", required=True, status="top5",
         locate=r"2.4 per cent|two to four per cent|2–4 per cent", answer=[r"\b2\W4\s*(%|per ?cent)|two to four"],
         origin="GMSR 2025", dependency="as U1"),
    dict(id="U3", text="IEA's lower estimate: about USD 52 billion a year for a 75% reduction (~2% of net income)",
         required=False, status="top5", locate=r"52 billion", answer=[r"52 billion"], origin="IEA Global Methane Tracker",
         dependency="restated in 2 UN SG chunks (footnote [24]) -> 1 origin, independent of GMSR")],
   "boundary": "Two different estimates with different scope (GMSR net cost of all measures; IEA cost of a 75% cut by 2030). "
               "Citing GMSR and the UN SG restatement of it is not independent corroboration."},
 "Q26": {"units": [
    dict(id="U1", text="About 1,942 parts per billion in 2024", required=True, status="top5", locate=r"1,942 parts per billion",
         answer=[r"1[,.]?942"], origin="WMO State of the Global Climate 2025", dependency="2 UN SG chunks restating WMO -> 1 origin"),
    dict(id="U2", text="Roughly 266% above pre-industrial levels", required=False, status="top5", locate=r"266 per cent",
         answer=[r"266"], origin="WMO State of the Global Climate 2025", dependency="as U1")],
   "boundary": "One origin (WMO) repeated twice in the UN report; GMSR chunks retrieved do not give the 2024 concentration."},
 "Q27": {"units": [
    dict(id="U1", text="Oil and gas methane emissions could fall by roughly 90%", required=True, status="top5",
         locate=r"roughly 90 per cent", answer=[r"\b90\s*(%|per ?cent)"], origin="IEA (via UN SG)",
         dependency="the SAME sentence in 2 chunks (chunk overlap) -> 1 origin, not 2 sources")],
   "boundary": "Retrieved wording is 'roughly 90 per cent' (executive summary). The report's chapter says 'over 90 per cent' "
               "(not retrieved)."},
}

def norm(t): return " ".join(t.split())

questions = {q["id"]: q for q in json.loads((EXP / "questions_frozen.json").read_text(encoding="utf-8"))["questions"]}
snapshot = {q["id"]: q for q in json.loads((EXP / "retrieval_snapshot.json").read_text(encoding="utf-8"))["questions"]}
corpus = [json.loads(l) for l in open("ecorag_data/embeddings/records.jsonl", encoding="utf-8")]
assert set(GOLD) == set(questions), "every frozen question needs gold labels"

errors, out = [], []
for qid, q in questions.items():
    g, sources = GOLD[qid], snapshot[qid]["sources"]
    units = []
    for u in g["units"]:
        pat = re.compile(u["locate"], re.I)
        in_top5 = [s["n"] for s in sources if pat.search(norm(s["text"]))]
        top5_ids = {s["chunk_id"] for s in sources}
        in_corpus = [r["id"] for r in corpus if pat.search(norm(r["document"]))]
        observed = "top5" if in_top5 else ("corpus" if in_corpus else "absent")
        if observed != u["status"]:
            errors.append(f"{qid} {u['id']}: annotated {u['status']} but search finds {observed} (top5 {in_top5}, corpus {in_corpus[:4]})")
        units.append({**u, "support_top5": in_top5,
                      "support_top5_chunks": [s["chunk_id"] for s in sources if s["n"] in in_top5],
                      "corpus_chunks_not_retrieved": [c for c in in_corpus if c not in top5_ids][:10],
                      "independent_origins_top5": 1 if in_top5 else 0})
    required = [u for u in units if u["required"]]
    n_top5 = sum(u["status"] == "top5" for u in required)
    sufficiency = "sufficient" if n_top5 == len(required) else ("partial" if n_top5 else "insufficient")
    expected = {"sufficient": "full answer", "partial": "answer the supported part and state the gap",
                "insufficient": "abstain (state the sources do not contain enough information)"}[sufficiency]
    out.append({"id": qid, "category": q["category"], "category_name": q["category_name"], "question": q["question"],
                "top5": [s["chunk_id"] for s in sources], "units": units,
                "required_units": len(required), "required_units_in_top5": n_top5,
                "required_units_retrieval_failure": sum(u["status"] == "corpus" for u in required),
                "required_units_absent_from_corpus": sum(u["status"] == "absent" for u in required),
                "retrieval_sufficiency": sufficiency, "expected_behaviour": expected, "evidence_boundary": g["boundary"]})

if errors:
    print("GOLD VALIDATION FAILED:"); [print("  ", e) for e in errors]; sys.exit(1)

payload = {"created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
           "rule": "Built from the frozen questions, frozen top-5 snapshot and corpus only - before any Experiment C generation.",
           "questions": out}
text = json.dumps(payload, ensure_ascii=False, indent=2)
(EXP / "gold.json").write_text(text, encoding="utf-8")
with open(EXP / "FREEZE_LOG.txt", "a", encoding="utf-8") as f:
    f.write(f"{payload['created_at']}  gold.json  sha256={hashlib.sha256(text.encode('utf-8')).hexdigest()}  (validated, before any generation)\n")

lines = []
for g in out:
    lines.append(f"{g['id']} [{g['category']}] {g['question']}")
    lines.append(f"   retrieval sufficiency: {g['retrieval_sufficiency'].upper()}  (required units in top-5: {g['required_units_in_top5']}/"
                 f"{g['required_units']}; retrieval failures: {g['required_units_retrieval_failure']}; absent from corpus: "
                 f"{g['required_units_absent_from_corpus']})  -> expected: {g['expected_behaviour']}")
    for u in g["units"]:
        where = (f"top-5 {u['support_top5']}" if u["status"] == "top5" else
                 f"NOT RETRIEVED (in corpus: {u['corpus_chunks_not_retrieved'][:2]})" if u["status"] == "corpus" else "ABSENT from corpus")
        lines.append(f"   {u['id']} {'req' if u['required'] else 'opt'} | {u['text']} | {where} | origin: {u['origin']} | {u['dependency']}")
    lines.append(f"   boundary: {g['evidence_boundary']}")
    lines.append("")
(EXP / "gold.txt").write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))
from collections import Counter
print("sufficiency by question:", dict(Counter(g["retrieval_sufficiency"] for g in out)))
print("by type x sufficiency:", dict(Counter((g["category"], g["retrieval_sufficiency"]) for g in out)))
