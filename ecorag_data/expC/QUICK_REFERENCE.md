# EcoRAG Experiment C – Quick Reference Card

## Key Numbers at a Glance

| Metric | Value | Status |
|--------|-------|--------|
| **Calibration Accuracy** | 19/27 = 70% | ⚠️ Acceptable |
| **Content Fully Correct** | 18/27 = 67% | ⚠️ Acceptable |
| **Citations Incorrect** | 20/85 = 24% | ❌ Major Issue |
| **Evidence Coverage** | 32/35 = 91% | ✅ Strong |
| **Questions Tested** | 27 (frozen) | – |
| **Model** | Qwen2.5-3B (CPU) | – |

---

## Performance by Evidence Condition

### When Evidence IS Available (Sufficient)
- **Calibration:** 14/14 = **100%** ✅
- **Content OK:** 13/14 = **93%** ✅
- **Citations OK:** 7/14 = **50%** ⚠️

**→ The system excels when evidence exists.**

### When Evidence Is MISSING (Insufficient)
- **Abstain Rate:** 4/9 = **44%** ❌
- **Over-Answer Rate:** 5/9 = **56%** ❌
- **Content OK:** 4/9 = **44%** ❌

**→ The system FAILS by over-answering instead of abstaining.**

### When Evidence Is PARTIAL
- **Calibration:** 1/4 = **25%** ❌❌

**→ Worst performance. System can't handle incomplete evidence.**

---

## Performance by Question Type

| Type | Category | Calib. | Citations | Issue |
|------|----------|--------|-----------|-------|
| **a** | Single chunk | 83% | 83% ✅ | None – works great |
| **b** | Multi-chunk | 80% | 20% ❌ | Citations break on synthesis |
| **c** | Partial | 20% ❌❌ | 20% | Worst type – can't handle gaps |
| **d** | Unanswerable | 80% | 80% | Good – knows when to abstain |
| **e** | Multi-source | 83% | 17% ❌❌ | Citations confused across docs |

**→ Worst performance: Type C (partial) and Type E (multi-source citations)**

---

## Citation Correctness Breakdown

**Manual Review (85 cited claims):**
- Supported: 65 = **76%** ✓
- Misattributed: 11 = **13%**
- Unsupported: 9 = **11%**
- **INCORRECT TOTAL: 20 = 24%** ❌

**Per Question Average:**
- Error rate: **0.33** (1 in 3 claims wrong on average)

**Most Problematic:**
- Dependent-source questions: **78% error** ❌❌
- Single-chunk questions: **0% error** ✅

---

## Failure Taxonomy (55 Required Units)

| Type | Count | % | Root Cause |
|------|-------|---|------------|
| Retrieval | 10 | 18% | Wasn't in top-5 |
| Calibration | 4 | 7% | Over-answered weak evidence |
| Generation | 3 | 5% | Retrieved but not used |
| Citation | 5 | 9% | Used but cited wrong |
| **CORRECT** | **33** | **60%** | All OK |

**→ Largest problems: Retrieval (18%) + Calibration (7%)**

---

## Critical Insights

### ✅ What Works Well
1. **Using available evidence** – 91% coverage of top-5
2. **Single-source synthesis** – 83% accuracy on simple questions
3. **Knowing what to skip** – 80% correct on unanswerable questions
4. **Reading comprehension** – Only 5% generation failures

### ❌ What Fails
1. **Knowing when to abstain** – Only 44% abstention on missing evidence
2. **Multi-source reasoning** – 78% citation errors on dependent questions
3. **Partial evidence** – 25% calibration on incomplete answers
4. **Citation binding** – 24% of claims cite wrong sources

### The Core Problem
**The model over-answers.**
- When evidence is absent → it answers anyway (5/9 times)
- When evidence is partial → it treats it like no evidence and answers fully
- When evidence is multi-source → it gets confused about what came from where

---

## What We DON'T Know

- ❓ Would other models have same problems?
- ❓ Would a larger model (7B+) calibrate better?
- ❓ Would different prompting help?
- ❓ What if we used different retrieval (BM25, re-ranking)?
- ❓ Does a second reviewer agree? (Only 1 reviewer did this)
- ❓ How much does this generalize beyond 27 questions?

---

## Recommendations (Priority Order)

1. **Add calibration signal** – Tell the model when evidence is weak
2. **Fix citation binding** – Track which document supports which claim
3. **Handle partial evidence** – Special prompting for incomplete answers
4. **Expand test set** – 27 questions is small; need 100+
5. **Get second reviewer** – Validate the citation judgments

---

## Files in This Report

- `RESEARCH_SUMMARY.txt` – Full detailed results with all metrics and numbers
- `EcoRAG_Experiment_C_Report.pdf` – Formatted presentation (10 pages)
- `QUICK_REFERENCE.md` – This card (quick lookup)

- `results.json` – Raw model outputs (frozen, unchanged)
- `gold.json` – Ground truth labels (frozen, unchanged)
- `manual_review.json` – Citation annotations (85 claims manually reviewed)
- `scores.json` – All computed metrics
- `report.txt` – Aggregated results table

---

## Research Integrity

✅ Frozen before run (questions, gold, prompt, model)  
✅ No changes during execution (run aborted on mismatch)  
✅ Manual review done post-hoc (not changing raw outputs)  
✅ Reproducible (Q01-Q06 byte-identical to Experiment B)  
❓ Single reviewer (no inter-rater reliability check)  
⚠️ Three post-hoc gold corrections (Q10, Q18, Q22)  

---

**Generated:** 2026-10-04  
**Status:** Final Analysis (Primary results use frozen gold)
