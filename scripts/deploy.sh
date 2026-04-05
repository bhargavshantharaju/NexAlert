#!/bin/bash

################################################################################
# NexAlert v3.0 - Automated Deployment Script
# Installs dependencies, sets up Python environment, configures Nginx
# Run: sudo ./deploy.sh
################################################################################

set -e

echo "=========================================="
echo "NexAlert v3.0 - Deployment Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Error handling
error_exit() {
    echo -e "${RED}ERROR: $1${NC}"
    exit 1
}

success_msg() {
    echo -e "${GREEN}✓ $1${NC}"
}

info_msg() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# ============================================================================
# SYSTEM REQUIREMENTS CHECK
# ============================================================================

echo "Checking system requirements..."

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   error_exit "This script must be run as root (use: sudo ./deploy.sh)"
fi

# Check OS
if ! command -v apt-get &> /dev/null; then
    error_exit "This script requires a Debian/Ubuntu based system"
fi

success_msg "System requirements verified"
echo ""

# ============================================================================
# UPDATE SYSTEM
# ============================================================================

echo "Updating system packages..."
apt-get update
apt-get upgrade -y
success_msg "System packages updated"
echo ""

# ============================================================================
# INSTALL SYSTEM DEPENDENCIES
# ============================================================================

echo "Installing system dependencies..."

# Required packages
PACKAGES="python3 python3-pip python3-dev python3-venv git curl wget nginx supervisor dnsmasq iptables build-essential libssl-dev libffi-dev"

apt-get install -y $PACKAGES

success_msg "System dependencies installed"
echo ""

# ============================================================================
# PYTHON VIRTUAL ENVIRONMENT
# ============================================================================

echo "Setting up Python virtual environment..."

APP_DIR="/opt/nexalert"
VENV_DIR="$APP_DIR/venv"

# Create app directory if not exists
if [ -d "$APP_DIR" ]; then
    info_msg "App directory already exists at $APP_DIR"
else
    mkdir -p "$APP_DIR"
    success_msg "Created app directory: $APP_DIR"
fi

cd "$APP_DIR"

# Create virtual environment
if [ -d "$VENV_DIR" ]; then
    info_msg "Virtual environment already exists"
else
    python3 -m venv "$VENV_DIR"
    success_msg "Virtual environment created"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# ============================================================================
# INSTALL PYTHON DEPENDENCIES
# ============================================================================

echo "Installing Python dependencies..."

# Check if requirements.txt exists
if [ -f "requirements.txt" ]; then
    pip install --upgrade pip setuptools wheel
    pip install -r requirements.txt
    success_msg "Python dependencies installed"
else
    info_msg "requirements.txt not found, manually installing packages..."
    pip install --upgrade pip setuptools wheel
    pip install Flask==2.3.3 Flask-SocketIO==5.3.4 python-socketio==5.9.0 python-engineio==4.7.0 \
                python-dotenv==1.0.0 Werkzeug==2.3.7 eventlet==0.33.3 gevent==23.9.1 \
                gevent-websocket==0.10.1 requests==2.31.0 bcrypt==4.0.1 PyJWT==2.8.0
    success_msg "Python packages installed"
fi

echo ""

# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================

echo "Initializing database..."

if [ -f "database/schema.sql" ]; then
    sqlite3 database/nexalert.db < database/schema.sql
    success_msg "Database initialized"
else
    error_exit "schema.sql not found"
fi

echo ""

# ============================================================================
# NGINX CONFIGURATION
# ============================================================================

echo "Configuring Nginx as reverse proxy..."

# Create Nginx config
NGINX_CONFIG="/etc/nginx/sites-available/nexalert"

cat > "$NGINX_CONFIG" << 'EOF'
upstream nexalert_app {
    server 127.0.0.1:5000;
}

server {
    listen 80 default_server;
    listen [::]:80 default_server;
    
    server_name _;
    
    # Redirect HTTP to HTTPS (if SSL certificates are available)
    # Uncomment after SSL setup:
    # return 301 https://$server_name$request_uri;
    
    # For development, allow HTTP
    
    client_max_body_size 10M;
    
    location / {
        proxy_pass http://nexalert_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
    
    location /static {
        alias /opt/nexalert/static;
        expires 30d;
    }
    
    # Gzip compression
    gzip on;
    gzip_types text/plain text/css text/javascript application/json;
    gzip_min_length 1000;
}

# HTTPS configuration (uncomment after SSL setup)
# server {
#     listen 443 ssl http2 default_server;
#     listen [::]:443 ssl http2 default_server;
#     
#     ssl_certificate /etc/ssl/certs/nexalert.crt;
#     ssl_certificate_key /etc/ssl/private/nexalert.key;
#     ssl_protocols TLSv1.2 TLSv1.3;
#     ssl_ciphers HIGH:!aNULL:!MD5;
#     
#     # ... rest of server config ...
# }
EOF

# Enable site
ln -sf "$NGINX_CONFIG" /etc/nginx/sites-enabled/nexalert

# Remove default config if exists
rm -f /etc/nginx/sites-enabled/default

# Test Nginx config
if nginx -t 2>/dev/null; then
    success_msg "Nginx configuration is valid"
    # Restart Nginx
    systemctl restart nginx
    success_msg "Nginx started/restarted"
else
    error_exit "Nginx configuration test failed"
fi

echo ""

# ============================================================================
# SYSTEMD SERVICE FILE
# ============================================================================

echo "Setting up SystemD service..."

SERVICE_FILE="/etc/systemd/system/nexalert.service"

cat > "$SERVICE_FILE" << 'EOF'
[Unit]
Description=NexAlert v3.0 Emergency Mesh Platform
After=network.target
StartLimitBurst=5
StartLimitIntervalSec=60

[Service]
Type=simple
User=root
Restart=always
RestartSec=10
WorkingDirectory=/opt/nexalert
Environment="PATH=/opt/nexalert/venv/bin"
ExecStart=/opt/nexalert/venv/bin/python /opt/nexalert/app/app.py
StandardOutput=journal
StandardError=journal
SyslogIdentifier=nexalert

# Auto-restart on crash (max 5 restarts per 60 seconds)
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Reload SystemD daemon
systemctl daemon-reload

# Enable service to start on boot
systemctl enable nexalert

# Start service
systemctl start nexalert

success_msg "NexAlert SystemD service installed and started"
echo ""

# ============================================================================
# LOGGING SETUP
# ============================================================================

echo "Setting up logging..."

# Create logs directory
mkdir -p "$APP_DIR/logs"
chmod 755 "$APP_DIR/logs"

# Setup log rotation
cat > /etc/logrotate.d/nexalert << 'EOF'
/opt/nexalert/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 root root
    sharedscripts
}
EOF

success_msg "Logging configured"
echo ""

# ============================================================================
# FIREWALL CONFIGURATION (UFW)
# ============================================================================

echo "Configuring firewall..."

# Check if UFW is installed
if command -v ufw &> /dev/null; then
    ufw allow 22/tcp      # SSH
    ufw allow 80/tcp      # HTTP
    ufw allow 443/tcp     # HTTPS
    ufw allow 5000/tcp    # Flask dev (internal)
    success_msg "Firewall rules configured"
else
    info_msg "UFW not installed, skipping firewall configuration"
fi

echo ""

# ============================================================================
# FINAL VALIDATION
# ============================================================================

echo "=========================================="
echo "Deployment Status Check"
echo "=========================================="
echo ""

# Check if service is running
if systemctl is-active --quiet nexalert; then
    success_msg "NexAlert service is running"
else
    info_msg "NexAlert service status: not running"
    echo "To start manually: sudo systemctl start nexalert"
fi

# Check Nginx
if systemctl is-active --quiet nginx; then
    success_msg "Nginx is running"
else
    info_msg "Nginx is not running"
fi

echo ""
echo "=========================================="
echo "Deployment Summary"
echo "=========================================="
echo ""
echo "✓ System packages installed"
echo "✓ Python environment configured"
echo "✓ Database initialized"
echo "✓ Nginx reverse proxy configured"
echo "✓ SystemD service created"
echo "✓ Logging configured"
echo ""
echo "Application directory: $APP_DIR"
echo "Virtual environment: $VENV_DIR"
echo "Database file: $APP_DIR/database/nexalert.db"
echo ""
echo "Access the application at: http://localhost"
echo "Dashboard at: http://localhost/dashboard"
echo ""
echo "To view logs:"
echo "  journalctl -u nexalert -f"
echo ""
echo "To restart the service:"
echo "  sudo systemctl restart nexalert"
echo ""
echo "=========================================="
echo "Next Steps:"
echo "=========================================="
echo "1. Run setup_network.sh to configure dual WiFi mesh networking"
echo "2. Update Google Maps API key in dashboard.html"
echo "3. Configure SSL certificates for HTTPS"
echo "4. Adjust firewall and security settings as needed"
echo ""
success_msg "Deployment completed successfully!"
echo ""
