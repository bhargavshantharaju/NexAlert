# NexAlert v3.0 - Testing & Troubleshooting Guide

## 🧪 Testing Checklist

### Initial Setup Tests

#### 1. Service Status Check
```bash
# Check if main service is running
sudo systemctl status nexalert

# Check environmental monitor
sudo systemctl status nexalert-environmental

# Check alert service
sudo systemctl status nexalert-alerts

# All should show "active (running)" in green
```

#### 2. Network Configuration Test
```bash
# Check hotspot is broadcasting
nmcli device status
# Should show wlan1 as "connected"

# Check IP assignment
ip addr show wlan1
# Should show 10.42.0.1/24

# Test DNS resolution
nslookup google.com 10.42.0.1
# Should redirect to 10.42.0.1 (captive portal)
```

#### 3. Database Test
```bash
cd /home/pi/nexalert_v3
source venv/bin/activate
python3 backend/utils/db_manager.py stats

# Should show:
# - Database exists
# - Tables created
# - No errors
```

#### 4. Web Server Test
```bash
# Check Flask is running
sudo netstat -tlnp | grep 5000
# Should show python listening on 0.0.0.0:5000

# Check nginx
sudo systemctl status nginx
curl http://localhost/health
# Should return JSON with status "healthy"
```

### Functional Tests

#### Test 1: Phone Registration
1. Connect phone to "NexAlert-Emergency" WiFi
2. Should auto-open browser to registration page
3. Fill: Name="Test User", Phone="+919876543210", Username="testuser"
4. Click "Join Network"
5. Should redirect to main chat interface

**Expected Result:** User appears in dashboard user list with green "Online" status

#### Test 2: Messaging
1. On phone: Send message "Test message 123"
2. On dashboard: Message appears in real-time
3. Dashboard: Send broadcast "Broadcast test"
4. Phone: Broadcast appears with red background

**Expected Result:** All messages delivered within 1-2 seconds

#### Test 3: SOS Alert
1. On phone: Go to SOS tab
2. Select "Medical Emergency"
3. Add description: "Test alert - ignore"
4. Click "Send Alert"
5. Dashboard: Alert appears immediately with red marker on map

**Expected Result:** 
- Alert in dashboard list
- Red blinking marker on map
- Alert counter increments

#### Test 4: Contact Sync
1. Phone: Go to Contacts tab
2. Click "Sync Contacts"
3. Mock contacts appear
4. Register another user with one of the mock phone numbers
5. Original user's contact list shows them as "On Network"

**Expected Result:** Network detection works, online status updates

#### Test 5: Location Tracking
1. Phone: Allow location access
2. Move around (or spoof location)
3. Dashboard: User marker updates position
4. Click marker: Info window shows correct name/phone

**Expected Result:** Real-time location updates on map

#### Test 6: Environmental Monitoring
1. Dashboard: Right sidebar shows sensor data
2. Temperature, humidity, air quality update every 60 seconds
3. Chart shows historical air quality trend

**Expected Result:** Data refreshes, chart updates

---

## 🐛 Common Problems & Solutions

### Problem 1: Hotspot Not Broadcasting

**Symptoms:**
- Can't see "NexAlert-Emergency" WiFi
- wlan1 shows "disconnected"

**Solutions:**

```bash
# Check USB dongle is detected
lsusb
# Should show your WiFi adapter

# Restart NetworkManager
sudo systemctl restart NetworkManager

# Manually start hotspot
sudo nmcli connection up NexAlert-Hotspot

# Check status
nmcli device status

# If still failing, check dmesg for driver errors
dmesg | grep -i wifi | tail -20
```

**Common Causes:**
- USB dongle not plugged in
- Wrong interface name (check with `ip link`)
- Driver not installed (install `firmware-realtek` or similar)

---

### Problem 2: Captive Portal Not Redirecting

**Symptoms:**
- Phone connects but doesn't auto-open browser
- Have to manually type 10.42.0.1

**Solutions:**

```bash
# Check dnsmasq is running
sudo systemctl status dnsmasq

# Restart dnsmasq
sudo systemctl restart dnsmasq

# Check iptables rules
sudo iptables -t nat -L -n -v

# Re-apply iptables rules
sudo iptables -t nat -F
sudo iptables -t nat -A PREROUTING -i wlan1 -p tcp --dport 80 -j REDIRECT --to-port 80
sudo iptables -t nat -A PREROUTING -i wlan1 -p tcp --dport 443 -j REDIRECT --to-port 80
sudo sh -c "iptables-save > /etc/iptables.rules"

# Test DNS
dig @10.42.0.1 google.com
# Should return 10.42.0.1
```

**Common Causes:**
- dnsmasq not configured correctly
- iptables rules not applied
- Firewall blocking port 53/80

---

### Problem 3: Website Not Loading

**Symptoms:**
- Connection timeout
- 502 Bad Gateway
- Can't reach server

**Solutions:**

```bash
# Check if Flask is running
sudo systemctl status nexalert
sudo journalctl -u nexalert -n 50

# Check nginx
sudo systemctl status nginx
sudo nginx -t

# Check port binding
sudo netstat -tlnp | grep -E '(5000|80)'

# Restart everything
sudo systemctl restart nexalert
sudo systemctl restart nginx

# Check logs
tail -f /home/pi/nexalert_v3/logs/nexalert.log
```

**Common Causes:**
- Python dependencies missing
- Database file locked
- Port 5000 already in use

---

### Problem 4: Database Errors

**Symptoms:**
- "OperationalError: no such table"
- "Database is locked"
- API returns 500 errors

**Solutions:**

```bash
cd /home/pi/nexalert_v3
source venv/bin/activate

# Reinitialize database
python3 << EOF
import sys
sys.path.insert(0, '/home/pi/nexalert_v3/backend')
from app import app, db
with app.app_context():
    db.create_all()
    print("✓ Tables created")
EOF

# Check database file
ls -lh database/nexalert.db
# Should exist and be writable

# Check permissions
sudo chown -R pi:pi /home/pi/nexalert_v3/database

# Backup and vacuum
python3 backend/utils/db_manager.py full-backup
```

**Common Causes:**
- Database not initialized
- File permissions wrong
- Corrupted database (restore from backup)

---

### Problem 5: Services Won't Start

**Symptoms:**
- `systemctl status nexalert` shows "failed"
- "Module not found" errors
- Python crashes immediately

**Solutions:**

```bash
# Check Python environment
cd /home/pi/nexalert_v3
source venv/bin/activate
python3 -c "import flask; print('Flask OK')"

# Reinstall dependencies
pip install --upgrade -r requirements.txt

# Check service file
sudo systemctl cat nexalert.service
# Verify paths are correct

# Run manually to see errors
cd /home/pi/nexalert_v3
source venv/bin/activate
python3 backend/app.py

# Check logs
sudo journalctl -u nexalert -n 100 --no-pager
```

**Common Causes:**
- Virtual environment not activated
- Dependencies not installed
- Wrong working directory in service file

---

### Problem 6: WebSocket Not Working

**Symptoms:**
- Messages don't appear in real-time
- Have to refresh page to see updates
- Console shows "WebSocket connection failed"

**Solutions:**

```bash
# Check if SocketIO is running
sudo netstat -tlnp | grep 5000

# Check nginx websocket config
sudo cat /etc/nginx/sites-enabled/nexalert
# Should have "proxy_set_header Upgrade $http_upgrade"

# Test WebSocket connection
wscat -c ws://10.42.0.1/socket.io/?transport=websocket

# Check firewall
sudo iptables -L -n | grep 5000
```

**Common Causes:**
- nginx not configured for WebSocket
- CORS issues
- Eventlet not installed

---

### Problem 7: GPS Location Not Working

**Symptoms:**
- User markers don't appear on map
- "Location unavailable" errors

**Solutions:**

**On Phone:**
- Grant location permission in browser
- Use HTTPS (or localhost for testing)
- Check browser console for geolocation errors

**On Dashboard:**
```javascript
// Check if location updates are being sent
// Open browser console on phone:
navigator.geolocation.getCurrentPosition(
    pos => console.log(pos.coords),
    err => console.error(err)
);
```

**Common Causes:**
- Location permission denied
- Not using HTTPS (required by browsers)
- GPS disabled on phone

---

### Problem 8: Google Maps Not Loading

**Symptoms:**
- Gray map
- "This page can't load Google Maps correctly"
- API key errors

**Solutions:**

1. **Get a valid API key:**
   - Go to https://console.cloud.google.com/
   - Create project → Enable "Maps JavaScript API"
   - Create credentials → API key

2. **Add key to dashboard:**
```bash
nano /home/pi/nexalert_v3/backend/templates/dashboard.html
# Find: YOUR_GOOGLE_MAPS_API_KEY
# Replace with: AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXX
```

3. **Restart Flask:**
```bash
sudo systemctl restart nexalert
```

---

### Problem 9: Environmental Sensors Not Reading

**Symptoms:**
- Dashboard shows "--" for all sensor values
- Mock data only

**Solutions:**

```bash
# Check if sensor service is running
sudo systemctl status nexalert-environmental

# Check logs
tail -f /home/pi/nexalert_v3/logs/environmental.log

# Test I2C connection
sudo i2cdetect -y 1
# Should show 0x76 or 0x77 for BME680

# Install sensor libraries
pip install adafruit-circuitpython-bme680

# Run sensor script manually
python3 /home/pi/nexalert_v3/backend/services/environmental_monitor.py
```

**Common Causes:**
- Sensors not connected
- I2C not enabled (raspi-config → Interface Options → I2C)
- Wrong I2C address

---

### Problem 10: SMS/Calls Not Sending

**Symptoms:**
- Alerts created but no SMS/call
- Alert service crashes

**Solutions:**

```bash
# Check alert service
sudo systemctl status nexalert-alerts
sudo journalctl -u nexalert-alerts -n 50

# Test modem connection
ls /dev/ttyUSB*
# Should show /dev/ttyUSB0, /dev/ttyUSB1, etc.

# Test AT commands
screen /dev/ttyUSB2 115200
# Type: AT
# Should respond: OK

# Configure Twilio (if using)
nano /home/pi/nexalert_v3/backend/services/alert_service.py
# Add your Twilio credentials
```

**Common Causes:**
- Modem not connected
- Wrong USB port
- Twilio credentials not set
- No mobile signal

---

## 🔍 Diagnostic Commands

### Quick Health Check
```bash
#!/bin/bash
echo "=== NexAlert Health Check ==="
echo ""
echo "Services:"
systemctl is-active nexalert && echo "  ✓ Main service" || echo "  ✗ Main service"
systemctl is-active nginx && echo "  ✓ Nginx" || echo "  ✗ Nginx"
systemctl is-active dnsmasq && echo "  ✓ DNS" || echo "  ✗ DNS"
echo ""
echo "Network:"
nmcli device | grep wlan
echo ""
echo "Web:"
curl -s http://localhost/health | jq .
echo ""
echo "Database:"
ls -lh /home/pi/nexalert_v3/database/nexalert.db
echo ""
echo "Logs (last 5 lines):"
tail -5 /home/pi/nexalert_v3/logs/nexalert.log
```

### Performance Monitoring
```bash
# CPU/Memory usage
htop

# Network traffic
iftop -i wlan1

# Disk space
df -h

# Service resource usage
systemctl status nexalert --no-pager -l
```

---

## 📊 Performance Optimization

### For Raspberry Pi 5
```bash
# Increase swap if needed
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Set CONF_SWAPSIZE=2048
sudo dphys-swapfile setup
sudo dphys-swapfile swapon

# Optimize database
python3 /home/pi/nexalert_v3/backend/utils/db_manager.py vacuum

# Clear old logs
sudo journalctl --vacuum-time=7d
```

### For Better WiFi Range
```bash
# Increase TX power (if supported)
sudo iwconfig wlan1 txpower 30

# Use 5GHz if dongle supports it
# Edit /etc/NetworkManager/system-connections/NexAlert-Hotspot.nmconnection
# Add: band=a (for 5GHz)
```

---

## 🚨 Emergency Recovery

### If Everything Breaks
```bash
# 1. Stop all services
sudo systemctl stop nexalert nexalert-environmental nexalert-alerts nginx

# 2. Backup database
cp /home/pi/nexalert_v3/database/nexalert.db /home/pi/nexalert_backup.db

# 3. Reinstall dependencies
cd /home/pi/nexalert_v3
source venv/bin/activate
pip install --upgrade --force-reinstall -r requirements.txt

# 4. Reset database
rm database/nexalert.db
python3 << EOF
from backend.app import app, db
with app.app_context():
    db.create_all()
EOF

# 5. Restart everything
sudo systemctl start nexalert nginx
sudo systemctl restart NetworkManager
```

### Nuclear Option: Full Reinstall
```bash
cd /home/pi
sudo systemctl stop nexalert nexalert-environmental nexalert-alerts
sudo systemctl disable nexalert nexalert-environmental nexalert-alerts
rm -rf nexalert_v3
unzip nexalert_v3.zip
cd nexalert_v3/scripts
./deploy.sh
```

---

For more help, check logs:
```bash
sudo journalctl -u nexalert -f
tail -f /home/pi/nexalert_v3/logs/nexalert.log
```
