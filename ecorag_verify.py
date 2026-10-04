# ============================================================
# EcoRAG - citation & grounding verifier (deterministic, no LLM, no API)
# ============================================================
# Checks a generated answer claim-by-claim against the source blocks the LLM was given.
# It does NOT rewrite the answer; it only reports.
#
# For every claim (sentence) it records:
#   - which sources the model cited, and in which format ([2], SOURCE [2], Document [2], ...)
#   - where each key number of the claim actually occurs in the sources
#   - how many of the claim's content words occur in each source (best 1-3 sentence passage)
#   - a status: supported / partially_supported / misattributed / unsupported / no_citation
#   - date/scope mismatches (claim says "in 2025", the sentence with that figure says "By February 2026")
#
# What "supported" means here: the claim's key numbers occur in the cited source AND most of its
# content words occur in one passage of that source. That is WORD-LEVEL evidence, not proof that
# the meaning is preserved. A paraphrase that changes the meaning can still pass; see LIMITATIONS.
#
# Run this file directly to verify the saved v2 results (the raw outputs are not modified).

import json
import re
from collections import Counter
from pathlib import Path


# --- 1. Settings (fixed in advance, not tuned to the test answers) ---
SUPPORTED_COVERAGE = 0.60   # >= 60% of the claim's content words in one source passage -> supported
PARTIAL_COVERAGE = 0.35     # >= 35% -> partially supported
WINDOW_SENTENCES = 3        # a passage = up to 3 consecutive sentences of a source
MIN_KEY_NUMBER = 10         # numbers below 10 ("1 percentage point") are too common to prove anything

STOPWORDS = set("""a an the and or but of to in on at by for with from as is are was were be been being
this that these those it its their there them they which who whom what when where while than then so such
can could may might must should would will shall do does did has have had not no nor into onto over under
about above below between through during before after also more most other some any each all both
per via up down out off very just only same own too how why our we you your he she his her one two""".split())
META_WORDS = {"according", "source", "sources", "document", "documents", "evidence", "provided",
              "highlight", "highlights", "states", "notes", "mentions", "additionally", "however",
              "specifically", "include", "includes", "including"}
ABSTAIN = re.compile(r"do(es)? not contain enough information|not enough information|cannot be answered|"
                     r"no information (is|was) (provided|available)", re.IGNORECASE)
VAGUE_ATTRIBUTION = re.compile(r"\baccording to (the )?(sources|evidence|documents|reports?)\b(?!\s*\[?\d)",
                               re.IGNORECASE)
YEAR = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
NUMBER = re.compile(r"(?<![A-Za-z\d.,])(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)(?![A-Za-z\d])")
TIME_PHRASE = re.compile(r"\b(?:by|in|since|from|until|between|as of|during|at the end of|end of)\s+"
                         r"(?:[A-Z][a-z]+\s+)?(?:19|20)\d{2}\b", re.IGNORECASE)

# Citation formats, most specific first (each match is removed before the next pattern runs)
NUMS = r"(\d+(?:\s*(?:,|and|–|-)\s*\d+)*)"
CITATION_PATTERNS = [
    ("SOURCE [n]",   re.compile(r"\bsources?\s*\[" + NUMS + r"\]", re.IGNORECASE)),
    ("Document [n]", re.compile(r"\bdocuments?\s*\[" + NUMS + r"\]", re.IGNORECASE)),
    ("SOURCE n",     re.compile(r"\bsources?\s+" + NUMS + r"\b", re.IGNORECASE)),
    ("Document n",   re.compile(r"\bdocuments?\s+" + NUMS + r"\b", re.IGNORECASE)),
    ("[n]",          re.compile(r"\[" + NUMS + r"\]")),
]


# --- 2. Text helpers ---
def expand_numbers(group):
    """'2, 4' -> [2, 4]; '1-3' -> [1, 2, 3]; '1 and 2' -> [1, 2]."""
    out = []
    for part in re.split(r"\s*(?:,|and)\s*", group):
        bounds = re.split(r"\s*[–-]\s*", part)
        if len(bounds) == 2 and all(b.isdigit() for b in bounds):
            out.extend(range(int(bounds[0]), int(bounds[1]) + 1))
        elif part.strip().isdigit():
            out.append(int(part))
    return out

def find_citations(text):
    """Return (cited source numbers, formats used, text with the citation markers removed)."""
    numbers, formats = [], []
    for fmt, pattern in CITATION_PATTERNS:
        for m in pattern.finditer(text):
            numbers.extend(expand_numbers(m.group(1)))
            formats.append(fmt)
        text = pattern.sub(" ", text)
    return sorted(set(numbers)), formats, text

def stem(word):
    for suffix in ("ations", "ation", "ing", "ies", "ied", "es", "ed", "ly", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            word = word[:-len(suffix)] + ("y" if suffix in ("ies", "ied") else "")
            break
    return word[:-1] if word.endswith("e") and len(word) > 4 else word

def content_words(text):
    words = set()
    for token in re.findall(r"[a-z][a-z'’\-]*", text.lower()):
        for part in token.replace("’", "'").split("-"):
            part = part.strip("'")
            if len(part) >= 3 and part not in STOPWORDS and part not in META_WORDS:
                words.add(stem(part))
    return words

def normalise_numbers(text):
    return re.sub(r"(?<=\d),(?=\d{3}\b)", "", text)          # "5,000" -> "5000"

def key_numbers(text):
    """Numbers that identify a fact: >= 10, decimals and years; ranges count as both ends."""
    found = []
    for raw in NUMBER.findall(text):
        value = raw.replace(",", "")
        if "." in value or float(value) >= MIN_KEY_NUMBER:
            found.append(value)
    return list(dict.fromkeys(found))

def contains_number(text, number):
    return re.search(r"(?<![\d.])" + re.escape(number) + r"(?!\d|\.\d)", normalise_numbers(text)) is not None

def split_sentences(text):
    text = " ".join(text.split())
    return [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z\"“(\[]|\d)", text) if s.strip()]

def source_sentences(text):
    """Sentences of a source block (bullets, table rows and lines are split too)."""
    pieces = []
    for line in re.split(r"\n+", text):
        pieces.extend(split_sentences(line))
    return pieces


# --- 3. Split the answer into claims ---
def split_claims(answer):
    claims = []
    for line in answer.splitlines():
        line = line.strip()
        if not line:
            continue
        line = re.sub(r"^(\d+[.)]|[-*•])\s+", "", line)        # list markers
        heading = None
        bold = re.match(r"^\*\*(.+?)\*\*\s*:?\s*", line)         # "**Thermal limits**: ..."
        if bold:
            heading, line = bold.group(1).strip(" :"), line[bold.end():]
        line = line.replace("**", "")
        for sentence in split_sentences(line):
            cites, _, rest = find_citations(sentence)
            if cites and not content_words(rest) and not key_numbers(rest) and claims:
                claims[-1]["text"] += " " + sentence              # a lone "[2]." belongs to the previous claim
            else:
                claims.append({"text": sentence, "heading": heading})
    return claims


# --- 4. Evidence for one claim in one source ---
def best_passage(claim_words, sentences):
    """Highest share of the claim's content words found in up to WINDOW_SENTENCES consecutive sentences."""
    best, best_text = 0.0, ""
    if not claim_words:
        return best, best_text
    for i in range(len(sentences)):
        for size in range(1, WINDOW_SENTENCES + 1):
            window = " ".join(sentences[i:i + size])
            coverage = len(claim_words & content_words(window)) / len(claim_words)
            if coverage > best:
                best, best_text = coverage, window
    return round(best, 2), best_text

def support_level(numbers_found_all, coverage):
    if numbers_found_all and coverage >= SUPPORTED_COVERAGE:
        return "supported"
    if numbers_found_all and coverage >= PARTIAL_COVERAGE:
        return "partial"
    return "none"

def date_scope_issues(claim_text, numbers, sources):
    """Claim attaches a year to a figure, but every source sentence with that figure carries a different year."""
    claim_years = set(YEAR.findall(claim_text))
    if not claim_years:
        return []
    issues = []
    for number in numbers:
        if YEAR.fullmatch(number):
            continue
        hits = [(s["n"], sent) for s in sources for sent in source_sentences(s["text"])
                if contains_number(sent, number)]
        dated = [(n, sent) for n, sent in hits if YEAR.search(sent)]
        if dated and not any(claim_years & set(YEAR.findall(sent)) for _, sent in hits):
            n, sent = dated[0]
            issues.append({
                "number": number,
                "claim_says": TIME_PHRASE.findall(claim_text) or sorted(claim_years),
                "source": n,
                "source_says": TIME_PHRASE.findall(sent) or sorted(set(YEAR.findall(sent))),
                "source_sentence": sent[:220],
            })
    return issues


# --- 5. Verify one answer ---
def verify_answer(answer, sources):
    """Deterministic claim-by-claim check of an answer against its numbered sources."""
    by_n = {s["n"]: s for s in sources}
    sentences = {s["n"]: source_sentences(s["text"]) for s in sources}
    results = []

    for i, claim in enumerate(split_claims(answer), 1):
        cited, formats, plain = find_citations(claim["text"])
        valid = [n for n in cited if n in by_n]
        invalid = [n for n in cited if n not in by_n]
        words = content_words(plain)
        numbers = key_numbers(plain)

        if ABSTAIN.search(plain):
            kind = "abstention"
        elif plain.strip().endswith(":") or len(words) < 3:
            kind = "framing"                       # "The main challenges include:" etc.
        else:
            kind = "factual"

        number_locations = {num: [n for n in by_n if contains_number(by_n[n]["text"], num)] for num in numbers}
        coverage, passages = {}, {}
        for n in by_n:
            coverage[n], passages[n] = best_passage(words, sentences[n])

        def level_for(source_numbers):
            all_found = all(any(n in number_locations[num] for n in source_numbers) for num in numbers)
            return support_level(all_found, max(coverage[n] for n in source_numbers))

        source_levels = {n: level_for([n]) for n in by_n}
        supporting = [n for n, lvl in source_levels.items() if lvl != "none"]

        status, problems = kind, []
        if kind == "factual":
            if not valid:
                status = "no_citation"
                problems.append("factual claim has no citation" +
                                (f"; matching content found in {supporting}" if supporting
                                 else "; no retrieved source matches it"))
            else:
                missing = [num for num in numbers if not set(number_locations[num]) & set(valid)]
                elsewhere = {num: number_locations[num] for num in missing if number_locations[num]}
                nowhere = [num for num in missing if not number_locations[num]]
                cited_level = level_for(valid)
                if elsewhere:
                    status = "misattributed"
                    problems.append("; ".join(f"'{num}' is not in cited source {valid} but is in {locs}"
                                              for num, locs in elsewhere.items()))
                elif nowhere:
                    status = "unsupported"
                    problems.append(f"number(s) {nowhere} not found in any retrieved source")
                elif cited_level == "supported":
                    status = "supported"
                elif cited_level == "partial":
                    status = "partially_supported"
                    problems.append(f"only {max(coverage[n] for n in valid):.0%} of the claim's words found in cited source")
                elif any(source_levels[n] == "supported" for n in by_n if n not in valid):
                    status = "misattributed"
                    problems.append(f"cited {valid} does not match; best matching source is "
                                    f"{max((n for n in by_n if n not in valid), key=lambda n: coverage[n])}")
                else:
                    status = "unsupported"
                    problems.append(f"no retrieved source matches it (best word coverage "
                                    f"{max(coverage.values()):.0%})")
        if invalid:
            problems.append(f"cites non-existent source(s) {invalid}")
        if any(f != "[n]" for f in formats):
            problems.append(f"non-standard citation format: {sorted(set(formats))}")
        if VAGUE_ATTRIBUTION.search(plain):
            problems.append("vague attribution ('according to the sources') instead of a source number")
        dates = date_scope_issues(plain, numbers, sources) if kind == "factual" else []
        for d in dates:
            problems.append(f"date/scope: claim says {d['claim_says']} for '{d['number']}', "
                            f"source [{d['source']}] says {d['source_says']}")

        results.append({
            "claim_id": i,
            "claim": claim["text"],
            "heading": claim["heading"],
            "kind": kind,
            "citations": valid,
            "invalid_citations": invalid,
            "citation_formats": formats,
            "citation_status": status,
            "supporting_sources": supporting,
            "key_numbers": {num: locs for num, locs in number_locations.items()},
            "word_coverage": coverage,
            "date_scope_issues": dates,
            "problem": "; ".join(problems) or None,
            "needs_human_review": status in ("supported", "partially_supported") and not numbers,
        })

    factual = [r for r in results if r["kind"] == "factual"]
    counts = Counter(r["citation_status"] for r in factual)
    summary = {
        "factual_claims": len(factual),
        "with_citation": sum(bool(r["citations"]) for r in factual),
        "supported": counts["supported"],
        "partially_supported": counts["partially_supported"],
        "misattributed": counts["misattributed"],
        "unsupported_cited": counts["unsupported"],
        "uncited": counts["no_citation"],
        "uncited_but_matching_source": sum(r["citation_status"] == "no_citation" and bool(r["supporting_sources"])
                                           for r in factual),
        "uncited_and_unmatched": sum(r["citation_status"] == "no_citation" and not r["supporting_sources"]
                                     for r in factual),
        "date_scope_mismatches": sum(bool(r["date_scope_issues"]) for r in factual),     # claims affected
        "date_scope_figures": sum(len(r["date_scope_issues"]) for r in factual),           # figures affected
        "non_standard_citation_format": sum(any(f != "[n]" for f in r["citation_formats"]) for r in results),
        "vague_attribution": sum(bool(VAGUE_ATTRIBUTION.search(r["claim"])) for r in results),
        "abstained": bool(results) and all(r["kind"] in ("abstention", "framing") for r in results)
                     and any(r["kind"] == "abstention" for r in results),
    }
    return {"summary": summary, "claims": results}


# --- 6. Readable report ---
STATUS_LABEL = {"supported": "SUPPORTED", "partially_supported": "PARTIAL", "misattributed": "MISATTRIBUTED",
                "unsupported": "UNSUPPORTED", "no_citation": "NO CITATION", "framing": "framing",
                "abstention": "ABSTENTION"}

def format_report(question, answer, verification):
    lines = ["=" * 90, f"Q: {question}", "-" * 90, "ANSWER (unchanged):", answer, "-" * 90]
    for r in verification["claims"]:
        lines.append(f"[{STATUS_LABEL[r['citation_status']]}] claim {r['claim_id']}: {r['claim']}")
        if r["kind"] == "factual":
            lines.append(f"    cited: {r['citations'] or 'none'}   sources that match: {r['supporting_sources'] or 'none'}"
                         f"   word coverage: {r['word_coverage']}")
            if r["key_numbers"]:
                lines.append("    numbers -> sources: " + ", ".join(f"{k}->{v or 'NONE'}" for k, v in r["key_numbers"].items()))
        if r["problem"]:
            lines.append(f"    PROBLEM: {r['problem']}")
        if r["needs_human_review"]:
            lines.append("    (word-level match only: meaning not verified)")
    s = verification["summary"]
    lines.append("-" * 90)
    lines.append(f"SUMMARY: {s['factual_claims']} factual claims | {s['with_citation']} cited | "
                 f"{s['supported']} supported | {s['partially_supported']} partial | {s['misattributed']} misattributed | "
                 f"{s['unsupported_cited']} cited-but-unsupported | {s['uncited']} uncited "
                 f"({s['uncited_but_matching_source']} matching a source, {s['uncited_and_unmatched']} matching none) | "
                 f"{s['date_scope_mismatches']} claim(s) with date/scope mismatch ({s['date_scope_figures']} figures) | "
                 f"abstained: {s['abstained']}")
    return "\n".join(lines)

LIMITATIONS = [
    "Support is judged by key numbers and shared content words, not by meaning: a paraphrase that "
    "changes the meaning (e.g. '12% of these alerts' vs '12 per cent global response rate in 2025') can pass.",
    "Distortions without numbers or dates (e.g. 'competition among energy sources' vs 'housing and industry "
    "competing with data centres for grid capacity') are not detected.",
    "Numbers below 10 are ignored for attribution because they occur in almost every source.",
    "Heavy paraphrases of a correct fact can score as partial/no match (false negatives).",
    "When all sources come from the same report, shared topic words (e.g. 'cost of capital', 'clean energy') "
    "raise word coverage for any on-topic sentence, so a generic sentence can appear to match a source.",
    "Date checks only catch a figure whose year differs from every source sentence containing that figure.",
    "Whether the answer actually answers the question (e.g. 'why' instead of 'how') is out of scope.",
]


# --- 7. Run on the saved v2 results ---
if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    DATA_DIR = Path("ecorag_data")
    VERSION = sys.argv[1] if len(sys.argv) > 1 else "v2"     # which saved run to verify: v2, v3, ...
    runs = []
    for name in [f"rag_{VERSION}_results_q1_q3.json", f"rag_{VERSION}_results_q4_q6.json"]:
        path = DATA_DIR / name
        if path.exists():
            runs.extend(json.loads(path.read_text(encoding="utf-8")))
    if not runs:
        raise FileNotFoundError(f"No saved {VERSION} results found in ecorag_data/")

    report_lines, records = [], []
    for run in runs:
        verification = verify_answer(run["answer"], run["sources"])
        records.append({"question": run["question"], "model": run["model"],
                        "prompt_version": run.get("prompt_version"), "answer": run["answer"], **verification})
        report_lines.append(format_report(run["question"], run["answer"], verification))

    totals = Counter()
    for r in records:
        totals.update({k: v for k, v in r["summary"].items() if not isinstance(v, bool)})
    table = ["", "=" * 90, f"TOTALS ({VERSION} answers, {runs[0]['model'].split('/')[-1]})", "=" * 90,
             f"{'Q':<4}{'claims':>7}{'cited':>7}{'suppor.':>9}{'partial':>9}{'misattr.':>10}{'unsup.':>8}"
             f"{'uncited':>9}{'date':>6}{'format':>8}  abstained"]
    for i, r in enumerate(records, 1):
        s = r["summary"]
        table.append(f"Q{i:<3}{s['factual_claims']:>7}{s['with_citation']:>7}{s['supported']:>9}"
                     f"{s['partially_supported']:>9}{s['misattributed']:>10}{s['unsupported_cited']:>8}"
                     f"{s['uncited']:>9}{s['date_scope_mismatches']:>6}{s['non_standard_citation_format']:>8}  {s['abstained']}")
    table.append(f"{'ALL':<4}{totals['factual_claims']:>7}{totals['with_citation']:>7}{totals['supported']:>9}"
                 f"{totals['partially_supported']:>9}{totals['misattributed']:>10}{totals['unsupported_cited']:>8}"
                 f"{totals['uncited']:>9}{totals['date_scope_mismatches']:>6}{totals['non_standard_citation_format']:>8}")
    table.append(f"Uncited claims matching a source: {totals['uncited_but_matching_source']} | "
                 f"uncited claims matching no source: {totals['uncited_and_unmatched']} | "
                 f"'date' = claims with a date/scope mismatch ({totals['date_scope_figures']} figures)")
    table += ["", f"Thresholds: supported >= {SUPPORTED_COVERAGE:.0%} word coverage + all key numbers in cited source; "
              f"partial >= {PARTIAL_COVERAGE:.0%}; passages of up to {WINDOW_SENTENCES} sentences; numbers < {MIN_KEY_NUMBER} ignored.",
              "", "LIMITATIONS:"] + [f" - {l}" for l in LIMITATIONS]
    report = "\n".join(report_lines + table)

    (DATA_DIR / f"rag_{VERSION}_citation_verification.txt").write_text(report, encoding="utf-8")
    (DATA_DIR / f"rag_{VERSION}_citation_verification.json").write_text(json.dumps({
        "method": "deterministic: citation regexes, key-number matching, content-word coverage, year checks (no LLM)",
        "thresholds": {"supported_coverage": SUPPORTED_COVERAGE, "partial_coverage": PARTIAL_COVERAGE,
                       "window_sentences": WINDOW_SENTENCES, "min_key_number": MIN_KEY_NUMBER},
        "limitations": LIMITATIONS,
        "totals": dict(totals),
        "results": records,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(report)
    print(f"\nSaved {DATA_DIR / f'rag_{VERSION}_citation_verification.json'} and .txt")
