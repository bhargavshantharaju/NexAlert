# NexAlert v3.0 - Complete Rebuild

**Autonomous Solar-Powered LoRa Mesh Emergency Communication Platform**

## 🚀 What's New in v3.0

### Major Changes from Previous Version

#### 1. **Auto-Start on Boot**
- Systemd service runs automatically
- No more manual terminal commands
- Restarts automatically if it crashes

#### 2. **Separate Network Interfaces**
- **wlan0** (onboard WiFi) → Connects to your home/lab WiFi for internet
- **wlan1** (USB dongle) → Broadcasts "NexAlert-Emergency" hotspot

#### 3. **Captive Portal**
- When phones connect to the hotspot, they auto-redirect to the registration page
- No need to manually type `10.42.0.1` anymore

#### 4. **User Registration**
- Name + Phone Number + Username required to join
- Persistent user database (SQLite)

#### 5. **Contact Sync & Network Detection**
- Upload your phone contacts
- See which contacts are online on the network
- Dashboard shows ALL users + their contact lists

#### 6. **Expanded SOS Types**
- 12 emergency categories (was 4):
  - Medical, Fire, Flood, Earthquake, Accident, Violence
  - Natural Disaster, Power Outage, Gas Leak, Missing Person, Animal Attack, Other

#### 7. **Broadcasting**
- Send messages to everyone or specific users
- Group creation for targeted broadcasts

#### 8. **Google Maps Integration** (Dashboard Only)
- Real-time location tracking of all users
- SOS alerts plotted on map
- Phone interface does NOT have maps (per your requirement)

#### 9. **No More SSL Warnings**
- Nginx reverse proxy handles HTTP cleanly
- Optional: Can add Let's Encrypt later for HTTPS

#### 10. **Reliable Architecture**
- Flask + SQLite backend
- WebSocket (SocketIO) for real-time updates
- Single unified app (not multiple services fighting each other)

---

## 📦 Installation Instructions

### Step 1: Copy Files to Raspberry Pi

```bash
# On your laptop (where you have the ZIP file)
scp nexalert_v3.zip pi@venom.local:/home/pi/

# SSH into the Pi
ssh pi@venom.local

# Extract the files
cd /home/pi
unzip nexalert_v3.zip
mv nexalert_v3_rebuild nexalert_v3
```

### Step 2: Run Deployment Script

```bash
cd /home/pi/nexalert_v3/scripts
chmod +x deploy.sh
./deploy.sh
```

**What the script does:**
1. Installs system packages (Python, dnsmasq, nginx)
2. Creates Python virtual environment
3. Installs Python dependencies
4. Sets up database
5. Configures network (hotspot on wlan1)
6. Sets up captive portal DNS
7. Installs systemd service
8. Configures nginx reverse proxy
9. **Reboots the Pi**

### Step 3: After Reboot

The system will automatically start. Check status:

```bash
sudo systemctl status nexalert
```

View logs:
```bash
sudo journalctl -u nexalert -f
# OR
tail -f /home/pi/nexalert_v3/logs/nexalert.log
```

---

## 🌐 Network Configuration

### How It Works

#### wlan0 (Onboard WiFi)
- **Purpose:** Connect to your home/lab WiFi for internet access
- **Configuration:** Use `raspi-config` or NetworkManager GUI
- **Example:**
  ```bash
  sudo nmcli device wifi connect "YourWiFiSSID" password "YourPassword"
  ```

#### wlan1 (USB Dongle)
- **Purpose:** Broadcast NexAlert hotspot
- **SSID:** `NexAlert-Emergency`
- **Password:** `nexalert2025`
- **IP Range:** `10.42.0.0/24`
- **Gateway:** `10.42.0.1` (the Pi)

#### Captive Portal
- When a phone connects to "NexAlert-Emergency", it will auto-redirect to the registration page
- Uses `dnsmasq` to intercept all DNS queries
- Uses `iptables` to redirect HTTP traffic

---

## 📱 Phone Interface Features

### Registration
- Full Name
- Phone Number  
- Username

### Tabs
1. **Chat** 💬
   - One-to-one messaging
   - Broadcast to all users
   - Real-time updates via WebSocket

2. **SOS** 🚨
   - 12 emergency types
   - Optional description
   - Automatic location capture
   - Immediate broadcast to dashboard

3. **Contacts** 👥
   - Sync phone contacts
   - See who's on the network
   - Filter: All / Online / On Network

### What Phone DOES NOT Have
- ❌ Google Maps (dashboard only)
- ❌ Environmental sensor data
- ❌ Admin controls

---

## 🖥️ Dashboard Features (Coming Next)

The dashboard (`http://10.42.0.1/dashboard`) will have:

1. **Google Maps**
   - Real-time user locations
   - SOS alert markers
   - Click on markers for details

2. **User List**
   - All registered users
   - Online/offline status
   - Contact lists for each user

3. **Environmental Data**
   - Temperature, humidity, air quality
   - Battery and solar voltage
   - Historical charts

4. **Alert Management**
   - List of all SOS alerts
   - Resolve/acknowledge alerts
   - Filter by type and status

5. **Broadcasting**
   - Send announcements to all users
   - Create broadcast groups
   - Message history

---

## 🔧 Manual Controls (If Needed)

### Start Service Manually
```bash
sudo systemctl start nexalert
```

### Stop Service
```bash
sudo systemctl stop nexalert
```

### Restart Service
```bash
sudo systemctl restart nexalert
```

### Disable Auto-Start
```bash
sudo systemctl disable nexalert
```

### Re-Enable Auto-Start
```bash
sudo systemctl enable nexalert
```

### View Realtime Logs
```bash
sudo journalctl -u nexalert -f
```

### Access Database Directly
```bash
cd /home/pi/nexalert_v3/database
sqlite3 nexalert.db
# Inside SQLite:
.tables
SELECT * FROM users;
.quit
```

---

## 🐛 Troubleshooting

### Issue: Hotspot Not Broadcasting

**Check NetworkManager:**
```bash
nmcli connection show
nmcli device status
```

**Restart NetworkManager:**
```bash
sudo systemctl restart NetworkManager
```

**Manual Hotspot Activation:**
```bash
sudo nmcli connection up NexAlert-Hotspot
```

### Issue: Captive Portal Not Working

**Check dnsmasq:**
```bash
sudo systemctl status dnsmasq
sudo systemctl restart dnsmasq
```

**Check iptables rules:**
```bash
sudo iptables -t nat -L -n -v
```

**Re-apply iptables:**
```bash
sudo iptables -t nat -A PREROUTING -i wlan1 -p tcp --dport 80 -j REDIRECT --to-port 80
sudo iptables -t nat -A PREROUTING -i wlan1 -p tcp --dport 443 -j REDIRECT --to-port 80
sudo sh -c "iptables-save > /etc/iptables.rules"
```

### Issue: Service Won't Start

**Check logs:**
```bash
sudo journalctl -u nexalert -n 50 --no-pager
```

**Common fixes:**
```bash
# Ensure virtual environment exists
cd /home/pi/nexalert_v3
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Check permissions
sudo chown -R pi:pi /home/pi/nexalert_v3
```

### Issue: Website Not Accessible

**Check if Flask is running:**
```bash
sudo netstat -tlnp | grep 5000
```

**Check nginx:**
```bash
sudo systemctl status nginx
sudo nginx -t
```

**Restart everything:**
```bash
sudo systemctl restart nexalert
sudo systemctl restart nginx
```

---

## 🔐 Security Notes

### Default Credentials
- **Hotspot Password:** `nexalert2025`
- **Change it:** Edit `/etc/NetworkManager/system-connections/NexAlert-Hotspot.nmconnection`

### Database
- SQLite file: `/home/pi/nexalert_v3/database/nexalert.db`
- **No password** — it's a local file
- Backup regularly if deploying in production

### Future: HTTPS with Let's Encrypt
```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

---

## 📊 Database Schema

### Tables

1. **users** — Registered network users
2. **contacts** — User's phone contacts + network sync status
3. **messages** — One-to-one and broadcast messages
4. **alerts** — Emergency SOS alerts
5. **environmental_data** — Sensor readings
6. **broadcast_groups** — Group broadcast management
7. **group_members** — Group membership

---

## 🛠️ Development

### Add New Alert Types

Edit `backend/app.py`:
```python
ALERT_TYPES = {
    'your_new_type': {
        'color': '#ff0000',
        'icon': '🔥',
        'label': 'Your New Emergency'
    }
}
```

### Add New API Endpoints

Add to `backend/app.py`:
```python
@app.route('/api/your-endpoint', methods=['POST'])
def your_function():
    # Your code here
    return jsonify({'status': 'success'})
```

### Customize Phone UI

- **HTML:** `backend/templates/phone.html`
- **CSS:** `backend/static/css/phone.css`
- **JS:** `backend/static/js/phone.js`

---

## 🚀 Pushing to GitHub

```bash
cd /home/pi/nexalert_v3
git init
git add .
git commit -m "NexAlert v3.0 - Complete rebuild"

# Create a repo on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/nexalert_v3.git
git branch -M main
git push -u origin main
```

---

## 📞 Support

Created by: Bhargav  
Organization: IEEE ComSoc BMSIT&M  
Project: NexAlert 3.0  
Date: March 2026

For issues, check logs first:
```bash
sudo journalctl -u nexalert -f
tail -f /home/pi/nexalert_v3/logs/nexalert.log
```
>>>>>>> 5c50a14 (NexAlert v3.0 - Complete production rebuild)
