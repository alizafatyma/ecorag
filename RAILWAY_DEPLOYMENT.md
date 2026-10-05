# 🚀 Deploy EcoRAG on Railway (FREE)

Complete guide to deploy your EcoRAG to Railway — free tier, no quota issues.

---

## ✅ What You Need (Already Have)

- ✅ `ecorag_api_production.py` - Backend API
- ✅ `ecorag_frontend_live.html` - Frontend UI
- ✅ `ecorag_ask.py` - RAG system
- ✅ `ecorag_data/` - Database & embeddings
- ✅ `requirements.txt` - Dependencies (create below)

---

## 🔧 Step 1: Create `requirements.txt`

Create a file called `requirements.txt` in your project root:

```
flask==2.3.0
flask-cors==4.0.0
torch==2.0.0
transformers==4.30.0
sentence-transformers==2.2.2
chromadb==1.5.9
pymupdf==1.28.2
```

---

## 📦 Step 2: Push to GitHub

```bash
cd /path/to/your/ecorag

# Initialize git (if not already)
git init

# Add all files
git add -A

# Commit
git commit -m "EcoRAG: Ready for Railway deployment"

# Add GitHub remote
git remote add origin https://github.com/YOUR_USERNAME/ecorag.git

# Push
git branch -M main
git push -u origin main
```

---

## 🚀 Step 3: Deploy to Railway

### 1. Go to Railway
```
https://railway.app
```

### 2. Sign Up
- Click "Start Project"
- Use GitHub (easiest)

### 3. Create New Project
- Click "Create New Project"
- Select "Deploy from GitHub repo"
- Select `ecorag` repo
- Click "Deploy"

### 4. Configure
Railway auto-detects Python. It will:
- Install `requirements.txt`
- Detect Flask app
- Start your server

### 5. Set Start Command (if needed)
```
python ecorag_api_production.py
```

### 6. Environment Variables (Optional)
```
PORT=8000
ENVIRONMENT=production
```

### 7. Wait & Get URL
```
Your live site:
https://ecorag-[random].up.railway.app

Share this URL!
```

---

## ✅ Test It Works

Once deployed:

```bash
# Health check
curl https://ecorag-[random].up.railway.app/api/health

# Ask a question
curl -X POST https://ecorag-[random].up.railway.app/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is methane?"}'
```

---

## 💰 Pricing

- **Free tier**: $5/month credit (usually lasts months)
- **No charges** if under $5/month
- **Monitor usage** in Railway dashboard

---

## 📊 File Structure on Railway

```
ecorag/
├── ecorag_api_production.py     (main app)
├── ecorag_frontend_live.html    (UI)
├── ecorag_ask.py                (RAG)
├── ecorag_verify.py
├── ecorag_embeddings.py
├── ecorag_data/                 (database + embeddings)
│   ├── chroma/
│   └── embeddings/
└── requirements.txt             (dependencies)
```

---

## 🎯 Next Steps

1. Create `requirements.txt` locally
2. Push to GitHub
3. Go to railway.app
4. Deploy from GitHub repo
5. Get your live URL
6. Share it!

---

## 🆘 Troubleshooting

### Build fails with "torch not found"
- Railway is slow to download torch
- Wait 5-10 minutes for build to complete
- Check logs in Railway dashboard

### "No module named ecorag_ask"
- Make sure all files are pushed to GitHub
- Check git status: `git status`

### API responds but no answers
- Check Railway logs for errors
- Ensure ecorag_data/ was pushed (large files)
- Add to `.gitignore` check — chroma/ shouldn't be ignored

---

## 📱 Frontend URL

Once Railway is live, visit:
```
https://ecorag-[random].up.railway.app/
```

No backend URL needed — it's all on the same server!

---

**Ready? Push to GitHub and deploy to Railway!** 🎉
