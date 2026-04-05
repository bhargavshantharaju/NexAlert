#!/bin/bash

################################################################################
# NexAlert v3.0 - Network Setup Script
# Configures dual WiFi interface setup (wlan0 for internet, wlan1 for hotspot)
# Sets up captive portal via dnsmasq
# Run: sudo ./setup_network.sh
################################################################################

set -e

echo "=========================================="
echo "NexAlert v3.0 - Network Configuration"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

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
# SYSTEM REQUIREMENTS
# ============================================================================

echo "Checking system requirements..."

if [[ $EUID -ne 0 ]]; then
   error_exit "This script must be run as root"
fi

# Check for required network tools
REQUIRED_TOOLS="nmcli dnsmasq iptables ip"
for tool in $REQUIRED_TOOLS; do
    if ! command -v $tool &> /dev/null; then
        error_exit "$tool is not installed"
    fi
done

success_msg "System requirements verified"
echo ""

# ============================================================================
# NETWORK INTERFACE DETECTION
# ============================================================================

echo "Detecting network interfaces..."

# Get available WiFi interfaces
WLAN_INTERFACES=($(nmcli device status 2>/dev/null | grep wifi | awk '{print $1}'))

if [ ${#WLAN_INTERFACES[@]} -lt 2 ]; then
    error_exit "At least 2 WiFi interfaces are required for mesh setup. Found: ${#WLAN_INTERFACES[@]}"
fi

# Assign interfaces
WLAN_INTERNET="${WLAN_INTERFACES[0]}"
WLAN_HOTSPOT="${WLAN_INTERFACES[1]}"

info_msg "Internet Interface: $WLAN_INTERNET"
info_msg "Hotspot Interface: $WLAN_HOTSPOT"
echo ""

# ============================================================================
# INTERNET CONNECTION (wlan0)
# ============================================================================

echo "Setting up internet interface ($WLAN_INTERNET)..."

# Check if interface is connected
if ! nmcli device show "$WLAN_INTERNET" | grep -q "CONNECTED"; then
    info_msg "Interface $WLAN_INTERNET is not connected. Please connect to WiFi."
    echo "Available networks:"
    nmcli device wifi list
    read -p "Enter network SSID: " SSID
    read -sp "Enter password: " PASSWORD
    echo ""
    
    nmcli device wifi connect "$SSID" password "$PASSWORD" ifname "$WLAN_INTERNET"
fi

success_msg "Internet interface ($WLAN_INTERNET) configured"
echo ""

# ============================================================================
# HOTSPOT INTERFACE SETUP (wlan1)
# ============================================================================

echo "Setting up hotspot interface ($WLAN_HOTSPOT)..."

# Check if interface supports AP mode
info_msg "Checking AP mode support..."

if ! iw "$WLAN_HOTSPOT" info | grep -q "AP"; then
    error_exit "Interface $WLAN_HOTSPOT does not support AP (Access Point) mode. You may need a different USB WiFi dongle that supports AP mode."
fi

success_msg "Interface $WLAN_HOTSPOT supports AP mode"

# Bring interface down
nmcli device set "$WLAN_HOTSPOT" managed no
ip link set "$WLAN_HOTSPOT" down

success_msg "Interface brought down"
echo ""

# ============================================================================
# CONFIGURE STATIC IP FOR HOTSPOT
# ============================================================================

echo "Configuring static IP for hotspot..."

# Set static IP on hotspot interface
ip link set "$WLAN_HOTSPOT" up
ip addr flush dev "$WLAN_HOTSPOT"
ip addr add 10.42.0.1/24 dev "$WLAN_HOTSPOT"

success_msg "Static IP 10.42.0.1/24 assigned to $WLAN_HOTSPOT"
echo ""

# ============================================================================
# DNSMASQ CONFIGURATION (Captive Portal)
# ============================================================================

echo "Configuring dnsmasq for captive portal..."

# Backup original config
cp /etc/dnsmasq.conf /etc/dnsmasq.conf.backup.$(date +%s)

# Create NexAlert-specific dnsmasq config
cat > /etc/dnsmasq.conf << 'EOF'
# NexAlert v3.0 DHCP & DNS Configuration

# Listen only on hotspot interface
interface=wlan1
bind-interfaces

# DHCP Configuration
dhcp-range=10.42.0.50,10.42.0.150,12h
dhcp-option=option:router,10.42.0.1
dhcp-option=option:dns-server,10.42.0.1

# Captive Portal Configuration
# CRITICAL: This line redirects ALL DNS queries to the gateway
# This ensures any URL typed (google.com, etc.) gets redirected to the captive portal
address=/#/10.42.0.1

# Log DHCP requests (optional, for debugging)
log-facility=/var/log/dnsmasq.log
log-dhcp

# Disable DNSSEC
dnssec

# Cache DNS
cache-size=150
EOF

# Kill any running dnsmasq instances
pkill dnsmasq || true
sleep 1

# Start dnsmasq
dnsmasq -C /etc/dnsmasq.conf

success_msg "dnsmasq configured and started"
info_msg "Captive portal DNS redirection active"
echo ""

# ============================================================================
# IPTABLES FIREWALL RULES
# ============================================================================

echo "Configuring iptables firewall rules..."

# Enable IP forwarding
echo 1 > /proc/sys/net/ipv4/ip_forward
echo "net.ipv4.ip_forward = 1" >> /etc/sysctl.conf
sysctl -p > /dev/null

# Clear existing rules
iptables -F
iptables -t nat -F

# Allow established connections
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# Allow loopback
iptables -A INPUT -i lo -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT

# Allow SSH for remote management
iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# Allow HTTP and HTTPS
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# Allow Flask app ports
iptables -A INPUT -p tcp --dport 5000 -j ACCEPT

# Allow DNS (port 53)
iptables -A INPUT -p udp --dport 53 -j ACCEPT
iptables -A INPUT -p tcp --dport 53 -j ACCEPT

# Allow DHCP (port 67, 68)
iptables -A INPUT -p udp --dport 67:68 -j ACCEPT

# Allow communication between interfaces
iptables -A FORWARD -i "$WLAN_HOTSPOT" -j ACCEPT
iptables -A FORWARD -i "$WLAN_INTERNET" -j ACCEPT
iptables -A FORWARD -o "$WLAN_HOTSPOT" -j ACCEPT
iptables -A FORWARD -o "$WLAN_INTERNET" -j ACCEPT

# NAT configuration: allow hotspot users to access internet through wlan0
iptables -t nat -A POSTROUTING -o "$WLAN_INTERNET" -j MASQUERADE
iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE

# Captive Portal: HTTP traffic redirection
# Redirect all HTTP traffic on port 80 to localhost:80
iptables -t nat -A PREROUTING -i "$WLAN_HOTSPOT" -p tcp --dport 80 -j DNAT --to-destination 10.42.0.1

# Optional: Redirect HTTPS traffic too (for full-screen captive portal)
# iptables -t nat -A PREROUTING -i wlan1 -p tcp --dport 443 -j DNAT --to-destination 10.42.0.1:443

success_msg "iptables rules configured"
echo ""

# ============================================================================
# CREATE HOSTAP CONFIGURATION (AP Mode)
# ============================================================================

echo "Creating hostapd configuration for AP mode..."

# Check if hostapd is installed
if ! command -v hostapd &> /dev/null; then
    info_msg "Installing hostapd..."
    apt-get update > /dev/null
    apt-get install -y hostapd > /dev/null
    success_msg "hostapd installed"
fi

# Create hostapd config file
HOSTAPD_CONFIG="/etc/hostapd/nexalert.conf"

cat > "$HOSTAPD_CONFIG" << 'EOF'
# NexAlert v3.0 hostapd Configuration
# AP (Access Point) mode configuration for wlan1

interface=wlan1
driver=nl80211

# WiFi settings
ssid=NexAlert-Emergency
channel=6
hw_mode=g
max_num_sta=50

# WPA2 Security (optional - can be disabled for open network)
# Uncomment for WPA2 security:
# wpa=2
# wpa_passphrase=NexAlert@2024
# wpa_key_mgmt=WPA-PSK
# wpa_pairwise=CCMP

# Uncomment for open network (no authentication):
ieee80211d=1
country_code=US
EOF

success_msg "hostapd configuration created"
echo ""

# ============================================================================
# SYSTEMD SERVICE FOR HOSTAPD
# ============================================================================

echo "Creating systemd service files..."

# hostapd service
cat > /etc/systemd/system/hostapd-nexalert.service << 'EOF'
[Unit]
Description=NexAlert Hostapd (AP Mode)
BindsTo=sys-subsystem-net-devices-wlan1.device
After=sys-subsystem-net-devices-wlan1.device
PartOf=nexalert.service

[Service]
Type=simple
ExecStart=/usr/sbin/hostapd /etc/hostapd/nexalert.conf
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Allow hostapd to see config
chmod 644 "$HOSTAPD_CONFIG"

# Reload systemd
systemctl daemon-reload

# Start hostapd
systemctl enable hostapd-nexalert
systemctl start hostapd-nexalert

success_msg "hostapd service created and started"
echo ""

# ============================================================================
# PERSIST IPTABLES RULES
# ============================================================================

echo "Persisting iptables rules..."

# Install iptables-persistent if needed
if ! command -v iptables-save &> /dev/null; then
    apt-get install -y iptables-persistent > /dev/null
fi

# Save rules
iptables-save > /etc/iptables/rules.v4

success_msg "iptables rules saved"
echo ""

# ============================================================================
# VERIFY CONFIGURATION
# ============================================================================

echo "=========================================="
echo "Verifying Network Configuration"
echo "=========================================="
echo ""

# Check interfaces
echo "Network Interfaces:"
ip link show | grep -E "wlan|eth"
echo ""

# Check IP addresses
echo "IPv4 Addresses:"
ip addr show | grep "inet " | grep -v "127.0"
echo ""

# Check dnsmasq
if pgrep -x dnsmasq > /dev/null; then
    success_msg "dnsmasq is running"
else
    echo -e "${RED}✗ dnsmasq is not running${NC}"
fi

# Check hostapd
if systemctl is-active --quiet hostapd-nexalert; then
    success_msg "hostapd is running"
else
    echo -e "${RED}✗ hostapd is not running${NC}"
fi

# Check iptables rules
echo ""
echo "Active iptables rules (summary):"
iptables -L | head -5
echo "..."

echo ""
echo "=========================================="
echo "Network Configuration Summary"
echo "=========================================="
echo ""
echo "Internet Interface:  $WLAN_INTERNET"
echo "Hotspot Interface:   $WLAN_HOTSPOT"
echo "Gateway IP:          10.42.0.1"
echo "DHCP Range:          10.42.0.50 - 10.42.0.150"
echo ""
echo "Services Running:"
echo "  - dnsmasq (DHCP & DNS)"
echo "  - hostapd (AP mode)"
echo "  - iptables (Firewall & NAT)"
echo ""
echo "Captive Portal Features:"
echo "  - Open WiFi network: 'NexAlert-Emergency'"
echo "  - All DNS requests redirect to 10.42.0.1 (gateway)"
echo "  - HTTP traffic redirected to application"
echo "  - Full internet access via $WLAN_INTERNET (mesh routing)"
echo ""
echo "=========================================="
echo "Troubleshooting:"
echo "=========================================="
echo ""
echo "View dnsmasq logs:"
echo "  tail -f /var/log/dnsmasq.log"
echo ""
echo "Check hostapd status:"
echo "  systemctl status hostapd-nexalert"
echo ""
echo "Verify iptables rules:"
echo "  iptables -L -n -v"
echo ""
echo "Restart dnsmasq:"
echo "  systemctl restart dnsmasq"
echo ""
echo "Restart hostapd:"
echo "  systemctl restart hostapd-nexalert"
echo ""
success_msg "Network setup completed successfully!"
echo ""
