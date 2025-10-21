# 🔧 Quick Deployment Fix

## Issue

Server failed to start due to missing `requests` module:

```
ModuleNotFoundError: No module named 'requests'
```

## Solution

Added `requests>=2.31.0` to `requirements.txt` and pushed to GitHub.

## Steps to Fix on Server

### Option 1: SSH and Redeploy (Recommended)

```bash
# SSH into server
ssh root@146.190.10.188

# Navigate to project
cd ~/zdenrgy_analytics

# Pull latest changes
git pull origin main

# Activate virtual environment
source venv/bin/activate

# Install missing dependency
pip install -r requirements.txt

# Restart service
sudo systemctl restart zdenergy

# Verify it's running
sudo systemctl status zdenergy

# Watch logs to confirm success
sudo journalctl -u zdenergy -f
```

### Option 2: Use Deploy Script

```bash
# SSH into server
ssh root@146.190.10.188

# Navigate to project
cd ~/zdenrgy_analytics

# Pull latest changes
git pull origin main

# Run deploy script (installs deps automatically)
bash deploy.sh
```

## Expected Output

After fix, you should see:

```
✅ [INFO] Starting gunicorn 23.0.0
✅ [INFO] Listening at: http://0.0.0.0:5000
✅ [INFO] Using worker: gthread
✅ [INFO] Booting worker with pid: XXXXX
✅ TCP server started on port 6000 in background thread
```

## Verification

1. **Check service status:**

   ```bash
   sudo systemctl status zdenergy
   ```

   Should show: `Active: active (running)`

2. **Test web interface:**

   ```bash
   curl http://localhost:5000/
   ```

   Should return HTML dashboard

3. **Test API:**
   ```bash
   curl http://localhost:5000/api/status
   ```
   Should return JSON with system stats

## Why This Happened

- The `data_sources.py` module uses `requests` for REST API data sources
- `requests` was imported but not listed in `requirements.txt`
- When the server installed dependencies, `requests` was skipped
- On import, Python couldn't find the module

## Prevention

- Always ensure imports match `requirements.txt`
- Test fresh virtual environment installs before deploying
- Consider using `pip freeze > requirements.txt` after development

---

**Quick Commands for Server:**

```bash
# If still having issues, try:
cd ~/zdenrgy_analytics
git pull
source venv/bin/activate
pip install --upgrade -r requirements.txt
sudo systemctl restart zdenergy
sudo journalctl -u zdenergy -n 50 --no-pager
```
