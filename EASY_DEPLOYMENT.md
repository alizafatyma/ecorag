# 🚀 Deploy EcoRAG for Everyone (Easy Way)

Make your website live and accessible with just a URL. No setup needed for users!

---

## ⭐ EASIEST OPTION: Replit (Recommended)

Replit hosts **both** frontend and backend in one place. Just share a link!

### Step 1: Go to Replit
- Visit: **https://replit.com**
- Sign up (use your GitHub account)

### Step 2: Create New Replit Project
```
1. Click "Create Repl"
2. Language: "Python"
3. Name: "ecorag"
4. Click "Create"
```

### Step 3: Upload Your Files
```
1. Click "Upload files" button (left sidebar)
2. Select and upload:
   - ecorag_api.py
   - ecorag_ask.py
   - ecorag_verify.py
   - ecorag_build_chroma.py
   - ecorag_embeddings.py
   - ecorag_frontend_live.html
   - ecorag_data/expC/ (all files)
   
3. Create file: pyproject.toml
```

### Step 4: Create Dependencies File

Create a file called `pyproject.toml` with:

```toml
[project]
name = "ecorag"
version = "1.0.0"
description = "Environmental RAG System"
dependencies = [
    "flask==2.3.0",
    "flask-cors==4.0.0",
    "torch==2.0.0",
    "transformers==4.30.0",
    "sentence-transformers==2.2.2",
    "chromadb==1.5.9",
    "pymupdf==1.28.2",
]
```

### Step 5: Run It

```
1. Click "Run" button (top)
2. Flask app starts on a Replit URL
3. Share the URL with anyone!
```

**Your live website:** `https://ecorag.replit.dev` (example)

---

## 🌐 OPTION 2: Netlify + Railway (Professional)

### Frontend on Netlify (Static)
```
1. Go to netlify.com
2. Drag & drop ecorag_frontend_live.html
3. Get instant URL
```

### Backend on Railway (Free)
```
1. Go to railway.app
2. Create new project from GitHub (your ecorag repo)
3. Add environment variables
4. Deploy
5. Get API URL
```

Update frontend to use:
```javascript
const API_URL = 'https://your-railway-app.railway.app/api/ask';
```

---

## 📱 OPTION 3: All-in-One with Render

### Deploy Everything
```
1. Go to render.com
2. Sign up with GitHub
3. Select "New Web Service"
4. Connect your ecorag GitHub repo
5. Runtime: Python 3.11
6. Build command: pip install -r requirements.txt
7. Start command: python ecorag_api.py
8. Deploy
```

**Your live website:** `https://ecorag-your-name.onrender.com`

---

## 🎯 BEST FOR YOU: Modified API + Frontend

Make the frontend work with any backend. Here's the modified setup:

### Modified `ecorag_api.py`
```python
"""Updated API that serves the frontend too"""
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from ecorag_ask import ask_ecorag

app = Flask(__name__, static_folder='.')
CORS(app)

@app.route('/')
def serve_frontend():
    """Serve the HTML frontend"""
    return send_file('ecorag_frontend_live.html')

@app.route('/api/ask', methods=['POST'])
def ask():
    """Answer questions using real EcoRAG"""
    try:
        data = request.json
        question = data.get('question', '')
        
        if not question:
            return jsonify({'error': 'No question'}), 400
        
        result = ask_ecorag(question, debug=False)
        
        return jsonify({
            'question': question,
            'answer': result['answer'],
            'citations': [
                {'source': s.get('chunk_id', 'Unknown'), 
                 'text': s.get('text', '')[:200]}
                for s in result['sources'][:3]
            ],
            'confidence': 0.80
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
```

### Modified `ecorag_frontend_live.html`
Change this line:
```javascript
const API_URL = 'http://localhost:5000/api/ask';
```

To this:
```javascript
const API_URL = '/api/ask';  // Relative URL works everywhere
```

---

## 📋 Complete Setup for Replit (Step-by-Step)

### Files to Upload
```
ecorag/
├── ecorag_api.py (updated version above)
├── ecorag_frontend_live.html (updated version above)
├── ecorag_ask.py
├── ecorag_verify.py
├── ecorag_build_chroma.py
├── ecorag_embeddings.py
├── pyproject.toml
└── ecorag_data/
    └── expC/
        ├── questions_frozen.json
        ├── gold.json
        ├── results.json
        ├── manual_review.json
        └── scores.json
```

### 1. Create on Replit

```
https://replit.com/new/python
```

### 2. Add Files

```
Click "Upload files" and add all files above
```

### 3. Create `pyproject.toml`

```toml
[project]
name = "ecorag"
dependencies = [
    "flask==2.3.0",
    "flask-cors==4.0.0",
    "torch==2.0.0",
    "transformers==4.30.0",
    "sentence-transformers==2.2.2",
    "chromadb==1.5.9",
]
```

### 4. Run

```
Click "Run" button
```

### 5. Share URL

```
Everyone can visit:
https://ecorag.replit.dev

No setup needed!
```

---

## 🎯 Which One Should You Choose?

| Option | Setup Time | Cost | Best For |
|--------|-----------|------|----------|
| **Replit** | 5 min | Free | Everyone (easiest) |
| **Netlify + Railway** | 10 min | Free | Professional setup |
| **Render** | 10 min | Free | All-in-one |
| **GitHub Pages + API** | 15 min | Free | GitHub integration |

**I RECOMMEND: REPLIT** (takes 5 minutes, easiest)

---

## 🔧 Setup Checklist for Replit

- [ ] Go to replit.com
- [ ] Sign up with GitHub
- [ ] Create new Python Repl
- [ ] Upload all files (drag & drop)
- [ ] Create pyproject.toml file
- [ ] Click "Run"
- [ ] Wait for "Listening on port 5000"
- [ ] Share the URL with friends
- [ ] Done!

---

## 📊 What Users See

When someone visits your URL:

```
1. They see the EcoRAG interface
2. They type a question
3. Their computer sends it to YOUR server
4. Your AI system processes it
5. They get an answer with citations
6. All in real-time!
```

No downloads, no installation, no Python commands needed!

---

## 🚀 After Deployment

### Share Your Live Site
```
"Try EcoRAG: https://ecorag.replit.dev"
```

### Show People
- Ask environmental questions
- See AI answers with citations
- View the research metrics
- Read the professional PDF report

### Monitor Usage
- Replit shows you traffic
- See what questions people ask
- Track performance

---

## 💡 Pro Tips

### 1. Add Custom Domain (Optional)
```
On Replit:
Settings > Domain > Add custom domain
```

### 2. Keep It Running
```
Replit free tier stops after 30 mins of inactivity
Paid tier ($5-7/month) keeps it running 24/7
```

### 3. If Models Are Too Large
```
Host on Railway or Render (more resources)
Or use model quantization to reduce size
```

---

## 🎉 Result

After setup, your EcoRAG website is:

✅ **Live** - People can visit anytime  
✅ **No Setup** - Just click the link  
✅ **Real AI** - Uses your actual Qwen2.5 model  
✅ **Full Features** - Answers, citations, research  
✅ **Shareable** - One URL for everyone  

---

## 📱 Share This URL

Once deployed, you can share:

```
"Check out my EcoRAG environmental AI system!
Visit: https://ecorag.replit.dev

Ask questions about:
- Methane emissions
- Green jobs
- Energy grids
- Steel decarbonization
- Critical minerals

No installation needed, just visit the link!"
```

---

## ❓ Troubleshooting

### If Models Don't Load
```
Solution: Install on Replit, wait for downloads
(Takes 5-10 minutes on first run)
```

### If API Connection Fails
```
Solution: Update API_URL in frontend
from: 'http://localhost:5000/api/ask'
to: '/api/ask'
```

### If Chroma Database Missing
```
Solution: Add ecorag_data/chroma/ to files
Or run: python ecorag_build_chroma.py first
```

---

**Ready to go live? Use REPLIT - it's the easiest!** 🚀
