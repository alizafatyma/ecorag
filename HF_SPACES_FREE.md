# 🚀 Deploy EcoRAG FREE on Hugging Face Spaces (Gradio)

Completely free, no Docker paid plans needed!

---

## ⭐ FREE OPTION: Hugging Face Spaces + Gradio

**Cost:** $0  
**Time:** 10 minutes  
**Complexity:** Easy  

---

## 🔧 Step-by-Step (FREE)

### Step 1: Create HF Account
```
1. Go to https://huggingface.co
2. Sign up (free)
3. Verify email
```

### Step 2: Create New Space
```
1. Go to https://huggingface.co/spaces
2. Click "Create new Space"
3. Settings:
   - Space name: ecorag
   - Space SDK: Gradio (NOT Docker)
   - Private: No
4. Click "Create Space"
```

### Step 3: Create `app.py`

On Hugging Face Spaces, create file `app.py`:

```python
import gradio as gr
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

try:
    from ecorag_ask import ask_ecorag
    READY = True
except:
    READY = False

def answer_question(question):
    """Answer using EcoRAG"""
    if not question.strip():
        return "Please enter a question", ""
    
    if not READY:
        return "System loading...", ""
    
    try:
        result = ask_ecorag(question, debug=False)
        answer = result.get('answer', 'No answer')
        
        citations = ""
        for i, source in enumerate(result.get('sources', [])[:3], 1):
            text = source.get('text', '')[:150]
            citations += f"{i}. {source.get('chunk_id', 'Unknown')}\n{text}\n\n"
        
        return answer, citations
    except Exception as e:
        return f"Error: {str(e)}", ""

# Create Gradio interface
with gr.Blocks(title="🌿 EcoRAG") as demo:
    gr.Markdown("# 🌿 EcoRAG - Environmental AI Assistant")
    gr.Markdown("Ask questions about environmental sustainability, renewable energy, and climate action.")
    
    with gr.Row():
        with gr.Column():
            question = gr.Textbox(
                label="Your Question",
                placeholder="Ask about methane emissions, green jobs, grid modernization...",
                lines=3
            )
            btn = gr.Button("Ask EcoRAG", variant="primary")
        
        with gr.Column():
            answer = gr.Textbox(
                label="Answer",
                lines=6,
                interactive=False
            )
    
    citations = gr.Textbox(
        label="📚 Sources & Citations",
        lines=4,
        interactive=False
    )
    
    btn.click(answer_question, inputs=question, outputs=[answer, citations])

if __name__ == "__main__":
    demo.launch()
```

### Step 4: Create `requirements.txt`

Create file `requirements.txt`:

```
gradio==4.20.0
torch==2.0.0
transformers==4.30.0
sentence-transformers==2.2.2
chromadb==1.5.9
pymupdf==1.28.2
```

### Step 5: Upload Your Files

On Hugging Face Spaces, upload:
```
1. app.py (already created above)
2. requirements.txt (already created above)
3. ecorag_ask.py
4. ecorag_verify.py
5. ecorag_build_chroma.py
6. ecorag_embeddings.py
7. ecorag_data/ folder (drag and drop)
```

### Step 6: Wait & Done!

```
HF Spaces will:
✅ Install packages
✅ Download model
✅ Start the server
✅ Give you a URL

Takes ~5-15 minutes first time
```

### Step 7: Get Your URL

```
Your website:
https://username-ecorag.hf.space

Share this with ANYONE!
```

---

## ✅ What Everyone Sees

1. Visit: `https://username-ecorag.hf.space`
2. See: Beautiful Gradio interface
3. Type: A question about environmental topics
4. Get: Real AI answer instantly
5. See: Citations & sources
6. No setup, no Python, no downloads!

---

## 📊 File Structure

```
HF Space/
├── app.py                 (Gradio interface)
├── requirements.txt       (packages)
├── ecorag_ask.py         (your RAG system)
├── ecorag_verify.py
├── ecorag_build_chroma.py
├── ecorag_embeddings.py
└── ecorag_data/
    ├── expC/
    │   ├── questions_frozen.json
    │   ├── gold.json
    │   ├── results.json
    │   └── [other files]
    └── chroma/
```

---

## 🎯 Why Gradio?

✅ **Free** - No paid tier  
✅ **Easy** - 10 lines of code per interface  
✅ **Fast** - Auto-deploys  
✅ **Built for ML** - Made for AI models  
✅ **Mobile friendly** - Works on phones  

---

## 🚀 Quick Steps Summary

1. Go to https://huggingface.co/spaces
2. Create new Space → Gradio (FREE)
3. Upload files
4. Wait 5-15 minutes
5. Share URL
6. Done!

---

## 📱 What Works

✅ Desktop  
✅ Tablet  
✅ Mobile phone  
✅ Any browser  

---

## 🌐 Final Result

```
Share this URL with ANYONE:

https://username-ecorag.hf.space

They click it → see your AI working
No setup, no downloads, completely free!
```

---

## 💡 Pro Tip

If Gradio interface isn't pretty enough, you can:
- Use Streamlit (also free)
- Or keep the frontend + Flask (costs $7/month on Railway)

But **Gradio is completely free and works great!**

---

**Ready? Go to huggingface.co/spaces and start!** 🚀
