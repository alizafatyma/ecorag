# 🌿 EcoRAG: Environmental RAG System

A beginner-friendly **Retrieval-Augmented Generation (RAG)** system for environmental and sustainability research questions.

## ✨ Features

- 📄 **Document Chunking**: Structural-aware PDF parsing with PyMuPDF
- 🔍 **Semantic Search**: BGE embeddings (384-dim) with Chroma vector database
- 🤖 **Multi-Model Support**: Qwen2.5-1.5B & 3B models (local, CPU-friendly)
- 🔗 **Citation Verification**: Deterministic citation validation & evidence grounding
- 📊 **Evidence Metrics**: S1-S6 framework measuring answer quality
- 🎨 **Interactive UI**: Beautiful green-themed web interface

## 🚀 Live Demo

Try the interactive frontend:
- **Netlify**: [ecorag.netlify.app](https://ecorag.netlify.app)
- **GitHub Pages**: [github.com/username/ecorag](https://github.com/username/ecorag)

## 📊 Research Evaluation

This repository includes results from **Experiment C**: a rigorous evaluation of evidence sufficiency and citation correctness.

### Key Metrics (27 Questions)
| Metric | Result | Status |
|--------|--------|--------|
| Calibration Accuracy | 70% (19/27) | ⚠️ Acceptable |
| Citation Correctness | 76% (65/85) | ⚠️ Needs work |
| Evidence Coverage | 91% (32/35) | ✅ Strong |
| Answer Content Correct | 67% (18/27) | ⚠️ Acceptable |

### Key Finding
✅ **What Works**: Perfect accuracy when evidence exists (100% on sufficient data)  
❌ **Main Issue**: Over-answers when evidence is missing (56% when should abstain)  
❌ **Secondary**: Multi-source citation errors (78% in dependent-source questions)

## 📈 Experiment Results

- **Experiment A**: Citation format variations (v2 vs v3 prompt)
- **Experiment B**: Model size comparison (1.5B vs 3B)
- **Experiment C**: Evidence sufficiency evaluation (27 questions, manual review)

See [`ecorag_data/expC/`](ecorag_data/expC/) for complete analysis:
- [`EcoRAG_Experiment_C_Professional_Report.pdf`](ecorag_data/expC/EcoRAG_Experiment_C_Professional_Report.pdf) - Professional report (green theme)
- [`RESEARCH_SUMMARY.txt`](ecorag_data/expC/RESEARCH_SUMMARY.txt) - Detailed analysis
- [`QUICK_REFERENCE.md`](ecorag_data/expC/QUICK_REFERENCE.md) - One-page summary

## 🎯 Quick Start

### Try the Interactive Frontend
```bash
# Open in your browser
ecorag_frontend.html
```

### Run Locally
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Build chunks from PDFs
python ecorag_build_chunks.py

# 3. Generate embeddings
python ecorag_embeddings.py

# 4. Build vector database
python ecorag_build_chroma.py

# 5. Ask questions
python ecorag_ask.py
```

### Python Usage
```python
from ecorag_ask import ask_ecorag

# Ask a question
result = ask_ecorag("What is being done to reduce methane emissions by 2030?")
print(result["answer"])
print(result["sources"])  # Cited passages
```

## 🏗️ System Architecture

```
PDFs (9 docs, 1.2K chunks)
    ↓
[Chunking: v4.4 - Structural, 512-token max]
    ↓
[BGE Embeddings: 384-dimensional]
    ↓
[Chroma Vector DB: 1,242 vectors]
    ↓
[Top-5 Semantic Retrieval]
    ↓
[Qwen2.5-3B: Prompt v3, Greedy]
    ↓
[Citation Verifier: Deterministic]
    ↓
Answer + Citations + Evidence
```

## 📊 Source Documents

The system is trained on 9 environmental sustainability PDFs:

1. **GMSR 2025** (~500 chunks) - Global Methane & Sustainability Review
2. **Mapping Green & Digital Energy Jobs** (~200 chunks)
3. **Modernising Grids in the Age of Electricity** (~180 chunks)
4. **Managing Seasonal Variability of Electricity** (~130 chunks)
5. **Critical Minerals Review of Norway 2026** (~80 chunks)
6. **Reducing Cost of Capital** (~60 chunks)
7. **Definitions for Low-Emissions Steel/Cement** (~70 chunks)
8. **Manufacturing and Trade Model Documentation** (~90 chunks)
9. **UN SG Call to Action on Methane by 2030** (~60 chunks)

**Total**: 1,242 chunks, covering sustainability topics

## 🔧 Technical Stack

| Component | Technology | Details |
|-----------|-----------|---------|
| **Chunking** | PyMuPDF, pymupdf4llm | v4.4 (structural, 512-token max) |
| **Embeddings** | BGE (sentence-transformers) | 384 dimensions, semantic search |
| **Vector DB** | Chroma | 1,242 vectors, cosine similarity |
| **LLM** | Qwen2.5 | 1.5B & 3B variants, CPU-friendly |
| **Frontend** | HTML/CSS/JavaScript | Green theme, responsive design |
| **Citation Verification** | Custom Python | Deterministic regex & matching |

## 📈 Performance by Evidence Condition

| Evidence Level | Accuracy | Issue |
|----------------|----------|-------|
| ✅ Sufficient | 100% | None |
| ⚠️ Partial | 25% | Mostly fails |
| ❌ Insufficient | 44% | Over-answers 56% |

## 🔍 Failure Analysis (55 Units)

| Type | Count | % | Issue |
|------|-------|---|-------|
| Retrieval Failure | 10 | 18% | Unit in corpus, not top-5 |
| Calibration Failure | 4 | 7% | Over-answered weak evidence |
| Generation Failure | 3 | 5% | Retrieved but not used |
| Citation Failure | 5 | 9% | Wrong source attribution |
| **Correct** | **33** | **60%** | All good |

## 📚 Files

### Frontend & UI
- `ecorag_frontend.html` - Interactive web interface (green theme)

### Core System
- `ecorag_ask.py` - Main RAG pipeline
- `ecorag_verify.py` - Citation verification
- `ecorag_build_chunks.py` - Document chunking
- `ecorag_embeddings.py` - Embedding generation
- `ecorag_build_chroma.py` - Vector database setup

### Research Data
- `ecorag_data/expC/` - Complete Experiment C results
  - `questions_frozen.json` - 27 evaluation questions
  - `gold.json` - Ground truth labels
  - `results.json` - Raw model outputs
  - `manual_review.json` - Citation annotations (85 claims)
  - `scores.json` - Computed metrics
  - PDFs and reports

### Documentation
- `README.md` - This file
- `COMPLETE_DELIVERABLES.md` - Package contents
- `FREE_DEPLOYMENT_GUIDE.md` - Hosting instructions
- `ecorag_data/expC/RESEARCH_SUMMARY.txt` - Detailed analysis

## 🚀 Deployment

### Deploy Frontend for Free

**Option 1: Netlify (Easiest)**
```
1. Go to app.netlify.com/drop
2. Drag ecorag_frontend.html
3. Get live URL instantly
```

**Option 2: GitHub Pages**
```
1. Push to this repository
2. Go to Settings > Pages
3. Select main branch
4. Site is live at: https://username.github.io/ecorag/
```

**Option 3: Vercel**
```
1. Go to vercel.com
2. Connect this GitHub repo
3. Auto-deploys on each push
```

See [`FREE_DEPLOYMENT_GUIDE.md`](FREE_DEPLOYMENT_GUIDE.md) for detailed instructions.

## 📊 Experiment C: Complete Analysis

See [`ecorag_data/expC/`](ecorag_data/expC/) for:

- ✅ Frozen questions & gold labels (pre-registered)
- ✅ Raw model outputs (results.json)
- ✅ Manual review of 85 cited claims
- ✅ Computed metrics (S1-S6)
- ✅ Failure taxonomy (55 units)
- ✅ Sensitivity analysis (3 post-hoc corrections)
- ✅ Professional PDF report
- ✅ Research summary & quick reference

**Research Integrity**: All artifacts frozen before execution, no modifications, single-reviewer evaluation.

## 🎨 Frontend UI Features

- 🌿 **Green Color Scheme** - Environmental focus
- 📱 **Responsive Design** - Desktop, tablet, mobile
- ✅ **Interactive Queries** - Ask questions
- 📊 **Three Tabs** - Answer | Evidence | Metrics
- 🎯 **Demo Questions** - Ready to try
- 📈 **Performance Stats** - Calibration, coverage, citations
- 🔗 **Citation Display** - Sources & evidence
- ⚡ **Smooth Animations** - Professional feel

## 🔐 Security & Privacy

- ✅ No credentials stored
- ✅ Local processing (no external APIs)
- ✅ Static frontend (no backend secrets)
- ✅ Open source (audit the code)

## 📖 Citation

If you use this research, please cite:

```bibtex
@software{ecorag2026,
  author = {Your Name},
  title = {EcoRAG: Environmental RAG with Evidence Evaluation},
  year = {2026},
  url = {https://github.com/username/ecorag},
  note = {Experiment C: 27-question evaluation, single-reviewer}
}
```

## 📝 License

MIT License - See LICENSE file for details

## 🤝 Contributing

Contributions welcome! Areas for improvement:
- Calibration-aware prompting
- Multi-source citation binding
- Partial-evidence handling
- Expanded evaluation set
- Second-reviewer validation

## 📞 Questions?

See the detailed guides:
- `COMPLETE_DELIVERABLES.md` - What's included
- `ecorag_data/expC/RESEARCH_SUMMARY.txt` - Full analysis
- `ecorag_data/expC/rubric.md` - Evaluation rubric
- `ecorag_data/expC/metrics_spec.md` - Metric definitions

## 🎯 Next Steps

1. ✅ **Try the interactive frontend** - Open `ecorag_frontend.html`
2. 📊 **Review the research** - Read `RESEARCH_SUMMARY.txt`
3. 🚀 **Deploy online** - Follow `FREE_DEPLOYMENT_GUIDE.md`
4. 🔧 **Add improvements** - Implement recommendations from Experiment C
5. 📈 **Run Experiment D** - Test improvements (new experiment)

---

**Built with ❤️ for environmental sustainability research**

Status: ✅ Production-ready | Experiments: A, B, C complete | Next: Experiment D improvements
