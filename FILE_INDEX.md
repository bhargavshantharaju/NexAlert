# NexAlert v3.0 - Complete File Index

## 📋 Project Overview

**NexAlert v3.0** is a production-ready emergency mesh communication platform. This document provides a complete guide to all files and their purposes.

---

## 📂 File Structure & Component Guide

### 🔧 Configuration & Setup Files

```
NexAlert/
│
├── .env.example                          # Environment variables template
│   └─ Copy to .env and customize with your settings
│
├── requirements.txt                      # Python dependencies (pip install -r)
│   ├─ Flask (web framework)
│   ├─ Flask-SocketIO (real-time messaging)
│   ├─ SQLite3 (database)
│   ├─ bcrypt (password hashing)
│   └─ PyJWT (auth tokens)
│
├── README.md                             # Complete documentation
│   ├─ Architecture overview
│   ├─ Deployment instructions
│   ├─ API endpoints reference
│   ├─ Troubleshooting guide
│   └─ 20+ sections
│
├── QUICKSTART.md                         # 5-minute quick start guide
│   ├─ Step-by-step deployment
│   ├─ Testing procedures
│   ├─ Common commands
│   └─ Emergency recovery
│
└── FILE_INDEX.md                         # This file - complete component guide
```

---

### 🖥️ Backend Application Code

```
app/
│
├── app.py (2000+ lines)                 # Main Flask backend server
│   │
│   ├── Authentication                    # password hashing, JWT tokens
│   │   ├─ /api/register
│   │   ├─ /api/login
│   │   └─ @token_required decorator
│   │
│   ├── User Management                   # profile, location updates
│   │   ├─ /api/user/profile
│   │   └─ /api/user/location
│   │
│   ├── Emergency Contacts                # CRUD operations
│   │   ├─ /api/contacts (GET, POST)
│   │   └─ Online/offline status tracking
│   │
│   ├── SOS Alert System                  # 12-category alerts
│   │   ├─ /api/sos/trigger
│   │   ├─ /api/sos/acknowledge/<id>
│   │   ├─ /api/sos/alerts
│   │   └─ Broadcast to all connected clients
│   │
│   ├── Messaging System                  # One-to-one & broadcast
│   │   ├─ /api/messages/send
│   │   ├─ /api/broadcast/send
│   │   └─ SQLite persistence
│   │
│   ├── Environmental Sensors             # Temperature, humidity, power
│   │   ├─ /api/sensors/data (POST)
│   │   ├─ /api/sensors/data/<user_id> (GET)
│   │   └─ Time-series storage
│   │
│   ├── Real-Time Events (WebSocket)      # SocketIO handlers
│   │   ├─ @socketio.on('connect')
│   │   ├─ @socketio.on('user_online')
│   │   ├─ @socketio.on('chat_message')
│   │   └─ Broadcasting to all clients
│   │
│   ├── Database Utilities                # SQLite connection management
│   │   ├─ get_db_connection()
│   │   ├─ query_db() - SELECT operations
│   │   ├─ execute_db() - INSERT/UPDATE/DELETE
│   │   └─ init_db() from schema
│   │
│   ├── Error Handling                    # 404, 500 handlers
│   │   ├─ Try-catch blocks
│   │   ├─ Logging all errors
│   │   └─ JSON error responses
│   │
│   ├── 12 SOS Categories                 # Hard-coded categories
│   │   ├─ 1: Medical
│   │   ├─ 2: Fire
│   │   ├─ 3: Flood
│   │   ├─ ... (12 total)
│   │
│   └── Main Entry Point                  # Database init + SocketIO run
│       ├─ Check if DB exists
│       ├─ Create logs directory
│       └─ Start server on 0.0.0.0:5000
```

---

### 🗄️ Database (SQLite3)

```
database/
│
├── schema.sql (400+ lines)               # Database schema definition
│   │
│   ├── users table
│   │   ├─ id, phone_number (UNIQUE), name, email
│   │   ├─ password_hash, location_lat/lon
│   │   ├─ online_status, last_seen
│   │   └─ Indexed on: phone, location
│   │
│   ├── contacts table (emergency contacts)
│   │   ├─ id, user_id, contact_phone_number
│   │   ├─ contact_name, contact_email
│   │   ├─ contact_type, priority
│   │   └─ Foreign key: users.id
│   │
│   ├── sos_alerts table (emergency distress)
│   │   ├─ id, user_id, category
│   │   ├─ severity (1-4), description
│   │   ├─ location_lat/lon, timestamp
│   │   ├─ status (active/acknowledged/resolved)
│   │   ├─ responder_id
│   │   └─ Indexed on: user_id, status, timestamp
│   │
│   ├── messages table (chat history)
│   │   ├─ id, sender_id, recipient_id
│   │   ├─ broadcast_group_id, message_text
│   │   ├─ message_type, timestamp, is_read
│   │   └─ Indexed on: sender, recipient, timestamp
│   │
│   ├── broadcast_groups table (group messaging)
│   │   ├─ id, admin_id, group_name
│   │   ├─ description, area_radius_meters
│   │   ├─ center_lat/lon, created_at
│   │   └─ Foreign key: users.id
│   │
│   ├── environmental_data table (sensors)
│   │   ├─ id, user_id, temperature_celsius
│   │   ├─ humidity_percent, battery_voltage
│   │   ├─ solar_panel_voltage, timestamp
│   │   └─ Indexed on: user_id, timestamp
│   │
│   ├── session_tokens table (auth)
│   │   ├─ id, user_id, token (UNIQUE)
│   │   ├─ expires_at, created_at
│   │   └─ Foreign key: users.id
│   │
│   └── alert_acknowledgments table
│       ├─ id, alert_id, user_id, response
│       ├─ timestamp
│       └─ Foreign keys: sos_alerts.id, users.id
│
└── nexalert.db (created at runtime)
    └─ SQLite binary database file
       ├─ Auto-created on first app.py run
       ├─ All tables initialized from schema.sql
       └─ Persistent across restarts
```

**Design Notes:**
- Foreign keys enforce referential integrity
- Indices on frequently queried columns (user_id, phone, timestamp, status)
- UNIQUE constraints prevent duplicates
- CASCADE delete on foreign keys

---

### 📱 Frontend - Mobile Interface

```
templates/
├── phone.html (800+ lines)               # Mobile web app UI
│   │
│   ├── Registration Screen              # Account creation
│   │   └─ Form: name, phone, email, password
│   │
│   ├── Login Screen                     # Authentication
│   │   └─ Form: phone, password
│   │
│   └── Main App (Tabbed Interface)
│       │
│       ├─ Chat Tab (💬)                 # One-to-one messaging
│       │  ├─ Message list (received/sent)
│       │  ├─ Message input box
│       │  └─ Real-time updates via SocketIO
│       │
│       ├─ SOS Tab (🆘)                  # Emergency alerts
│       │  ├─ 12 category buttons
│       │  ├─ Severity selector (1-4)
│       │  ├─ Description textarea
│       │  └─ "TRIGGER SOS" button
│       │
│       ├─ Contacts Tab (👥)             # Emergency contacts
│       │  ├─ List of saved contacts
│       │  ├─ Online/offline status
│       │  ├─ Add contact form
│       │  └─ Contact type (emergency/family/friend)
│       │
│       └─ Profile Tab (👤)              # User profile
│           ├─ Display name, phone, email
│           ├─ Online status
│           └─ Logout button
│
└── phone.html also includes:
    ├─ Notification system (toast alerts)
    ├─ Screen/tab navigation logic
    └─ Responsive design (mobile-first)

static/js/
├── phone.js (800+ lines)                 # Mobile app logic
│   │
│   ├── Global State Management
│   │   ├─ app.userId, app.token
│   │   ├─ app.userLocation (GPS)
│   │   ├─ app.socket (SocketIO connection)
│   │   └─ app.currentTab
│   │
│   ├── Initialization
│   │   ├─ Check localStorage for previous login
│   │   ├─ GetGeolocation (watch position)
│   │   ├─ Setup DOM event listeners
│   │   └─ Initialize SocketIO connection
│   │
│   ├── Authentication
│   │   ├─ handleRegistration() → POST /api/register
│   │   ├─ handleLogin() → POST /api/login
│   │   ├─ logout() → Clear localStorage
│   │   └─ Token storage in localStorage
│   │
│   ├── Chat System
│   │   ├─ sendMessage() → POST /api/messages/send
│   │   ├─ displayReceivedMessage() → SocketIO
│   │   └─ updateContactStatus() → real-time
│   │
│   ├── SOS System
│   │   ├─ selectSOSCategory() → UI update
│   │   ├─ triggerSOS() → POST /api/sos/trigger
│   │   ├─ displaySOSAlert() → SocketIO
│   │   └─ Automatic location capture
│   │
│   ├── Contacts Management
│   │   ├─ loadContacts() → GET /api/contacts
│   │   ├─ addContact() → POST /api/contacts
│   │   └─ updateContactStatus() → online indicator
│   │
│   ├── Real-Time Communication
│   │   ├─ initializeSocket() → SocketIO connection
│   │   ├─ Event handlers for: new_message, sos_alert, user_status
│   │   └─ Heartbeat/ping to keep connection alive
│   │
│   ├── Utilities
│   │   ├─ showNotification() → Toast alerts
│   │   ├─ escapeHtml() → XSS prevention
│   │   └─ Periodic location updates every 30s
│   │
│   └── LocalStorage Persistence
│       ├─ nexalert_token → JWT token
│       ├─ nexalert_user_id → User ID
│       └─ Auto-login on app reload

static/css/
├── styles.css (1000+ lines)              # All UI styling
│   │
│   ├── Root CSS Variables
│   │   ├─ --primary-color: #FF6B6B (red)
│   │   ├─ --secondary-color: #4ECDC4 (teal)
│   │   ├─ --success-color: #2ECC71 (green)
│   │   └─ ... more theme colors
│   │
│   ├── Mobile-First Responsive Design
│   │   ├─ 100vh viewport for mobile
│   │   ├─ Touch-friendly buttons (48px min)
│   │   ├─ Readable text (16px+ on mobile)
│   │   └─ @media queries for tablets/desktop
│   │
│   ├── Screens (Registration, Login, Main)
│   │   ├─ .screen class with animation
│   │   ├─ slideIn animation (0.3s)
│   │   └─ .active state visibility
│   │
│   ├── Tab Navigation
│   │   ├─ Bottom tab bar (4 tabs)
│   │   ├─ Active tab highlight
│   │   └─ Icon + label
│   │
│   ├── Form Elements
│   │   ├─ Input styling (border-radius, focus state)
│   │   ├─ Button hover effects
│   │   ├─ Disabled state styling
│   │   └─ Validation feedback colors
│   │
│   ├── Chat Interface
│   │   ├─ Message bubbles (sent/received)
│   │   ├─ Timestamp labels
│   │   ├─ Smooth message animations
│   │   └─ Input bar sticky positioning
│   │
│   ├── SOS Interface
│   │   ├─ 12 category grid (3x4 responsive)
│   │   ├─ Category hover + selected states
│   │   ├─ Red danger button for trigger
│   │   └─ Severity selector dropdown
│   │
│   ├── Contacts List
│   │   ├─ Contact cards with online badge
│   │   ├─ Hover elevation effect
│   │   ├─ Add contact modal form
│   │   └─ Status indicator (green/gray)
│   │
│   ├── Notifications
│   │   ├─ Toast alerts (bottom pop-up)
│   │   ├─ Success/error/info/warning colors
│   │   ├─ 3-second auto-dismiss
│   │   └─ Smooth slide-in animation
│   │
│   ├── Dark Mode Support
│   │   ├─ @media (prefers-color-scheme: dark)
│   │   ├─ Background colors inverted
│   │   └─ Contrast adjustments
│   │
│   └── Custom Scrollbar
│       ├─ Webkit scrollbar styling
│       └─ Rounded thumb + track
```

---

### 📊 Frontend - Admin Dashboard

```
templates/
├── dashboard.html (600+ lines)           # Admin dashboard UI
│   │
│   ├── Layout
│   │   ├─ Sidebar navigation (left)
│   │   ├─ Main content area (right)
│   │   └─ Header with controls (top)
│   │
│   ├── Sidebar Navigation
│   │   ├─ 📍 Live Map
│   │   ├─ ⚠️ Active Alerts
│   │   ├─ 👥 Users
│   │   ├─ 📊 Sensor Data
│   │   └─ 📢 Broadcast
│   │
│   ├── Views
│   │   └─ Each view is a .view div
│   │
│   ├── View 1: Live Map (Default)
│   │   └─ <div id="live-map"> (Google Maps)
│   │
│   ├── View 2: Active Alerts
│   │   ├─ Stats grid (active/critical/online)
│   │   ├─ Alert cards grid
│   │   ├─ Severity badges
│   │   └─ Acknowledge buttons
│   │
│   ├── View 3: Users Table
│   │   ├─ Name, Phone, Status, Last Seen, Location
│   │   └─ Online/offline indicators
│   │
│   ├── View 4: Sensor Data
│   │   ├─ Sensor cards grid
│   │   ├─ Temperature, humidity, battery
│   │   ├─ Solar panel voltage
│   │   └─ Last update timestamp
│   │
│   └── View 5: Broadcast
│       ├─ Broadcast message form
│       ├─ Title input
│       ├─ Message textarea
│       ├─ Target group selector
│       └─ Send button
│
│   ├── Embedded CSS (700+ lines)
│   │   ├─ Dashboard layout grid
│   │   ├─ Sidebar styling
│   │   ├─ Alert cards design
│   │   ├─ Table styling
│   │   ├─ Form styling
│   │   └─ Responsive media queries
│   │
│   └── External Scripts
│       ├─ Google Maps API (injected via ID)
│       ├─ Socket.IO client
│       └─ dashboard.js

static/js/
├── dashboard.js (600+ lines)             # Dashboard logic
│   │
│   ├── Global State
│   │   ├─ dashboard.map (Google Maps instance)
│   │   ├─ dashboard.markers (user location markers)
│   │   ├─ dashboard.alertMarkers (SOS pins)
│   │   ├─ dashboard.socket (WebSocket)
│   │   ├─ dashboard.allAlerts (alert list)
│   │   └─ dashboard.allUsers (user list)
│   │
│   ├── Google Maps Integration
│   │   ├─ initializeMap() → Create map instance
│   │   ├─ addUserMarker() → Green/gray circles (online/offline)
│   │   ├─ addSOSMarker() → Red/orange/yellow pins (severity)
│   │   └─ Map centered at first alert
│   │
│   ├── Data Loading
│   │   ├─ loadAlerts() → GET /api/sos/alerts
│   │   ├─ loadUsers() → Derived from alerts
│   │   ├─ loadSensorData() → GET /api/sensors/data/<id>
│   │   └─ Periodic refresh every 30s
│   │
│   ├── Real-Time Socket Events
│   │   ├─ Listen: sos_alert → new emergency
│   │   ├─ Listen: location_update → user moved
│   │   ├─ Listen: user_status_change → online/offline
│   │   ├─ Listen: sensor_data → environmental update
│   │   └─ Play notification sound on alert
│   │
│   ├── Rendering Functions
│   │   ├─ updateAlertStats() → Update stat cards
│   │   ├─ renderAlertsList() → Alert cards grid
│   │   ├─ renderUsersTable() → User list table
│   │   └─ renderSensorCards() → Sensor data cards
│   │
│   ├── Actions
│   │   ├─ acknowledgeAlert() → POST /api/sos/acknowledge/<id>
│   │   ├─ sendBroadcast() → API call
│   │   └─ playNotificationSound() → Web Audio API
│   │
│   ├── Navigation
│   │   ├─ setupNavigation() → Click handlers
│   │   ├─ switchView() → Show/hide views
│   │   └─ Update header title
│   │
│   └── Utilities
│       ├─ refreshData() → Reload all data
│       ├─ logout() → Redirect to home
│       └─ Map resize trigger on view switch
```

---

### 🚀 Deployment & Networking Scripts

```
scripts/
│
├── deploy.sh (800+ lines)                # Automated deployment
│   │
│   ├── System Setup
│   │   ├─ Check if running as root
│   │   ├─ Check if Ubuntu/Debian system
│   │   └─ Error handling + colorized output
│   │
│   ├── System Package Installation
│   │   ├─ apt update && apt upgrade
│   │   ├─ Install: python3, pip, nginx, sqlite3
│   │   ├─ Install: supervisor, dnsmasq, iptables
│   │   └─ Install: build-essential, libssl-dev
│   │
│   ├── Python Virtual Environment
│   │   ├─ Create venv in /opt/nexalert/venv
│   │   ├─ Activate venv for dependency install
│   │   └─ Install requirements.txt
│   │
│   ├── Database Initialization
│   │   ├─ sqlite3 < schema.sql
│   │   ├─ Create initial tables
│   │   └─ Setup indices for performance
│   │
│   ├── Nginx Reverse Proxy
│   │   ├─ Create /etc/nginx/sites-available/nexalert
│   │   ├─ Proxy to localhost:5000
│   │   ├─ WebSocket upgrade headers
│   │   ├─ Static asset caching
│   │   ├─ Gzip compression
│   │   ├─ Enable site + disable default
│   │   └─ Validate config + restart
│   │
│   ├── SystemD Service
│   │   ├─ Create /etc/systemd/system/nexalert.service
│   │   ├─ Set Type=simple, Restart=always
│   │   ├─ Auto-start on boot
│   │   ├─ Crash recovery (5 restarts/60s)
│   │   └─ Journal logging
│   │
│   ├── Logging Setup
│   │   ├─ Create /opt/nexalert/logs
│   │   ├─ Setup logrotate for daily rotation
│   │   ├─ Keep 7-day backup
│   │   └─ Compress old logs
│   │
│   ├── Firewall (UFW)
│   │   ├─ Allow SSH (22/tcp)
│   │   ├─ Allow HTTP (80/tcp)
│   │   ├─ Allow HTTPS (443/tcp)
│   │   ├─ Allow Flask debug (5000/tcp)
│   │   └─ Enable UFW
│   │
│   └── Final Validation
│       ├─ Check if service is running
│       ├─ Check if Nginx is running
│       ├─ Print summary report
│       ├─ List next steps
│       └─ Display access URLs
│
├── setup_network.sh (700+ lines)        # Mesh network config
│   │
│   ├── System Checks
│   │   ├─ Verify running as root
│   │   ├─ Check required network tools
│   │   └─ Detect WiFi interfaces
│   │
│   ├── Interface Detection
│   │   ├─ Find 2+ WiFi interfaces
│   │   ├─ Assign wlan0 (internet), wlan1 (hotspot)
│   │   └─ Validate interface count
│   │
│   ├── Internet Configuration (wlan0)
│   │   ├─ Check if already connected
│   │   ├─ Prompt for SSID/password if not
│   │   ├─ nmcli device wifi connect
│   │   └─ Verify connectivity
│   │
│   ├── Hotspot Configuration (wlan1)
│   │   ├─ Verify AP mode support (iw capability check)
│   │   ├─ Bring interface down
│   │   ├─ Set static IP 10.42.0.1/24
│   │   ├─ Bring interface up
│   │   └─ Assign to unmanaged mode
│   │
│   ├── dnsmasq Configuration
│   │   ├─ Backup original /etc/dnsmasq.conf
│   │   ├─ Create NexAlert-specific config
│   │   ├─ SET DHCP RANGE: 10.42.0.50-150
│   │   ├─ SET CRITICAL: address=/#/10.42.0.1 (CAPTIVE PORTAL!)
│   │   ├─ Configure upstream DNS
│   │   ├─ Kill existing dnsmasq
│   │   └─ Start new dnsmasq
│   │
│   ├── iptables Firewall Rules
│   │   ├─ Enable IP forwarding (echo 1 > /proc/sys/net/ipv4/ip_forward)
│   │   ├─ Clear existing rules
│   │   ├─ Allow established connections
│   │   ├─ Allow loopback, SSH, HTTP, HTTPS
│   │   ├─ Allow DNS (53), DHCP (67/68)
│   │   ├─ FORWARD between interfaces
│   │   ├─ NAT: Masquerade on internet interface
│   │   ├─ Captive Portal: DNAT port 80 to 10.42.0.1
│   │   └─ opt: DNAT port 443 to 10.42.0.1
│   │
│   ├── hostapd Configuration (AP Mode)
│   │   ├─ Install hostapd if not present
│   │   ├─ Create /etc/hostapd/nexalert.conf
│   │   ├─ SET SSID: NexAlert-Emergency
│   │   ├─ Set channel 6, hw_mode g
│   │   ├─ MAX 50 connected stations
│   │   ├─ Optional: WPA2 security
│   │   └─ Or open network (no auth)
│   │
│   ├── SystemD Service for hostapd
│   │   ├─ Create /etc/systemd/system/hostapd-nexalert.service
│   │   ├─ Enable on boot
│   │   ├─ Start service
│   │   └─ Bind to wlan1 availability
│   │
│   ├── iptables Persistence
│   │   ├─ Install iptables-persistent
│   │   ├─ Save rules with iptables-save
│   │   └─ Restore on boot via systemctl
│   │
│   ├── Verification
│   │   ├─ Show network interfaces
│   │   ├─ Show IP addresses
│   │   ├─ List running services
│   │   ├─ Display iptables rules
│   │   └─ Test with ping
│   │
│   └── Summary + Troubleshooting
│       ├─ Gateway IP, DHCP range
│       ├─ Service status
│       ├─ Log inspection commands
│       └─ Emergency restart commands
│
└── verify_installation.sh (400+ lines) # Installation validator
    │
    ├── Check Permissions
    │   └─ Verify running as root/sudo
    │
    ├── System Dependencies (8 checks)
    │   ├─ python3, pip3, nginx, sqlite3
    │   ├─ dnsmasq, iptables, git
    │   └─ Report version of each
    │
    ├── Directory Structure (7 checks)
    │   ├─ /opt/nexalert, /app, /database
    │   ├─ /static, /templates, /scripts, /logs
    │   └─ Green checkmark if all present
    │
    ├── Required Files (9 checks)
    │   ├─ app.py, schema.sql, nexalert.db
    │   ├─ HTML, JS, CSS files
    │   ├─ Show file size
    │   └─ Report missing files
    │
    ├── Service Status (4 checks)
    │   ├─ nexalert, nginx, dnsmasq, hostapd
    │   ├─ Active/inactive status
    │   └─ Warnings for inactive services
    │
    ├── Network Configuration (4 checks)
    │   ├─ Count WiFi interfaces
    │   ├─ Check IP forwarding enabled
    │   ├─ Gateway IP 10.42.0.1 present
    │   └─ iptables NAT rules configured
    │
    ├── Port Availability (4 checks)
    │   ├─ Ports 80, 443, 5000, 3000
    │   ├─ Use lsof to detect listening services
    │   └─ Report which process owns each port
    │
    ├─ Database Validation (2 checks)
    │   ├─ File exists and readable
    │   ├─ Count tables in database
    │   └─ Test sqlite3 connectivity
    │
    ├─ Connectivity Tests (3 checks)
    │   ├─ http://localhost accessibility (curl)
    │   ├─ /health endpoint response
    │   └─ External internet (ping 8.8.8.8)
    │
    ├─ Service Status Report
    │   ├─ Full systemctl status for each service
    │   └─ Detailed error messages
    │
    └─ Summary Report
        ├─ Total tests, passed/failed/warnings
        ├─ Pass/fail verdict
        ├─ Troubleshooting commands
        └─ Database debug queries
```

---

### ⚙️ Configuration Files

```
config/
│
├── nexalert.service                      # SystemD service file
│   │
│   ├── [Unit] Section
│   │   ├─ Description & documentation
│   │   ├─ After=network.target, syslog.target
│   │   ├─ Wants=network-online.target
│   │   └─ StartLimitBurst/IntervalSec
│   │
│   ├── [Service] Section
│   │   ├─ Type=simple (blocking process)
│   │   ├─ User=root, Group=root
│   │   ├─ Working directory
│   │   ├─ Environment variables
│   │   ├─ ExecStart=/opt/nexalert/venv/bin/python app.py
│   │   ├─ Restart=always
│   │   ├─ RestartSec=10 (delay before restart)
│   │   ├─ MaxStartRetries=5
│   │   ├─ Journal logging
│   │   ├─ Security settings (NoNewPrivileges, ProtectSystem)
│   │   ├─ Process limits (file descriptors, processes)
│   │   └─ Timeout/kill settings
│   │
│   └── [Install] Section
│       └─ WantedBy=multi-user.target (run at boot)
│
└── dnsmasq.conf (400+ lines)             # Captive portal DNS/DHCP
    │
    ├── Interface Configuration
    │   ├─ interface=wlan1 (hotspot only)
    │   ├─ bind-interfaces (no system resolv.conf)
    │   └─ no-resolv (use custom DNS)
    │
    ├── DHCP Configuration (CRITICAL!)
    │   ├─ dhcp-range=10.42.0.50,10.42.0.150,12h
    │   ├─ Set gateway IP (10.42.0.1)
    │   ├─ Set DNS servers (point to gateway)
    │   ├─ Domain name (nexalert.local)
    │   ├─ MTU settings
    │   └─ Lease management
    │
    ├── CAPTIVE PORTAL (MOST IMPORTANT!)
    │   ├─ address=/#/10.42.0.1
    │   │  └─ EVERY DNS query → gateway IP!
    │   │     User types google.com → resolves to 10.42.0.1
    │   │     Nginx shows login page
    │   ├─ Optional whitelist exceptions
    │   └─ Optional bypasses for localhost
    │
    ├── DNS Configuration
    │   ├─ Upstream DNS servers (8.8.8.8, Cloudflare)
    │   ├─ DNS cache settings
    │   ├─ DNSSEC enable/disable
    │   ├─ Minimal TTL (3600)
    │   └─ Negative cache TTL
    │
    ├── Logging
    │   ├─ Log queries (verbose debugging)
    │   ├─ Log DHCP transactions
    │   ├─ Log facility (syslog)
    │   └─ View logs: tail -f /var/log/dnsmasq.log
    │
    ├── Performance Tuning
    │   ├─ Listen addresses
    │   ├─ Max DHCP clients (150)
    │   ├─ Cache size (150 entries)
    │   └─ Connection tracking
    │
    ├── Security
    │   ├─ bogus-priv (reject private ranges)
    │   ├─ reply-delay settings
    │   ├─ strict-order (no forwarding)
    │   └─ no-hosts (no /etc/hosts)
    │
    └── Advanced Options
        ├─ Local domain additions
        ├─ Specific DNS records for services
        ├─ Host file includes (addn-hosts)
        └─ Debugging mode toggle
```

---

## 🔑 Key Features Summary

| Feature | Component | Technology |
|---------|-----------|-----------|
| User Authentication | Backend | Flask + JWT + bcrypt |
| Real-Time Messaging | Backend + Frontend | SocketIO (WebSocket) |
| Emergency Alerts | Backend + Frontend | SOS system + broadcast |
| User Tracking | Frontend (Maps) | Google Maps API |
| Database | Backend | SQLite3 |
| Web Server | Infrastructure | Nginx reverse proxy |
| Mesh Network | Scripts | dnsmasq + iptables + hostapd |
| Service Management | Infrastructure | SystemD |
| Mobile UI | Frontend | HTML5 + CSS3 + JS |
| Dashboard | Frontend | Google Maps + charts |
| API | Backend | RESTful + SocketIO |
| Authentication | Frontend | JWT tokens + LocalStorage |

---

## 📊 File Statistics

| Component | Files | Lines | Language |
|-----------|-------|-------|----------|
| Backend | 1 | 2000+ | Python |
| Database Schema | 1 | 400+ | SQL |
| Mobile Frontend | 1 | 800+ | HTML/CSS/JS (1600+) |
| Dashboard Frontend | 1 | 600+ | HTML/CSS/JS (1300+) |
| Deployment Scripts | 3 | 2000+ | Bash |
| Configuration Files | 2 | 700+ | Config/YAML |
| Documentation | 3 | 2000+ | Markdown |
| **TOTAL** | **12** | **9,800+** | **Production Code** |

---

## 🚀 Deployment Path

1. **Get Files** → Clone repo / download ZIP
2. **Run deploy.sh** → Install dependencies + backend
3. **Run setup_network.sh** → Configure mesh networking
4. **Run verify_installation.sh** → Validate everything
5. **Add Google Maps API Key** → Update dashboard.html
6. **Access NexAlert** → http://<pi-ip-address>
7. **Register** → Create account on phone interface
8. **Test SOS** → Trigger emergency alert
9. **Connect to WiFi** → Join "NexAlert-Emergency" network
10. **Verify Mesh** → Test internet passthrough

---

## 📝 Next Steps

- [ ] Read [README.md](README.md) for comprehensive documentation
- [ ] Read [QUICKSTART.md](QUICKSTART.md) for 5-minute setup
- [ ] Register and test on phone UI
- [ ] Trigger a test SOS alert
- [ ] Connect WiFi client to "NexAlert-Emergency"
- [ ] Verify captive portal auto-login
- [ ] Test real-time messaging (SocketIO)
- [ ] View admin dashboard with Google Maps
- [ ] Monitor logs: `journalctl -u nexalert -f`

---

**NexAlert v3.0** - Complete Emergency Communication Platform ✨
