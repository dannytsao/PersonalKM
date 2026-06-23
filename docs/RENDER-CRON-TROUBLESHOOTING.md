# Render Cron Troubleshooting Guide

## How to Check if Cron Jobs are Running

### Method 1: Render Dashboard (Easiest)

1. Go to https://render.com and log in
2. Navigate to your **personal-km-line-bot** service
3. Click on the **Cron Jobs** tab in the left sidebar
4. You'll see:
   - `personal-km-weekly-ingestion` - Runs Saturday 23:00 UTC (Sunday 07:00 UTC+8)
   - `personal-km-housekeeping` - Runs daily at 01:00 UTC

**Check each cron job for:**
- ✅ **Status**: Enabled/Paused/Disabled
- 📜 **Logs**: Recent execution history
- ⏰ **Next Run**: Scheduled time

### Method 2: Render API (Programmatic)

You can use the Render API to check cron job status.

**Prerequisites:**
1. Get your Render API key from: https://dashboard.render.com/api-keys
2. Get your Cron Job ID from the Render dashboard URL

**Check cron job status:**
```bash
# Replace YOUR_API_KEY with your Render API key
# Replace CRON_JOB_ID with the cron job ID from Render dashboard

curl -X GET "https://api.render.com/v1/cron-jobs/CRON_JOB_ID" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json"
```

**Get cron job logs:**
```bash
curl -X GET "https://api.render.com/v1/cron-jobs/CRON_JOB_ID/logs" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

**Trigger a cron job manually:**
```bash
curl -X POST "https://api.render.com/v1/cron-jobs/CRON_JOB_ID/run" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Method 3: Check GitHub for Ingestion Commits

The PersonalKM Bot commits to GitHub when ingestion runs. Look for commits from `PersonalKM Bot`:

```bash
cd ~/Documents/PersonalKM
git log --oneline --author="PersonalKM Bot"
```

If there are no commits from `PersonalKM Bot` after the cron schedule, the ingestion likely didn't run or failed.

---

## Common Issues and Fixes

### Issue 1: Cron Job Not Listed
**Symptoms:** You don't see cron jobs in the dashboard

**Possible causes:**
- Cron jobs were deleted
- You're looking at the wrong Render account
- The service wasn't created with the render.yaml

**Fix:**
1. Check if `render.yaml` is in the root of your GitHub repo
2. Verify the cron definitions match the format in this repo
3. Delete and recreate the cron jobs manually on Render

### Issue 2: Cron Job is Paused
**Symptoms:** Cron job exists but doesn't run

**Fix:**
1. Go to Render Dashboard → Cron Jobs
2. Find the paused cron job
3. Click **Resume** or **Enable**

### Issue 3: Cron Runs but 0 Files Processed
**Symptoms:** Cron runs successfully but no files are ingested

**Possible causes:**
1. **Files not pushed to GitHub** before cron ran
   - The cron clones fresh from GitHub each time
   - If files weren't pushed, they're not available on Render

2. **Git sync issue**
   - Render might not have pulled the latest commits

3. **Wrong VAULT_PATH**
   - Check that `VAULT_PATH` matches where files should be

**Fix:**
1. Check GitHub to confirm files are committed
2. Check the cron logs for specific errors
3. Verify `VAULT_PATH` is correct in render.yaml

### Issue 4: OpenAI API Failure
**Symptoms:** Logs show "Could not connect to OpenAI"

**Possible causes:**
- `OPENAI_API_KEY` not set in cron job environment
- API key is incorrect
- OpenAI API is down

**Fix:**
1. Go to Render Dashboard → Cron Job → Environment
2. Verify `OPENAI_API_KEY` is set correctly
3. Check that the key has sufficient credits

### Issue 5: No Notification Received
**Symptoms:** Ingestion ran but you didn't get notified

**Possible causes:**
- `NOTIFY_DISCORD_WEBHOOK` or `NOTIFY_LINE_WEBHOOK` not configured
- Webhook URLs are incorrect

**Fix:**
1. Set notification webhooks in Render cron job environment:
   - `NOTIFY_DISCORD_WEBHOOK`: Your Discord webhook URL
   - `NOTIFY_LINE_WEBHOOK`: LINE Notify webhook URL

---

## Verification Checklist

Before assuming ingestion failed, verify:

- [ ] Cron job is **Enabled** (not paused)
- [ ] Cron job has **recent logs** showing execution
- [ ] Files are **committed to GitHub** before the cron ran
- [ ] `OPENAI_API_KEY` is set in the cron job environment
- [ ] `VAULT_REPO_URL` is correct
- [ ] Notification webhooks are configured (optional)

---

## Testing Ingestion Locally

You can test the ingestion system locally:

```bash
cd ~/Documents/PersonalKM
python scripts/test_ingestion.py
```

This will:
- Check if raw/ directory exists and has files
- Verify the glob pattern finds subdirectory files
- Check environment variables

---

## Getting Help

If you've verified all the above and ingestion still isn't working:

1. Check Render status page: https://status.render.com/
2. Check OpenAI status: https://status.openai.com/
3. Review Render cron logs for specific error messages
4. Try manually triggering the cron job from Render dashboard
