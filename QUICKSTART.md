# NexAlert v3.0 - QUICK START GUIDE

## ⚡ 5-Minute Setup

### Step 1: Copy to Raspberry Pi
```bash
scp nexalert_v3.zip pi@venom.local:/home/pi/
ssh pi@venom.local
cd /home/pi
unzip nexalert_v3.zip
mv nexalert_v3_rebuild nexalert_v3
```

### Step 2: Run Installation
```bash
cd /home/pi/nexalert_v3/scripts
chmod +x deploy.sh
./deploy.sh
```

**The script will:**
- Install all dependencies
- Set up network (WiFi + hotspot)
- Configure auto-start
- Reboot automatically

### Step 3: After Reboot

**Hotspot will be broadcasting:**
- SSID: `NexAlert-Emergency`
- Password: `nexalert2025`

**Connect any phone and it will auto-redirect to registration!**

---

## 🌐 Access URLs

- **Phone Interface:** `http://10.42.0.1/phone` (auto-redirects)
- **Dashboard:** `http://10.42.0.1/dashboard`
- **API Health:** `http://10.42.0.1/health`

---

## 🔧 Common Commands

### Check Status
```bash
sudo systemctl status nexalert
```

### View Logs
```bash
sudo journalctl -u nexalert -f
```

### Restart Service
```bash
sudo systemctl restart nexalert
```

### Stop Service
```bash
sudo systemctl stop nexalert
```

---

## 📍 Google Maps API Key

**IMPORTANT:** The dashboard uses Google Maps. You need an API key.

1. Go to: https://console.cloud.google.com/
2. Create a project
3. Enable "Maps JavaScript API"
4. Create API key
5. Edit `/home/pi/nexalert_v3/backend/templates/dashboard.html`
6. Replace `YOUR_GOOGLE_MAPS_API_KEY` with your key

---

## 🐛 Troubleshooting

### Hotspot not working?
```bash
sudo systemctl restart NetworkManager
sudo nmcli connection up NexAlert-Hotspot
```

### Can't access website?
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

---

## 📱 Demo Flow

1. **Turn on Pi** → Auto-starts, hotspot broadcasts
2. **Connect phone** to "NexAlert-Emergency"
3. **Registration page** opens automatically
4. **Enter name + phone + username**
5. **Start chatting** and sending SOS alerts!
6. **Open dashboard** on laptop at `http://10.42.0.1/dashboard`
7. **See live map** with user locations and alerts

---

## 🎯 Key Features Working Out of the Box

✅ Auto-start on boot  
✅ Captive portal (auto-redirect)  
✅ Name + phone registration  
✅ 12 SOS alert types  
✅ Real-time chat  
✅ Contact sync  
✅ Broadcasting  
✅ Google Maps dashboard  
✅ WebSocket live updates  
✅ Separate WiFi & hotspot  

---

For full documentation, see `README.md`
