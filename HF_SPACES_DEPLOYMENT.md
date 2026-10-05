# 🚀 Deploy EcoRAG with Model Online (Hugging Face Spaces)

Deploy everything including the AI model - people access via simple URL.

---

## ⭐ BEST OPTION: Hugging Face Spaces

**Why:** Free hosting for AI models, automatic scaling, super easy

### What You Get
✅ Model hosted in cloud  
✅ Frontend website  
✅ API working  
✅ Shareable URL  
✅ Completely free  

---

## 🔧 Step-by-Step Setup

### Step 1: Create Hugging Face Account
```
1. Go to https://huggingface.co
2. Click "Sign Up"
3. Complete signup (free)
```

### Step 2: Create New Space
```
1. Go to https://huggingface.co/spaces
2. Click "Create new Space"
3. Settings:
   - Owner: Your username
   - Space name: ecorag
   - License: OpenRAIL-M (or OpenAssistant)
   - Space SDK: Docker
   - Private: No (so everyone can access)
4. Click "Create Space"
```

### Step 3: Create Dockerfile

In your Space, create a file called `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir \
    flask==2.3.0 \
    flask-cors==4.0.0 \
    torch==2.0.0 \
    transformers==4.30.0 \
    sentence-transformers==2.2.2 \
    chromadb==1.5.9 \
    pymupdf==1.28.2

# Copy application files
COPY ecorag_api_production.py app.py
COPY ecorag_ask.py .
COPY ecorag_verify.py .
COPY ecorag_build_chroma.py .
COPY ecorag_embeddings.py .
COPY ecorag_frontend_live.html .
COPY ecorag_data ./ecorag_data
COPY requirements.txt .

# Set environment
ENV PYTHONUNBUFFERED=1
ENV PORT=7860

# Run
CMD ["python", "app.py"]
```

### Step 4: Create app.py

Create `app.py` (rename your api):

```python
# Same as ecorag_api_production.py
# See below for full code
```

### Step 5: Upload All Files

On Hugging Face Spaces:
```
1. Click "Files" tab
2. Drag & drop:
   - ecorag_api_production.py (rename to app.py)
   - ecorag_frontend_live.html
   - ecorag_ask.py
   - ecorag_verify.py
   - ecorag_data/ (entire folder)
   - Dockerfile
   - requirements.txt
```

### Step 6: Wait for Deploy

```
Hugging Face will:
1. Build the Docker container
2. Download the Qwen2.5 model
3. Start the server
4. Give you a public URL

Takes 5-15 minutes first time
```

### Step 7: Share the URL

```
Your live website:
https://username-ecorag.hf.space

Share this with ANYONE!
```

---

## 📋 File Structure for HF Spaces

```
your-space/
├── Dockerfile              (Docker setup)
├── app.py                  (main API - renamed from ecorag_api_production.py)
├── ecorag_frontend_live.html
├── ecorag_ask.py
├── ecorag_verify.py
├── ecorag_build_chroma.py
├── ecorag_embeddings.py
├── requirements.txt
└── ecorag_data/
    ├── expC/
    │   ├── questions_frozen.json
    │   ├── gold.json
    │   ├── results.json
    │   └── [other files]
    └── [other folders]
```

---

## 🐳 Dockerfile Explained

```dockerfile
FROM python:3.11-slim           # Base Python image
WORKDIR /app                    # Working directory
RUN pip install ...             # Install packages
COPY ...                        # Copy your files
ENV PORT=7860                   # HF Spaces uses port 7860
CMD ["python", "app.py"]        # Run your app
```

---

## ✅ What Users Will See

1. **Visit URL:** `https://username-ecorag.hf.space`
2. **See:** Beautiful green-themed interface
3. **Ask:** A question about environmental topics
4. **Get:** Real answer from Qwen2.5 model
5. **See:** Citations and sources
6. **No setup needed!**

---

## 🎯 The Flow

```
User visits URL
    ↓
Frontend loads from HF Spaces
    ↓
User types question
    ↓
Sends to your backend API
    ↓
Backend runs Qwen2.5 model
    ↓
Model retrieves from Chroma DB
    ↓
Model generates answer
    ↓
User sees result instantly
```

---

## 📊 Comparison: Where to Deploy

| Platform | Model | Cost | Setup | Scalable |
|----------|-------|------|-------|----------|
| **HF Spaces** | ✅ Yes | Free | 10 min | Yes |
| Replit | ❌ Might crash | Free | 5 min | No |
| Railway | ✅ Yes | Free tier | 15 min | Yes |
| Render | ✅ Yes | Free tier | 15 min | Yes |
| AWS | ✅ Yes | $ | 30 min | Yes |

**I recommend: Hugging Face Spaces** (free + built for models)

---

## 🚀 Quick Reference

### Create Space
```
huggingface.co/spaces
→ Create new Space
→ Docker SDK
→ Name: ecorag
```

### Upload Files
```
Files tab → Drag & drop all files
(Or git push if you use git)
```

### Deploy
```
Click "Run" or just wait
HF Spaces auto-builds and deploys
```

### Share
```
Copy the Space URL
Share with anyone!
```

---

## ⚡ Speed Notes

**First run:** 5-15 minutes (downloading model)  
**Subsequent runs:** Instant  
**Model size:** ~2.3GB  
**Memory needed:** 4GB+ (HF Spaces provides this)  

---

## 🆘 Troubleshooting

### Model Too Large?
```
Solution: Use model quantization
Or use Ollama.ai for model serving
```

### Space Takes Too Long?
```
Normal: First build takes 10-15 min
You'll see progress in the logs
```

### API Not Responding?
```
Check Space logs for errors
Restart the Space if needed
```

---

## 📱 Mobile Access

The website works on:
- ✅ Desktop
- ✅ Tablet
- ✅ Mobile phone
- ✅ Anywhere with internet

Just share the URL!

---

## 🎉 Final Result

```
Your live EcoRAG website:
👉 https://username-ecorag.hf.space

Everyone can access instantly!
No downloads, no setup, no Python.
Just a simple URL.
```

---

**Next: Go to huggingface.co/spaces and create a new Space!** 🚀
