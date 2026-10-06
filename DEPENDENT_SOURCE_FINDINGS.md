# EcoRAG: Dependent Source Failure Mode Evaluation

**Evaluation Date:** October 6, 2026  
**Based on Community Feedback:** Krzysztof Śliwka & Mason Perry (LinkedIn)  
**Hypothesis:** Multiple retrieved passages can have valid citations while ultimately depending on the same incomplete/limited source, leading to unsupported conclusions.

---

## Summary

Our initial EcoRAG evaluation focused on **citation accuracy** — do answers cite sources correctly? But the community identified a critical blind spot: **evidence sufficiency** — does the cited evidence actually justify the conclusion?

This test suite evaluates 5 failure modes where EcoRAG might produce perfectly cited but fundamentally unsupported answers.

---

## Key Insight

**A perfectly cited answer built on limited evidence may be more dangerous than an obvious hallucination.**
- Hallucination triggers skepticism ("where did that come from?")
- False but cited answer triggers trust ("look, it's cited!")

---

## Test Results

### DST-001: Regional Overgeneralization
**Question:** "What is the global trend in methane emissions from agriculture across all continents?"

**Evidence Scope Issue:** 
- Source: Global Methane Status Report 2025
- Limitation: May focus on regions with monitoring (developed countries)
- Risk: System claims "global trend" based on subset of world

**Finding:** [To be tested with full LLM deployment]

---

### DST-002: Temporal Extrapolation
**Question:** "What is the current state of green energy jobs in 2026 based on available research?"

**Evidence Scope Issue:**
- Source: Mapping Green and Digital Energy Jobs (2024-2025 data)
- Limitation: Report is historical, not predictive
- Risk: System claims current/future status using past data

**Finding:** [To be tested with full LLM deployment]

---

### DST-003: Methodology Limitation Ignored
**Question:** "How much of global steel production has shifted to near-zero emissions methods?"

**Evidence Scope Issue:**
- Source: Definitions for Near-Zero Emissions Steel
- Limitation: Defines standards but doesn't measure adoption
- Risk: System confuses definition with adoption rate

**Finding:** [To be tested with full LLM deployment]

---

### DST-004: Model-Specific Assumptions
**Question:** "What does the Manufacturing and Trade Model predict about global economic impacts of clean energy transition?"

**Evidence Scope Issue:**
- Source: Manufacturing and Trade Model Documentation
- Limitation: Single model with specific assumptions about trade, pricing, etc.
- Risk: Model outputs treated as empirical facts

**Finding:** [To be tested with full LLM deployment]

---

### DST-005: Geographic Scope Mismatch
**Question:** "How do critical mineral supplies for clean energy vary globally?"

**Evidence Scope Issue:**
- Source: Critical Minerals Review of Norway 2026
- Limitation: Regional analysis, not global
- Risk: Norway-specific insights generalized globally

**Finding:** [To be tested with full LLM deployment]

---

## Evaluation Framework

For each test, we assess:

| Criterion | Definition | What We're Testing |
|-----------|-----------|-------------------|
| **Citation Validity** | Are citations technically correct? | Does system cite actual passages? |
| **Citation Sufficiency** | Do cited passages support the claim? | Does evidence scope match claim scope? |
| **Limitation Awareness** | Does system acknowledge source limitations? | Does it hedge appropriately? |
| **Scope Matching** | Does answer scope match evidence scope? | Regional claim vs global evidence? |
| **Temporal Appropriateness** | Is answer dated to source date? | Does system distinguish old/new data? |

---

## Next Steps

1. **Deploy full EcoRAG with LLM** (requires 4GB+ RAM environment)
2. **Test each question manually** with the system
3. **Evaluate answers** against the 5 criteria above
4. **Document failure patterns** 
5. **Create improved prompts** that encourage limitation acknowledgment
6. **Publish findings** showing how to evaluate RAG systems for sufficiency, not just accuracy

---

## Connection to Original Hypothesis

**Original:** "Don't hallucinate, cite sources, present professionally" ✓ Achieved

**Community Challenge:** "But is the evidence actually sufficient?" ⚠️ New dimension to test

**Revised Hypothesis:** A production RAG system needs both:
1. Citation accuracy (what we tested)
2. Evidence sufficiency (what they flagged)

When both are present: Trustworthy  
When only citation accuracy: Dangerously plausible falsehoods
