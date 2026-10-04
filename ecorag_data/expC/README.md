# EcoRAG Experiment C – Complete Research Report

## Overview

This directory contains the **complete Experiment C research outputs** for EcoRAG, a beginner-friendly RAG system over environmental and sustainability PDFs.

**Status:** ✅ Final Analysis Complete  
**Date:** 2026-10-04  
**Sample Size:** 27 questions (frozen before execution)  
**Model:** Qwen2.5-3B-Instruct  
**Review:** Single-reviewer manual annotation  

---

## Quick Start

### 📘 For a Presentation
**→ Start here:** `EcoRAG_Experiment_C_Report.pdf` (13 pages)

Professional formatted report with:
- Executive summary
- All 6 evidence sufficiency metrics (S1-S6)
- Citation correctness analysis
- Performance by evidence condition & question type
- Key findings & recommendations

### 📋 For Complete Details
**→ Read:** `RESEARCH_SUMMARY.txt` (~400 lines)

Comprehensive text report with:
- Detailed metric explanations
- All numerical results with fractions (numerator/denominator)
- Performance breakdown by condition, type, and question
- Failure taxonomy
- Sensitivity analysis
- Plain-English findings

### ⚡ For Quick Lookup
**→ Use:** `QUICK_REFERENCE.md` (1 page)

One-page cheat sheet with:
- Key numbers at a glance
- Performance tables
- Critical insights
- What works / what fails
- Recommendations

---

## Key Findings (TL;DR)

| Aspect | Result | Status |
|--------|--------|--------|
| Calibration Accuracy | 70% (19/27) | ⚠️ Acceptable but not robust |
| Citation Correctness | 76% correct (manual review) | ❌ Major issue (24% incorrect) |
| Evidence Utilization | 91% (32/35) | ✅ Strong |
| Content Fully Correct | 67% (18/27) | ⚠️ Acceptable |

### The Problem
The system **over-answers when it shouldn't:**
- When evidence is **sufficient**: ✅ 100% correct (14/14)
- When evidence is **insufficient**: ❌ Only 44% abstain (4/9); 56% over-answer
- When evidence is **partial**: ❌❌ Only 25% handle correctly (1/4)

### The Secondary Problem
Citations are **frequently wrong**, especially in multi-source questions:
- Single-chunk questions: 0% citation error ✓
- Dependent-source questions: **78% citation error** ✗

---

## Files in This Directory

### 📊 Main Outputs (Read These)
```
EcoRAG_Experiment_C_Report.pdf      PDF presentation (13 pages)
RESEARCH_SUMMARY.txt                Full detailed report (~400 lines)
QUICK_REFERENCE.md                  One-page cheat sheet
README.md                            This file
```

### 🔬 Research Data (Frozen, Don't Modify)
```
questions_frozen.json               27 curated questions (FROZEN)
gold.json                           Ground truth labels (FROZEN)
retrieval_snapshot.json             Top-5 retrieved (FROZEN)
rubric.md                           Evaluation rubric (FROZEN)
metrics_spec.md                     Metric definitions
FREEZE_LOG.txt                      Hash verification log
```

### 📈 Results & Analysis (Raw Data)
```
results.json                        Raw model outputs (675 KB)
manual_review.json                  Citation annotations (85 claims)
scores.json                         Computed metrics (all views)
gold_erratum.json                   Post-hoc corrections (Q10, Q18, Q22)

run_output.txt                      Detailed run log (406 KB)
report.txt                          Aggregated results table (46 KB)
run_stderr.txt                      Error log (empty = clean run)
```

### 📄 Supporting Docs
```
gold.txt                            Human-readable gold labels
```

---

## Metrics Explained (S1-S6)

### S1: Retrieval Sufficiency
How much of the required evidence is in the top-5?
- **Result:** 35/45 = 78% of required units were retrieved

### S2: Answer-Unit Coverage
How much retrieved evidence is actually used?
- **S2-gen:** 91% of retrieved units are covered
- **S2-e2e:** 64% of all required units are covered

### S3: Conclusion Justification
Are the model's claims supported by the cited passages?
- **S3a:** 61% mean score (cited passages justify)
- **S3b:** 70% mean score (full top-5 justifies)

### S4: Calibrated Behaviour
Does the model's behaviour match the evidence quality?
- Sufficient → Answer fully: **100%** ✓
- Partial → Answer + state gap: **25%** ✗
- Insufficient → Abstain: **44%** ✗
- **Overall:** 70% accuracy

### S5: Over-Reach Claims
Claims that go beyond retrieved evidence.
- **Total:** 9/86 = 10% of all claims
- **Questions affected:** 6/22 = 27%

### S6: Independent Support
Citation diversity and source binding.
- **Covered units with supporting citations:** 86%
- **Mean distinct origins:** 0.86 (low diversity)

---

## Performance Summary

### By Evidence Condition
| Condition | Questions | Calibration | Content OK | Citations OK |
|-----------|-----------|-------------|------------|--------------|
| Sufficient | 14 | 100% ✓ | 93% | 50% |
| Partial | 4 | 25% ✗ | 25% | 25% |
| Insufficient | 9 | 44% ✗ | 44% | – |

### By Question Type
| Type | Count | Calib. | Content | Citations | Issue |
|------|-------|--------|---------|-----------|-------|
| a (single-chunk) | 6 | 83% | 83% | 83% ✓ | None |
| b (multi-chunk) | 5 | 80% | 60% | 20% | Synthesis citations |
| c (partial) | 5 | 20% | 20% | 20% | WORST |
| d (unanswerable) | 5 | 80% | 80% | 80% | Good |
| e (dependent) | 6 | 83% | 83% | 17% | CITATIONS BROKEN |

---

## Failure Analysis

55 required answer units broke down as:

| Cause | Units | % |
|-------|-------|---|
| Retrieval (in corpus, not top-5) | 10 | 18% |
| Calibration (over-answered weak evidence) | 4 | 7% |
| Generation (retrieved but not used) | 3 | 5% |
| Citation (used but cited wrong) | 5 | 9% |
| **Correct** | **33** | **60%** |

**Primary issues:** Retrieval (18%) + Calibration (7%) = 25%

---

## Critical Issues

### 1. Over-Answering When Evidence Is Missing
- Insufficient evidence: should abstain 9 times, actually does 4 times (44%)
- This is the **PRIMARY FAILURE MODE**

### 2. Multi-Source Citation Confusion
- Dependent-source questions: 78% citation error rate
- System confuses which document supports which claim
- Symptom: correct factual content, wrong source attribution

### 3. Partial Evidence Not Understood
- Only 1 of 4 partial-evidence questions handled correctly (25%)
- System treats partial like absent (over-answers)

### 4. Single Reviewer
- No inter-rater reliability check
- Three post-hoc gold corrections found (Q10, Q18, Q22)
- Results are lower bound on true performance

---

## Reproducibility

✅ **Verified reproducible:**
- Questions 1-6 run in both Experiment B and C
- Answers are byte-identical (greedy decoding)
- Citation metrics identical (6/31 misattributed in both)
- Confirms deterministic system and frozen evidence

---

## Limitations

1. **Small sample:** 27 questions (22 with substantive answers)
2. **Single reviewer:** No agreement checking
3. **One model:** Results specific to Qwen2.5-3B
4. **Frozen configuration:** No ablations tested
5. **Post-hoc errors:** Three gold corrections needed after run

---

## Recommendations for Experiment D

1. **Add calibration awareness** – Tell model when confidence should be low
2. **Fix citation binding** – Track source→claim explicitly
3. **Handle partial evidence** – Special prompting for incomplete answers
4. **Multi-source reasoning** – Explicit tracking across documents
5. **Expand evaluation** – 100+ questions, second reviewer
6. **Different models** – Test generalization beyond Qwen2.5-3B

---

## How to Use These Reports

### For Stakeholders / Management
👉 Read: `EcoRAG_Experiment_C_Report.pdf`

### For Researchers / Engineers
👉 Read: `RESEARCH_SUMMARY.txt` + examine `scores.json`

### For Quick Briefings
👉 Use: `QUICK_REFERENCE.md`

### For Reproducibility
👉 See: `FREEZE_LOG.txt` for hash verification

### For Next Experiment
👉 Reference: `gold_erratum.json` and `sensitivity` section of `scores.json`

---

## Data Integrity

All frozen artifacts have been verified:
- ✓ `questions_frozen.json` – Unchanged
- ✓ `gold.json` – Unchanged
- ✓ `retrieval_snapshot.json` – Unchanged
- ✓ `results.json` – Unchanged (raw model outputs)
- ✓ `run_output.txt` – Unchanged (complete run log)

Hash verification: See `FREEZE_LOG.txt`

---

## Citation

If you use these results, cite:
```
EcoRAG Experiment C: Evidence Sufficiency and Citation Correctness Evaluation
Generated: 2026-10-04
Dataset: 27 environmental sustainability questions
Model: Qwen2.5-3B-Instruct
Review: Single-reviewer manual annotation
```

---

## Contact & Questions

For detailed metric explanations, see `metrics_spec.md`

For evaluation rubric details, see `rubric.md`

For complete results data, access `scores.json` directly (JSON format, all aggregates)

---

**Status:** ✅ Final Analysis Complete  
**Integrity:** ✅ Frozen artifacts verified  
**Reproducibility:** ✅ Q01-Q06 byte-identical  
**Review:** ⚠️ Single-reviewer (limitations noted)
