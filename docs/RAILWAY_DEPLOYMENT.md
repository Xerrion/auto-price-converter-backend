# Railway Deployment Guide

This guide walks you through deploying the Auto Price Converter backend to Railway with external cron scheduling via GitHub Actions.

## Architecture Overview

```
Chrome Extension → Railway API (serverless, idle-to-zero)
                      ↓
                   Supabase Database
                      ↑
GitHub Actions Cron → POST /jobs/sync (daily at 06:00 UTC)
```

**Benefits of this setup:**
- **Cost-effective**: ~$0.50/month (Railway only runs during requests)
- **Scalable**: Handles 1 user or 10,000 users at the same cost
- **Reliable**: GitHub Actions provides free, reliable cron scheduling
- **Serverless**: Railway auto-scales and idles when not in use

---

## Prerequisites

1. **GitHub Account** - For repository hosting and Actions
2. **Railway Account** - Sign up at https://railway.app (free tier available)
3. **Supabase Project** - Database for storing exchange rates
4. **Fixer.io API Key** - (Optional) For additional currency coverage

---

## Step 1: Push Code to GitHub

Your code is already in a local git repository. Push it to GitHub:

```bash
# This should already be done if following the main deployment plan
git remote -v  # Verify remote is set
git push -u origin main
```

---

## Step 2: Create Railway Project

### Option A: Via Web Dashboard (Recommended)

1. Go to https://railway.app/new
2. Click **"Deploy from GitHub repo"**
3. Authorize Railway to access your GitHub account
4. Select the repository: `auto-price-converter-backend`
5. Railway will automatically detect it as a Python/FastAPI project
6. Click **"Deploy Now"**

### Option B: Via Railway CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Deploy
railway up
```

---

## Step 3: Configure Environment Variables

In the Railway dashboard, go to your project → **Variables** tab and add the following:

### Required Variables

| Variable | Value | Description |
|----------|-------|-------------|
| `SUPABASE_URL` | `https://your-project.supabase.co` | Your Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | `eyJ...` | Supabase service role key (secret) |
| `SYNC_API_KEY` | `your-random-secret` | API key to protect /jobs/sync endpoint |

### Scheduler Configuration (Critical!)

| Variable | Value | Description |
|----------|-------|-------------|
| `ENABLE_SCHEDULER` | `false` | ⚠️ Must be `false` for external cron |
| `SCHEDULER_MODE` | `external` | ⚠️ Must be `external` |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FIXER_API_KEY` | - | Fixer.io API key for additional currencies |
| `SYNC_INTERVAL_HOURS` | `24` | How often to sync (used by cron schedule) |
| `PROVIDER_PRIORITY` | `fixer,frankfurter` | Which API providers to use |
| `ALLOW_ORIGINS` | `*` | CORS allowed origins |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `ENVIRONMENT` | `production` | Environment name |

### Example Configuration

```bash
SUPABASE_URL=https://abcdefgh.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SYNC_API_KEY=my-super-secret-key-12345
FIXER_API_KEY=abc123def456
ENABLE_SCHEDULER=false
SCHEDULER_MODE=external
SYNC_INTERVAL_HOURS=24
PROVIDER_PRIORITY=fixer,frankfurter
ALLOW_ORIGINS=*
LOG_LEVEL=INFO
ENVIRONMENT=production
```

---

## Step 4: Wait for Deployment

Railway will:
1. Clone your repository
2. Detect Python/FastAPI via `railway.toml` and `Procfile`
3. Install dependencies: `pip install -e .`
4. Start server: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Run health checks: `GET /health`

**Typical deployment time**: 2-3 minutes

### Monitor Deployment

- Go to **Deployments** tab in Railway dashboard
- Watch build logs for any errors
- Wait for status to show **"Success"** with green checkmark

---

## Step 5: Get Your Railway URL

After successful deployment:

1. Go to your project in Railway dashboard
2. Click **"Settings"** → **"Domains"**
3. Railway auto-generates a URL like:
   ```
   https://auto-price-converter-backend-production-xxxx.up.railway.app
   ```
4. **Copy this URL** - you'll need it for GitHub secrets and the Chrome extension

---

## Step 6: Test Your Deployment

Test all endpoints to ensure everything works:

```bash
# Save your Railway URL
export RAILWAY_URL="https://your-app.up.railway.app"

# Test health endpoint
curl "$RAILWAY_URL/health"
# Expected: {"status":"healthy"}

# Test rates endpoint
curl "$RAILWAY_URL/rates/latest"
# Expected: JSON with exchange rates (or 404 if no data yet)

# Test symbols endpoint
curl "$RAILWAY_URL/symbols/latest"
# Expected: JSON with currency symbols (or 404 if no data yet)

# Test protected endpoint (should fail without auth)
curl -X POST "$RAILWAY_URL/jobs/sync"
# Expected: 403 Forbidden

# Test protected endpoint WITH auth
curl -X POST "$RAILWAY_URL/jobs/sync" \
  -H "X-API-Key: your-sync-secret"
# Expected: 200 OK with sync results
```

---

## Step 7: Configure GitHub Secrets

GitHub Actions needs to know your Railway URL and API key to trigger syncs.

### Add Secrets via GitHub CLI

```bash
# Navigate to your repository
cd /path/to/auto-price-converter-backend

# Add Railway URL
gh secret set RAILWAY_API_URL --body="https://your-app.up.railway.app"

# Add sync API key (same as in Railway env vars)
gh secret set SYNC_API_KEY --body="your-sync-secret"

# Verify secrets were added
gh secret list
```

### Add Secrets via Web UI

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **"New repository secret"**
4. Add `RAILWAY_API_URL`:
   - **Name**: `RAILWAY_API_URL`
   - **Value**: `https://your-app.up.railway.app`
5. Click **"New repository secret"** again
6. Add `SYNC_API_KEY`:
   - **Name**: `SYNC_API_KEY`
   - **Value**: `your-sync-secret` (same as Railway)

---

## Step 8: Test GitHub Actions Workflow

Manually trigger the sync workflow to verify everything works:

### Via GitHub CLI

```bash
# Trigger the workflow
gh workflow run "Sync Exchange Rates"

# Wait 10-15 seconds, then check status
gh run list --workflow="Sync Exchange Rates" --limit 1

# View detailed logs (replace RUN_ID with actual ID from above)
gh run view RUN_ID --log
```

### Via Web UI

1. Go to your repository on GitHub
2. Click **Actions** tab
3. Select **"Sync Exchange Rates"** workflow
4. Click **"Run workflow"** dropdown
5. Click **"Run workflow"** button
6. Wait ~30 seconds for completion
7. Click on the workflow run to see logs

### Expected Output

✅ **Success** - Green checkmark with:
```
HTTP Status: 200
Response: {"message":"Sync completed successfully"}
✅ Exchange rates synced successfully
```

❌ **Failure** - Red X indicates an issue. Check:
- Railway URL is correct in GitHub secrets
- SYNC_API_KEY matches between Railway and GitHub
- Railway deployment is running (not paused)
- Railway logs for detailed error messages

---

## Step 9: Verify Automatic Scheduling

The GitHub Actions workflow is configured to run daily at **06:00 UTC**.

To verify:

1. Go to **Actions** tab on GitHub
2. Select **"Sync Exchange Rates"** workflow
3. You should see runs appearing daily at the scheduled time

To change the schedule:
1. Edit `.github/workflows/sync-rates.yml`
2. Update the cron expression:
   ```yaml
   schedule:
     - cron: '0 6 * * *'  # Daily at 06:00 UTC
   ```
3. Cron format: `minute hour day month weekday`
4. Examples:
   - `'0 0 * * *'` - Daily at 00:00 UTC
   - `'0 12 * * *'` - Daily at 12:00 UTC
   - `'0 */6 * * *'` - Every 6 hours

---

## Step 10: Update Chrome Extension

Update your Chrome extension to point to the Railway API:

```bash
# Navigate to extension directory
cd /path/to/auto-price-converter

# Edit .env file
# Change from:
VITE_RATES_API_BASE=http://127.0.0.1:8000

# To:
VITE_RATES_API_BASE=https://your-app.up.railway.app

# Rebuild extension
npm run build

# Reload extension in Chrome
# Go to chrome://extensions/, find your extension, click "Reload"
```

### Test Extension

1. Visit any website (e.g., amazon.com)
2. Open DevTools → Console
3. Look for API calls to your Railway URL
4. Verify prices are converting correctly
5. Check Network tab - should see 200 OK from Railway

---

## Monitoring & Maintenance

### Railway Dashboard

**Metrics** tab shows:
- **CPU Usage**: Should spike during requests, idle otherwise
- **Memory**: Typically 50-100 MB
- **Network**: Bandwidth usage (minimal with ETag caching)
- **Monthly Hours**: Should be <10 hours/month (~2.5 hours expected)

**Logs** tab shows:
- Application startup messages
- API requests (INFO level)
- Sync operations
- Errors with stack traces

### GitHub Actions

**Actions** tab shows:
- Daily cron run history
- Success/failure status
- Detailed logs for each run
- Manual trigger option

### Cost Monitoring

**Railway Billing** tab shows:
- Current month usage: ~$0.25-0.50 expected
- Estimated monthly cost: ~$0.50-1.00 expected
- Free tier credit remaining: ~$4.50 (out of $5/month)

**Expected monthly costs:**
- Railway: ~$0.50
- GitHub Actions: $0.00 (free tier)
- Supabase: $0.00 (free tier for <500MB)
- **Total: ~$0.50/month** ✅

---

## Troubleshooting

### Issue: Railway Build Fails

**Symptoms**: Deployment shows "Build Failed" status

**Solutions**:
1. Check Railway build logs for specific error
2. Verify `pyproject.toml` syntax is valid:
   ```bash
   python -m pip install -e .  # Test locally
   ```
3. Ensure all required files exist:
   - `railway.toml`
   - `Procfile`
   - `runtime.txt`
   - `pyproject.toml`

### Issue: Health Check Fails

**Symptoms**: Deployment shows "Unhealthy" or restarts frequently

**Solutions**:
1. Test health endpoint manually:
   ```bash
   curl https://your-app.up.railway.app/health
   ```
2. Check Railway logs for application errors
3. Verify environment variables are set correctly
4. Ensure `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are valid

### Issue: GitHub Actions Sync Fails

**Symptoms**: Workflow runs show red X, "Error: Sync endpoint returned 403/500"

**Solutions**:

**403 Forbidden**:
- Verify `SYNC_API_KEY` secret matches Railway env var
- Check Railway logs - should see authentication error

**500 Internal Server Error**:
- Check Railway logs for detailed error
- Verify Supabase credentials are correct
- Test sync endpoint manually:
  ```bash
  curl -X POST "https://your-app.up.railway.app/jobs/sync" \
    -H "X-API-Key: your-sync-secret" -v
  ```

**Connection Refused**:
- Railway deployment may be paused - check dashboard
- URL in GitHub secrets may be incorrect

### Issue: Extension Can't Connect to API

**Symptoms**: Extension shows "Failed to fetch rates" or prices don't convert

**Solutions**:
1. Verify extension `.env` has correct `VITE_RATES_API_BASE`
2. Rebuild extension: `npm run build`
3. Check browser console for CORS errors
4. If CORS error, update Railway env var:
   ```bash
   ALLOW_ORIGINS=chrome-extension://your-extension-id,*
   ```
5. Test API directly in browser:
   ```
   https://your-app.up.railway.app/rates/latest
   ```

### Issue: High Railway Costs

**Symptoms**: Monthly usage exceeds expected ~$0.50

**Possible Causes**:
1. **SCHEDULER_MODE is "internal"** (app runs 24/7)
   - Fix: Set `SCHEDULER_MODE=external` in Railway
2. **Extension calling API too frequently**
   - Check extension logs - should cache for 24 hours
3. **High traffic** (many users)
   - This is expected! Consider upgrading plan

**Verify serverless mode**:
```bash
# Check Railway logs after 5 minutes of inactivity
# Should show: "Application sleeping" or similar
```

### Issue: No Data in Database

**Symptoms**: `/rates/latest` returns 404

**Solutions**:
1. Trigger manual sync via GitHub Actions
2. Or call sync endpoint directly:
   ```bash
   curl -X POST "https://your-app.up.railway.app/jobs/sync" \
     -H "X-API-Key: your-sync-secret"
   ```
3. Check Railway logs for sync errors
4. Verify Supabase tables exist (run `sql/schema.sql`)

---

## Rolling Back

If something goes wrong, you can easily roll back:

### Revert to Previous Deployment

1. Go to Railway dashboard → **Deployments**
2. Find the last working deployment
3. Click **"Redeploy"**

### Revert Code Changes

```bash
# View git history
git log --oneline

# Revert to previous commit (e.g., before deployment changes)
git revert HEAD

# Push to GitHub (triggers new Railway deployment)
git push
```

### Switch Back to Local API

In Chrome extension `.env`:
```bash
# Temporarily use local backend
VITE_RATES_API_BASE=http://127.0.0.1:8000

# Rebuild
npm run build

# Start local backend
uv run uvicorn app.main:app --reload
```

---

## Advanced Configuration

### Custom Domain

To use your own domain instead of Railway's generated URL:

1. Go to Railway dashboard → **Settings** → **Domains**
2. Click **"Add Custom Domain"**
3. Enter your domain: `api.yourdomain.com`
4. Add DNS record as instructed by Railway:
   ```
   Type: CNAME
   Name: api
   Value: your-app.up.railway.app
   ```
5. Wait for DNS propagation (~10 minutes)
6. Update GitHub secrets with new domain

### Rate Limiting

To protect against abuse, add rate limiting:

1. Install package:
   ```bash
   pip install slowapi
   ```
2. Add to `app/main.py`:
   ```python
   from slowapi import Limiter, _rate_limit_exceeded_handler
   from slowapi.util import get_remote_address
   
   limiter = Limiter(key_func=get_remote_address)
   app.state.limiter = limiter
   app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
   ```
3. Apply to routes:
   ```python
   @router.get("/rates/latest")
   @limiter.limit("100/minute")
   async def get_latest_rates(...):
       ...
   ```

### Monitoring Alerts

**Railway Notifications**:
1. Go to **Settings** → **Notifications**
2. Enable "Deployment failed" notifications
3. Add email or webhook URL

**GitHub Actions Notifications**:
1. Go to repository → **Actions** → **Sync Exchange Rates**
2. Click **"..."** menu → **"Enable notifications"**
3. Get email alerts on workflow failures

**External Monitoring** (Recommended):
- Use [UptimeRobot](https://uptimerobot.com/) (free tier: 50 monitors)
- Monitor `https://your-app.up.railway.app/health` every 5 minutes
- Get alerts if endpoint is down

---

## Security Best Practices

1. **Never commit secrets** to git
   - `.env` is in `.gitignore` ✅
   - Use environment variables only

2. **Rotate API keys regularly**
   - Update `SYNC_API_KEY` every 3-6 months
   - Update in both Railway and GitHub secrets

3. **Restrict CORS origins** (production)
   - Change from `ALLOW_ORIGINS=*`
   - To `ALLOW_ORIGINS=chrome-extension://your-extension-id`
   - Get extension ID from `chrome://extensions/`

4. **Use HTTPS only**
   - Railway provides HTTPS by default ✅
   - Never use `http://` in production

5. **Monitor logs for suspicious activity**
   - Watch for failed auth attempts
   - Check for unusual traffic patterns

---

## Performance Optimization

### Database Indexing

Ensure Supabase tables have proper indexes:

```sql
-- Already in schema.sql, but verify:
CREATE INDEX IF NOT EXISTS idx_rates_entries_run_id 
  ON rates_entries(run_id);
  
CREATE INDEX IF NOT EXISTS idx_rates_entries_created 
  ON rates_entries(created_at DESC);
```

### Caching Strategy

Current implementation:
- **ETag caching** (backend): Returns 304 Not Modified if data unchanged
- **24-hour cache** (extension): Stored in `chrome.storage.local`
- **Memory cache** (extension): Loaded in background service worker

Result: ~99% of requests served from cache, minimal Railway compute time ✅

### Connection Pooling

If traffic increases, consider connection pooling for Supabase:

```python
# In app/core/database.py
from supabase import create_client, Client

# Use persistent client instance (already implemented)
client: Client = create_client(
    supabase_url=settings.supabase_url,
    supabase_key=settings.supabase_service_role_key,
)
```

---

## FAQ

### Q: Can I use internal scheduler instead of GitHub Actions?

**A:** Yes, but it costs more:
- Set `SCHEDULER_MODE=internal` and `ENABLE_SCHEDULER=true` in Railway
- Railway will run 24/7: ~$2-3/month vs ~$0.50/month with external cron
- Still within free tier ($5/month), but less efficient

### Q: What if I exceed Railway free tier?

**A:** Railway free tier includes $5/month credit:
- With external cron: ~$0.50/month (90% remaining)
- With internal scheduler: ~$2-3/month (40-60% remaining)
- If exceeded, Railway will pause your app and notify you
- Consider upgrading to Hobby plan ($5/month) for unlimited hours

### Q: Can I deploy to other platforms?

**A:** Yes! This backend works on any platform with Python support:
- **Heroku**: Similar setup, use `Procfile`
- **Render**: Similar to Railway, auto-detects Python
- **Fly.io**: Requires `Dockerfile` (not included)
- **DigitalOcean App Platform**: Use `Procfile`
- **AWS Lambda**: Requires serverless framework setup

### Q: How do I update the backend after deployment?

**A:** Just push to GitHub:
```bash
# Make changes to code
git add .
git commit -m "feat: new feature"
git push

# Railway auto-deploys from GitHub
# Wait ~2-3 minutes for new deployment
```

### Q: Can I run database migrations automatically?

**A:** Yes, but carefully:
- Add migration step to `railway.toml`:
  ```toml
  [build]
  buildCommand = "pip install -e . && python migrate.py"
  ```
- Create `migrate.py` script to apply Supabase migrations
- Or apply manually via Supabase dashboard (safer)

### Q: What happens if GitHub Actions is down?

**A:** Rare, but possible:
- Rates won't sync for that day (cached data remains valid for 24h)
- Extension continues working with last synced data
- Next day's sync will catch up
- Manual trigger option always available via Railway endpoint

---

## Support & Resources

- **Railway Docs**: https://docs.railway.app/
- **GitHub Actions Docs**: https://docs.github.com/en/actions
- **Supabase Docs**: https://supabase.com/docs
- **FastAPI Docs**: https://fastapi.tiangolo.com/

**Need Help?**
- Check Railway logs first (most issues are evident there)
- Review this troubleshooting guide
- Check GitHub Actions logs for cron issues
- Test endpoints manually with `curl` for debugging

---

## Checklist: Post-Deployment

After following this guide, verify:

- [ ] Railway deployment status shows "Success"
- [ ] Health endpoint returns 200 OK
- [ ] All 11 environment variables configured in Railway
- [ ] `SCHEDULER_MODE=external` and `ENABLE_SCHEDULER=false` set
- [ ] GitHub secrets configured (RAILWAY_API_URL, SYNC_API_KEY)
- [ ] GitHub Actions workflow runs successfully (manual trigger test)
- [ ] Automatic cron schedule verified (daily at 06:00 UTC)
- [ ] Chrome extension updated with Railway URL
- [ ] Extension connects and loads rates successfully
- [ ] Railway usage <10 hours/month after 1 week
- [ ] Costs within free tier (~$0.50/month)

**Congratulations!** 🎉 Your backend is now deployed and fully operational!
