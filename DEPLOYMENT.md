# Railway Deployment Guide

This guide walks you through deploying the Persistent Sales Assistant Agent to Railway.

## Prerequisites

1. **GitHub Account** — You'll connect your repo to Railway
2. **Groq API Key** — Get a free one from [console.groq.com](https://console.groq.com)
3. **Railway Account** — Sign up at [railway.app](https://railway.app) (free tier available)

## Step-by-Step Deployment

### 1. Prepare Your Repository

Ensure these files are in your repository root:

- ✅ `Procfile` — Tells Railway how to start the app
- ✅ `runtime.txt` — Specifies Python 3.11.9
- ✅ `requirements.txt` — All Python dependencies
- ✅ `catalog.json` — Product catalog
- ✅ `.env.example` — Template for environment variables
- ✅ `app/` directory — All application code

### 2. Get Your Groq API Key

1. Go to [console.groq.com](https://console.groq.com)
2. Sign up with GitHub or email (free tier available)
3. In the dashboard, click **"API Keys"** or **"Keys"**
4. Click **"Create API Key"**
5. Copy the key to a safe place

### 3. Push to GitHub

If not already done:

```bash
git init
git add .
git commit -m "Initial commit: Persistent Sales Assistant Agent"
git remote add origin https://github.com/YOUR_USERNAME/sales-assistant-agent.git
git branch -M main
git push -u origin main
```

### 4. Create Railway Project

1. Go to [railway.app](https://railway.app)
2. Sign up / Log in
3. Click **"New Project"** (or **"Create New"**)
4. Select **"Deploy from GitHub Repo"**
5. You'll be prompted to authorize Railway with GitHub — click **"Authorize"**
6. Search for your `sales-assistant-agent` repo and select it
7. Railway will auto-detect the `Procfile` and start building

### 5. Add Environment Variables

While the build is running:

1. Go to your Railway project dashboard
2. Click the **"Variables"** tab (or **"Settings"** if it's under a different tab)
3. Add the following variables:

```
LLM_API_KEY=sk-xxxxx-your-groq-key-here
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=llama-3.1-8b-instant
DATABASE_URL=sqlite:///./sales_agent.db
EVAL_CONFIDENCE_THRESHOLD=0.55
```

Make sure to replace `sk-xxxxx-...` with your actual Groq API key.

### 6. Wait for Deployment

Railway will:

1. Build the Docker image
2. Install dependencies from `requirements.txt`
3. Start the uvicorn server

You'll see status like:

```
✓ Build complete
✓ Service running
```

### 7. Get Your Live URL

In the Railway dashboard, you'll see a public URL like:

```
https://sales-assistant-agent-production.up.railway.app
```

(The exact domain depends on what Railway assigns.)

### 8. Test the Live Service

Use the curl commands below to verify everything works:

```bash
# Replace with your actual Railway URL
RAILWAY_URL="https://sales-assistant-agent-production.up.railway.app"

# Test 1: Health check
curl $RAILWAY_URL/health
# Expected: {"status":"ok"}

# Test 2: Get catalog
curl $RAILWAY_URL/catalog
# Expected: JSON with 3 plans (Starter, Growth, Enterprise)

# Test 3: First chat (Session 1) - Ask about Enterprise
curl -X POST "$RAILWAY_URL/chat/user-bob" \
  -H "Content-Type: application/json" \
  -d '{"message":"Tell me about your Enterprise plan. Does it have SSO?"}'
# Expected: Response with eval block, tools_called list, session_id

# Test 4: Second chat (Session 2) - Demonstrate memory
# Note: Same user_id, but NO session_id in request = new session
curl -X POST "$RAILWAY_URL/chat/user-bob" \
  -H "Content-Type: application/json" \
  -d '{"message":"Does that plan also include audit logs?"}'
# Expected: Response references prior Enterprise interest

# Test 5: View history
curl "$RAILWAY_URL/chat/user-bob/history"
# Expected: Array with 4 messages (2 user + 2 assistant)

# Test 6: View eval metrics
curl "$RAILWAY_URL/chat/user-bob/evals"
# Expected: Aggregated scores across all responses

# Test 7: Delete memory (GDPR reset)
curl -X DELETE "$RAILWAY_URL/chat/user-bob/memory"
# Expected: {"deleted": true, ...}

# Test 8: Verify memory was deleted (history still exists for audit)
curl "$RAILWAY_URL/chat/user-bob/history"
# Expected: Still shows history, but memory table was cleared
```

## Troubleshooting

### Build Failed

**Problem:** Railway shows "Build Failed"

**Solution:**
1. Check the **"Deploy"** tab in Railway for detailed error logs
2. Common issues:
   - Missing `Procfile` or `requirements.txt`
   - Python version mismatch (should be 3.11.9)
   - Missing `catalog.json`

### Service Won't Start (Runtime Error)

**Problem:** Railway shows the service crashed on startup

**Solution:**
1. Check **"Logs"** tab for error messages
2. Most common:
   - Missing environment variable `LLM_API_KEY` → set it in Variables
   - Import error → ensure all files are committed to GitHub
3. Try redeploying by clicking **"Redeploy"** in Railway dashboard

### Chat Endpoint Returns 500 Error

**Problem:** `/chat/{user_id}` returns a 500 error

**Solution:**
1. Check Railway logs
2. Likely causes:
   - Invalid Groq API key → test with `LLM_API_KEY` not set (fallback scoring should work)
   - Database permission issue → SQLite should work on Railway

### Memory Not Persisting

**Problem:** Second call to same user_id doesn't remember first call

**Solution:**
- Verify you're using the **same `user_id`** in both calls
- Different `user_id` = different users = no shared memory (by design)
- Check `/chat/{user_id}/history` to see if messages are being saved

### Groq API Errors

**Problem:** LLM responses are failing

**Solution:**
1. Verify your Groq API key is correct (check console.groq.com)
2. Verify your account has not exceeded free tier limits
3. Railway will fall back to deterministic hardcoded responses if LLM fails (see `_fallback_response()` in `llm_service.py`)

## Monitoring

### View Real-Time Logs

In Railway dashboard:

1. Click your project
2. Click the **"Logs"** tab
3. Filter by service name or search for errors

### Monitor Usage

Railway tracks:

- Build time
- Deployment status
- Network activity
- Uptime

Free tier includes:

- 5 GB storage (SQLite can use this)
- 100 GB/month bandwidth

## Updating the Code

After you make changes and push to GitHub:

1. Railway watches your GitHub repo automatically
2. On push to `main`, Railway auto-redeploys
3. Deployment takes ~1-2 minutes

To check deployment status:

1. Go to Railway dashboard
2. Click **"Deployments"** tab
3. Most recent deployment at the top

## Scaling Considerations

For production use:

### Current Setup (Railway Free Tier)

- ✅ Single instance
- ✅ SQLite database (good for <1000 concurrent users)
- ✅ Groq API (excellent for free tier)

### Upgrade Path

As you scale:

1. **Multiple Instances** → Switch `DATABASE_URL` from SQLite to PostgreSQL on Railway
2. **Better Memory** → Replace keyword extraction with vector embeddings (Pinecone, Weaviate)
3. **Separate Eval Model** → Use a dedicated small model for evaluation instead of the chat model
4. **Caching** → Add Redis to cache catalog searches

To upgrade from SQLite to PostgreSQL:

1. In Railway dashboard, add a **PostgreSQL** service
2. Railway provides the connection string automatically
3. Change `DATABASE_URL` env var to point to Postgres
4. That's it! The abstracted memory layer handles the swap.

## Summary

Your live URL will be: **[Add your Railway URL here after deployment]**

Example curl to test:

```bash
curl https://your-railway-url/health
```

If you see `{"status":"ok"}`, you're live! 🚀

---

**Questions?** Check Railway docs at [docs.railway.app](https://docs.railway.app)
