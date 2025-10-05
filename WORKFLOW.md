# 🚀 Quick Deployment Guide

Simple guide for pushing updates to your Digital Ocean droplet.

## 📝 Daily Workflow

### On Windows (Edit & Push)

```powershell
# 1. Navigate to your project
cd C:\Users\MEHAK-AADIL\Desktop\python\zdenergy

# 2. Check what changed
git status

# 3. Add all changes
git add .

# 4. Commit with a message
git commit -m "Brief description of what you changed"

# 5. Push to GitHub
git push
```

### On Droplet (Deploy)

```bash
# 1. SSH into your droplet
ssh root@YOUR_DROPLET_IP

# 2. Navigate to project folder
cd ~/zdenrgy_analytics

# 3. Pull latest changes
git pull

# 4. Restart the service
sudo systemctl restart zdenergy

# 5. Check if it's running
sudo systemctl status zdenergy

# 6. (Optional) View live logs
sudo journalctl -u zdenergy -f
# Press Ctrl+C to stop viewing logs
```

---

## ⚡ Even Simpler with the Deploy Script

Instead of steps 3-5 above, just run:

```bash
cd ~/zdenrgy_analytics
./deploy.sh
```

This automatically does everything!

---

## 🔍 Useful Commands on Droplet

```bash
# View last 50 lines of logs
sudo journalctl -u zdenergy -n 50

# View live logs (real-time)
sudo journalctl -u zdenergy -f

# Restart the service
sudo systemctl restart zdenergy

# Stop the service
sudo systemctl stop zdenergy

# Start the service
sudo systemctl start zdenergy

# Check service status
sudo systemctl status zdenergy

# Check if ports are listening
sudo netstat -tlnp | grep -E '5000|6000'
```

---

## 📋 Quick Reference Card

| Task | Windows Command | Droplet Command |
|------|----------------|-----------------|
| **Edit code** | Edit in VS Code | - |
| **Save & Push** | `git add . && git commit -m "msg" && git push` | - |
| **Deploy** | - | `cd ~/zdenrgy_analytics && ./deploy.sh` |
| **View logs** | - | `sudo journalctl -u zdenergy -f` |
| **Restart** | - | `sudo systemctl restart zdenergy` |

---

## 🎯 Example Workflow

Let's say you want to change the temperature display:

**1. On Windows:**
```powershell
cd C:\Users\MEHAK-AADIL\Desktop\python\zdenergy

# Edit readings.py in VS Code
# Make your changes...

git add .
git commit -m "Changed temperature display format"
git push
```

**2. On Droplet:**
```bash
ssh root@YOUR_DROPLET_IP
cd ~/zdenrgy_analytics
./deploy.sh
```

**3. Done!** Visit `http://YOUR_DROPLET_IP:5000` to see changes.

---

## ⚠️ Troubleshooting

### Service won't start after update
```bash
# Check logs for errors
sudo journalctl -u zdenergy -n 50

# Try running manually to see error
cd ~/zdenrgy_analytics
source venv/bin/activate
gunicorn -w 4 -b 0.0.0.0:5000 readings:app
```

### Port already in use
```bash
# See what's using the port
sudo netstat -tlnp | grep 5000

# Kill the process if needed
sudo kill -9 PROCESS_ID
sudo systemctl restart zdenergy
```

### Can't access from browser
```bash
# Check firewall
sudo ufw status

# Make sure ports are open
sudo ufw allow 5000/tcp
sudo ufw allow 6000/tcp
```

---

## 💡 Pro Tips

1. **Commit often** - Small, frequent commits are better than big ones
2. **Use descriptive commit messages** - "Fixed bug" ❌ vs "Fixed temperature sensor parsing error" ✅
3. **Test locally first** - Run `python readings.py` on Windows before pushing
4. **Check logs after deploy** - Always verify the service started correctly
5. **Keep a terminal open** - Use `sudo journalctl -u zdenergy -f` while testing

---

## 📞 Need Help?

If something goes wrong:
1. Check service status: `sudo systemctl status zdenergy`
2. Check logs: `sudo journalctl -u zdenergy -n 100`
3. Try manual run: `cd ~/zdenrgy_analytics && source venv/bin/activate && gunicorn readings:app`

---

**Repository:** https://github.com/aadilnoufal/zdenrgy_analytics  
**Web Interface:** http://YOUR_DROPLET_IP:5000  
**TCP Data Port:** YOUR_DROPLET_IP:6000
