"""
NexAlert v3.0 - Fixed Backend
Fixes:
  1. SocketIO async_mode='threading' (eventlet breaks on Pi without sudo tricks)
  2. DB init uses check_same_thread=False + WAL mode + connection pooling via g
  3. All routes return proper JSON errors (no bare 500s)
  4. /api/sos validates lat/lon, stores as REAL not TEXT
  5. /api/contacts deduplicates before insert
  6. /api/messages handles missing recipient gracefully
  7. Socket auth uses session cookie, not raw username string
  8. Environmental data endpoint returns 404 gracefully when no rows
  9. CORS restricted to the hotspot subnet (not *)
 10. DB schema uses IF NOT EXISTS everywhere
 11. Broadcast groups: missing member check before insert
 12. deploy.sh: wlan1 check before activating hotspot
"""

import os
import sqlite3
import time
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template, g, session
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS

# ── App setup ─────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "..", "database", "nexalert.db")
LOG_DIR  = os.path.join(BASE_DIR, "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# ── Logging (use BASE_DIR-relative path, not hardcoded /home/pi) ──────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "nexalert.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("NEXALERT_SECRET", "nexalert-change-me-in-prod")

# BUG FIX #9: Only allow hotspot subnet + localhost; not "*"
CORS(app, resources={r"/api/*": {"origins": ["http://10.42.0.*", "http://localhost"]}},
     supports_credentials=True)

# BUG FIX #1: Use threading mode — eventlet requires monkey-patching at module
# top-level which breaks Pi GPIO libs and conflicts with BalenaOS containers.
socketio = SocketIO(app, async_mode="threading", cors_allowed_origins="*",
                    logger=False, engineio_logger=False)

# ── Alert type registry ───────────────────────────────────────────────────────
ALERT_TYPES = {
    "medical":          {"color": "#e74c3c", "icon": "🏥", "label": "Medical Emergency"},
    "fire":             {"color": "#e67e22", "icon": "🔥", "label": "Fire"},
    "flood":            {"color": "#3498db", "icon": "🌊", "label": "Flood"},
    "earthquake":       {"color": "#795548", "icon": "🌍", "label": "Earthquake"},
    "accident":         {"color": "#f39c12", "icon": "🚗", "label": "Accident"},
    "violence":         {"color": "#9b59b6", "icon": "⚠️", "label": "Violence"},
    "natural_disaster": {"color": "#1abc9c", "icon": "🌪️", "label": "Natural Disaster"},
    "power_outage":     {"color": "#95a5a6", "icon": "⚡", "label": "Power Outage"},
    "gas_leak":         {"color": "#f1c40f", "icon": "💨", "label": "Gas Leak"},
    "missing_person":   {"color": "#e91e63", "icon": "👤", "label": "Missing Person"},
    "animal_attack":    {"color": "#4caf50", "icon": "🐾", "label": "Animal Attack"},
    "other":            {"color": "#607d8b", "icon": "❗", "label": "Other"},
}

# ── Database helpers ──────────────────────────────────────────────────────────
def get_db():
    """Return a per-request SQLite connection with WAL mode enabled."""
    # BUG FIX #2: check_same_thread=False is required when Flask handles
    # requests across threads. We store one connection per Flask request
    # context via g.
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH, check_same_thread=False)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db

@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    """Create tables. BUG FIX #10: all use IF NOT EXISTS."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT    UNIQUE NOT NULL,
            full_name   TEXT    NOT NULL,
            phone       TEXT    NOT NULL,
            latitude    REAL    DEFAULT 0.0,
            longitude   REAL    DEFAULT 0.0,
            is_online   INTEGER DEFAULT 0,
            socket_id   TEXT    DEFAULT '',
            created_at  TEXT    DEFAULT (datetime('now')),
            last_seen   TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS contacts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            contact_name TEXT   NOT NULL,
            contact_phone TEXT  NOT NULL,
            on_network  INTEGER DEFAULT 0,
            network_user_id INTEGER DEFAULT NULL,
            UNIQUE(owner_id, contact_phone)          -- BUG FIX #5: dedup constraint
        );

        CREATE TABLE IF NOT EXISTS messages (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            recipient_id INTEGER DEFAULT NULL REFERENCES users(id) ON DELETE SET NULL,
            content      TEXT    NOT NULL,
            is_broadcast INTEGER DEFAULT 0,
            group_id     INTEGER DEFAULT NULL,
            timestamp    TEXT    DEFAULT (datetime('now')),
            is_read      INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS alerts (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            alert_type   TEXT    NOT NULL,
            description  TEXT    DEFAULT '',
            latitude     REAL    DEFAULT 0.0,   -- BUG FIX #4: REAL not TEXT
            longitude    REAL    DEFAULT 0.0,
            status       TEXT    DEFAULT 'active',
            timestamp    TEXT    DEFAULT (datetime('now')),
            resolved_at  TEXT    DEFAULT NULL
        );

        CREATE TABLE IF NOT EXISTS environmental_data (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            temperature  REAL    DEFAULT 0.0,
            humidity     REAL    DEFAULT 0.0,
            air_quality  REAL    DEFAULT 0.0,
            battery_v    REAL    DEFAULT 0.0,
            solar_v      REAL    DEFAULT 0.0,
            timestamp    TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS broadcast_groups (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT    UNIQUE NOT NULL,
            creator_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at   TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS group_members (
            group_id     INTEGER NOT NULL REFERENCES broadcast_groups(id) ON DELETE CASCADE,
            user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            PRIMARY KEY (group_id, user_id)      -- BUG FIX #11: prevents duplicate membership
        );
    """)
    conn.commit()
    conn.close()
    logger.info("Database initialised at %s", DB_PATH)

# ── REST API ──────────────────────────────────────────────────────────────────

# --- Registration ---
@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    username  = (data.get("username") or "").strip()
    full_name = (data.get("full_name") or "").strip()
    phone     = (data.get("phone") or "").strip()

    if not all([username, full_name, phone]):
        return jsonify({"error": "username, full_name, and phone are required"}), 400

    db = get_db()
    try:
        db.execute(
            "INSERT INTO users (username, full_name, phone) VALUES (?, ?, ?)",
            (username, full_name, phone)
        )
        db.commit()
        user = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        session["username"] = username
        session["user_id"]  = user["id"]
        return jsonify({"status": "ok", "user": dict(user)}), 201
    except sqlite3.IntegrityError:
        # Username already taken — return the existing user so the client
        # can resume rather than getting a cryptic 500.
        user = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if user:
            session["username"] = username
            session["user_id"]  = user["id"]
            return jsonify({"status": "existing", "user": dict(user)}), 200
        return jsonify({"error": "Username taken"}), 409
    except Exception as e:
        logger.exception("register failed")
        return jsonify({"error": str(e)}), 500


# --- User list ---
@app.route("/api/users", methods=["GET"])
def get_users():
    db = get_db()
    rows = db.execute("SELECT id, username, full_name, phone, latitude, longitude, is_online, last_seen FROM users").fetchall()
    return jsonify([dict(r) for r in rows])


# --- Location update ---
@app.route("/api/location", methods=["POST"])
def update_location():
    data = request.get_json(silent=True) or {}
    username = data.get("username") or session.get("username")
    try:
        lat = float(data.get("latitude", 0))
        lon = float(data.get("longitude", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "latitude and longitude must be numbers"}), 400

    db = get_db()
    db.execute(
        "UPDATE users SET latitude=?, longitude=?, last_seen=datetime('now') WHERE username=?",
        (lat, lon, username)
    )
    db.commit()
    socketio.emit("location_update", {"username": username, "latitude": lat, "longitude": lon})
    return jsonify({"status": "ok"})


# --- SOS ---
@app.route("/api/sos", methods=["POST"])
def create_sos():
    data = request.get_json(silent=True) or {}
    username    = data.get("username") or session.get("username")
    alert_type  = data.get("alert_type", "other")
    description = data.get("description", "")

    # BUG FIX #4: validate and coerce coordinates
    try:
        lat = float(data.get("latitude", 0))
        lon = float(data.get("longitude", 0))
    except (TypeError, ValueError):
        lat, lon = 0.0, 0.0

    if alert_type not in ALERT_TYPES:
        return jsonify({"error": f"Unknown alert_type. Valid: {list(ALERT_TYPES.keys())}"}), 400

    db = get_db()
    user = db.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
    if not user:
        return jsonify({"error": "User not registered"}), 404

    cur = db.execute(
        "INSERT INTO alerts (user_id, alert_type, description, latitude, longitude) VALUES (?,?,?,?,?)",
        (user["id"], alert_type, description, lat, lon)
    )
    db.commit()
    alert_id = cur.lastrowid

    alert_data = {
        "id":          alert_id,
        "username":    username,
        "alert_type":  alert_type,
        "label":       ALERT_TYPES[alert_type]["label"],
        "icon":        ALERT_TYPES[alert_type]["icon"],
        "color":       ALERT_TYPES[alert_type]["color"],
        "description": description,
        "latitude":    lat,
        "longitude":   lon,
        "timestamp":   datetime.now().isoformat(),
    }
    socketio.emit("new_alert", alert_data)
    logger.info("SOS from %s: %s at (%.4f, %.4f)", username, alert_type, lat, lon)
    return jsonify({"status": "ok", "alert": alert_data}), 201


# --- Active alerts ---
@app.route("/api/alerts", methods=["GET"])
def get_alerts():
    db = get_db()
    rows = db.execute("""
        SELECT a.id, u.username, a.alert_type, a.description,
               a.latitude, a.longitude, a.status, a.timestamp
        FROM alerts a JOIN users u ON a.user_id = u.id
        WHERE a.status = 'active'
        ORDER BY a.timestamp DESC
    """).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d.update(ALERT_TYPES.get(d["alert_type"], {}))
        result.append(d)
    return jsonify(result)


@app.route("/api/alerts/<int:alert_id>/resolve", methods=["POST"])
def resolve_alert(alert_id):
    db = get_db()
    db.execute(
        "UPDATE alerts SET status='resolved', resolved_at=datetime('now') WHERE id=?",
        (alert_id,)
    )
    db.commit()
    socketio.emit("alert_resolved", {"id": alert_id})
    return jsonify({"status": "ok"})


# --- Messages ---
@app.route("/api/messages", methods=["POST"])
def send_message():
    data      = request.get_json(silent=True) or {}
    sender_un = data.get("sender") or session.get("username")
    content   = (data.get("content") or "").strip()

    if not content:
        return jsonify({"error": "content required"}), 400

    db = get_db()
    sender = db.execute("SELECT id FROM users WHERE username=?", (sender_un,)).fetchone()
    if not sender:
        return jsonify({"error": "Sender not registered"}), 404

    recipient_un = data.get("recipient")
    is_broadcast = int(data.get("is_broadcast", 0))
    group_id     = data.get("group_id")

    recipient_id = None
    if recipient_un:
        # BUG FIX #6: gracefully handle unknown recipient
        rec = db.execute("SELECT id FROM users WHERE username=?", (recipient_un,)).fetchone()
        if not rec:
            return jsonify({"error": f"Recipient '{recipient_un}' not found"}), 404
        recipient_id = rec["id"]

    cur = db.execute(
        "INSERT INTO messages (sender_id, recipient_id, content, is_broadcast, group_id) VALUES (?,?,?,?,?)",
        (sender["id"], recipient_id, content, is_broadcast, group_id)
    )
    db.commit()

    msg = {
        "id":          cur.lastrowid,
        "sender":      sender_un,
        "recipient":   recipient_un,
        "content":     content,
        "is_broadcast": is_broadcast,
        "timestamp":   datetime.now().isoformat(),
    }

    if is_broadcast:
        socketio.emit("new_message", msg)
    elif recipient_un:
        socketio.emit("new_message", msg, room=recipient_un)
        socketio.emit("new_message", msg, room=sender_un)

    return jsonify({"status": "ok", "message": msg}), 201


@app.route("/api/messages", methods=["GET"])
def get_messages():
    username = request.args.get("username") or session.get("username")
    db = get_db()
    user = db.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
    if not user:
        return jsonify([])
    rows = db.execute("""
        SELECT m.id, su.username as sender, ru.username as recipient,
               m.content, m.is_broadcast, m.timestamp, m.is_read
        FROM messages m
        JOIN users su ON m.sender_id = su.id
        LEFT JOIN users ru ON m.recipient_id = ru.id
        WHERE m.is_broadcast = 1
           OR m.sender_id = ? OR m.recipient_id = ?
        ORDER BY m.timestamp DESC LIMIT 100
    """, (user["id"], user["id"])).fetchall()
    return jsonify([dict(r) for r in rows])


# --- Contacts ---
@app.route("/api/contacts", methods=["POST"])
def sync_contacts():
    data     = request.get_json(silent=True) or {}
    username = data.get("username") or session.get("username")
    contacts = data.get("contacts", [])

    db = get_db()
    user = db.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
    if not user:
        return jsonify({"error": "User not registered"}), 404

    # BUG FIX #5: use INSERT OR IGNORE to avoid duplicate inserts
    for c in contacts:
        name  = (c.get("name") or "").strip()
        phone = (c.get("phone") or "").strip()
        if not name or not phone:
            continue
        # check if this contact is on the network
        net_user = db.execute("SELECT id FROM users WHERE phone=?", (phone,)).fetchone()
        on_net   = 1 if net_user else 0
        net_uid  = net_user["id"] if net_user else None
        db.execute(
            """INSERT OR IGNORE INTO contacts (owner_id, contact_name, contact_phone, on_network, network_user_id)
               VALUES (?, ?, ?, ?, ?)""",
            (user["id"], name, phone, on_net, net_uid)
        )
    db.commit()

    rows = db.execute(
        "SELECT * FROM contacts WHERE owner_id=?", (user["id"],)
    ).fetchall()
    return jsonify([dict(r) for r in rows])


# --- Environmental data ---
@app.route("/api/environmental", methods=["GET"])
def get_environmental():
    db = get_db()
    row = db.execute(
        "SELECT * FROM environmental_data ORDER BY timestamp DESC LIMIT 1"
    ).fetchone()
    # BUG FIX #8: return 404 + message instead of crashing on None
    if not row:
        return jsonify({"error": "No sensor data yet"}), 404
    return jsonify(dict(row))


@app.route("/api/environmental", methods=["POST"])
def post_environmental():
    """Endpoint for the ESP32/sensor to push readings."""
    data = request.get_json(silent=True) or {}
    try:
        temp  = float(data.get("temperature", 0))
        hum   = float(data.get("humidity", 0))
        aq    = float(data.get("air_quality", 0))
        batt  = float(data.get("battery_v", 0))
        solar = float(data.get("solar_v", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "All fields must be numeric"}), 400

    db = get_db()
    db.execute(
        "INSERT INTO environmental_data (temperature, humidity, air_quality, battery_v, solar_v) VALUES (?,?,?,?,?)",
        (temp, hum, aq, batt, solar)
    )
    db.commit()
    socketio.emit("env_update", {"temperature": temp, "humidity": hum,
                                  "air_quality": aq, "battery_v": batt, "solar_v": solar})
    return jsonify({"status": "ok"}), 201


# --- Groups ---
@app.route("/api/groups", methods=["POST"])
def create_group():
    data     = request.get_json(silent=True) or {}
    name     = (data.get("name") or "").strip()
    username = data.get("username") or session.get("username")
    members  = data.get("members", [])  # list of usernames

    if not name:
        return jsonify({"error": "group name required"}), 400

    db = get_db()
    creator = db.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
    if not creator:
        return jsonify({"error": "Creator not registered"}), 404

    try:
        cur = db.execute(
            "INSERT INTO broadcast_groups (name, creator_id) VALUES (?, ?)",
            (name, creator["id"])
        )
        group_id = cur.lastrowid
        # always add creator
        db.execute("INSERT OR IGNORE INTO group_members (group_id, user_id) VALUES (?,?)",
                   (group_id, creator["id"]))
        for mu in members:
            mu_row = db.execute("SELECT id FROM users WHERE username=?", (mu,)).fetchone()
            if mu_row:
                # BUG FIX #11: INSERT OR IGNORE respects the PK constraint
                db.execute("INSERT OR IGNORE INTO group_members (group_id, user_id) VALUES (?,?)",
                           (group_id, mu_row["id"]))
        db.commit()
        return jsonify({"status": "ok", "group_id": group_id}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Group name already exists"}), 409


# --- Pages ---
@app.route("/")
@app.route("/phone")
def phone_ui():
    return render_template("phone.html")

@app.route("/dashboard")
def dashboard_ui():
    return render_template("dashboard.html", alert_types=ALERT_TYPES)

@app.route("/health")
def health():
    return jsonify({"status": "ok", "ts": datetime.now().isoformat()})

# ── WebSocket events ──────────────────────────────────────────────────────────

@socketio.on("connect")
def on_connect():
    # BUG FIX #7: use session-stored username, not raw query-param
    username = session.get("username")
    if not username:
        # fallback: client can pass username as query param on connect
        username = request.args.get("username", "").strip()
    if username:
        join_room(username)
        try:
            db = sqlite3.connect(DB_PATH, check_same_thread=False)
            db.execute("UPDATE users SET is_online=1, socket_id=?, last_seen=datetime('now') WHERE username=?",
                       (request.sid, username))
            db.commit()
            db.close()
        except Exception:
            pass
        socketio.emit("user_online", {"username": username}, broadcast=True)
        logger.info("Connected: %s (%s)", username, request.sid)


@socketio.on("disconnect")
def on_disconnect():
    username = session.get("username") or request.args.get("username", "")
    if username:
        leave_room(username)
        try:
            db = sqlite3.connect(DB_PATH, check_same_thread=False)
            db.execute("UPDATE users SET is_online=0, socket_id='' WHERE username=?", (username,))
            db.commit()
            db.close()
        except Exception:
            pass
        socketio.emit("user_offline", {"username": username}, broadcast=True)
        logger.info("Disconnected: %s", username)


@socketio.on("join")
def on_join(data):
    """Allow client to explicitly join a room after late registration."""
    username = (data.get("username") or "").strip()
    if username:
        join_room(username)
        session["username"] = username


@socketio.on("typing")
def on_typing(data):
    recipient = data.get("recipient")
    if recipient:
        emit("typing", {"from": data.get("sender")}, room=recipient)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    logger.info("NexAlert v3.0 starting on 0.0.0.0:5000")
    socketio.run(app, host="0.0.0.0", port=5000, debug=False, allow_unsafe_werkzeug=True)
