# EcoRAG Experiment C – Scoring rubric (frozen before any Experiment C generation)

This rubric is fixed before the model is run. Scores are assigned against the frozen gold labels
(`gold.json`) and the frozen top-5 evidence (`retrieval_snapshot.json`), never against what the model "should
have known". Every manual decision is recorded with the answer text it refers to and an evidence phrase
located in the sources (same approach as Experiment B).

Citation correctness (claim level) and evidence sufficiency (question level) are scored and reported
**separately**. No score combines them.

---

## 1. Units of analysis

- **Claim**: one factual sentence or line of the answer (as split by `ecorag_verify.py`). Used for citation
  correctness and over-reach (S5).
- **Answer unit**: one fact a complete answer must contain, defined in `gold.json` before the run. Used for
  coverage (S2), independent support (S6) and the failure taxonomy.
- **Question**: used for sufficiency (S1), justification (S3) and calibrated behaviour (S4).

## 2. Answer-unit coverage (S2)

An answer unit is **covered** when the answer states its content correctly:
- numbers match the source exactly or with rounding the source itself uses ("almost 42 per cent" -> "about 42%" is fine);
- the entity, year/period and scope match (a figure "by February 2026" stated as "in 2025" is **not** covered).

A unit stated with a wrong number, date or scope is **not covered** and is also recorded as over-reach (S5).
The regex in `gold.json` is only a pre-check; the manual decision is final and recorded with the answer phrase.

## 3. Conclusion justification (S3)

The **main conclusion** is the set of claims that directly answer the question (framing sentences and
abstention lines excluded). It is judged twice:
- **S3a**: against the union of the passages the answer actually **cites**;
- **S3b**: against the union of **all top-5** passages (whether cited or not).

| Label | Score | Criteria |
|---|---|---|
| **Justified** | 1 | Every claim in the main conclusion is stated by the evidence or follows from it without added assumptions; numbers, dates and scope match; no part of the conclusion depends on information outside the evidence. |
| **Partially justified** | 0.5 | The core of the conclusion is supported, but at least one part is not: a qualifier is changed, an extra detail is unsupported, one of several parts lacks support, or (S3a only) the support exists in the top-5 but not in the cited passages. |
| **Not justified** | 0 | The main conclusion is unsupported or contradicted by the evidence, rests on a different metric/entity/period, or answers a different question. |
| **N/A** | – | The answer abstains completely (no main conclusion); judged under S4 instead. |

For a question whose gold label is *insufficient*, any substantive answer to the asked question is
**not justified** under S3b.

## 4. Over-reach (S5)

A claim is **over-reach** if it asserts something the top-5 evidence does not support. Each claim receives at
most one label (the most severe, in this order):

| Code | Type | Example |
|---|---|---|
| O4 | Fabricated fact or number not in the top-5 (including general knowledge) | an Indian EV sales figure |
| O2 | Substituted metric, entity or period | flexibility-needs growth presented as demand growth; a 2023 figure presented as 2024; a solar salary presented as a heat pump salary |
| O1 | Scope or date shift of a real figure | "5,000 alerts in 2025" (source: cumulative by February 2026); "12% of these alerts" (source: global response rate in 2025) |
| O5 | False corroboration: dependent repeats presented as independent agreement | "several reports confirm 42%" when all repeats trace to GMSR |
| O3 | Unsupported generalisation, causal claim or inference | "this proves the policy works" |

**Not over-reach:** faithful paraphrase; rounding the source uses; correctly attributed alternative estimates
("GMSR estimates USD 98 billion, the IEA about USD 52 billion"); an explicit statement that information is
missing; framing sentences without factual content (counted separately as *filler*).

## 5. Calibrated behaviour and abstention (S4)

Observed behaviour of each answer:

| Behaviour | Definition |
|---|---|
| **FULL** | Answers every part of the question and states no gap. |
| **PARTIAL+GAP** | Answers the supported part(s) and explicitly says the sources lack the other part(s). |
| **ABSTAIN** | States that the sources do not contain enough information and makes no substantive claim answering the question. Mentioning related evidence is allowed only if it is clearly presented as *not* answering the question. |

Rules:
- An abstention line combined with a substantive answer to the missing part is **FULL** (and the extra claims are scored under S5).
- A citation attached to an abstention line does not change the behaviour (recorded as a format issue).
- An answer to a *different* question (e.g. Experiment A's hydrogen-mission line for the EV question) is **FULL** with over-reach, not ABSTAIN.

Correct behaviour by gold label:

| Gold retrieval sufficiency | Correct behaviour |
|---|---|
| sufficient | FULL |
| partial | PARTIAL+GAP |
| insufficient | ABSTAIN |

## 6. Independent support (S6)

For every required answer unit the answer covers:
- count the cited chunks that contain the unit, and the number of **distinct origins** among them (origins are
  defined in `gold.json`: chunks restating the same underlying report, the same chunk overlap, or the same
  document count as **one** origin);
- **dependent multi-citation**: two or more cited chunks for a unit that share one origin (recorded, not an error by itself);
- **false corroboration**: the answer text claims agreement across sources/reports/studies while the gold origin count is 1 (an error; also O5 under S5).

## 7. Failure taxonomy (per required answer unit)

Each required unit receives exactly one primary outcome, checked in this order:

1. **Retrieval failure** – unit exists in the corpus but not in the top-5 (`status = corpus` in `gold.json`). Attributed to retrieval whatever the answer does.
2. **Sufficiency/calibration failure** – the unit is not in the top-5 (`corpus` or `absent`) and the answer nevertheless states a substantive value for it.
3. **Generation failure** – the unit is in the top-5 but the answer omits it or misstates it.
4. **Citation failure** – the unit is stated correctly but the citation attached to it does not contain it (from the claim-level manual review).
5. **Correct** – stated correctly with a supporting citation, or (for units not in the top-5) correctly reported as missing.

## 8. Outlier rule (pre-registered)

An answer is an **outlier** if it exceeds the v3 prompt's 8 claim lines or is cut off at the 400-token cap.
Results are reported pooled, excluding outliers, and as per-question averages; no other exclusions.

## 9. Reviewers

All manual decisions are made by one reviewer (Claude) following this rubric, each recorded with its evidence.
A second, independent review of a stratified subset is offered to the user (`second_reviewer_sheet.csv`); if it
is completed, agreement is reported. Otherwise the results are labelled **single-reviewer**.
