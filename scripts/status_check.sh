#!/bin/bash
# NexAlert Service Status Monitor
# Quick visual status check for all components

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          NexAlert v3.0 - System Status                ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to check service
check_service() {
    if systemctl is-active --quiet $1; then
        echo -e "${GREEN}✓${NC} $2"
        return 0
    else
        echo -e "${RED}✗${NC} $2"
        return 1
    fi
}

# Function to check port
check_port() {
    if sudo netstat -tlnp | grep -q ":$1 "; then
        echo -e "${GREEN}✓${NC} Port $1 listening"
        return 0
    else
        echo -e "${RED}✗${NC} Port $1 not listening"
        return 1
    fi
}

# Services
echo -e "${YELLOW}SERVICES:${NC}"
check_service nexalert "Main NexAlert Service"
check_service nexalert-environmental "Environmental Monitor"
check_service nexalert-alerts "SMS/Call Alert Service"
check_service nginx "Nginx Web Server"
check_service dnsmasq "DNS/DHCP Server"
check_service NetworkManager "Network Manager"

echo ""
echo -e "${YELLOW}NETWORK:${NC}"
# Check hotspot
if nmcli device | grep -q "wlan1.*connected"; then
    echo -e "${GREEN}✓${NC} Hotspot Active (wlan1)"
else
    echo -e "${RED}✗${NC} Hotspot Inactive"
fi

# Check IP
if ip addr show wlan1 2>/dev/null | grep -q "10.42.0.1"; then
    echo -e "${GREEN}✓${NC} IP Address 10.42.0.1"
else
    echo -e "${RED}✗${NC} IP Address not configured"
fi

echo ""
echo -e "${YELLOW}WEB SERVICES:${NC}"
check_port 5000
check_port 80

# Check Flask health
if curl -s http://localhost/health | grep -q "healthy"; then
    echo -e "${GREEN}✓${NC} Flask API responding"
else
    echo -e "${RED}✗${NC} Flask API not responding"
fi

echo ""
echo -e "${YELLOW}DATABASE:${NC}"
if [ -f "/home/pi/nexalert_v3/database/nexalert.db" ]; then
    SIZE=$(du -h /home/pi/nexalert_v3/database/nexalert.db | cut -f1)
    echo -e "${GREEN}✓${NC} Database exists (${SIZE})"
else
    echo -e "${RED}✗${NC} Database not found"
fi

echo ""
echo -e "${YELLOW}RESOURCES:${NC}"
# CPU load
LOAD=$(uptime | awk -F'load average:' '{print $2}' | cut -d',' -f1 | xargs)
echo -e "${BLUE}ℹ${NC} CPU Load: ${LOAD}"

# Memory
MEM=$(free -h | awk '/^Mem:/ {print $3 "/" $2}')
echo -e "${BLUE}ℹ${NC} Memory: ${MEM}"

# Disk
DISK=$(df -h /home | awk 'NR==2 {print $5}')
echo -e "${BLUE}ℹ${NC} Disk Usage: ${DISK}"

# Temperature
if [ -f "/sys/class/thermal/thermal_zone0/temp" ]; then
    TEMP=$(cat /sys/class/thermal/thermal_zone0/temp)
    TEMP_C=$((TEMP/1000))
    echo -e "${BLUE}ℹ${NC} CPU Temp: ${TEMP_C}°C"
fi

echo ""
echo -e "${YELLOW}QUICK STATS:${NC}"
cd /home/pi/nexalert_v3
source venv/bin/activate
python3 backend/utils/db_manager.py stats 2>/dev/null | grep -E "(Users|Messages|Alerts)" | head -3

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "For detailed logs: ${YELLOW}sudo journalctl -u nexalert -f${NC}"
echo -e "For live monitoring: ${YELLOW}htop${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
