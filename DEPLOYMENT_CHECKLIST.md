# NexAlert v3.0 - Complete Deployment Checklist

## 📋 Pre-Deployment Checklist

### Hardware Requirements
- [ ] Raspberry Pi 5 (or Pi 4 with 4GB+ RAM)
- [ ] USB WiFi dongle (wlan1) for hotspot
- [ ] MicroSD card (32GB+ recommended)
- [ ] 4G USB modem (optional - for SMS/calls)
- [ ] BME680 sensor (optional - environmental monitoring)
- [ ] Solar panel + charge controller + battery (for field deployment)

### Software Prerequisites
- [ ] Raspberry Pi OS (64-bit) installed and updated
- [ ] SSH enabled
- [ ] Hostname set to `venom` (or note actual hostname)
- [ ] Internet connection working on wlan0

---

## 🚀 Deployment Steps

### Phase 1: File Transfer (5 min)

```bash
# On your laptop
scp nexalert_v3_FINAL.zip pi@venom.local:/home/pi/

# SSH into Pi
ssh pi@venom.local

# Extract
cd /home/pi
unzip nexalert_v3_FINAL.zip
mv nexalert_v3_rebuild nexalert_v3
```

**Checklist:**
- [ ] ZIP file copied successfully
- [ ] Extracted to `/home/pi/nexalert_v3`
- [ ] All files present (check with `ls -la nexalert_v3/`)

---

### Phase 2: Run Deployment Script (15-20 min)

```bash
cd /home/pi/nexalert_v3/scripts
chmod +x deploy.sh
./deploy.sh
```

**What happens:**
1. Installs system packages (Python, nginx, dnsmasq)
2. Creates Python virtual environment
3. Installs Python dependencies
4. Initializes database
5. Configures network (hotspot on wlan1)
6. Sets up captive portal DNS
7. Installs systemd services
8. Configures nginx
9. **Reboots automatically**

**Checklist:**
- [ ] Script runs without errors
- [ ] All packages installed
- [ ] Database created (`database/nexalert.db` exists)
- [ ] Pi reboots automatically

---

### Phase 3: Post-Reboot Verification (5 min)

Wait 2-3 minutes after reboot, then SSH back in:

```bash
ssh pi@venom.local
cd /home/pi/nexalert_v3/scripts
./status_check.sh
```

**Expected Output:**
```
✓ Main NexAlert Service
✓ Environmental Monitor
✓ SMS/Call Alert Service
✓ Nginx Web Server
✓ DNS/DHCP Server
✓ Hotspot Active (wlan1)
✓ IP Address 10.42.0.1
✓ Port 5000 listening
✓ Port 80 listening
✓ Flask API responding
✓ Database exists
```

**Checklist:**
- [ ] All services showing ✓ (green checkmarks)
- [ ] Hotspot "NexAlert-Emergency" visible on phone WiFi list
- [ ] Can connect to hotspot (password: `nexalert2025`)

---

### Phase 4: Functional Testing (10 min)

#### Test 1: Phone Registration
1. Connect phone to "NexAlert-Emergency"
2. Browser should auto-open to registration
3. Register with test data
4. Should redirect to chat interface

**Checklist:**
- [ ] Captive portal works (auto-opens browser)
- [ ] Registration form loads
- [ ] Registration succeeds
- [ ] Redirected to main app

#### Test 2: Dashboard Access
On laptop:
1. Connect to "NexAlert-Emergency" hotspot
2. Open browser: `http://10.42.0.1/dashboard`
3. Should see map, user list, stats

**Checklist:**
- [ ] Dashboard loads
- [ ] Map displays (Bengaluru centered)
- [ ] Registered user appears in user list
- [ ] Stats show 1 user online

#### Test 3: Messaging
1. Phone: Send message "Test 123"
2. Dashboard: Message appears in broadcast list
3. Dashboard: Send broadcast "Dashboard test"
4. Phone: Broadcast appears

**Checklist:**
- [ ] Messages sent from phone appear on dashboard
- [ ] Messages sent from dashboard appear on phone
- [ ] Real-time updates work (no refresh needed)

#### Test 4: SOS Alert
1. Phone: Go to SOS tab
2. Select any emergency type
3. Add description
4. Send alert
5. Dashboard: Check alert appears

**Checklist:**
- [ ] Alert sent successfully
- [ ] Alert appears in dashboard alert list
- [ ] Alert counter increments
- [ ] (If GPS enabled) Alert marker on map

---

### Phase 5: Configuration (10 min)

#### Google Maps API Key

**CRITICAL - Dashboard won't show map without this!**

1. Get API key:
   - Go to https://console.cloud.google.com/
   - Create project
   - Enable "Maps JavaScript API"
   - Create credentials → API key

2. Add to dashboard:
```bash
nano /home/pi/nexalert_v3/backend/templates/dashboard.html
# Find line: maps/api/js?key=YOUR_GOOGLE_MAPS_API_KEY
# Replace YOUR_GOOGLE_MAPS_API_KEY with your actual key
# Save: Ctrl+X, Y, Enter

# Restart Flask
sudo systemctl restart nexalert
```

**Checklist:**
- [ ] API key obtained
- [ ] Added to dashboard.html
- [ ] Service restarted
- [ ] Map loads correctly

#### Optional: SMS/Call Configuration

If you have Twilio or 4G modem:

```bash
nano /home/pi/nexalert_v3/backend/services/alert_service.py

# For Twilio:
TWILIO_ENABLED = True
TWILIO_ACCOUNT_SID = "your_account_sid"
TWILIO_AUTH_TOKEN = "your_auth_token"
TWILIO_PHONE_NUMBER = "+1234567890"

# For 4G modem:
USE_4G_MODEM = True
MODEM_PORT = "/dev/ttyUSB2"  # Check with: ls /dev/ttyUSB*

# Save and restart
sudo systemctl restart nexalert-alerts
```

**Checklist:**
- [ ] Twilio credentials configured (if using)
- [ ] Modem port identified (if using)
- [ ] Alert service restarted
- [ ] Test alert sends SMS/call

#### Optional: Enable Automated Backups

```bash
crontab -e
# Add this line:
30 2 * * 0 /home/pi/nexalert_v3/venv/bin/python3 /home/pi/nexalert_v3/backend/utils/db_manager.py full-backup >> /home/pi/nexalert_v3/logs/maintenance.log 2>&1
```

**Checklist:**
- [ ] Cron job added
- [ ] Will run weekly backups at 2:30 AM Sunday

---

## 🎉 Deployment Complete!

### Final Verification Commands

```bash
# Service status
sudo systemctl status nexalert

# Live logs
sudo journalctl -u nexalert -f

# Database stats
cd /home/pi/nexalert_v3
source venv/bin/activate
python3 backend/utils/db_manager.py stats

# System health
./scripts/status_check.sh
```

---

## 📱 User Guide (Share with Demo Attendees)

### Connecting to NexAlert

1. **Connect WiFi:**
   - Network: `NexAlert-Emergency`
   - Password: `nexalert2025`

2. **Registration:**
   - Browser opens automatically
   - Enter: Name, Phone, Username
   - Click "Join Network"

3. **Features:**
   - **Chat Tab:** Send messages, broadcast announcements
   - **SOS Tab:** Send emergency alerts (12 types)
   - **Contacts Tab:** Sync phone contacts, see who's online

4. **Dashboard (Admin Only):**
   - URL: `http://10.42.0.1/dashboard`
   - Live map with user locations
   - Real-time alerts
   - Environmental data
   - Broadcast messages

---

## 🐛 Quick Troubleshooting

### Hotspot not visible?
```bash
sudo systemctl restart NetworkManager
sudo nmcli connection up NexAlert-Hotspot
```

### Website not loading?
```bash
sudo systemctl restart nexalert
sudo systemctl restart nginx
```

### Database error?
```bash
cd /home/pi/nexalert_v3
source venv/bin/activate
python3 << EOF
from backend.app import app, db
with app.app_context():
    db.create_all()
EOF
```

### Check logs:
```bash
sudo journalctl -u nexalert -n 100
tail -f /home/pi/nexalert_v3/logs/nexalert.log
```

**For detailed troubleshooting, see `TROUBLESHOOTING.md`**

---

## 📊 Post-Deployment Monitoring

### Daily Checks
- [ ] `./scripts/status_check.sh` - All green?
- [ ] Check disk space: `df -h`
- [ ] Check logs for errors: `tail -f logs/nexalert.log`

### Weekly Maintenance
- [ ] Backup database: `python3 backend/utils/db_manager.py backup`
- [ ] Clean old data: `python3 backend/utils/db_manager.py cleanup`
- [ ] Check for updates: `apt update && apt list --upgradable`

### Before Demo/Presentation
- [ ] Reboot Pi to ensure clean start
- [ ] Verify hotspot broadcasting
- [ ] Test with one phone registration
- [ ] Check dashboard loads correctly
- [ ] Verify environmental sensors (if connected)

---

## 🎯 Success Criteria

Your deployment is successful when:

✅ Hotspot broadcasts automatically on boot  
✅ Phones connect and auto-open registration  
✅ Users can register and send messages  
✅ SOS alerts work end-to-end  
✅ Dashboard shows live map with user locations  
✅ Environmental data updates (if sensors connected)  
✅ System runs stably for 24+ hours without intervention  

---

## 📞 Support Contacts

**Project Lead:** Bhargav  
**Organization:** IEEE ComSoc BMSIT&M  
**Advisor:** Dr. A. Shobha Rani  

**Documentation:**
- Full README: `README.md`
- Quick start: `QUICKSTART.md`
- Troubleshooting: `TROUBLESHOOTING.md`

**Logs Location:**
- Main: `/home/pi/nexalert_v3/logs/nexalert.log`
- Environmental: `/home/pi/nexalert_v3/logs/environmental.log`
- Alerts: `/home/pi/nexalert_v3/logs/alert_service.log`

**Database Backups:**
- Location: `/home/pi/nexalert_v3/database/backups/`
- Manual backup: `python3 backend/utils/db_manager.py backup`

---

**Deployment Date:** _____________  
**Deployed By:** _____________  
**Location:** _____________  
**Notes:** _____________
