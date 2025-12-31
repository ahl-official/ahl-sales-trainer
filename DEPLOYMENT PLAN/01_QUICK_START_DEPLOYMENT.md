# ⚡ QUICK DEPLOYMENT CHECKLIST - 30 MINUTES

**Your Goal:** Deploy AHL Sales Trainer to Render  
**Your Budget:** $0 (Free tier) or $7/month (Starter tier)  
**Your Timeline:** 30-45 minutes

---

## 📋 PHASE 1: PREPARE CODE (10 minutes)

### Step 1: Make Code Changes ⚠️ CRITICAL
Open `CODE_CHANGES_REQUIRED.md` and make the 3 required changes to `app.py`:
- [ ] Change #1: Fix FRONTEND_DIR (line 260)
- [ ] Change #2: Make database configurable (line 258)
- [ ] Change #3: Fix directory creation (line 2161)

### Step 2: Add New Files
Copy these files to your project root:
- [ ] Copy `.gitignore` (prevents uploading secrets)
- [ ] Copy `render.yaml` (automates deployment)
- [ ] Copy `gunicorn_config.py` (optimizes server)

### Step 3: Test Locally
```bash
python app.py
```
- [ ] Server starts without errors
- [ ] Visit http://localhost:5050
- [ ] Login page loads correctly

**If errors:** Review `CODE_CHANGES_REQUIRED.md` again

---

## 📦 PHASE 2: PUSH TO GITHUB (5 minutes)

### Step 1: Initialize Git
```bash
git init
git add .
git commit -m "Prepare for Render deployment"
```

### Step 2: Create GitHub Repository
1. Go to https://github.com/new
2. Name: `ahl-sales-trainer`
3. Visibility: **Private** (recommended)
4. **Don't** initialize with README
5. Click "Create repository"

### Step 3: Push Code
```bash
# Replace YOUR-USERNAME with your GitHub username
git remote add origin https://github.com/YOUR-USERNAME/ahl-sales-trainer.git
git branch -M main
git push -u origin main
```

### Step 4: Verify
- [ ] Visit your GitHub repo
- [ ] Files are there
- [ ] **NO .env file** (should be blocked by .gitignore)

---

## 🚀 PHASE 3: DEPLOY TO RENDER (15 minutes)

### Step 1: Sign Up
- [ ] Go to https://render.com
- [ ] Sign up with GitHub (easiest)
- [ ] Choose **Hobby** plan (Free)

### Step 2: Create Web Service
1. Click "New +" → "Web Service"
2. Connect your GitHub account (authorize)
3. Select `ahl-sales-trainer` repository
4. Render detects `render.yaml` automatically
5. Click "Apply Blueprint"

### Step 3: Add Environment Variables
Click on your service → "Environment" → "Add Environment Variable"

**Required (6 variables):**

| Key | Value | Where to Get |
|-----|-------|--------------|
| `SECRET_KEY` | [Generate new] | Run: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `OPENROUTER_API_KEY` | sk-or-v1-... | https://openrouter.ai/keys |
| `OPENAI_API_KEY` | sk-... | https://platform.openai.com/api-keys |
| `PINECONE_API_KEY` | pcsk_... | https://app.pinecone.io |
| `PINECONE_INDEX_HOST` | https://...pinecone.io | Pinecone dashboard → your index |
| `DATABASE_PATH` | /opt/render/project/src/data/sales_trainer.db | Copy exactly |

**Optional:**
| Key | Value | Purpose |
|-----|-------|---------|
| `MAIL_USERNAME` | your@email.com | Email notifications |
| `MAIL_PASSWORD` | app-password | Email notifications |

- [ ] All variables added
- [ ] Click "Save Changes"

### Step 4: Wait for Build
- Watch the "Logs" tab
- Build takes 5-10 minutes
- Look for: "Build successful ✓"
- Look for: "Your service is live 🎉"

---

## ✅ PHASE 4: VERIFY DEPLOYMENT (5 minutes)

### Test 1: Health Check
Your URL: `https://YOUR-APP-NAME.onrender.com`

Visit: `https://YOUR-APP-NAME.onrender.com/api/health`

**Expected:**
```json
{
  "status": "healthy",
  "db": {"ok": true},
  "rate_limiting": true
}
```

### Test 2: Login Page
Visit: `https://YOUR-APP-NAME.onrender.com/`

- [ ] Login page loads (may take 30-60s first time on Free tier)
- [ ] CSS/styling works
- [ ] No console errors (F12 → Console)

### Test 3: Login as Admin
- Username: `admin`
- Password: `admin123`

- [ ] Login successful
- [ ] Redirects to upload page
- [ ] Can see categories

### Test 4: Create Test User
1. Go to "Create Candidate Account"
2. Username: `test`
3. Password: `Test123!`
4. Name: `Test User`

- [ ] User created successfully
- [ ] No errors

---

## 🎉 SUCCESS! YOU'RE DEPLOYED!

Your app is live at: `https://YOUR-APP-NAME.onrender.com`

**Share this URL with:**
- ✅ Sales team
- ✅ Trainees
- ✅ Managers
- ✅ Anyone (if public)

---

## 📊 POST-DEPLOYMENT TASKS

### Immediate (Do Now):
- [ ] **Change admin password** (login → settings)
- [ ] **Upload training content** (admin dashboard)
- [ ] **Create real user accounts** (not test accounts)
- [ ] **Set up API budget alerts** (OpenRouter, OpenAI)

### Within 24 Hours:
- [ ] **Monitor API costs** (check OpenRouter/OpenAI usage)
- [ ] **Test with real users** (2-3 people)
- [ ] **Review Render logs** (check for errors)
- [ ] **Decide: Keep Free or Upgrade to Starter?**

### Optional Upgrades:
- [ ] **Custom domain** ($0 - just configure DNS)
- [ ] **Starter plan** ($7/month - no cold starts)
- [ ] **Persistent disk** ($0 on Starter - 1GB included)
- [ ] **Email notifications** (add MAIL_* env vars)

---

## 💰 FREE TIER LIMITATIONS

**What You Get (FREE):**
- ✅ 512MB RAM
- ✅ Free HTTPS
- ✅ Unlimited users
- ✅ 750 hours/month (plenty!)

**What You Don't Get:**
- ⚠️ Spins down after 15 min inactivity
- ⚠️ 30-60 second cold start
- ⚠️ Database resets on redeploy
- ⚠️ No persistent disk

**When to Upgrade ($7/month Starter):**
- ✅ Need always-on (no delays)
- ✅ Need persistent database
- ✅ More than 10 active users
- ✅ Professional use case

---

## 🐛 COMMON ISSUES & FIXES

### Issue: "Build failed"
**Check logs for:**
- Missing Python dependency → Update `requirements.txt`
- Syntax error → Fix code, push again
- Missing file → Check if all files pushed to GitHub

**Fix:** Fix the error, commit, push → Render auto-redeploys

---

### Issue: "Application error" or 500 error
**Check Render logs:**
- Missing environment variable → Add in dashboard
- Wrong DATABASE_PATH → Check spelling
- API key invalid → Regenerate and update

**Fix:** Add/fix env var → Service restarts automatically

---

### Issue: Login page doesn't load (404)
**Check:**
- Did you make Change #1 (FRONTEND_DIR)?
- Are HTML files in GitHub repo?
- Check Render logs for "FileNotFoundError"

**Fix:** Verify code changes, push to GitHub

---

### Issue: "Database not found"
**This is normal on Free tier!**
- Database resets on each deploy
- Need Starter plan + persistent disk

**Temporary Fix:**
- Accept that you'll need to re-create admin user after each restart
- Or upgrade to Starter ($7)

---

### Issue: Slow/timeout (45+ seconds)
**This is normal on Free tier after 15min inactivity**

**Options:**
1. Accept the delay (it's free!)
2. Upgrade to Starter ($7) for always-on
3. Keep a tab open to ping it every 10min (hacky)

---

## 🔄 UPDATING YOUR APP

Made changes? Here's how to redeploy:

```bash
# Make your changes
git add .
git commit -m "Update: describe your changes"
git push origin main
```

**Render automatically redeploys!** (takes 2-5 minutes)

Watch "Logs" tab to see deployment progress.

---

## 📞 GET HELP

**Render Community:** https://community.render.com  
**Render Status:** https://status.render.com  
**Render Docs:** https://render.com/docs

**Review these documents:**
- `RENDER_DEPLOYMENT_PLAN.md` - Complete guide
- `CODE_CHANGES_REQUIRED.md` - Detailed code changes

---

## 🎯 YOUR NEXT STEPS

Right now, you should:

1. ✅ **Make the 3 code changes** (see `CODE_CHANGES_REQUIRED.md`)
2. ✅ **Copy the 3 new files** (.gitignore, render.yaml, gunicorn_config.py)
3. ✅ **Test locally** (`python app.py`)
4. ✅ **Push to GitHub**
5. ✅ **Deploy on Render**
6. ✅ **Add environment variables**
7. ✅ **Test the live app**

**Estimated time:** 30-45 minutes total

---

## 🎊 FINAL CHECKLIST

Before you start:
- [ ] I have all my API keys ready
- [ ] I have a GitHub account
- [ ] I have generated a SECRET_KEY
- [ ] I have 30-45 minutes free time
- [ ] I have read CODE_CHANGES_REQUIRED.md

During deployment:
- [ ] Made all 3 code changes
- [ ] Tested locally (works!)
- [ ] Pushed to GitHub (no .env file!)
- [ ] Created Render account
- [ ] Added all environment variables
- [ ] Build succeeded
- [ ] Health check passes
- [ ] Can login as admin

After deployment:
- [ ] Changed admin password
- [ ] Created test user
- [ ] Set up API cost alerts
- [ ] Shared URL with team

---

**Ready? Let's deploy! 🚀**

**Stuck? Check:** `RENDER_DEPLOYMENT_PLAN.md` for detailed troubleshooting
