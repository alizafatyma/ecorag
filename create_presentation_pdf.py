#!/usr/bin/env python3
"""EcoRAG Experiment C - Comprehensive PDF Presentation"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, white
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, KeepTogether
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
import json
from datetime import datetime
from pathlib import Path

EXP = Path("ecorag_data/expC")
output_file = "ecorag_data/expC/EcoRAG_Experiment_C_Report.pdf"

results = json.loads((EXP / "results.json").read_text(encoding="utf-8"))
gold = json.loads((EXP / "gold.json").read_text(encoding="utf-8"))["questions"]
manual_review = json.loads((EXP / "manual_review.json").read_text(encoding="utf-8"))
scores = json.loads((EXP / "scores.json").read_text(encoding="utf-8"))

pdf = SimpleDocTemplate(output_file, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch,
                        leftMargin=0.75*inch, rightMargin=0.75*inch, title="EcoRAG Experiment C")

styles = getSampleStyleSheet()
title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=24,
                             textColor=HexColor('#1a3d5c'), spaceAfter=12, alignment=TA_CENTER, fontName='Helvetica-Bold')
heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'], fontSize=14,
                               textColor=HexColor('#2d5a7b'), spaceAfter=10, spaceBefore=10, fontName='Helvetica-Bold')
subheading_style = ParagraphStyle('SubHeading', parent=styles['Heading3'], fontSize=11,
                                  textColor=HexColor('#4a7ba7'), spaceAfter=6, fontName='Helvetica-Bold')
body_style = ParagraphStyle('CustomBody', parent=styles['BodyText'], fontSize=9, alignment=TA_JUSTIFY, spaceAfter=8, leading=11)
normal_style = ParagraphStyle('Normal', parent=styles['BodyText'], fontSize=9, spaceAfter=6)

def create_header(title, subtitle=""):
    elements = [Paragraph(title, heading_style)]
    if subtitle:
        elements.append(Paragraph(subtitle, normal_style))
    elements.append(Spacer(1, 0.15*inch))
    return elements

def create_metric_table(data, widths=None):
    if widths is None:
        widths = [3.5*inch, 1.5*inch]
    table = Table(data, colWidths=widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#4a7ba7')),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, HexColor('#f0f5f9')]),
    ]))
    return table

story = []

# TITLE PAGE
story.append(Spacer(1, 1.5*inch))
story.append(Paragraph("EcoRAG", ParagraphStyle('Title', parent=styles['Heading1'], fontSize=28,
                       textColor=HexColor('#1a3d5c'), alignment=TA_CENTER, fontName='Helvetica-Bold')))
story.append(Paragraph("Experiment C", ParagraphStyle('Subtitle', parent=styles['Heading2'], fontSize=18,
                       textColor=HexColor('#4a7ba7'), alignment=TA_CENTER, fontName='Helvetica')))
story.append(Spacer(1, 0.3*inch))
story.append(Paragraph("Evidence Sufficiency & Citation Correctness Evaluation", normal_style))
story.append(Spacer(1, 0.2*inch))
story.append(Paragraph(f"<b>Generated:</b> {datetime.now().strftime('%B %d, %Y')}", normal_style))
story.append(Paragraph("<b>Dataset:</b> 27 Environmental & Sustainability Questions", normal_style))
story.append(Paragraph("<b>Model:</b> Qwen2.5-3B-Instruct (CPU, bf16)", normal_style))
story.append(Paragraph("<b>Embeddings:</b> BGE bge-small-en-v1.5 (384 dim)", normal_style))
story.append(Paragraph("<b>Review:</b> Single-reviewer manual annotation", normal_style))
story.append(PageBreak())

# EXECUTIVE SUMMARY
story.extend(create_header("Executive Summary"))
story.append(Paragraph(
    "<b>Key Finding:</b> EcoRAG demonstrates consistent answer generation with strong evidence utilization "
    "(91% coverage of available sources) but significant weaknesses in calibration (70% accuracy) and citation "
    "correctness (24% of claims incorrectly attributed). The system reliably answers when evidence is sufficient "
    "(100% accuracy, 14/14 questions) but fails to abstain when evidence is insufficient (44% abstention recall, 4/9 questions).",
    body_style
))
story.append(Spacer(1, 0.15*inch))

summary_data = [
    ["Metric", "Result"],
    ["Total Questions", "27 (frozen)"],
    ["Questions with Sufficient Evidence", "14/27 (52%)"],
    ["Overall Calibration Accuracy", "19/27 (70%)"],
    ["Answer Content Fully Correct", "18/27 (67%)"],
    ["Citations Incorrect (Manual)", "20/85 (24%)"],
    ["Evidence Coverage in Top-5", "32/35 (91%)"],
    ["Reviewers", "1 (single-reviewer)"],
]
story.append(create_metric_table(summary_data))
story.append(PageBreak())

# OVERVIEW
story.extend(create_header("1. Overview & Methodology"))
story.append(Paragraph("<b>Objective:</b>", subheading_style))
story.append(Paragraph(
    "Measure EcoRAG's ability to retrieve evidence, generate grounded answers, and provide correct citations.",
    body_style
))
story.append(Spacer(1, 0.1*inch))

story.append(Paragraph("<b>Question Set (n=27):</b>", subheading_style))
question_types = [
    ["Type", "Category", "Count", "Purpose"],
    ["a", "Single-chunk questions", "6", "Highest retrievability"],
    ["b", "Multi-chunk questions", "5", "Requires synthesis"],
    ["c", "Partially answerable", "5", "Incomplete evidence"],
    ["d", "Unanswerable", "5", "No relevant evidence"],
    ["e", "Dependent-source", "6", "Cross-document dependency"],
]
story.append(create_metric_table(question_types, widths=[0.8*inch, 1.8*inch, 0.6*inch, 1.5*inch]))
story.append(PageBreak())

# METRICS
story.extend(create_header("2. Evidence Sufficiency Metrics (S1–S6)"))

story.append(Paragraph("<b>S1: Retrieval Sufficiency</b>", subheading_style))
s1_data = [
    ["Sufficiency Level", "Count", "Percentage"],
    ["Sufficient", "14", "52%"],
    ["Partial", "4", "15%"],
    ["Insufficient", "9", "33%"],
    ["Unit Retrieval Recall", "35/45", "78%"],
]
story.append(create_metric_table(s1_data))
story.append(Spacer(1, 0.1*inch))

story.append(Paragraph("<b>S2: Answer-Unit Coverage</b>", subheading_style))
s2_data = [
    ["Metric", "Pooled", "Per-Question Avg"],
    ["S2-gen (in top-5)", "32/35 = 91%", "0.89"],
    ["S2-e2e (all required)", "35/55 = 64%", "0.62"],
]
story.append(create_metric_table(s2_data))
story.append(Spacer(1, 0.1*inch))

story.append(Paragraph("<b>S3: Conclusion Justification</b>", subheading_style))
s3_data = [
    ["Metric", "Distribution", "Mean Score"],
    ["S3a (cited passages)", "10 just / 7 part / 5 not (n=22)", "0.61"],
    ["S3b (full top-5)", "14 just / 3 part / 5 not (n=22)", "0.70"],
]
story.append(create_metric_table(s3_data))
story.append(Spacer(1, 0.1*inch))

story.append(Paragraph("<b>S4: Calibrated Behaviour</b>", subheading_style))
s4_data = [
    ["Condition", "Count", "Accuracy"],
    ["Sufficient → FULL", "14/14", "100%"],
    ["Partial → PARTIAL+GAP", "1/4", "25%"],
    ["Insufficient → ABSTAIN", "4/9", "44%"],
    ["Overall Calibration", "19/27", "70%"],
]
story.append(create_metric_table(s4_data))
story.append(PageBreak())

# CITATION
story.extend(create_header("3. Citation Correctness"))

story.append(Paragraph("<b>Verifier Results:</b>", subheading_style))
verifier_data = [
    ["Metric", "Count", "Rate"],
    ["Claims with citations", "81/82", "99%"],
    ["Misattributed", "10/81", "12%"],
    ["Potentially supported", "68/81", "84%"],
]
story.append(create_metric_table(verifier_data))
story.append(Spacer(1, 0.1*inch))

story.append(Paragraph("<b>Manual Review Results:</b>", subheading_style))
manual_data = [
    ["Status", "Count", "Rate"],
    ["Supported", "65/85", "76%"],
    ["Misattributed", "11/85", "13%"],
    ["Unsupported", "9/85", "11%"],
    ["<b>Incorrect Total</b>", "<b>20/85</b>", "<b>24%</b>"],
]
story.append(create_metric_table(manual_data))
story.append(PageBreak())

# FAILURE TAXONOMY
story.extend(create_header("4. Failure Taxonomy"))
taxonomy_data = [
    ["Failure Category", "Units", "Percentage"],
    ["Retrieval Failure", "10", "18%"],
    ["Calibration/Sufficiency", "4", "7%"],
    ["Generation Failure", "3", "5%"],
    ["Citation Failure", "5", "9%"],
    ["<b>Correct</b>", "<b>33</b>", "<b>60%</b>"],
]
story.append(create_metric_table(taxonomy_data))
story.append(PageBreak())

# BY GOLD CONDITION
story.extend(create_header("5. Results by Evidence Condition"))

story.append(Paragraph("<b>Sufficient Evidence (14 questions):</b>", subheading_style))
suff_data = [
    ["Metric", "Value"],
    ["Calibration (FULL)", "14/14 = 100%"],
    ["Content fully correct", "13/14 = 93%"],
    ["All citations correct", "7/14 = 50%"],
]
story.append(create_metric_table(suff_data))
story.append(Spacer(1, 0.1*inch))

story.append(Paragraph("<b>Insufficient Evidence (9 questions):</b>", subheading_style))
insuff_data = [
    ["Metric", "Value"],
    ["Abstention recall", "4/9 = 44%"],
    ["Over-answered", "5/9 = 56%"],
    ["Content fully correct", "4/9 = 44%"],
]
story.append(create_metric_table(insuff_data))
story.append(PageBreak())

# BY TYPE
story.extend(create_header("6. Results by Question Type"))
type_summary = [
    ["Type", "Calib. Acc.", "Content OK", "Cit. Correct", "Finding"],
    ["a (single-chunk)", "83%", "83%", "83%", "Excellent"],
    ["b (multi-chunk)", "80%", "60%", "20%", "Citations weak"],
    ["c (partial)", "20%", "20%", "20%", "Hardest"],
    ["d (unanswerable)", "80%", "80%", "80%", "Good abstention"],
    ["e (dependent)", "83%", "83%", "17%", "Citations broken"],
]
story.append(create_metric_table(type_summary, widths=[0.7*inch, 0.8*inch, 0.8*inch, 0.9*inch, 1.2*inch]))
story.append(PageBreak())

# FINDINGS
story.extend(create_header("7. What This Experiment Tells Us"))

story.append(Paragraph(
    "<b style='font-size:11pt'>1. Strong evidence utilization.</b> "
    "When required units are in top-5, EcoRAG answers correctly 100% of the time. "
    "It covers 91% of available sources and justifies 70% of claims.",
    body_style
))
story.append(Spacer(1, 0.1*inch))

story.append(Paragraph(
    "<b style='font-size:11pt'>2. Calibration failure.</b> "
    "When evidence is insufficient, the model should abstain. It does so only 44% of the time, "
    "answering anyway by substituting related entities or generalizing beyond scope.",
    body_style
))
story.append(Spacer(1, 0.1*inch))

story.append(Paragraph(
    "<b style='font-size:11pt'>3. Citation errors.</b> "
    "24% of cited claims incorrectly point to sources. This is especially severe in dependent-source questions (78% incorrect).",
    body_style
))
story.append(Spacer(1, 0.1*inch))

story.append(Paragraph(
    "<b style='font-size:11pt'>4. Retrieval is secondary.</b> "
    "18% of required units are not retrieved. The bigger problem is over-answering when evidence is absent.",
    body_style
))
story.append(Spacer(1, 0.1*inch))

story.append(Paragraph(
    "<b style='font-size:11pt'>5. Single reviewer, frozen rubric.</b> "
    "27 questions with 3 post-hoc corrections found. Results are lower bound on agreement.",
    body_style
))
story.append(PageBreak())

# APPENDIX
story.extend(create_header("Appendix: Source Documents"))
story.append(Paragraph("9 PDFs, 1,242 chunks:", subheading_style))
pdfs_data = [
    ["Document", "Chunks", "Topic"],
    ["GMSR 2025", "~500", "Global Methane & Sustainability"],
    ["Mapping Green Jobs", "~200", "Energy Job Mapping"],
    ["Modernising Grids", "~180", "Grid Infrastructure"],
    ["Managing Seasonal Electricity", "~130", "Demand/Supply"],
    ["Critical Minerals", "~80", "Norway Minerals"],
    ["Other", "~152", "Finance, standards, policy"],
]
story.append(create_metric_table(pdfs_data, widths=[2.5*inch, 0.8*inch, 1.9*inch]))
story.append(Spacer(1, 0.3*inch))
story.append(Paragraph(
    f"<b>Report generated:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}<br/>"
    f"<b>Design:</b> Frozen before run; single reviewer; manual review post-hoc.",
    normal_style
))

pdf.build(story)
print(f"✓ PDF created: {output_file}")
print(f"  File size: {Path(output_file).stat().st_size / (1024*1024):.2f} MB")
