#!/bin/bash
# NexAlert v3.0 - Deployment Script for Raspberry Pi 5
# Run this ONCE after copying files to /home/pi/nexalert_v3/

set -e  # Exit on error

echo "=================================================="
echo "  NexAlert v3.0 Deployment"
echo "  Autonomous Emergency Communication Platform"
echo "=================================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as correct user
if [ "$USER" != "pi" ] && [ "$USER" != "venom" ]; then
    echo -e "${YELLOW}Warning: This script is designed to run as 'pi' or 'venom' user${NC}"
fi

INSTALL_DIR="/home/$(whoami)/nexalert_v3"

echo -e "${GREEN}Step 1: Installing system dependencies${NC}"
sudo apt-get update
sudo apt-get install -y \
    python3-pip \
    python3-venv \
    python3-dev \
    dnsmasq \
    hostapd \
    network-manager \
    sqlite3 \
    git \
    nginx

echo ""
echo -e "${GREEN}Step 2: Creating Python virtual environment${NC}"
cd "$INSTALL_DIR"
python3 -m venv venv
source venv/bin/activate

echo ""
echo -e "${GREEN}Step 3: Installing Python packages${NC}"
pip install --upgrade pip
pip install \
    flask \
    flask-socketio \
    flask-sqlalchemy \
    flask-cors \
    python-socketio \
    eventlet \
    requests \
    pyserial

echo ""
echo -e "${GREEN}Step 4: Creating database directory${NC}"
mkdir -p "$INSTALL_DIR/database"
mkdir -p "$INSTALL_DIR/logs"

# Initialize database
echo -e "${GREEN}Initializing database...${NC}"
python3 << EOF
import sys
sys.path.insert(0, '$INSTALL_DIR/backend')
from app import app, db
with app.app_context():
    db.create_all()
    print("✓ Database tables created")
EOF

echo ""
echo -e "${GREEN}Step 5: Setting up network configuration${NC}"

# Stop conflicting services
sudo systemctl stop dnsmasq
sudo systemctl stop hostapd

# Determine which interface is the USB dongle (wlan1 likely)
echo -e "${YELLOW}Configuring hotspot on wlan1 (USB dongle)${NC}"

# Copy NetworkManager hotspot profile
sudo cp "$INSTALL_DIR/network_config/hotspot.nmconnection" \
    /etc/NetworkManager/system-connections/NexAlert-Hotspot.nmconnection
sudo chmod 600 /etc/NetworkManager/system-connections/NexAlert-Hotspot.nmconnection

# Configure dnsmasq for captive portal
sudo cp "$INSTALL_DIR/network_config/dnsmasq-nexalert.conf" \
    /etc/dnsmasq.d/nexalert.conf

# Enable and restart services
sudo systemctl enable NetworkManager
sudo systemctl restart NetworkManager
sudo systemctl enable dnsmasq
sudo systemctl restart dnsmasq

echo ""
echo -e "${GREEN}Step 6: Installing systemd service${NC}"
sudo cp "$INSTALL_DIR/systemd_services/nexalert.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable nexalert.service
sudo systemctl start nexalert.service

echo ""
echo -e "${GREEN}Step 7: Configuring nginx reverse proxy (optional SSL)${NC}"
sudo tee /etc/nginx/sites-available/nexalert > /dev/null << 'NGINX_EOF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    # Redirect all HTTP to Flask app
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support
    location /socket.io {
        proxy_pass http://127.0.0.1:5000/socket.io;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
NGINX_EOF

sudo ln -sf /etc/nginx/sites-available/nexalert /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo systemctl enable nginx
sudo systemctl restart nginx

echo ""
echo -e "${GREEN}Step 8: Setting up captive portal redirect${NC}"
# Add iptables rules to redirect port 80 traffic
sudo iptables -t nat -A PREROUTING -i wlan1 -p tcp --dport 80 -j REDIRECT --to-port 80
sudo iptables -t nat -A PREROUTING -i wlan1 -p tcp --dport 443 -j REDIRECT --to-port 80

# Save iptables rules
sudo sh -c "iptables-save > /etc/iptables.rules"

# Create restore script
sudo tee /etc/network/if-pre-up.d/iptables > /dev/null << 'IPTABLES_EOF'
#!/bin/sh
iptables-restore < /etc/iptables.rules
IPTABLES_EOF

sudo chmod +x /etc/network/if-pre-up.d/iptables

echo ""
echo "=================================================="
echo -e "${GREEN}✅ NexAlert v3.0 Installation Complete!${NC}"
echo "=================================================="
echo ""
echo "📡 Hotspot SSID: NexAlert-Emergency"
echo "🔒 Password: nexalert2025"
echo "🌐 Access Point: http://10.42.0.1 or http://nexalert.local"
echo ""
echo "Service Status:"
sudo systemctl status nexalert.service --no-pager -l | head -10
echo ""
echo "To view logs:"
echo "  sudo journalctl -u nexalert -f"
echo "  tail -f $INSTALL_DIR/logs/nexalert.log"
echo ""
echo -e "${YELLOW}Rebooting in 10 seconds...${NC}"
echo "Press Ctrl+C to cancel"
sleep 10
sudo reboot
