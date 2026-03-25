"""
NexAlert v3.0 - Main Backend Application
Unified Flask app serving both dashboard and phone interfaces
"""

from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
from datetime import datetime, timedelta
import os
import json
import logging

from models import db, User, Contact, Message, Alert, EnvironmentalData, BroadcastGroup, GroupMember

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'nexalert_secret_2025_v3'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database/nexalert.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/nexalert.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Alert types configuration
ALERT_TYPES = {
    'medical': {'color': '#ff4444', 'icon': '🏥', 'label': 'Medical Emergency'},
    'fire': {'color': '#ff6600', 'icon': '🔥', 'label': 'Fire'},
    'flood': {'color': '#0066ff', 'icon': '🌊', 'label': 'Flood'},
    'earthquake': {'color': '#996600', 'icon': '🌋', 'label': 'Earthquake'},
    'accident': {'color': '#ff9900', 'icon': '🚗', 'label': 'Accident'},
    'violence': {'color': '#990000', 'icon': '⚠️', 'label': 'Violence/Threat'},
    'natural_disaster': {'color': '#666666', 'icon': '🌪️', 'label': 'Natural Disaster'},
    'power_outage': {'color': '#ffcc00', 'icon': '⚡', 'label': 'Power Outage'},
    'gas_leak': {'color': '#cc00cc', 'icon': '💨', 'label': 'Gas Leak'},
    'missing_person': {'color': '#00ccff', 'icon': '🔍', 'label': 'Missing Person'},
    'animal_attack': {'color': '#cc6600', 'icon': '🐾', 'label': 'Animal Attack'},
    'other': {'color': '#888888', 'icon': '📢', 'label': 'Other Emergency'}
}


# ============================================
# DATABASE INITIALIZATION
# ============================================

@app.before_first_request
def create_tables():
    """Create database tables on first request"""
    db.create_all()
    logger.info("Database tables created")


# ============================================
# HELPER FUNCTIONS
# ============================================

def get_client_ip():
    """Get the real IP address of the client"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0]
    return request.remote_addr


def update_user_status(user_id, is_online=True):
    """Update user's online status and last seen"""
    user = User.query.get(user_id)
    if user:
        user.is_online = is_online
        user.last_seen = datetime.utcnow()
        db.session.commit()
        
        # Broadcast status update to all clients
        socketio.emit('user_status_changed', {
            'user_id': user_id,
            'is_online': is_online,
            'last_seen': user.last_seen.isoformat()
        }, broadcast=True)


def sync_contacts_to_network(user_id, contacts_data):
    """
    Sync user's phone contacts and check who's on the network
    contacts_data: list of {'name': str, 'phone': str}
    """
    user = User.query.get(user_id)
    if not user:
        return {'error': 'User not found'}
    
    synced_contacts = []
    for contact_data in contacts_data:
        phone = contact_data.get('phone', '').strip()
        name = contact_data.get('name', 'Unknown').strip()
        
        if not phone:
            continue
        
        # Check if this contact is already in our database
        existing_contact = Contact.query.filter_by(
            user_id=user_id,
            contact_phone=phone
        ).first()
        
        if existing_contact:
            # Update name if changed
            existing_contact.contact_name = name
        else:
            # Create new contact entry
            existing_contact = Contact(
                user_id=user_id,
                contact_name=name,
                contact_phone=phone
            )
            db.session.add(existing_contact)
        
        # Check if this contact is registered on the network
        network_user = User.query.filter_by(phone_number=phone).first()
        if network_user:
            existing_contact.is_on_network = True
            existing_contact.network_user_id = network_user.id
        else:
            existing_contact.is_on_network = False
            existing_contact.network_user_id = None
        
        synced_contacts.append(existing_contact.to_dict())
    
    db.session.commit()
    logger.info(f"Synced {len(synced_contacts)} contacts for user {user_id}")
    
    return {'contacts': synced_contacts, 'count': len(synced_contacts)}


# ============================================
# AUTHENTICATION & USER MANAGEMENT
# ============================================

@app.route('/api/register', methods=['POST'])
def register():
    """Register a new user to the network"""
    data = request.get_json()
    
    full_name = data.get('full_name', '').strip()
    phone_number = data.get('phone_number', '').strip()
    username = data.get('username', '').strip()
    
    if not all([full_name, phone_number, username]):
        return jsonify({'error': 'Name, phone number, and username are required'}), 400
    
    # Check if user already exists
    existing_user = User.query.filter(
        (User.phone_number == phone_number) | (User.username == username)
    ).first()
    
    if existing_user:
        # User rejoining - update their info
        existing_user.full_name = full_name
        existing_user.ip_address = get_client_ip()
        existing_user.is_online = True
        existing_user.last_seen = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"User {username} rejoined the network")
        return jsonify({
            'message': 'Welcome back!',
            'user': existing_user.to_dict()
        }), 200
    
    # Create new user
    new_user = User(
        username=username,
        full_name=full_name,
        phone_number=phone_number,
        ip_address=get_client_ip(),
        is_online=True
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    logger.info(f"New user registered: {username} ({phone_number})")
    
    # Broadcast new user to all clients
    socketio.emit('new_user_joined', new_user.to_dict(), broadcast=True)
    
    return jsonify({
        'message': 'Successfully joined NexAlert network',
        'user': new_user.to_dict()
    }), 201


@app.route('/api/users', methods=['GET'])
def get_users():
    """Get all registered users"""
    users = User.query.all()
    return jsonify({
        'users': [u.to_dict() for u in users],
        'count': len(users),
        'online_count': len([u for u in users if u.is_online])
    })


@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """Get specific user details"""
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict())


@app.route('/api/users/<int:user_id>/location', methods=['POST'])
def update_location(user_id):
    """Update user's GPS location"""
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    
    user.latitude = data.get('latitude')
    user.longitude = data.get('longitude')
    user.last_seen = datetime.utcnow()
    db.session.commit()
    
    # Broadcast location update
    socketio.emit('location_updated', {
        'user_id': user_id,
        'latitude': user.latitude,
        'longitude': user.longitude
    }, broadcast=True)
    
    return jsonify({'message': 'Location updated'})


# ============================================
# CONTACTS MANAGEMENT
# ============================================

@app.route('/api/users/<int:user_id>/contacts/sync', methods=['POST'])
def sync_contacts(user_id):
    """Sync phone contacts to the network"""
    data = request.get_json()
    contacts_data = data.get('contacts', [])
    
    result = sync_contacts_to_network(user_id, contacts_data)
    return jsonify(result)


@app.route('/api/users/<int:user_id>/contacts', methods=['GET'])
def get_contacts(user_id):
    """Get user's synced contacts"""
    contacts = Contact.query.filter_by(user_id=user_id).all()
    
    return jsonify({
        'contacts': [c.to_dict() for c in contacts],
        'total': len(contacts),
        'on_network': len([c for c in contacts if c.is_on_network])
    })


# ============================================
# MESSAGING
# ============================================

@app.route('/api/messages', methods=['POST'])
def send_message():
    """Send a message (one-to-one or broadcast)"""
    data = request.get_json()
    
    sender_id = data.get('sender_id')
    receiver_id = data.get('receiver_id')  # None for broadcast
    content = data.get('content', '').strip()
    is_broadcast = data.get('is_broadcast', False)
    
    if not content:
        return jsonify({'error': 'Message content is required'}), 400
    
    message = Message(
        sender_id=sender_id,
        receiver_id=receiver_id,
        content=content,
        is_broadcast=is_broadcast
    )
    
    db.session.add(message)
    db.session.commit()
    
    # Broadcast message via WebSocket
    socketio.emit('new_message', message.to_dict(), broadcast=True)
    
    logger.info(f"Message sent from {sender_id} to {receiver_id or 'broadcast'}")
    
    return jsonify({
        'message': 'Message sent',
        'data': message.to_dict()
    }), 201


@app.route('/api/messages', methods=['GET'])
def get_messages():
    """Get messages (with optional filtering)"""
    user_id = request.args.get('user_id', type=int)
    is_broadcast = request.args.get('broadcast', type=bool)
    
    query = Message.query
    
    if user_id:
        query = query.filter(
            (Message.sender_id == user_id) | (Message.receiver_id == user_id)
        )
    
    if is_broadcast is not None:
        query = query.filter_by(is_broadcast=is_broadcast)
    
    messages = query.order_by(Message.sent_at.desc()).limit(100).all()
    
    return jsonify({
        'messages': [m.to_dict() for m in messages],
        'count': len(messages)
    })


# ============================================
# ALERTS/SOS
# ============================================

@app.route('/api/alerts', methods=['POST'])
def create_alert():
    """Create a new SOS alert"""
    data = request.get_json()
    
    user_id = data.get('user_id')
    alert_type = data.get('alert_type')
    severity = data.get('severity', 'high')
    description = data.get('description', '')
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    
    if alert_type not in ALERT_TYPES:
        return jsonify({'error': 'Invalid alert type'}), 400
    
    alert = Alert(
        user_id=user_id,
        alert_type=alert_type,
        severity=severity,
        description=description,
        latitude=latitude,
        longitude=longitude
    )
    
    db.session.add(alert)
    db.session.commit()
    
    # Broadcast alert immediately
    socketio.emit('new_alert', alert.to_dict(), broadcast=True)
    
    logger.warning(f"NEW ALERT: {alert_type} from user {user_id} at ({latitude}, {longitude})")
    
    return jsonify({
        'message': 'Alert created',
        'alert': alert.to_dict()
    }), 201


@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    """Get all alerts (with optional filtering)"""
    is_resolved = request.args.get('resolved', type=bool)
    alert_type = request.args.get('type')
    
    query = Alert.query
    
    if is_resolved is not None:
        query = query.filter_by(is_resolved=is_resolved)
    
    if alert_type:
        query = query.filter_by(alert_type=alert_type)
    
    alerts = query.order_by(Alert.created_at.desc()).all()
    
    return jsonify({
        'alerts': [a.to_dict() for a in alerts],
        'count': len(alerts),
        'alert_types': ALERT_TYPES
    })


@app.route('/api/alerts/<int:alert_id>/resolve', methods=['POST'])
def resolve_alert(alert_id):
    """Mark an alert as resolved"""
    alert = Alert.query.get_or_404(alert_id)
    alert.is_resolved = True
    alert.resolved_at = datetime.utcnow()
    db.session.commit()
    
    socketio.emit('alert_resolved', alert.to_dict(), broadcast=True)
    
    return jsonify({'message': 'Alert resolved', 'alert': alert.to_dict()})


@app.route('/api/alert-types', methods=['GET'])
def get_alert_types():
    """Get all available alert types"""
    return jsonify(ALERT_TYPES)


# ============================================
# ENVIRONMENTAL DATA
# ============================================

@app.route('/api/environmental', methods=['POST'])
def log_environmental_data():
    """Log environmental sensor readings"""
    data = request.get_json()
    
    env_data = EnvironmentalData(
        temperature=data.get('temperature'),
        humidity=data.get('humidity'),
        air_quality=data.get('air_quality'),
        uv_index=data.get('uv_index'),
        battery_voltage=data.get('battery_voltage'),
        solar_voltage=data.get('solar_voltage')
    )
    
    db.session.add(env_data)
    db.session.commit()
    
    # Broadcast to dashboard
    socketio.emit('environmental_update', env_data.to_dict(), broadcast=True)
    
    return jsonify(env_data.to_dict()), 201


@app.route('/api/environmental', methods=['GET'])
def get_environmental_data():
    """Get recent environmental data"""
    limit = request.args.get('limit', 100, type=int)
    data = EnvironmentalData.query.order_by(EnvironmentalData.timestamp.desc()).limit(limit).all()
    
    return jsonify({
        'data': [d.to_dict() for d in data],
        'count': len(data)
    })


# ============================================
# BROADCAST GROUPS
# ============================================

@app.route('/api/groups', methods=['POST'])
def create_group():
    """Create a broadcast group"""
    data = request.get_json()
    
    group = BroadcastGroup(
        name=data.get('name'),
        description=data.get('description', ''),
        created_by=data.get('created_by')
    )
    
    db.session.add(group)
    db.session.commit()
    
    return jsonify(group.to_dict()), 201


@app.route('/api/groups', methods=['GET'])
def get_groups():
    """Get all broadcast groups"""
    groups = BroadcastGroup.query.all()
    return jsonify({'groups': [g.to_dict() for g in groups]})


@app.route('/api/groups/<int:group_id>/members', methods=['POST'])
def add_group_member(group_id):
    """Add a member to a group"""
    data = request.get_json()
    
    member = GroupMember(
        group_id=group_id,
        user_id=data.get('user_id')
    )
    
    db.session.add(member)
    db.session.commit()
    
    return jsonify({'message': 'Member added'}), 201


# ============================================
# WEBSOCKET EVENTS
# ============================================

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    logger.info(f"Client connected: {request.sid}")
    emit('connection_established', {'message': 'Connected to NexAlert'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    logger.info(f"Client disconnected: {request.sid}")


@socketio.on('user_online')
def handle_user_online(data):
    """User came online"""
    user_id = data.get('user_id')
    if user_id:
        update_user_status(user_id, is_online=True)


@socketio.on('user_offline')
def handle_user_offline(data):
    """User went offline"""
    user_id = data.get('user_id')
    if user_id:
        update_user_status(user_id, is_online=False)


@socketio.on('location_broadcast')
def handle_location_broadcast(data):
    """Broadcast user location to dashboard"""
    emit('location_updated', data, broadcast=True)


# ============================================
# MAIN ROUTES
# ============================================

@app.route('/')
def index():
    """Landing page - redirect to phone interface"""
    return redirect(url_for('phone_interface'))


@app.route('/phone')
def phone_interface():
    """Phone/mobile interface"""
    return render_template('phone.html')


@app.route('/dashboard')
def dashboard():
    """Government/admin dashboard"""
    return render_template('dashboard.html')


@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'users_online': User.query.filter_by(is_online=True).count(),
        'total_users': User.query.count(),
        'active_alerts': Alert.query.filter_by(is_resolved=False).count()
    })


# ============================================
# RUN APPLICATION
# ============================================

if __name__ == '__main__':
    # Create database directory if it doesn't exist
    os.makedirs('database', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    # Run with SocketIO
    socketio.run(
        app,
        host='0.0.0.0',
        port=5000,
        debug=False,
        use_reloader=False,
        allow_unsafe_werkzeug=True
    )
