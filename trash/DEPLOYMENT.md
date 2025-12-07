# Deployment Guide for Digital Ocean Droplet

Complete guide to deploy the ZD Energy Sensor Dashboard on Digital Ocean.

## 📋 Prerequisites

- Digital Ocean Droplet (Ubuntu 20.04+ recommended)
- GitHub account
- SSH access to your droplet

## 🚀 First Time Setup

### 1. Push Code to GitHub (On Windows)

```powershell
# In your project folder
cd C:\Users\MEHAK-AADIL\Desktop\python\zdenergy

# Initialize git (if not done)
git init
git add .
git commit -m "Initial commit"

# Create repo on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/zdenergy.git
git branch -M main
git push -u origin main
```

### 2. Setup on Digital Ocean Droplet

SSH into your droplet:

```bash
ssh root@YOUR_DROPLET_IP
```

Clone and setup:

```bash
# Clone your repository
cd ~
git clone https://github.com/YOUR_USERNAME/zdenergy.git
cd zdenergy

# Make scripts executable
chmod +x setup_droplet.sh deploy.sh

# Run the setup script (does everything automatically)
./setup_droplet.sh
```

This will:

- ✅ Install Python 3, pip, venv
- ✅ Create virtual environment
- ✅ Install all dependencies
- ✅ Setup systemd service (auto-start on boot)
- ✅ Start your application

### 3. Verify It's Running

```bash
# Check service status
sudo systemctl status zdenergy

# View live logs
sudo journalctl -u zdenergy -f

# Test the endpoint
curl http://localhost:5000
```

Visit: `http://YOUR_DROPLET_IP:5000`

## 🔄 Daily Workflow: Making Updates

### On Windows (Edit & Push)

```powershell
# Edit your code in VS Code or any editor
# Then commit and push:

git add .
git commit -m "Description of changes"
git push
```

### On Droplet (Pull & Deploy)

```bash
cd ~/zdenergy
./deploy.sh
```

That's it! The `deploy.sh` script automatically:

- Pulls latest code
- Installs new dependencies
- Restarts the service

## 🛠️ Useful Commands

```bash
# Start the service
sudo systemctl start zdenergy

# Stop the service
sudo systemctl stop zdenergy

# Restart the service
sudo systemctl restart zdenergy

# Check status
sudo systemctl status zdenergy

# View logs (live)
sudo journalctl -u zdenergy -f

# View last 100 lines of logs
sudo journalctl -u zdenergy -n 100

# Check if port 5000 is listening
sudo netstat -tlnp | grep 5000

# Check if port 6000 (TCP sensor) is listening
sudo netstat -tlnp | grep 6000
```

## 🔒 Opening Firewall Ports

Digital Ocean droplets use UFW firewall:

```bash
# Allow HTTP (port 5000)
sudo ufw allow 5000/tcp

# Allow TCP sensor data (port 6000)
sudo ufw allow 6000/tcp

# Allow SSH (if not already)
sudo ufw allow 22/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

## 🌐 Optional: Setup Nginx Reverse Proxy

For production, it's better to use Nginx on port 80:

```bash
sudo nano /etc/nginx/sites-available/zdenergy
```

Add this configuration:

```nginx
server {
    listen 80;
    server_name YOUR_DROPLET_IP;  # or your domain

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable and restart:

```bash
sudo ln -s /etc/nginx/sites-available/zdenergy /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

Now access via: `http://YOUR_DROPLET_IP` (no port needed!)

## 🔐 Optional: Add SSL Certificate (HTTPS)

If you have a domain name:

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d yourdomain.com

# Auto-renewal is setup automatically
```

## 📊 Monitoring

Check app health:

```bash
# Check if service is running
systemctl is-active zdenergy

# Check memory usage
ps aux | grep gunicorn

# Check disk space
df -h

# Check system resources
htop
```

## 🐛 Troubleshooting

### Service won't start

```bash
# Check logs for errors
sudo journalctl -u zdenergy -n 50

# Check if ports are already in use
sudo netstat -tlnp | grep 5000
sudo netstat -tlnp | grep 6000
```

### Permission issues

```bash
# Fix ownership
sudo chown -R $USER:$USER ~/zdenergy
```

### Can't connect from outside

```bash
# Check firewall
sudo ufw status

# Check if app is binding to 0.0.0.0 (not 127.0.0.1)
sudo netstat -tlnp | grep 5000
```

## 📈 Performance Tuning

Edit `/etc/systemd/system/zdenergy.service` to adjust workers:

```ini
# For 1GB droplet: 2-3 workers
ExecStart=/home/your-username/zdenergy/venv/bin/gunicorn -w 3 -b 0.0.0.0:5000 --timeout 120 readings:app

# For 2GB droplet: 4-5 workers
ExecStart=/home/your-username/zdenergy/venv/bin/gunicorn -w 5 -b 0.0.0.0:5000 --timeout 120 readings:app
```

Then reload:

```bash
sudo systemctl daemon-reload
sudo systemctl restart zdenergy
```

## 🎯 Quick Reference

| Task           | Command                           |
| -------------- | --------------------------------- |
| Deploy updates | `./deploy.sh`                     |
| View logs      | `sudo journalctl -u zdenergy -f`  |
| Restart        | `sudo systemctl restart zdenergy` |
| Check status   | `sudo systemctl status zdenergy`  |

---

Need help? Check the logs first: `sudo journalctl -u zdenergy -f`
