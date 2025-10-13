#!/bin/bash
# Deployment script for Digital Ocean Droplet
# Run this on your droplet after git pull

set -e

echo "🚀 Starting deployment..."

# Pull latest code
echo "📥 Pulling latest code from GitHub..."
git pull origin main

# Activate virtual environment
echo "🐍 Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Ensure systemd uses a single Gunicorn worker with threads (safe for TCP thread)
if grep -q "ExecStart=.*gunicorn" /etc/systemd/system/zdenergy.service; then
	echo "🔧 Patching systemd unit for single-worker gunicorn..."
	sudo sed -i 's/ExecStart=.*gunicorn.*/ExecStart='"$(pwd | sed 's/\//\\\//g')"'\/venv\/bin\/gunicorn -w 1 --threads 8 -b 0.0.0.0:5000 --timeout 120 readings:app/' /etc/systemd/system/zdenergy.service || true
	echo "🔄 Reloading systemd daemon..."
	sudo systemctl daemon-reload
fi

# Restart the service
echo "🔄 Restarting zdenergy service..."
sudo systemctl restart zdenergy

# Check status
echo "✅ Checking service status..."
sudo systemctl status zdenergy --no-pager

echo "🎉 Deployment complete!"
echo "📊 View logs: sudo journalctl -u zdenergy -f"
