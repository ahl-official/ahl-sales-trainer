# 🚀 RENDER DEPLOYMENT PLAN - AHL SALES TRAINER

**Project Manager:** Deployment Checklist  
**Target Platform:** Render (Hobby Account + Free/Starter Web Service)  
**Estimated Time:** 45-60 minutes  
**Difficulty:** Intermediate

---

## 📋 PRE-DEPLOYMENT CHECKLIST

### ✅ Prerequisites (Complete These First!)

- [ ] **GitHub Account** - Sign up at https://github.com
- [ ] **Render Account** - Sign up at https://render.com (Hobby - Free)
- [ ] **API Keys Ready:**
  - [ ] OpenRouter API Key (get from https://openrouter.ai/keys)
  - [ ] OpenAI API Key (get from https://platform.openai.com/api-keys)
  - [ ] Pinecone API Key + Index Host (get from https://pinecone.io)
- [ ] **Generate SECRET_KEY:**
  ```bash
  python3 -c "import secrets; print(secrets.token_hex(32))"
  ```
  Save the output (64 characters)

---

## 🔧 CRITICAL CODE CHANGES REQUIRED

### ❌ ISSUES FOUND IN YOUR CODEBASE:

1. **Frontend files in wrong location** - HTML files are in root, but app.py expects `../frontend/`
2. **Database path not configurable** - Hardcoded to `data/sales_trainer.db`
3. **No .gitignore** - Will upload sensitive data to GitHub
4. **No Render configuration files** - Need render.yaml or manual setup
5. **Static file serving path incorrect** - FRONTEND_DIR points to wrong location
6. **No health check for Render** - Already exists at `/api/health` ✅

---

## 📝 STEP-BY-STEP CHANGES

### **CHANGE 1: Fix Frontend File Paths** ⚠️ CRITICAL

**File:** `app.py`  
**Line:** 260  
**Current:**
```python
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))
```

**Change to:**
```python
# Render deployment: HTML files are in the same directory as app.py
FRONTEND_DIR = os.path.abspath(os.path.dirname(__file__))
```

**Why:** Your HTML files (login.html, trainer.html, etc.) are in the root directory, not in a separate `frontend/` folder.

---

### **CHANGE 2: Make Database Path Configurable** ⚠️ CRITICAL

**File:** `app.py`  
**Line:** 258  
**Current:**
```python
db = Database('data/sales_trainer.db')
```

**Change to:**
```python
# Support Render persistent disk or local development
DB_PATH = os.environ.get('DATABASE_PATH', 'data/sales_trainer.db')
db = Database(DB_PATH)
```

**Why:** Render needs to use a persistent disk mount point, not a relative path.

---

### **CHANGE 3: Create .gitignore File** ⚠️ CRITICAL

**Create new file:** `.gitignore`  
**Location:** Root directory (same level as app.py)

**Content:**
```gitignore
# Environment variables (NEVER commit this!)
.env
.env.local
.env.production

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Database
*.db
*.sqlite
*.sqlite3
data/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Testing
.pytest_cache/
.coverage
htmlcov/

# Temporary files
*.tmp
*.bak
cookies.txt
```

**Why:** Prevents uploading sensitive data (API keys, database) to GitHub.

---

### **CHANGE 4: Create render.yaml** (Optional but Recommended)

**Create new file:** `render.yaml`  
**Location:** Root directory

**Content:**
```yaml
services:
  # Main web service
  - type: web
    name: ahl-sales-trainer
    env: python
    region: oregon  # or singapore (closest to you)
    plan: free  # Change to "starter" for $7/month always-on
    buildCommand: "pip install -r requirements.txt"
    startCommand: "gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120"
    healthCheckPath: /api/health
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.6
      - key: PORT
        generateValue: true
      - key: SECRET_KEY
        generateValue: true
        sync: false
      - key: DATABASE_PATH
        value: /opt/render/project/src/data/sales_trainer.db
      # Add these manually in Render dashboard:
      # - OPENROUTER_API_KEY
      # - OPENAI_API_KEY
      # - PINECONE_API_KEY
      # - PINECONE_INDEX_HOST
      # - ALLOWED_ORIGINS (optional)
```

**Why:** Automates Render configuration (alternative to manual setup).

---

### **CHANGE 5: Update Database Initialization**

**File:** `app.py`  
**Lines:** 2161-2162  
**Current:**
```python
# Ensure data directory exists
os.makedirs('data', exist_ok=True)
```

**Change to:**
```python
# Ensure data directory exists (extract from DB_PATH)
db_dir = os.path.dirname(DB_PATH)
if db_dir:  # Only create if path has a directory component
    os.makedirs(db_dir, exist_ok=True)
```

**Why:** Supports both local `data/` folder and Render's custom paths.

---

### **CHANGE 6: Add Gunicorn Config File** (Optional)

**Create new file:** `gunicorn_config.py`  
**Location:** Root directory

**Content:**
```python
"""
Gunicorn configuration for Render deployment
"""
import os
import multiprocessing

# Bind to PORT from environment (Render provides this)
bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"

# Workers = (2 x CPU cores) + 1
workers = multiprocessing.cpu_count() * 2 + 1
workers = min(workers, 4)  # Cap at 4 for free/starter tier

# Threads per worker
threads = 4

# Timeout for requests (seconds)
timeout = 120

# Worker class
worker_class = 'sync'

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Keep-alive connections
keepalive = 5

# Graceful timeout
graceful_timeout = 30

# Max requests before worker restart (prevent memory leaks)
max_requests = 1000
max_requests_jitter = 100
```

**Why:** Optimizes Gunicorn for Render's environment.

---

### **CHANGE 7: Update CORS for Production** (Optional)

**File:** `config.py` (if it exists) or add to `app.py`  
**Current:** Likely allows all origins

**Add environment variable support:**
```python
# In app.py after CORS initialization
ALLOWED_ORIGINS = os.environ.get(
    'ALLOWED_ORIGINS',
    'http://localhost:8000,http://127.0.0.1:8000'
).split(',')

# Update CORS config (in config.py or app.py)
# Add your Render URL after deployment
```

**Why:** Security - restrict CORS to your actual domains.

---

## 📦 PREPARE FOR GITHUB

### **STEP 1: Initialize Git Repository**

```bash
cd /path/to/your/project

# Initialize git
git init

# Add all files
git add .

# First commit
git commit -m "Initial commit - Prepare for Render deployment"
```

---

### **STEP 2: Create GitHub Repository**

1. Go to https://github.com/new
2. **Repository name:** `ahl-sales-trainer`
3. **Visibility:** Private (Recommended) or Public
4. **Don't initialize** with README/gitignore (we have our own)
5. Click "Create repository"

---

### **STEP 3: Push to GitHub**

```bash
# Add remote (replace YOUR-USERNAME)
git remote add origin https://github.com/YOUR-USERNAME/ahl-sales-trainer.git

# Push code
git branch -M main
git push -u origin main
```

**⚠️ VERIFY:** Check GitHub - your code should be there, but NO .env file!

---

## 🚀 RENDER DEPLOYMENT

### **OPTION A: Using render.yaml (Automated)**

1. **Login to Render:** https://dashboard.render.com
2. **Click:** "New +" → "Blueprint"
3. **Connect Repository:** Select your GitHub repo
4. **Render detects** `render.yaml` and configures automatically
5. **Add Environment Variables** (see section below)
6. **Click:** "Apply"
7. **Wait 5-10 minutes** for build

---

### **OPTION B: Manual Setup (If no render.yaml)**

1. **Login to Render:** https://dashboard.render.com
2. **Click:** "New +" → "Web Service"
3. **Connect GitHub Repository**
4. **Configure:**
   - **Name:** `ahl-sales-trainer`
   - **Region:** Oregon (US) or Singapore (Asia)
   - **Branch:** `main`
   - **Root Directory:** Leave empty
   - **Environment:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120`
   - **Plan:** Free (or Starter $7)
5. **Click:** "Advanced" → Add Environment Variables (see below)
6. **Click:** "Create Web Service"

---

### **🔐 ENVIRONMENT VARIABLES (Add in Render Dashboard)**

**Go to:** Your Web Service → Environment → Add Environment Variable

**Required Variables:**

| Key | Value | How to Get |
|-----|-------|------------|
| `SECRET_KEY` | [64 char hex] | Run: `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `OPENROUTER_API_KEY` | sk-or-v1-... | https://openrouter.ai/keys |
| `OPENAI_API_KEY` | sk-... | https://platform.openai.com/api-keys |
| `PINECONE_API_KEY` | pcsk_... | https://app.pinecone.io |
| `PINECONE_INDEX_HOST` | https://...pinecone.io | Pinecone dashboard |
| `PORT` | 10000 | Auto-generated by Render |
| `DATABASE_PATH` | /opt/render/project/src/data/sales_trainer.db | For persistent disk |

**Optional Variables:**

| Key | Value | Purpose |
|-----|-------|---------|
| `ALLOWED_ORIGINS` | https://your-app.onrender.com | CORS security |
| `MAIL_USERNAME` | your@email.com | Email notifications |
| `MAIL_PASSWORD` | app-password | Email notifications |
| `ADMIN_EMAIL` | admin@email.com | Receive alerts |

**⚠️ IMPORTANT:** After adding variables, click "Save Changes" and wait for automatic redeploy.

---

## 💾 PERSISTENT DISK SETUP (For Starter Plan Only)

**If you choose Starter ($7/month):**

1. Go to your Web Service → "Disks"
2. Click "Add Disk"
3. **Name:** `data`
4. **Mount Path:** `/opt/render/project/src/data`
5. **Size:** 1 GB (free)
6. Click "Create"
7. Wait for redeploy

**Why:** Saves your database permanently. Free tier loses data on restart!

---

## ✅ POST-DEPLOYMENT VERIFICATION

### **Test 1: Check Health Endpoint**

```bash
curl https://YOUR-APP.onrender.com/api/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "...",
  "db": {"ok": true},
  "rate_limiting": true
}
```

---

### **Test 2: Access Login Page**

Visit: `https://YOUR-APP.onrender.com/`

**Expected:** Login page loads (may take 30-60s on first load if Free tier)

---

### **Test 3: Login as Admin**

- **Username:** `admin`
- **Password:** `admin123`

**Expected:** Redirects to upload page

---

### **Test 4: Upload Content**

1. Select a category
2. Upload a test .txt file
3. Check for success message

**Expected:** Content uploads to Pinecone

---

### **Test 5: Create Test User**

1. Go to "Create Candidate Account"
2. Username: `testuser`
3. Password: `Test123!`
4. Name: `Test User`

**Expected:** User created successfully

---

## 🐛 TROUBLESHOOTING

### **Issue 1: "Application failed to start"**

**Check Render Logs:**
1. Go to Web Service → Logs
2. Look for error messages

**Common Causes:**
- Missing environment variable (SECRET_KEY, API keys)
- Syntax error in code
- Wrong build/start command

**Fix:** Add missing env vars, check logs for specific error

---

### **Issue 2: "Database not found" or resets on restart**

**Cause:** Using Free tier without persistent disk

**Fix:** 
- Upgrade to Starter ($7) and add disk
- Or accept that database resets (not for production!)

---

### **Issue 3: "404 Not Found" on frontend pages**

**Cause:** FRONTEND_DIR path is wrong

**Fix:** Verify Change #1 was applied correctly

---

### **Issue 4: "CORS Error" in browser console**

**Cause:** ALLOWED_ORIGINS doesn't include your Render URL

**Fix:** 
1. Add env var: `ALLOWED_ORIGINS=https://your-app.onrender.com`
2. Or update config.py to allow Render domain

---

### **Issue 5: "Cold start" - App takes 45 seconds to load**

**This is NORMAL on Free tier!**

**Fix:** 
- Upgrade to Starter ($7) for always-on service
- Or accept the delay (only happens after 15min inactivity)

---

### **Issue 6: "API calls failing" or "OpenRouter error"**

**Check:**
1. Environment variables are set correctly
2. API keys are valid (not expired)
3. API keys have correct permissions
4. Check API provider status pages

---

## 📊 MONITORING

### **Check Deployment Status:**
- Render Dashboard → Your Service → "Events" tab

### **View Logs:**
- Render Dashboard → Your Service → "Logs" tab
- Filter by Error/Warning

### **Monitor API Costs:**
- OpenRouter: https://openrouter.ai/account
- OpenAI: https://platform.openai.com/usage
- Pinecone: https://app.pinecone.io

**Set up budget alerts immediately!**

---

## 🎉 SUCCESS CHECKLIST

- [ ] Code pushed to GitHub
- [ ] Render service created
- [ ] All environment variables added
- [ ] Deployment successful (green checkmark)
- [ ] Health endpoint returns 200 OK
- [ ] Login page loads
- [ ] Can login as admin
- [ ] Can upload content
- [ ] Can create users
- [ ] Database persists (if Starter plan)
- [ ] API keys working
- [ ] No errors in logs

---

## 📞 GETTING HELP

**Render Logs:** Most issues show up here first  
**Render Status:** https://status.render.com  
**Community:** https://community.render.com

---

## 🔄 UPDATING YOUR APP (After Initial Deployment)

```bash
# Make changes to code
git add .
git commit -m "Update: description of changes"
git push origin main
```

**Render automatically redeploys!** (takes 2-5 minutes)

---

## 💰 COST SUMMARY

### **FREE TIER:**
- Render: $0/month
- APIs: $60-200/month
- **Total: $60-200/month**
- ⚠️ Cold starts, database resets

### **STARTER TIER ($7):**
- Render: $7/month
- APIs: $60-200/month
- **Total: $67-207/month**
- ✅ Always on, persistent database

---

## 📋 FINAL NOTES

1. **Never commit .env file** - Keep API keys secret
2. **Monitor API costs** - Set up alerts
3. **Start with Free tier** - Test before paying
4. **Upgrade to Starter** - Once you're satisfied
5. **Regular backups** - Export database periodically
6. **Update dependencies** - Run `pip list --outdated` monthly

---

**Questions?** Review this document carefully. 99% of issues are covered here!

**Ready to deploy?** Follow each step in order. Don't skip!

**Good luck! 🚀**
