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

# Ensure systemd unit uses a single worker (avoid per-process memory state)
echo "⚙️ Ensuring systemd unit is up-to-date..."
if [ -f /etc/systemd/system/zdenergy.service ]; then
	SERVICE_FILE=/etc/systemd/system/zdenergy.service
	# Update ExecStart to single worker with threads and correct venv path
	VENV_BIN="$(pwd)/venv/bin"
	ESCAPED_VENV_BIN=$(printf '%s\n' "$VENV_BIN" | sed 's:[\\&]:\\\\&:g')
	sudo sed -i "s#^ExecStart=.*#ExecStart=${ESCAPED_VENV_BIN}/gunicorn -w 1 --threads 4 -b 0.0.0.0:5000 --timeout 120 readings:app#" "$SERVICE_FILE"
	# Ensure PYTHONUNBUFFERED is present
	if ! grep -q '^Environment="PYTHONUNBUFFERED=1"' "$SERVICE_FILE"; then
		sudo sed -i '/^Environment="PATH=/a Environment="PYTHONUNBUFFERED=1"' "$SERVICE_FILE"
	fi
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
