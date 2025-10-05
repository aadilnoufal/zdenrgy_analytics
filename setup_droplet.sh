#!/bin/bash
# Initial setup script for Digital Ocean Droplet
# Run this ONCE when setting up a new droplet

set -e

echo "🔧 Setting up ZD Energy on Digital Ocean Droplet..."

# Update system
echo "📦 Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install Python and dependencies
echo "🐍 Installing Python and build tools..."
sudo apt-get install -y python3 python3-pip python3-venv git nginx

# Create virtual environment
echo "🌐 Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python packages
echo "📚 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Copy systemd service file
echo "⚙️ Setting up systemd service..."
sudo cp zdenergy.service /etc/systemd/system/zdenergy.service

# Update the service file with current username
CURRENT_USER=$(whoami)
sudo sed -i "s/your-username/$CURRENT_USER/g" /etc/systemd/system/zdenergy.service

# Set correct WorkingDirectory
CURRENT_DIR=$(pwd)
sudo sed -i "s|/home/your-username/zdenergy|$CURRENT_DIR|g" /etc/systemd/system/zdenergy.service

# Reload systemd and enable service
echo "🔄 Enabling service to start on boot..."
sudo systemctl daemon-reload
sudo systemctl enable zdenergy
sudo systemctl start zdenergy

# Check status
echo "✅ Service status:"
sudo systemctl status zdenergy --no-pager

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📝 Useful commands:"
echo "  Start:   sudo systemctl start zdenergy"
echo "  Stop:    sudo systemctl stop zdenergy"
echo "  Restart: sudo systemctl restart zdenergy"
echo "  Status:  sudo systemctl status zdenergy"
echo "  Logs:    sudo journalctl -u zdenergy -f"
echo ""
echo "🌐 Your app should now be running on:"
echo "  http://$(hostname -I | awk '{print $1}'):5000"
echo ""
echo "🔐 For production, consider setting up Nginx reverse proxy (see NGINX_SETUP.md)"
