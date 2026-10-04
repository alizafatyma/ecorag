# EcoRAG Experiment C – Metric specification (frozen before any Experiment C generation)

Fixed system: v4.4 chunks · BGE `bge-small-en-v1.5` · Chroma · top-5 content/table · Qwen2.5-3B-Instruct ·
v3 prompt (unchanged) · greedy · bf16 · max 400 new tokens · CPU.
Inputs: `questions_frozen.json`, `retrieval_snapshot.json`, `gold.json`, `rubric.md`.
The run aborts if any question's live top-5 differs from the snapshot.

## Citation correctness (claim level) – reported separately, as in Experiments A/B
- Verifier (unchanged `ecorag_verify.py`): factual claims, claims with a citation (coverage), potentially
  supported, partially supported, misattributed, misattributed / cited.
- Manual review: supported / minor distortion / partial / misattributed / misattributed per cited claim,
  each decision with an evidence phrase.

## Evidence sufficiency (question level)

| Metric | Per question | Aggregate |
|---|---|---|
| **S1 Retrieval sufficiency** | gold label: sufficient (all required units in top-5) / partial (some) / insufficient (none) | count per label; S1 = sufficient / 27; unit retrieval recall = required units in top-5 / required units present in the corpus |
| **S2 Answer-unit coverage** | S2-gen = covered required units / required units in top-5 (undefined if 0); S2-e2e = covered required units / all required units | pooled (sum/sum), per-question mean, by type |
| **S3 Conclusion justification** | S3a (cited passages) and S3b (all top-5): justified 1 / partial 0.5 / not 0; N/A if full abstention | label distribution and mean score over answering questions |
| **S4 Calibrated behaviour** | observed FULL / PARTIAL+GAP / ABSTAIN vs gold sufficient / partial / insufficient | 3x3 confusion matrix; calibration accuracy = diagonal / 27; abstention recall = ABSTAIN on insufficient / insufficient; false abstention = ABSTAIN on sufficient / sufficient |
| **S5 Over-reach** | over-reach claims (O1–O5) | over-reach claims / factual claims; questions with >= 1 over-reach / answering questions; counts by type |
| **S6 Independent support** | per covered unit: cited supporting chunks and distinct origins | mean distinct origins per covered unit; dependent multi-citations; false corroborations |

## Failure taxonomy (per required unit; priority order in rubric section 7)
retrieval failure · sufficiency/calibration failure · generation failure · citation failure · correct.

## Reporting views (all metrics)
1. pooled; 2. excluding pre-registered outliers (rubric section 8); 3. per-question average;
4. by question type (a–e); 5. continuity subset Q01–Q06 vs Experiment B (same model, prompt and evidence:
   answers are expected to be identical under greedy decoding — reported as a reproducibility check).

## Not done in Experiment C
No prompt, retrieval or model changes; no sufficiency-aware prompt; no optimisation on these results
(any improvement is Experiment D).
