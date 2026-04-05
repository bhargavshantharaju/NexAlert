-- NexAlert v3.0 Database Schema
-- SQLite3 Schema for emergency mesh communication system

-- Users Table: Core user information
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone_number TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    email TEXT,
    password_hash TEXT NOT NULL,
    location_lat REAL,
    location_lon REAL,
    online_status INTEGER DEFAULT 0,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Contacts Table: List of emergency contacts for each user
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    contact_phone_number TEXT NOT NULL,
    contact_name TEXT NOT NULL,
    contact_email TEXT,
    contact_type TEXT DEFAULT 'emergency', -- 'emergency', 'family', 'friend', 'official'
    priority INTEGER DEFAULT 0, -- 0 = normal, 1 = high, 2 = critical
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, contact_phone_number)
);

-- SOS Alerts Table: Emergency distress signals
CREATE TABLE IF NOT EXISTS sos_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    category TEXT NOT NULL, -- Medical, Fire, Flood, Earthquake, Accident, Violence, Natural Disaster, Power Outage, Gas Leak, Missing Person, Animal Attack, Other
    severity INTEGER DEFAULT 1, -- 1 = low, 2 = medium, 3 = high, 4 = critical
    description TEXT,
    location_lat REAL NOT NULL,
    location_lon REAL NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'active', -- 'active', 'acknowledged', 'resolved'
    responder_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (responder_id) REFERENCES users(id)
);

-- Messages Table: Chat history (one-to-one and broadcasts)
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER NOT NULL,
    recipient_id INTEGER, -- NULL for broadcast
    broadcast_group_id INTEGER,
    message_text TEXT NOT NULL,
    message_type TEXT DEFAULT 'text', -- 'text', 'image', 'location', 'alert'
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_read INTEGER DEFAULT 0,
    FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (recipient_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (broadcast_group_id) REFERENCES broadcast_groups(id)
);

-- Broadcast Groups Table: Group messaging for area-wide alerts
CREATE TABLE IF NOT EXISTS broadcast_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id INTEGER NOT NULL,
    group_name TEXT NOT NULL,
    description TEXT,
    area_radius_meters INTEGER DEFAULT 5000, -- Broadcast radius
    center_lat REAL,
    center_lon REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (admin_id) REFERENCES users(id)
);

-- Environmental Data Table: Sensor readings (Temperature, Humidity, Voltage)
CREATE TABLE IF NOT EXISTS environmental_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    temperature_celsius REAL,
    humidity_percent REAL,
    battery_voltage REAL,
    solar_panel_voltage REAL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Session Tokens Table: Auth token management
CREATE TABLE IF NOT EXISTS session_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Alert History Table: Tracking acknowledged/resolved alerts
CREATE TABLE IF NOT EXISTS alert_acknowledgments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    response TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (alert_id) REFERENCES sos_alerts(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone_number);
CREATE INDEX IF NOT EXISTS idx_users_location ON users(location_lat, location_lon);
CREATE INDEX IF NOT EXISTS idx_sos_alerts_user ON sos_alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_sos_alerts_status ON sos_alerts(status);
CREATE INDEX IF NOT EXISTS idx_sos_alerts_timestamp ON sos_alerts(timestamp);
CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_id);
CREATE INDEX IF NOT EXISTS idx_messages_recipient ON messages(recipient_id);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
CREATE INDEX IF NOT EXISTS idx_environmental_user ON environmental_data(user_id);
CREATE INDEX IF NOT EXISTS idx_environmental_timestamp ON environmental_data(timestamp);
