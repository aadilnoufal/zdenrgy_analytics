# 🔐 Server .env Setup Guide

## Issue

Server is trying to connect to local PostgreSQL instead of DigitalOcean managed database:

```
connection to server on socket "/var/run/postgresql/.s.PGSQL.5432" failed
```

This happens because the `.env` file (which contains DB credentials) is in `.gitignore` and was never created on the server.

## Solution: Create .env on Server

### Step 1: SSH into Server

```bash
ssh root@146.190.10.188
cd ~/zdenrgy_analytics
```

### Step 2: Create .env File

```bash
nano .env
```

### Step 3: Paste These Contents

```bash
# Database Configuration - DigitalOcean Managed PostgreSQL

# Flask Configuration
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=zdenergy-production-secret-key-$(openssl rand -hex 32)

# Server Settings
APP_HOST=0.0.0.0
HTTP_PORT=5000
TCP_PORT=6000
MAX_SAMPLES=5000
```

### Step 4: Save and Exit

- Press `Ctrl + O` to save
- Press `Enter` to confirm
- Press `Ctrl + X` to exit

### Step 5: Verify File Created

```bash
cat .env
```

### Step 6: Set Correct Permissions

```bash
chmod 600 .env  # Only root can read/write
```

### Step 7: Restart Service

```bash
sudo systemctl restart zdenergy
sudo journalctl -u zdenergy -f
```

## Expected Output After Fix

```
✅ Database connection pool created successfully
✅ Stored reading: t=2025-10-19T... temp=XX.XX°C rh=XX.XX% lux=XXXX.XX
✅ TCP server started on port 6000
```

## Alternative: One-Line Setup

```bash
ssh root@146.190.10.188 "cd ~/zdenrgy_analytics && cat > .env << 'EOF'
D

DB_SSLMODE=require
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=zdenergy-prod-secret-$(date +%s)
APP_HOST=0.0.0.0
HTTP_PORT=5000
TCP_PORT=6000
MAX_SAMPLES=5000
EOF
chmod 600 .env && sudo systemctl restart zdenergy"
```

## Security Note

⚠️ **IMPORTANT**: The `.env` file contains your database password. Keep it secure:

- ✅ File is already in `.gitignore` (won't be committed)
- ✅ Set permissions to `600` (only root can access)
- ✅ Never share this file publicly
- ⚠️ Consider rotating the DB password since it was exposed in git history

## Verification Checklist

- [ ] `.env` file exists on server
- [ ] File has correct permissions (`600`)
- [ ] Service restarts without errors
- [ ] Database queries work (check logs)
- [ ] Dashboard shows data at http://146.190.10.188:5000

## Troubleshooting

### Still Getting Socket Error?

```bash
# Check if .env is being loaded
cd ~/zdenrgy_analytics
source venv/bin/activate
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('DB_HOST:', os.getenv('DB_HOST'))"
```

Should print: `DB_HOST: zd-energy-db-do-user-22778792-0.f.db.ondigitalocean.com`

### Test DB Connection Manually

```bash
cd ~/zdenrgy_analytics
source venv/bin/activate
python test_database.py
```

### Check Service Environment

```bash
sudo systemctl show zdenergy --property=Environment
```

---

**Quick Fix Command (copy-paste into SSH session):**

```bash
cd ~/zdenrgy_analytics && cat > .env << 'EOF'

DB_NAME=defaultdb
DB_SSLMODE=require
FLASK_ENV=production
FLASK_DEBUG=False
EOF
chmod 600 .env && sudo systemctl restart zdenergy && sleep 2 && sudo journalctl -u zdenergy -n 20 --no-pager
```
