"""
EcoRAG: Dependent Source Failure Mode Test
============================================================
Test hypothesis: Multiple retrieved passages can have valid citations
while ultimately depending on the same incomplete/limited source,
leading to unsupported conclusions.

Based on feedback from Krzysztof Śliwka & Mason Perry
"""

DEPENDENT_SOURCE_TEST_CASES = [
    {
        "id": "DST-001",
        "category": "Regional Overgeneralization",
        "question": "What is the global trend in methane emissions from agriculture across all continents?",
        "expected_failure": "System may cite passages from global methane report, but if most passages come from regions with available data (developed countries), it might generalize to claim global trends when data is incomplete.",
        "source_dependency": "Global Methane Status Report 2025 (likely focused on regions with monitoring)",
        "what_evidence_lacks": "Coverage of emissions measurement in developing nations"
    },
    {
        "id": "DST-002",
        "category": "Temporal Extrapolation",
        "question": "What is the current state of green energy jobs in 2026 based on the available research?",
        "expected_failure": "Multiple passages might cite job statistics, but if all come from 2024-2025 reports, the system shouldn't claim knowledge of 2026 trends.",
        "source_dependency": "Mapping Green and Digital Energy Jobs (dated report)",
        "what_evidence_lacks": "Current 2026 data - sources are historical"
    },
    {
        "id": "DST-003",
        "category": "Methodology Limitation Ignored",
        "question": "How much of global steel production has shifted to near-zero emissions methods?",
        "expected_failure": "Citations might look valid from Steel & Cement definitions document, but the source may only define standards without measuring actual adoption rates.",
        "source_dependency": "Definitions for Near-Zero Emissions Steel (definition document, not adoption survey)",
        "what_evidence_lacks": "Actual market penetration/adoption data"
    },
    {
        "id": "DST-004",
        "category": "Model-Specific Limitations",
        "question": "What does the Manufacturing and Trade Model predict about global economic impacts of clean energy transition?",
        "expected_failure": "System might cite model outputs as if they're empirical facts, but models have assumptions that limit generalizability.",
        "source_dependency": "Manufacturing and Trade Model Documentation (single model with specific assumptions)",
        "what_evidence_lacks": "Validation against multiple independent models or empirical data"
    },
    {
        "id": "DST-005",
        "category": "Geographic Scope Mismatch",
        "question": "How do critical mineral supplies for clean energy vary globally?",
        "expected_failure": "Multiple passages might cite mineral data, but if Critical Minerals Review focuses on Norway, system shouldn't claim global supply insights.",
        "source_dependency": "Critical Minerals Review of Norway 2026 (regional, not global)",
        "what_evidence_lacks": "Global supply chain data - sources are Norway-specific"
    }
]

EVALUATION_CRITERIA = {
    "citation_validity": "Are citations technically correct?",
    "citation_sufficiency": "Do cited passages actually support the claim?",
    "source_limitation_awareness": "Does system acknowledge source limitations?",
    "scope_matching": "Does conclusion scope match evidence scope?",
    "temporal_appropriateness": "Is answer dated to source publication date?"
}

print("""
╔════════════════════════════════════════════════════════════════╗
║     EcoRAG: Dependent Source Failure Mode Test Suite           ║
║                                                                ║
║  Hypothesis: Valid citations ≠ justified conclusions          ║
║                                                                ║
║  Tests identify cases where EcoRAG retrieves correctly but     ║
║  makes claims beyond what evidence actually supports           ║
╚════════════════════════════════════════════════════════════════╝

Test Cases:
""")

for i, test in enumerate(DEPENDENT_SOURCE_TEST_CASES, 1):
    print(f"\n{i}. {test['id']}: {test['category']}")
    print(f"   Question: {test['question']}")
    print(f"   Potential Issue: {test['expected_failure']}")
    print(f"   Source Dependency: {test['source_dependency']}")
    print(f"   Evidence Gap: {test['what_evidence_lacks']}")

print(f"\n\nEvaluation Criteria:")
for criterion, description in EVALUATION_CRITERIA.items():
    print(f"  • {criterion}: {description}")

print(f"\n\nTo run this test:")
print(f"  1. For each test case, ask EcoRAG the question")
print(f"  2. Evaluate using criteria above")
print(f"  3. Document whether answer scope exceeds evidence scope")
print(f"  4. Note any limitations the system acknowledges")
