# NexAlert v3.0 - Autonomous Solar-Powered Emergency Mesh Platform

## Overview

**NexAlert v3.0** is a production-ready emergency communication system designed for Raspberry Pi devices. It combines a **dual-interface WiFi mesh network** with a **real-time SOS alert system**, **environmental sensor monitoring**, and a **web-based administrative dashboard**.

### Key Features

- ✅ **Dual WiFi Interface Mesh Network** (wlan0 for internet, wlan1 for "NexAlert-Emergency" hotspot)
- ✅ **12-Category SOS Alert System** (Medical, Fire, Flood, Earthquake, Accident, Violence, Natural Disaster, Power Outage, Gas Leak, Missing Person, Animal Attack, Other)
- ✅ **Mobile-First Phone Interface** (Registration, Chat, SOS Trigger, Contacts, Profile)
- ✅ **Google Maps Integration** (Live user tracking, alert visualization, environmental data)
- ✅ **Real-Time Communication** (Flask-SocketIO for instant messaging and alerts)
- ✅ **Captive Portal** (Auto-login redirect via dnsmasq, point-and-go WiFi)
- ✅ **Environmental Sensor Support** (Temperature, Humidity, Battery Voltage, Solar Panel Voltage)
- ✅ **Broadcast Messaging** (Area-wide emergency alerts)
- ✅ **Crash Recovery** (SystemD auto-restart with exponential backoff)
- ✅ **SQLite Database** (Persistent user, alert, and message storage)

---

## Project Structure

```
NexAlert/
├── app/
│   ├── app.py                 # Flask backend with SocketIO
│   └── __init__.py
├── database/
│   ├── schema.sql             # SQLite database schema
│   └── nexalert.db            # (created during setup)
├── templates/
│   ├── phone.html             # Mobile interface
│   └── dashboard.html         # Admin dashboard
├── static/
│   ├── js/
│   │   ├── phone.js           # Mobile app logic
│   │   └── dashboard.js       # Dashboard logic
│   └── css/
│       └── styles.css         # Mobile & dashboard styles
├── scripts/
│   ├── deploy.sh              # Automated deployment script
│   └── setup_network.sh       # Mesh network configuration
├── config/
│   ├── nexalert.service       # SystemD service file
│   ├── dnsmasq.conf           # Captive portal configuration
│   └── nginx.conf             # Reverse proxy configuration
├── logs/                      # Application logs
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

---

## System Architecture

### Backend
- **Flask 2.3.3** - Web framework
- **Flask-SocketIO 5.3.4** - Real-time bidirectional communication
- **SQLite3** - Persistent database
- **Nginx** - Reverse proxy & load balancer
- **SystemD** - Service management & crash recovery

### Frontend
- **Mobile Interface**: Responsive HTML5/CSS3/JavaScript
- **Dashboard**: Google Maps API + Real-time data visualization
- **SocketIO Client**: 100ms latency messaging

### Networking
- **Dual WiFi**: wlan0 (internet) + wlan1 (emergency hotspot)
- **dnsmasq**: DHCP server + DNS redirection
- **iptables**: Firewall + NAT + Captive Portal
- **hostapd**: AP mode access point
- **IP Forwarding**: Mesh routing between interfaces

---

## Quick Start (30 Minutes)

### Prerequisites

- Raspberry Pi 4B+ with 64-bit OS (Ubuntu Server 22.04 LTS recommended)
- 2x WiFi interfaces (built-in + USB dongle supporting AP mode)
- Internet connection on wlan0
- 4GB+ free storage
- USB WiFi dongle with AP mode support (e.g., TP-Link Archer T4U)

### 1. Clone/Download NexAlert

```bash
cd ~/Desktop
git clone https://github.com/yourusername/nexalert.git
cd nexalert
```

### 2. Run Deployment Script

```bash
sudo chmod +x scripts/deploy.sh
sudo ./scripts/deploy.sh
```

This will:
- ✓ Install system dependencies
- ✓ Create Python virtual environment
- ✓ Initialize SQLite database
- ✓ Configure Nginx reverse proxy
- ✓ Start NexAlert SystemD service
- ✓ Setup logging

**Output Example:**
```
✓ System packages installed
✓ Python environment configured
✓ Database initialized
✓ Nginx reverse proxy configured
✓ SystemD service created
✓ Deployment completed successfully!
```

### 3. Setup Mesh Network

```bash
sudo chmod +x scripts/setup_network.sh
sudo ./scripts/setup_network.sh
```

This will:
- ✓ Configure wlan1 as AP (hotspot)
- ✓ Setup dnsmasq DHCP server
- ✓ Configure iptables firewall/NAT
- ✓ Enable captive portal
- ✓ Start hostapd service

### 4. Access NexAlert

- **Mobile App**: http://localhost (or your Pi's IP)
- **Admin Dashboard**: http://localhost/dashboard
- **API Base**: http://localhost/api

### 5. Connect to Emergency Network

1. On any device, search for WiFi networks
2. Connect to **"NexAlert-Emergency"** (no password required)
3. Open any URL (google.com, example.com)
4. Automatically redirected to NexAlert login
5. Register or login
6. Full mesh network access + internet passthrough

---

## Configuration

### Google Maps API Key

⚠️ **REQUIRED BEFORE DASHBOARD USE**

1. Get API key: https://cloud.google.com/maps-platform
2. Enable Maps JavaScript API
3. Edit `templates/dashboard.html`
4. Replace `YOUR_GOOGLE_MAPS_APIKEY_HERE` with your key

```html
<script src="https://maps.googleapis.com/maps/api/js?key=YOUR_API_KEY_HERE"></script>
```

### Database

Located at: `/opt/nexalert/database/nexalert.db`

Reset database:
```bash
rm /opt/nexalert/database/nexalert.db
sqlite3 /opt/nexalert/database/nexalert.db < /opt/nexalert/database/schema.sql
sudo systemctl restart nexalert
```

### Environment Variables

Create `/opt/nexalert/.env`:
```bash
FLASK_ENV=production
SECRET_KEY=your-secret-key-here-change-in-production
DEBUG=False
```

### Nginx Configuration

Location: `/etc/nginx/sites-available/nexalert`

Modify listen ports, SSL certificates, or upstream servers:
```nginx
upstream nexalert_app {
    server 127.0.0.1:5000;
}

server {
    listen 80 default_server;
    # ... rest of config
}
```

---

## API Endpoints

### Authentication
- `POST /api/register` - User registration
- `POST /api/login` - User login

### User Management
- `GET /api/user/profile` - Get user profile
- `POST /api/user/location` - Update location

### Contacts
- `GET /api/contacts` - List emergency contacts
- `POST /api/contacts` - Add new contact

### SOS Alerts
- `POST /api/sos/trigger` - Trigger SOS alert
- `POST /api/sos/acknowledge/<id>` - Acknowledge alert
- `GET /api/sos/alerts` - Get active alerts

### Messages
- `POST /api/messages/send` - Send direct message
- `POST /api/broadcast/send` - Send broadcast message

### Sensor Data
- `POST /api/sensors/data` - Submit sensor readings
- `GET /api/sensors/data/<user_id>` - Get latest sensor data

### Health
- `GET /health` - Health check

---

## Real-Time Events (WebSocket)

### Server → Client
- `sos_alert` - New emergency alert
- `location_update` - User location change
- `user_status_change` - User online/offline
- `new_message` - Incoming message
- `broadcast_message` - Area-wide message
- `sensor_data` - Environmental data

### Client → Server
- `user_online` - Mark user as online
- `user_offline` - Mark user as offline
- `chat_message` - Send chat message
- `heartbeat` - Keep connection alive

---

## Monitoring & Logs

### View Logs

```bash
# Real-time log stream
journalctl -u nexalert -f

# Last 100 lines
journalctl -u nexalert -n 100

# View dnsmasq logs
sudo tail -f /var/log/dnsmasq.log

# View hostapd logs
sudo journalctl -u hostapd-nexalert -f
```

### Check Service Status

```bash
# NexAlert service
sudo systemctl status nexalert

# Nginx
sudo systemctl status nginx

# dnsmasq
sudo systemctl status dnsmasq

# hostapd
sudo systemctl status hostapd-nexalert
```

### Restart Services

```bash
# Restart NexAlert
sudo systemctl restart nexalert

# Restart networking
sudo systemctl restart nexalert-network

# Restart all
sudo systemctl restart nexalert nexalert-network nginx hostapd-nexalert dnsmasq
```

---

## Troubleshooting

### Issue: Captive Portal Not Working

**Symptom**: Connected to "NexAlert-Emergency" but no login redirect

**Solution**:
```bash
# Verify dnsmasq is running
ps aux | grep dnsmasq

# Check iptables rules
sudo iptables -t nat -L -n | grep DNAT

# Check wlan1 IP
ip addr show wlan1

# Restart dnsmasq
sudo systemctl restart dnsmasq
```

### Issue: No Internet Access on Hotspot

**Symptom**: Users can't access external websites through NexAlert

**Solution**:
```bash
# Check IP forwarding
cat /proc/sys/net/ipv4/ip_forward

# Enable if disabled
echo 1 | sudo tee /proc/sys/net/ipv4/ip_forward

# Check NAT rules
sudo iptables -t nat -L -n | grep MASQUERADE

# Check wlan0 connectivity
ip route show
```

### Issue: wlan1 (AP) Not Starting

**Symptom**: "NexAlert-Emergency" network not visible

**Solution**:
```bash
# Check AP mode support
iw wlan1 info | grep "AP"

# Verify hostapd config
cat /etc/hostapd/nexalert.conf

# Check hostapd logs
sudo journalctl -u hostapd-nexalert -n 50

# Restart hostapd
sudo systemctl restart hostapd-nexalert
```

### Issue: High CPU Usage

**Symptom**: NexAlert consuming 80%+ CPU

**Solution**:
```bash
# Check for database locks
lsof | grep nexalert.db

# Restart service
sudo systemctl restart nexalert

# Check for infinite loops in code
sudo gdb attach $(pgrep -f app.py)
```

---

## Performance Tuning

### Database Optimization

```bash
# Analyze indices
sqlite3 /opt/nexalert/database/nexalert.db "ANALYZE;"

# Vacuum database
sqlite3 /opt/nexalert/database/nexalert.db "VACUUM;"
```

### Nginx Tuning

```nginx
# Increase worker processes
worker_processes auto;

# Increase worker connections
events {
    worker_connections 4096;
}

# Enable gzip
gzip on;
gzip_types text/plain text/css application/json;
```

### Socket.IO Optimization

```python
# In app.py
socketio = SocketIO(
    app,
    async_mode='eventlet',
    cors_allowed_origins="*",
    ping_timeout=120,
    ping_interval=60,
    max_http_buffer_size=1000000
)
```

---

## Security Considerations

⚠️ **WARNING**: This is an emergency system. Security is important but NOT BYPASS LIFE-SAVING FEATURES.

### Recommended Security Measures

1. **Change Default Credentials**
   - Update Flask SECRET_KEY in `.env`
   - Use strong passwords for initial admin

2. **Enable HTTPS**
   - Generate SSL certificates: `sudo certbot certonly --standalone -d yourdomain.com`
   - Update Nginx config with SSL cert paths
   - Redirect HTTP to HTTPS in Nginx

3. **Firewall Hardening**
   ```bash
   # Restrict SSH access
   sudo ufw allow from 192.168.1.0/24 to any port 22
   
   # Enable UFW
   sudo ufw enable
   ```

4. **Database Encryption** (Optional)
   - Use SQLCipher for encrypted database
   - Update app.py to use encrypted DB

5. **API Authentication**
   - All API endpoints require valid JWT tokens
   - Tokens expire after 30 days
   - Implement API rate limiting

6. **Network Segmentation**
   - Isolate mesh network from main network
   - Use separate subnets (10.42.0.0/24 for mesh)

---

## Deployment Checklist

- [ ] Raspberry Pi with 2x WiFi interfaces
- [ ] Ubuntu Server 22.04 installed
- [ ] Internet connection on wlan0
- [ ] `deploy.sh` executed successfully
- [ ] `setup_network.sh` executed successfully
- [ ] Google Maps API key configured in dashboard.html
- [ ] Nginx reverse proxy working (port 80)
- [ ] SocketIO real-time chat tested
- [ ] SOS alert trigger tested
- [ ] Captive portal tested from WiFi client
- [ ] Navigation and location permissions verified
- [ ] SystemD service auto-restart tested (kill -9)
- [ ] Log rotation configured
- [ ] Firewall rules applied
- [ ] SSL certificates installed (if using HTTPS)
- [ ] Load balancing tested with multiple clients
- [ ] Environmental sensor data collection working

---

## Maintenance

### Weekly
```bash
# Check logs for errors
journalctl -u nexalert --since "1 week ago" | grep ERROR

# Verify all services running
sudo systemctl status nexalert nginx dnsmasq hostapd-nexalert

# Check disk space
df -h /
```

### Monthly
```bash
# Database vacuum and analysis
sqlite3 /opt/nexalert/database/nexalert.db "VACUUM; ANALYZE;"

# Update system packages
sudo apt update && sudo apt upgrade

# Restart services to apply any patches
sudo systemctl restart nexalert
```

### Quarterly
```bash
# Security audit
sudo fail2ban-client status all

# Backup database
cp /opt/nexalert/database/nexalert.db /backup/nexalert.db.$(date +%s)

# Test disaster recovery procedure
```

---

## Advanced Configuration

### Custom SOS Categories

Edit `app/app.py`:
```python
SOS_CATEGORIES = {
    1: "Medical",
    2: "Fire",
    # ... add custom categories
}
```

### Mesh Extension Range (Boost Signal)

```bash
# Increase TX power (if supported by hardware)
sudo iw reg set US
sudo iw wlan1 set txpower fixed 30mBm
```

### Convert to Production Database (PostgreSQL)

1. Install PostgreSQL
2. Update Flask app to use SQLAlchemy + psycopg2
3. Migrate database schema
4. Test and deploy

### Enable Let's Encrypt SSL

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot certonly --nginx -d nexalert.example.com
```

---

## Support & Contributing

### Report Issues
1. Check troubleshooting section
2. View logs: `journalctl -u nexalert -n 100`
3. Create GitHub issue with logs and steps to reproduce

### Contribute
1. Fork repository
2. Create feature branch: `git checkout -b feature/new-feature`
3. Commit changes: `git commit -am 'Add feature'`
4. Push to branch: `git push origin feature/new-feature`
5. Submit pull request

---

## License

NexAlert v3.0 is provided as-is for emergency communication purposes. Use at your own risk.

---

## Key Reminders

🚨 **IMPORTANT NOTES**:

1. **Captive Portal Magic**: The line `address=/#/10.42.0.1` in dnsmasq redirects ALL DNS requests to the gateway. This is the trick that makes the portal work.

2. **Dual WiFi Requirements**: Your USB dongle MUST support AP mode (`iw <interface> info | grep AP`). Not all WiFi donges support this.

3. **Google Maps API**: You MUST insert your own Google Maps API key before the dashboard will show the map.

4. **Crash Recovery**: The SystemD service has `Restart=always` and `RestartSec=10`, so if the app crashes, it will auto-restart (up to 5 times per 60 seconds).

5. **Database Persistence**: All data is stored in SQLite. The database persists across restarts.

6. **Network Routing**: Check the iptables rules to understand how dual-interface mesh routing works:
   ```bash
   sudo iptables -t nat -L -n
   ```

---

## Quick Reference

```bash
# Deploy from scratch
sudo ./scripts/deploy.sh && sudo ./scripts/setup_network.sh

# View logs
journalctl -u nexalert -f

# Restart service
sudo systemctl restart nexalert

# Access application
# Mobile: http://pi-ip-address
# Dashboard: http://pi-ip-address/dashboard

# Check network status
ip addr show | grep "inet"
nmcli device status
```

---

**NexAlert v3.0** - Because emergencies don't wait for the internet. ✨
