#!/bin/bash

################################################################################
# NexAlert v3.0 - Installation Verification Script
# Validates deployment and network configuration
# Run: ./verify_installation.sh
################################################################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

echo "=========================================="
echo "NexAlert v3.0 - Installation Verification"
echo "=========================================="
echo ""

# ============================================================================
# TEST FUNCTIONS
# ============================================================================

test_pass() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    ((PASS_COUNT++))
}

test_fail() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    ((FAIL_COUNT++))
}

test_warn() {
    echo -e "${YELLOW}⚠ WARN${NC}: $1"
    ((WARN_COUNT++))
}

# ============================================================================
# PERMISSION & PRIVILEGE CHECKS
# ============================================================================

echo -e "${BLUE}[1/8] Checking Permissions${NC}"
echo "---"

if [[ $EUID -eq 0 ]]; then
    test_pass "Running as root"
else
    test_warn "Not running as root (some tests may fail)"
fi
echo ""

# ============================================================================
# SYSTEM DEPENDENCIES
# ============================================================================

echo -e "${BLUE}[2/8] Checking System Dependencies${NC}"
echo "---"

COMMANDS=("python3" "pip3" "nginx" "sqlite3" "dnsmasq" "iptables" "git")

for cmd in "${COMMANDS[@]}"; do
    if command -v "$cmd" &> /dev/null; then
        VERSION=$($cmd --version 2>&1 | head -n1 || echo "installed")
        test_pass "$cmd: $VERSION"
    else
        test_fail "$cmd not installed"
    fi
done
echo ""

# ============================================================================
# APPLICATION DIRECTORY STRUCTURE
# ============================================================================

echo -e "${BLUE}[3/8] Checking Directory Structure${NC}"
echo "---"

DIRS=(
    "/opt/nexalert"
    "/opt/nexalert/app"
    "/opt/nexalert/database"
    "/opt/nexalert/static"
    "/opt/nexalert/templates"
    "/opt/nexalert/scripts"
    "/opt/nexalert/logs"
)

for dir in "${DIRS[@]}"; do
    if [ -d "$dir" ]; then
        test_pass "Directory exists: $dir"
    else
        test_warn "Directory missing: $dir"
    fi
done

echo ""

# ============================================================================
# REQUIRED FILES
# ============================================================================

echo -e "${BLUE}[4/8] Checking Required Files${NC}"
echo "---"

FILES=(
    "/opt/nexalert/app/app.py"
    "/opt/nexalert/database/schema.sql"
    "/opt/nexalert/database/nexalert.db"
    "/opt/nexalert/templates/phone.html"
    "/opt/nexalert/templates/dashboard.html"
    "/opt/nexalert/static/js/phone.js"
    "/opt/nexalert/static/js/dashboard.js"
    "/opt/nexalert/static/css/styles.css"
    "/opt/nexalert/requirements.txt"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        SIZE=$(stat -c %s "$file" 2>/dev/null || stat -f %z "$file" 2>/dev/null)
        test_pass "File exists: $file ($SIZE bytes)"
    else
        test_fail "File missing: $file"
    fi
done

echo ""

# ============================================================================
# SERVICE STATUS
# ============================================================================

echo -e "${BLUE}[5/8] Checking Service Status${NC}"
echo "---"

SERVICES=("nexalert" "nginx" "dnsmasq" "hostapd-nexalert")

for service in "${SERVICES[@]}"; do
    if systemctl is-active --quiet "$service" 2>/dev/null; then
        STATUS=$(systemctl is-active "$service")
        test_pass "Service $service: $STATUS"
    else
        test_warn "Service $service is not active"
    fi
done

echo ""

# ============================================================================
# NETWORK CONFIGURATION
# ============================================================================

echo -e "${BLUE}[6/8] Checking Network Configuration${NC}"
echo "---"

# Check WiFi interfaces
if command -v nmcli &> /dev/null; then
    WLAN_COUNT=$(nmcli device show 2>/dev/null | grep -c "GENERAL.DEVICE" || echo "0")
    if [ "$WLAN_COUNT" -ge 1 ]; then
        test_pass "WiFi interfaces detected: $WLAN_COUNT"
    else
        test_fail "No WiFi interfaces detected"
    fi
else
    test_warn "nmcli not available, skipping interface check"
fi

# Check IP forwarding
IP_FORWARD=$(cat /proc/sys/net/ipv4/ip_forward 2>/dev/null || echo "0")
if [ "$IP_FORWARD" == "1" ]; then
    test_pass "IP forwarding enabled"
else
    test_warn "IP forwarding disabled (required for mesh)"
fi

# Check gateway IP
if ip addr show 2>/dev/null | grep -q "10.42.0.1"; then
    test_pass "Gateway IP 10.42.0.1 configured"
else
    test_warn "Gateway IP 10.42.0.1 not found"
fi

# Check iptables NAT rules
if sudo iptables -t nat -L 2>/dev/null | grep -q "MASQUERADE"; then
    test_pass "iptables NAT rules configured"
else
    test_warn "iptables NAT rules not found"
fi

echo ""

# ============================================================================
# PORT AVAILABILITY
# ============================================================================

echo -e "${BLUE}[7/8] Checking Port Availability${NC}"
echo "---"

PORTS=("80" "443" "5000" "3000")

for port in "${PORTS[@]}"; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        PROCESS=$(lsof -i :$port -t -c -a | head -1 || echo "unknown")
        test_pass "Port $port is in use by process: $PROCESS"
    else
        test_warn "Port $port is available (might need to be listening)"
    fi
done

echo ""

# ============================================================================
# DATABASE VALIDATION
# ============================================================================

echo -e "${BLUE}[8/8] Checking Database${NC}"
echo "---"

DB_FILE="/opt/nexalert/database/nexalert.db"

if [ -f "$DB_FILE" ]; then
    DB_SIZE=$(stat -c %s "$DB_FILE" 2>/dev/null || stat -f %z "$DB_FILE" 2>/dev/null)
    test_pass "Database file exists ($DB_SIZE bytes)"
    
    # Check if database is readable
    if sqlite3 "$DB_FILE" ".tables" &>/dev/null; then
        TABLE_COUNT=$(sqlite3 "$DB_FILE" ".tables" | wc -w)
        test_pass "Database is readable ($TABLE_COUNT tables)"
    else
        test_fail "Database is not readable"
    fi
else
    test_fail "Database file not found: $DB_FILE"
fi

echo ""

# ============================================================================
# CONNECTIVITY TESTS
# ============================================================================

echo -e "${BLUE}[BONUS] Connectivity Tests${NC}"
echo "---"

# Test localhost accessibility
if curl -s http://localhost > /dev/null 2>&1; then
    test_pass "NexAlert accessible via http://localhost"
else
    test_warn "NexAlert not accessible via http://localhost"
fi

# Test API health endpoint
if curl -s http://localhost/health 2>/dev/null | grep -q "healthy"; then
    test_pass "Health check endpoint responding"
else
    test_warn "Health check endpoint not responding"
fi

# Test internet connectivity
if ping -c 1 8.8.8.8 > /dev/null 2>&1; then
    test_pass "Internet connectivity verified"
else
    test_warn "No internet connectivity"
fi

echo ""

# ============================================================================
# DETAILED STATUS REPORT
# ============================================================================

echo "=========================================="
echo "Service Status Report"
echo "=========================================="
echo ""

if command -v systemctl &> /dev/null; then
    echo "NexAlert Service:"
    sudo systemctl status nexalert --no-pager || echo "Status check failed"
    echo ""
    
    echo "Nginx Service:"
    sudo systemctl status nginx --no-pager || echo "Status check failed"
    echo ""
fi

# ============================================================================
# SUMMARY & RECOMMENDATIONS
# ============================================================================

TOTAL=$((PASS_COUNT + FAIL_COUNT + WARN_COUNT))

echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo -e "Total Tests: $TOTAL"
echo -e "${GREEN}Passed: $PASS_COUNT${NC}"
echo -e "${RED}Failed: $FAIL_COUNT${NC}"
echo -e "${YELLOW}Warnings: $WARN_COUNT${NC}"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    if [ $WARN_COUNT -eq 0 ]; then
        echo -e "${GREEN}✓ All systems nominal! NexAlert is ready.${NC}"
        exit 0
    else
        echo -e "${YELLOW}⚠ Installation complete with some warnings.${NC}"
        exit 0
    fi
else
    echo -e "${RED}✗ Installation has errors. Please review above.${NC}"
    exit 1
fi

echo ""

# ============================================================================
# TROUBLESHOOTING GUIDE
# ============================================================================

cat << 'EOF'

========================================
Troubleshooting Guide
========================================

1. Services Not Running?
   sudo systemctl start nexalert
   sudo systemctl start nginx
   sudo systemctl start dnsmasq
   sudo systemctl start hostapd-nexalert

2. Port Already in Use?
   sudo lsof -i :80
   sudo lsof -i :5000

3. Check Logs?
   journalctl -u nexalert -f
   sudo tail -f /var/log/dnsmasq.log

4. Network Issues?
   ip route show
   ip addr show
   nmcli device status

5. Database Problems?
   sqlite3 /opt/nexalert/database/nexalert.db
   .tables
   .schema

EOF
