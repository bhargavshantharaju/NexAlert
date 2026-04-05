#!/usr/bin/env python3
"""
NexAlert v3.0 - Backend Server
Autonomous Solar-Powered Emergency Mesh Platform
Implements Flask-SocketIO for real-time messaging and SOS alert system
"""

import os
import sqlite3
import json
import math
import logging
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms
import bcrypt
import jwt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/nexalert.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Flask app configuration
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'nexalert-emergency-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///./database/nexalert.db'
app.config['JSON_SORT_KEYS'] = False

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# SOS Categories - 12 Emergency Types
SOS_CATEGORIES = {
    1: "Medical",
    2: "Fire",
    3: "Flood",
    4: "Earthquake",
    5: "Accident",
    6: "Violence",
    7: "Natural Disaster",
    8: "Power Outage",
    9: "Gas Leak",
    10: "Missing Person",
    11: "Animal Attack",
    12: "Other"
}

SEVERITY_LEVELS = {
    1: "Low",
    2: "Medium",
    3: "High",
    4: "Critical"
}

# ============================================================================
# DATABASE UTILITIES
# ============================================================================

def get_db_connection():
    """Get a database connection with row factory for dict-like access"""
    conn = sqlite3.connect('database/nexalert.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database from schema.sql"""
    try:
        conn = get_db_connection()
        with open('database/schema.sql', 'r') as f:
            conn.executescript(f.read())
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

def query_db(query, args=(), one=False):
    """Execute a SELECT query"""
    try:
        conn = get_db_connection()
        cur = conn.execute(query, args)
        rv = cur.fetchall()
        conn.close()
        return (rv[0] if rv else None) if one else rv
    except sqlite3.Error as e:
        logger.error(f"Database query error: {e}")
        return None if one else []

def execute_db(query, args=()):
    """Execute an INSERT/UPDATE/DELETE query"""
    try:
        conn = get_db_connection()
        cur = conn.execute(query, args)
        conn.commit()
        last_id = cur.lastrowid
        conn.close()
        return last_id
    except sqlite3.Error as e:
        logger.error(f"Database execute error: {e}")
        return None

# ============================================================================
# AUTHENTICATION UTILITIES
# ============================================================================

def hash_password(password):
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, hash_):
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hash_.encode('utf-8'))

def generate_token(user_id):
    """Generate a JWT token for a user"""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(days=30),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

def verify_token(token):
    """Verify a JWT token and return user_id"""
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None

def token_required(f):
    """Decorator to require valid auth token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'Missing authorization token'}), 401
        
        user_id = verify_token(token)
        if not user_id:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        return f(user_id, *args, **kwargs)
    return decorated

# ============================================================================
# USER MANAGEMENT API
# ============================================================================

@app.route('/api/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.json
        
        # Validate input
        if not data.get('phone_number') or not data.get('name') or not data.get('password'):
            return jsonify({'error': 'Missing required fields'}), 400
        
        phone = data['phone_number']
        name = data['name']
        email = data.get('email', '')
        password = data['password']
        
        # Check if user exists
        existing = query_db('SELECT id FROM users WHERE phone_number = ?', (phone,), one=True)
        if existing:
            return jsonify({'error': 'User already exists'}), 409
        
        # Hash password and insert user
        password_hash = hash_password(password)
        user_id = execute_db(
            'INSERT INTO users (phone_number, name, email, password_hash) VALUES (?, ?, ?, ?)',
            (phone, name, email, password_hash)
        )
        
        if not user_id:
            return jsonify({'error': 'Registration failed'}), 500
        
        token = generate_token(user_id)
        logger.info(f"User registered: {phone}")
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'token': token,
            'message': 'Registration successful'
        }), 201
    
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    """User login"""
    try:
        data = request.json
        
        if not data.get('phone_number') or not data.get('password'):
            return jsonify({'error': 'Missing credentials'}), 400
        
        phone = data['phone_number']
        password = data['password']
        
        user = query_db('SELECT id, password_hash FROM users WHERE phone_number = ?', (phone,), one=True)
        if not user or not verify_password(password, user['password_hash']):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        token = generate_token(user['id'])
        logger.info(f"User logged in: {phone}")
        
        return jsonify({
            'success': True,
            'user_id': user['id'],
            'token': token,
            'message': 'Login successful'
        }), 200
    
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/profile', methods=['GET'])
@token_required
def get_profile(user_id):
    """Get user profile"""
    try:
        user = query_db(
            'SELECT id, phone_number, name, email, location_lat, location_lon, online_status, created_at FROM users WHERE id = ?',
            (user_id,),
            one=True
        )
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'user_id': user['id'],
            'phone_number': user['phone_number'],
            'name': user['name'],
            'email': user['email'],
            'location': {
                'lat': user['location_lat'],
                'lon': user['location_lon']
            },
            'online_status': bool(user['online_status']),
            'created_at': user['created_at']
        }), 200
    
    except Exception as e:
        logger.error(f"Profile retrieval error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/location', methods=['POST'])
@token_required
def update_location(user_id):
    """Update user location"""
    try:
        data = request.json
        
        if 'lat' not in data or 'lon' not in data:
            return jsonify({'error': 'Missing location data'}), 400
        
        lat = data['lat']
        lon = data['lon']
        
        execute_db(
            'UPDATE users SET location_lat = ?, location_lon = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (lat, lon, user_id)
        )
        
        logger.info(f"Location updated for user {user_id}: ({lat}, {lon})")
        
        # Broadcast location to connected clients
        socketio.emit('location_update', {
            'user_id': user_id,
            'lat': lat,
            'lon': lon,
            'timestamp': datetime.now().isoformat()
        }, broadcast=True)
        
        return jsonify({'success': True, 'message': 'Location updated'}), 200
    
    except Exception as e:
        logger.error(f"Location update error: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# CONTACT MANAGEMENT API
# ============================================================================

@app.route('/api/contacts', methods=['GET'])
@token_required
def get_contacts(user_id):
    """Get user's emergency contacts"""
    try:
        contacts = query_db(
            'SELECT id, contact_phone_number, contact_name, contact_email, contact_type, priority FROM contacts WHERE user_id = ? ORDER BY priority DESC',
            (user_id,)
        )
        
        contact_list = []
        if contacts:
            for contact in contacts:
                # Check if contact is online
                contact_user = query_db('SELECT online_status FROM users WHERE phone_number = ?', (contact['contact_phone_number'],), one=True)
                contact_list.append({
                    'id': contact['id'],
                    'phone_number': contact['contact_phone_number'],
                    'name': contact['contact_name'],
                    'email': contact['contact_email'],
                    'type': contact['contact_type'],
                    'priority': contact['priority'],
                    'online': bool(contact_user['online_status']) if contact_user else False
                })
        
        return jsonify({'contacts': contact_list}), 200
    
    except Exception as e:
        logger.error(f"Contact retrieval error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/contacts', methods=['POST'])
@token_required
def add_contact(user_id):
    """Add a new emergency contact"""
    try:
        data = request.json
        
        if not data.get('phone_number') or not data.get('name'):
            return jsonify({'error': 'Missing required fields'}), 400
        
        contact_id = execute_db(
            'INSERT INTO contacts (user_id, contact_phone_number, contact_name, contact_email, contact_type, priority) VALUES (?, ?, ?, ?, ?, ?)',
            (user_id, data['phone_number'], data['name'], data.get('email', ''), data.get('type', 'emergency'), data.get('priority', 0))
        )
        
        if not contact_id:
            return jsonify({'error': 'Failed to add contact'}), 500
        
        logger.info(f"Contact added for user {user_id}: {data['phone_number']}")
        
        return jsonify({
            'success': True,
            'contact_id': contact_id,
            'message': 'Contact added successfully'
        }), 201
    
    except Exception as e:
        logger.error(f"Contact creation error: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# SOS ALERT API
# ============================================================================

@app.route('/api/sos/trigger', methods=['POST'])
@token_required
def trigger_sos(user_id):
    """Trigger an SOS alert"""
    try:
        data = request.json
        
        if 'category' not in data or 'lat' not in data or 'lon' not in data:
            return jsonify({'error': 'Missing required fields'}), 400
        
        category = data.get('category')
        severity = data.get('severity', 3)
        description = data.get('description', '')
        lat = data['lat']
        lon = data['lon']
        
        # Validate category
        if category not in SOS_CATEGORIES:
            return jsonify({'error': 'Invalid SOS category'}), 400
        
        # Insert SOS alert
        alert_id = execute_db(
            'INSERT INTO sos_alerts (user_id, category, severity, description, location_lat, location_lon) VALUES (?, ?, ?, ?, ?, ?)',
            (user_id, SOS_CATEGORIES[category], severity, description, lat, lon)
        )
        
        if not alert_id:
            return jsonify({'error': 'Failed to trigger SOS'}), 500
        
        # Get user info for context
        user = query_db('SELECT phone_number, name FROM users WHERE id = ?', (user_id,), one=True)
        
        if not user:
            logger.error(f"User not found for SOS alert {alert_id}")
            return jsonify({'error': 'User not found'}), 404
        
        logger.warning(f"SOS ALERT TRIGGERED - ID: {alert_id}, User: {user['phone_number']}, Category: {category}, Severity: {severity}")
        
        # Broadcast SOS alert to all connected clients
        socketio.emit('sos_alert', {
            'alert_id': alert_id,
            'user_id': user_id,
            'user_name': user['name'],
            'user_phone': user['phone_number'],
            'category': SOS_CATEGORIES[category],
            'severity': SEVERITY_LEVELS.get(severity, 'Unknown'),
            'severity_level': severity,
            'description': description,
            'location': {'lat': lat, 'lon': lon},
            'timestamp': datetime.now().isoformat(),
            'status': 'active'
        }, broadcast=True)
        
        return jsonify({
            'success': True,
            'alert_id': alert_id,
            'message': 'SOS alert triggered successfully'
        }), 201
    
    except Exception as e:
        logger.error(f"SOS trigger error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/sos/acknowledge/<int:alert_id>', methods=['POST'])
@token_required
def acknowledge_sos(user_id, alert_id):
    """Acknowledge/respond to an SOS alert"""
    try:
        data = request.json
        response = data.get('response', '')
        
        # Update alert status
        execute_db(
            'UPDATE sos_alerts SET status = ?, responder_id = ? WHERE id = ?',
            ('acknowledged', user_id, alert_id)
        )
        
        # Record acknowledgment
        execute_db(
            'INSERT INTO alert_acknowledgments (alert_id, user_id, response) VALUES (?, ?, ?)',
            (alert_id, user_id, response)
        )
        
        alert = query_db('SELECT * FROM sos_alerts WHERE id = ?', (alert_id,), one=True)
        responder = query_db('SELECT name FROM users WHERE id = ?', (user_id,), one=True)
        
        if not responder:
            logger.error(f"Responder not found for alert {alert_id}")
            return jsonify({'error': 'Responder not found'}), 404
        
        logger.info(f"SOS Alert {alert_id} acknowledged by {responder['name']}")
        
        # Notify all clients
        socketio.emit('sos_acknowledged', {
            'alert_id': alert_id,
            'responder_id': user_id,
            'responder_name': responder['name'],
            'response': response,
            'timestamp': datetime.now().isoformat()
        }, broadcast=True)
        
        return jsonify({
            'success': True,
            'message': 'SOS alert acknowledged'
        }), 200
    
    except Exception as e:
        logger.error(f"SOS acknowledgment error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/sos/alerts', methods=['GET'])
@token_required
def get_active_alerts(user_id):
    """Get all active SOS alerts"""
    try:
        alerts = query_db(
            'SELECT * FROM sos_alerts WHERE status = ? ORDER BY timestamp DESC LIMIT 50',
            ('active',)
        )
        
        alert_list = []
        if alerts:
            for alert in alerts:
                user = query_db('SELECT name, phone_number FROM users WHERE id = ?', (alert['user_id'],), one=True)
                if not user:
                    continue
                alert_list.append({
                    'id': alert['id'],
                    'user_id': alert['user_id'],
                    'user_name': user['name'],
                    'user_phone': user['phone_number'],
                'category': alert['category'],
                'severity': SEVERITY_LEVELS.get(alert['severity'], 'Unknown'),
                'description': alert['description'],
                'location': {'lat': alert['location_lat'], 'lon': alert['location_lon']},
                'timestamp': alert['timestamp'],
                'status': alert['status']
            })
        
        return jsonify({'alerts': alert_list}), 200
    
    except Exception as e:
        logger.error(f"Alert retrieval error: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# ENVIRONMENTAL SENSOR DATA API
# ============================================================================

@app.route('/api/sensors/data', methods=['POST'])
@token_required
def submit_sensor_data(user_id):
    """Submit environmental sensor readings"""
    try:
        data = request.json
        
        temp = data.get('temperature')
        humidity = data.get('humidity')
        battery_voltage = data.get('battery_voltage')
        solar_voltage = data.get('solar_panel_voltage')
        
        execute_db(
            'INSERT INTO environmental_data (user_id, temperature_celsius, humidity_percent, battery_voltage, solar_panel_voltage) VALUES (?, ?, ?, ?, ?)',
            (user_id, temp, humidity, battery_voltage, solar_voltage)
        )
        
        logger.debug(f"Sensor data recorded for user {user_id}: Temp={temp}C, Humidity={humidity}%, Battery={battery_voltage}V")
        
        # Broadcast sensor data
        socketio.emit('sensor_data', {
            'user_id': user_id,
            'temperature': temp,
            'humidity': humidity,
            'battery_voltage': battery_voltage,
            'solar_panel_voltage': solar_voltage,
            'timestamp': datetime.now().isoformat()
        }, broadcast=True)
        
        return jsonify({'success': True, 'message': 'Sensor data recorded'}), 201
    
    except Exception as e:
        logger.error(f"Sensor data submission error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/sensors/data/<int:user_id>', methods=['GET'])
def get_sensor_data(user_id):
    """Get latest sensor data for a user (for dashboard)"""
    try:
        data = query_db(
            'SELECT * FROM environmental_data WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1',
            (user_id,),
            one=True
        )
        
        if not data:
            return jsonify({'error': 'No sensor data found'}), 404
        
        return jsonify({
            'user_id': data['user_id'],
            'temperature': data['temperature_celsius'],
            'humidity': data['humidity_percent'],
            'battery_voltage': data['battery_voltage'],
            'solar_panel_voltage': data['solar_panel_voltage'],
            'timestamp': data['timestamp']
        }), 200
    
    except Exception as e:
        logger.error(f"Sensor data retrieval error: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# MESSAGE & BROADCAST API
# ============================================================================

@app.route('/api/messages/send', methods=['POST'])
@token_required
def send_message(user_id):
    """Send a one-to-one message"""
    try:
        data = request.json
        
        if not data.get('recipient_id') or not data.get('message'):
            return jsonify({'error': 'Missing required fields'}), 400
        
        recipient_id = data['recipient_id']
        message_text = data['message']
        
        msg_id = execute_db(
            'INSERT INTO messages (sender_id, recipient_id, message_text, message_type) VALUES (?, ?, ?, ?)',
            (user_id, recipient_id, message_text, 'text')
        )
        
        sender = query_db('SELECT name FROM users WHERE id = ?', (user_id,), one=True)
        
        if sender:
            socketio.emit('new_message', {
                'message_id': msg_id,
                'sender_id': user_id,
                'sender_name': sender['name'],
                'recipient_id': recipient_id,
                'message': message_text,
                'timestamp': datetime.now().isoformat()
            })
        
        return jsonify({
            'success': True,
            'message_id': msg_id,
            'message': 'Message sent'
        }), 201
    
    except Exception as e:
        logger.error(f"Message sending error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/broadcast/send', methods=['POST'])
@token_required
def send_broadcast(user_id):
    """Send a broadcast message to a group"""
    try:
        data = request.json
        
        if not data.get('group_id') or not data.get('message'):
            return jsonify({'error': 'Missing required fields'}), 400
        
        group_id = data['group_id']
        message_text = data['message']
        
        msg_id = execute_db(
            'INSERT INTO messages (sender_id, broadcast_group_id, message_text, message_type) VALUES (?, ?, ?, ?)',
            (user_id, group_id, message_text, 'text')
        )
        
        sender = query_db('SELECT name FROM users WHERE id = ?', (user_id,), one=True)
        group = query_db('SELECT group_name FROM broadcast_groups WHERE id = ?', (group_id,), one=True)
        
        if sender and group:
            socketio.emit('broadcast_message', {
                'message_id': msg_id,
                'sender_id': user_id,
                'sender_name': sender['name'],
                'group_id': group_id,
                'group_name': group['group_name'],
                'message': message_text,
                'timestamp': datetime.now().isoformat()
            }, broadcast=True)
        
        return jsonify({
            'success': True,
            'message_id': msg_id,
            'message': 'Broadcast sent'
        }), 201
    
    except Exception as e:
        logger.error(f"Broadcast sending error: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# SOCKETIO HANDLERS (Real-time Communication)
# ============================================================================

@socketio.on('connect')
def handle_connect():
    """Handle user connection"""
    logger.info(f"Client connected: {request.sid}")
    socketio.emit('connection_response', {'status': 'Connected to NexAlert'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle user disconnection"""
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('user_online')
def handle_user_online(data):
    """Mark user as online"""
    try:
        user_id = data.get('user_id')
        if user_id:
            execute_db('UPDATE users SET online_status = 1, last_seen = CURRENT_TIMESTAMP WHERE id = ?', (user_id,))
            socketio.emit('user_status_change', {
                'user_id': user_id,
                'status': 'online',
                'timestamp': datetime.now().isoformat()
            }, broadcast=True)
            logger.info(f"User {user_id} marked as online")
    except Exception as e:
        logger.error(f"User online handler error: {e}")

@socketio.on('user_offline')
def handle_user_offline(data):
    """Mark user as offline"""
    try:
        user_id = data.get('user_id')
        if user_id:
            execute_db('UPDATE users SET online_status = 0, last_seen = CURRENT_TIMESTAMP WHERE id = ?', (user_id,))
            socketio.emit('user_status_change', {
                'user_id': user_id,
                'status': 'offline',
                'timestamp': datetime.now().isoformat()
            }, broadcast=True)
            logger.info(f"User {user_id} marked as offline")
    except Exception as e:
        logger.error(f"User offline handler error: {e}")

@socketio.on('chat_message')
def handle_chat_message(data):
    """Handle real-time chat messages"""
    try:
        sender_id = data.get('sender_id')
        recipient_id = data.get('recipient_id')
        message = data.get('message')
        
        if sender_id and recipient_id and message:
            msg_id = execute_db(
                'INSERT INTO messages (sender_id, recipient_id, message_text, message_type) VALUES (?, ?, ?, ?)',
                (sender_id, recipient_id, message, 'text')
            )
            
            socketio.emit('chat_message', {
                'message_id': msg_id,
                'sender_id': sender_id,
                'recipient_id': recipient_id,
                'message': message,
                'timestamp': datetime.now().isoformat()
            })
    except Exception as e:
        logger.error(f"Chat message handler error: {e}")

# ============================================================================
# WEB ROUTES
# ============================================================================

@app.route('/')
def index():
    """Serve phone interface by default"""
    return render_template('phone.html')

@app.route('/dashboard')
def dashboard():
    """Serve dashboard"""
    return render_template('dashboard.html')

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'NexAlert v3.0',
        'timestamp': datetime.now().isoformat()
    }), 200

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    # Initialize database if not exists
    if not os.path.exists('database/nexalert.db'):
        logger.info("Creating new database...")
        init_db()
    
    # Create logs directory if not exists
    os.makedirs('logs', exist_ok=True)
    
    logger.info("=" * 80)
    logger.info("NexAlert v3.0 - Backend Server Starting")
    logger.info("=" * 80)
    logger.info(f"Started at: {datetime.now()}")
    logger.info("Flask-SocketIO Server Ready for Real-time Communication")
    
    # Run with SocketIO
    socketio.run(
        app,
        host='0.0.0.0',
        port=5000,
        debug=os.getenv('FLASK_ENV') == 'development',
        allow_unsafe_werkzeug=True
    )
