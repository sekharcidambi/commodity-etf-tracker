# Deployment Guide - Commodity ETF Tracker

## Free Deployment: Vercel + Railway

This guide shows how to deploy for **FREE** using Vercel (frontend) and Railway (backend + database).

---

## Prerequisites

1. GitHub account
2. Vercel account (sign up at vercel.com)
3. Railway account (sign up at railway.app)

---

## Part 1: Prepare Your Repository

### 1. Create GitHub Repository

```bash
cd /Users/sekharcidambi/commodity-etf-tracker/commodity-etf-tracker

# Initialize git (if not already done)
git init
git add .
git commit -m "Initial commit - Commodity ETF Tracker"

# Create repository on GitHub and push
git remote add origin https://github.com/YOUR_USERNAME/commodity-etf-tracker.git
git branch -M main
git push -u origin main
```

---

## Part 2: Deploy Database + Backend to Railway

### 1. Sign Up for Railway
- Go to https://railway.app
- Sign in with GitHub

### 2. Create New Project
- Click "New Project"
- Select "Deploy PostgreSQL"
- Railway will create a PostgreSQL instance

### 3. Add TimescaleDB Extension

Once PostgreSQL is created:
- Click on the PostgreSQL service
- Go to "Connect" tab
- Copy the connection URL
- Use a database client to connect and run:

```sql
CREATE EXTENSION IF NOT EXISTS timescaledb;
```

### 4. Deploy Backend Service

- In the same Railway project, click "New Service"
- Select "GitHub Repo"
- Choose your `commodity-etf-tracker` repository
- Railway will detect it's a Python app

### 5. Configure Backend Environment Variables

In Railway backend service settings:
- Go to "Variables" tab
- Add these variables:

```
DATABASE_URL=${{Postgres.DATABASE_URL}}
FRONTEND_URL=https://your-app.vercel.app
PORT=8000
PYTHON_VERSION=3.11
```

### 6. Configure Build Settings

Create `railway.json` in project root (already created below)

### 7. Set Root Directory

In Railway backend service:
- Settings → Root Directory → Set to `backend`

### 8. Deploy

- Railway will automatically deploy
- Note the backend URL (e.g., `https://commodity-backend-production.up.railway.app`)

---

## Part 3: Deploy Frontend to Vercel

### 1. Sign Up for Vercel
- Go to https://vercel.com
- Sign in with GitHub

### 2. Import Repository
- Click "Add New" → "Project"
- Import your GitHub repository
- Select the repository

### 3. Configure Build Settings

- **Framework Preset:** Vite
- **Root Directory:** `frontend`
- **Build Command:** `npm run build`
- **Output Directory:** `dist`

### 4. Add Environment Variable

In Vercel project settings:
- Go to "Settings" → "Environment Variables"
- Add:

```
VITE_API_URL=https://your-backend-url.up.railway.app
```

Replace with your actual Railway backend URL.

### 5. Deploy

- Click "Deploy"
- Vercel will build and deploy your frontend
- You'll get a URL like `https://commodity-etf-tracker.vercel.app`

---

## Part 4: Update Backend CORS

Go back to Railway and update the `FRONTEND_URL` environment variable with your Vercel URL:

```
FRONTEND_URL=https://commodity-etf-tracker.vercel.app
```

Redeploy the backend service.

---

## Part 5: Initialize Database

### Option A: Via Railway Console

1. In Railway, go to PostgreSQL service
2. Click "Connect"
3. Copy the `psql` command
4. Run in your local terminal:

```bash
psql [connection-url-from-railway]
```

Then run the initialization script:

```bash
# Copy paste the contents of database/sql/01_init_timescale.sql
```

### Option B: Via Backend API

Once backend is deployed, you can use the API to initialize:

```bash
# This will run migrations on startup (if configured)
curl https://your-backend-url.up.railway.app/api/v1/health
```

---

## Part 6: Collect Data

### One-Time Data Collection

SSH into Railway backend or use Railway CLI:

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link to your project
railway link

# Run data collection
railway run python collect_all_data.py
```

### Schedule Data Collection (Cron)

Railway doesn't have built-in cron. Options:

**Option A: GitHub Actions (Free)**

Create `.github/workflows/collect-data.yml`:

```yaml
name: Collect Market Data
on:
  schedule:
    - cron: '0 0 * * *'  # Daily at midnight UTC
  workflow_dispatch:  # Manual trigger

jobs:
  collect:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger data collection
        run: |
          curl -X POST https://your-backend-url.up.railway.app/api/v1/data/collect-all
```

**Option B: EasyCron (Free tier)**

- Sign up at easycron.com
- Create cron job to hit your data collection endpoint daily

---

## Cost Breakdown

### Completely Free Setup:
- **Vercel:** Free (frontend hosting)
- **Railway:** $5 free credit/month
  - PostgreSQL: ~$2/month
  - Backend: ~$3/month
  - **Total: FREE** (within $5 credit)

### If You Exceed Free Tier:
- **Railway:** ~$10/month (after free credit)
- **Vercel:** Free (hobby projects)
- **Total:** ~$10/month

---

## Alternative: All-in-One Deployment (DigitalOcean)

If you prefer a single provider:

### DigitalOcean App Platform ($12/month)

1. Sign up at digitalocean.com
2. Create App → GitHub
3. Select repository
4. Configure:
   - Frontend: Static Site
   - Backend: Web Service (Python)
   - Database: PostgreSQL
5. Deploy

**Pros:**
- Single dashboard
- Predictable pricing
- Easy scaling

**Cons:**
- Not free
- Less generous free tier than Railway

---

## Custom Domain (Optional)

### Add to Vercel:
1. Go to Project Settings → Domains
2. Add your domain
3. Update DNS records at your domain registrar

### Add to Railway:
1. Go to Backend Service → Settings → Domains
2. Add custom domain
3. Update DNS records

---

## Monitoring & Maintenance

### Free Monitoring Tools:
- **Railway Dashboard:** Built-in metrics
- **Vercel Analytics:** Free tier
- **Better Stack (formerly Logtail):** Free tier for logs
- **UptimeRobot:** Free uptime monitoring

---

## Troubleshooting

### Frontend can't connect to backend:
- Check CORS configuration in backend
- Verify `VITE_API_URL` in Vercel
- Verify `FRONTEND_URL` in Railway

### Database connection issues:
- Check `DATABASE_URL` in Railway backend
- Verify TimescaleDB extension is installed
- Check database logs in Railway

### Data collection not working:
- Check backend logs in Railway
- Verify Stooq is accessible from Railway
- Check rate limits

---

## Security Checklist

Before going public:

- [ ] Change default passwords/secrets
- [ ] Enable HTTPS (automatic on Vercel/Railway)
- [ ] Set up proper CORS origins
- [ ] Add rate limiting to API
- [ ] Review database access permissions
- [ ] Add authentication if needed (for admin features)

---

## Next Steps

1. Monitor usage on Railway (check if staying within free tier)
2. Set up GitHub Actions for daily data collection
3. Add custom domain
4. Set up monitoring/alerts
5. Add Google Analytics (if desired)

---

## Need Help?

- Railway Docs: https://docs.railway.app
- Vercel Docs: https://vercel.com/docs
- Project Issues: [GitHub Issues](https://github.com/YOUR_USERNAME/commodity-etf-tracker/issues)
