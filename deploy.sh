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

# Restart the service
echo "🔄 Restarting zdenergy service..."
sudo systemctl restart zdenergy

# Check status
echo "✅ Checking service status..."
sudo systemctl status zdenergy --no-pager

echo "🎉 Deployment complete!"
echo "📊 View logs: sudo journalctl -u zdenergy -f"
