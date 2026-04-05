# NexAlert v3.0 - Quick Start Guide

## 🚀 5-Minute Deployment

### Step 1: System Preparation
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Download NexAlert
cd ~/Desktop
git clone <nexalert-repo-url>
cd nexalert

# Make scripts executable
chmod +x scripts/*.sh
```

### Step 2: Deploy Backend
```bash
# Run automated deployment (takes 5-10 minutes)
sudo ./scripts/deploy.sh

# Verify deployment
sudo ./scripts/verify_installation.sh
```

### Step 3: Setup Networking
```bash
# Configure dual WiFi mesh network
sudo ./scripts/setup_network.sh

# Verify network is active
nmcli device status
```

### Step 4: Configure Dashboard
```bash
# Edit dashboard HTML to add Google Maps API key
nano templates/dashboard.html

# Find: YOUR_GOOGLE_MAPS_APIKEY_HERE
# Replace with your actual API key
```

### Step 5: Access NexAlert
```
Mobile App:     http://<pi-ip-address>
Dashboard:      http://<pi-ip-address>/dashboard
API:            http://<pi-ip-address>/api
```

---

## 📱 Testing the System

### Test 1: Mobile Registration
1. Open http://<pi-ip> on phone
2. Click "Register"
3. Enter name, phone, email, password
4. Should see "Registration successful"

### Test 2: SOS Alert
1. Login to mobile app
2. Go to SOS tab
3. Select "Medical" category
4. Click "TRIGGER SOS ALERT"
5. Check dashboard to see alert on map

### Test 3: Mesh Network
1. Connect any device to "NexAlert-Emergency" WiFi
2. Open browser and visit any URL (google.com)
3. Should auto-redirect to login page
4. Login and get internet access through mesh

### Test 4: Real-Time Chat
1. Open 2 browser windows
2. Register as different users
3. Send messages between users
4. Messages should appear in real-time

---

## 🛠️ Common Commands

```bash
# View logs
journalctl -u nexalert -f

# Restart NexAlert
sudo systemctl restart nexalert

# Check service status
sudo systemctl status nexalert

# Verify mesh network
sudo iptables -t nat -L -n

# Monitor network traffic
sudo tcpdump -i wlan1

# View active connections
ss -ntp

# Check database
sqlite3 /opt/nexalert/database/nexalert.db

# View sensor data
sqlite3 /opt/nexalert/database/nexalert.db "SELECT * FROM environmental_data LIMIT 5;"

# Restart all services
sudo systemctl restart nexalert nginx dnsmasq hostapd-nexalert
```

---

## ⚠️ Critical Configuration

### Google Maps API Key ✋ REQUIRED
```bash
# 1. Get API key from:
#    https://cloud.google.com/maps-platform

# 2. Enable:
#    - Maps JavaScript API

# 3. Add to templates/dashboard.html:
#    <script src="https://maps.googleapis.com/maps/api/js?key=YOUR_KEY_HERE"></script>
```

### Captive Portal Magic
The captive portal works because of this line in `/etc/dnsmasq.conf`:
```bash
address=/#/10.42.0.1
```
This redirects ALL DNS requests to the gateway IP. When users connect and try to visit any website, they're redirected to NexAlert login page.

### USB WiFi Dongle Requirements
Your USB dongle MUST support **AP (Access Point) mode**:
```bash
# Check before purchase:
iw wlan1 info | grep "AP"

# If AP is listed, it's compatible
# Good options: TP-Link Archer T4U, Alfa AWUS036NHA
```

---

## 📊 Monitoring Checklist

| Check | Command | Expected |
|-------|---------|----------|
| NexAlert Running | `systemctl status nexalert` | active (running) |
| Nginx Running | `systemctl status nginx` | active (running) |
| dnsmasq Running | `systemctl status dnsmasq` | active (running) |
| Mesh Network Active | `nmcli device status` | wlan0 connected, wlan1 connected |
| Gateway IP | `ip addr show wlan1` | 10.42.0.1/24 |
| Firewall Rules | `sudo iptables -t nat -L` | MASQUERADE + DNAT rules |
| Database | `ls -lh /opt/nexalert/database/nexalert.db` | > 1MB |
| Port 80 | `curl http://localhost` | HTML response |
| WebSocket | Browser console | `Socket connected` |

---

## 🚨 Emergency Recovery

If something breaks:

```bash
# Step 1: Restart everything
sudo systemctl restart nexalert nginx dnsmasq hostapd-nexalert

# Step 2: Check logs
journalctl -u nexalert -n 50

# Step 3: Reset network
sudo ./scripts/setup_network.sh

# Step 4: Verify installation
sudo ./scripts/verify_installation.sh

# Step 5: Nuclear option - redeploy
sudo systemctl stop nexalert
sudo ./scripts/deploy.sh
sudo systemctl start nexalert
```

---

## 🔐 Production Checklist

Before going live:

- [ ] Change `SECRET_KEY` in Flask app
- [ ] Install SSL certificate (Let's Encrypt)
- [ ] Setup database backups
- [ ] Configure firewall properly (UFW)
- [ ] Enable authentication on admin dashboard
- [ ] Test SOS alerts with real contacts
- [ ] Verify GPS accuracy
- [ ] Test sensor data collection
- [ ] Run under load (test with multiple users)
- [ ] Setup monitoring alerts
- [ ] Document all changes
- [ ] Train users on app UI
- [ ] Practice emergency procedures

---

## 📞 Getting Help

### Check Logs
```bash
# Recent errors
journalctl -u nexalert | grep ERROR

# Full service log
journalctl -u nexalert -n 100

# dnsmasq issues
sudo tail -f /var/log/dnsmasq.log

# Nginx issues
sudo tail -f /var/log/nginx/error.log
```

### Verify Network
```bash
# Is mesh hotspot broadcasting?
nmcli device wifi list

# Do clients connect?
sudo cat /var/lib/misc/dnsmasq.leases

# Are messages routing?
sudo tcpdump -i wlan1 -n

# Is NAT working?
sudo iptables -t nat -L -v -n
```

### Database Debug
```bash
# List all tables
sqlite3 /opt/nexalert/database/nexalert.db ".tables"

# Count users
sqlite3 /opt/nexalert/database/nexalert.db "SELECT COUNT(*) FROM users;"

# List recent alerts
sqlite3 /opt/nexalert/database/nexalert.db "SELECT * FROM sos_alerts ORDER BY timestamp DESC LIMIT 5;"

# Check database integrity
sqlite3 /opt/nexalert/database/nexalert.db "PRAGMA integrity_check;"
```

---

## 🎯 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Raspberry Pi 4B+                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ ┌──────────────────────────────────────────────────────┐   │
│ │               NexAlert v3.0 (Flask-SocketIO)         │   │
│ ├──────────────────────────────────────────────────────┤   │
│ │  Port 5000: Backend API + WebSocket Server          │   │
│ │  - Real-time messaging                              │   │
│ │  - SOS alert broadcast                              │   │
│ │  - Location tracking                                │   │
│ │  - Sensor data collection                           │   │
│ └──────────────────────────────────────────────────────┘   │
│                            ▲                                 │
│                            │                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Nginx Reverse Proxy (Port 80)                       │  │
│  │  ├─ Phone Interface (phone.html)                     │  │
│  │  ├─ Admin Dashboard (dashboard.html)                │  │
│  │  └─ Static Assets (CSS/JS)                          │  │
│  └──────────────────────────────────────────────────────┘  │
│       ▲          ▲              ▲          ▲                 │
│       │          │              │          │                 │
│   HTTP  HTTPs   WS      WSS   STATIC      API                │
│       │          │              │          │                 │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Networking Layer                                   │    │
│  ├─────────────────────────────────────────────────────┤    │
│  │  wlan0 (Internet)  │  wlan1 (Hotspot)              │    │
│  │  DHCP Client       │  DHCP Server (dnsmasq)        │    │
│  │  (WAN)             │  Captive Portal                │    │
│  │                    │  200+ devices possible        │    │
│  │  Gateway IP        │  Gateway IP: 10.42.0.1        │    │
│  │  Dynamic           │  Subnet: 10.42.0.0/24         │    │
│  └─────────────────────────────────────────────────────┘    │
│       ▲                            ▲                         │
│       │ WAN Route                  │ MESH Route             │
│       │ (Internet)                 │ (Emergency Network)    │
│       │                            │                        │
│   ISP/WiFi              [Users Connect Here]              │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  SQLite Database (/opt/nexalert/database/)           │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  Users │ Contacts │ SOS Alerts │ Messages           │  │
│  │  Sensors │ Sessions │ Groups                        │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔥 Performance Tips

```bash
# 1. Increase file descriptors
ulimit -n 65535

# 2. Tune kernel for network
echo "net.core.rmem_max=134217728" | sudo tee -a /etc/sysctl.conf
echo "net.core.wmem_max=134217728" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

# 3. Database optimization
sqlite3 /opt/nexalert/database/nexalert.db "PRAGMA journal_mode=WAL;"
sqlite3 /opt/nexalert/database/nexalert.db "PRAGMA synchronous=NORMAL;"
sqlite3 /opt/nexalert/database/nexalert.db "PRAGMA cache_size=10000;"

# 4. Monitor resource usage
watch -n 1 'top -b -n 1 | head -20'
```

---

**NexAlert v3.0 - Ready for Deployment** ✨
