"""
NexAlert v3.0 - Database Models
SQLite database with user management, contacts, messages, and alerts
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    """Registered users in the NexAlert network"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    phone_number = db.Column(db.String(15), unique=True, nullable=False)
    device_id = db.Column(db.String(100), unique=True)  # MAC or device fingerprint
    ip_address = db.Column(db.String(15))
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    is_online = db.Column(db.Boolean, default=False)
    is_dashboard_user = db.Column(db.Boolean, default=False)  # Government/admin access
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy='dynamic')
    received_messages = db.relationship('Message', foreign_keys='Message.receiver_id', backref='receiver', lazy='dynamic')
    alerts = db.relationship('Alert', backref='user', lazy='dynamic')
    contacts = db.relationship('Contact', foreign_keys='Contact.user_id', backref='owner', lazy='dynamic')
    
    def __repr__(self):
        return f'<User {self.username} ({self.phone_number})>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'full_name': self.full_name,
            'phone_number': self.phone_number,
            'ip_address': self.ip_address,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'is_online': self.is_online,
            'is_dashboard_user': self.is_dashboard_user,
            'joined_at': self.joined_at.isoformat() if self.joined_at else None
        }


class Contact(db.Model):
    """User's phone contacts synced to the system"""
    __tablename__ = 'contacts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    contact_name = db.Column(db.String(120), nullable=False)
    contact_phone = db.Column(db.String(15), nullable=False)
    is_on_network = db.Column(db.Boolean, default=False)  # Is this contact registered?
    network_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to the actual network user if they're registered
    network_user = db.relationship('User', foreign_keys=[network_user_id])
    
    def __repr__(self):
        return f'<Contact {self.contact_name} ({self.contact_phone})>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'contact_name': self.contact_name,
            'contact_phone': self.contact_phone,
            'is_on_network': self.is_on_network,
            'network_user': self.network_user.to_dict() if self.network_user else None,
            'added_at': self.added_at.isoformat() if self.added_at else None
        }


class Message(db.Model):
    """Messages between users (one-to-one or broadcast)"""
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Null = broadcast
    content = db.Column(db.Text, nullable=False)
    is_broadcast = db.Column(db.Boolean, default=False)
    is_read = db.Column(db.Boolean, default=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Message from {self.sender_id} to {self.receiver_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'sender': self.sender.to_dict() if self.sender else None,
            'receiver': self.receiver.to_dict() if self.receiver else None,
            'content': self.content,
            'is_broadcast': self.is_broadcast,
            'is_read': self.is_read,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None
        }


class Alert(db.Model):
    """Emergency SOS alerts"""
    __tablename__ = 'alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    alert_type = db.Column(db.String(50), nullable=False)  # medical, fire, flood, etc.
    severity = db.Column(db.String(20), default='high')  # low, medium, high, critical
    description = db.Column(db.Text, nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    is_resolved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<Alert {self.alert_type} from {self.user_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'user': self.user.to_dict() if self.user else None,
            'alert_type': self.alert_type,
            'severity': self.severity,
            'description': self.description,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'is_resolved': self.is_resolved,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None
        }


class EnvironmentalData(db.Model):
    """Sensor readings from the central hub"""
    __tablename__ = 'environmental_data'
    
    id = db.Column(db.Integer, primary_key=True)
    temperature = db.Column(db.Float, nullable=True)
    humidity = db.Column(db.Float, nullable=True)
    air_quality = db.Column(db.Float, nullable=True)  # PM2.5 or gas resistance
    uv_index = db.Column(db.Float, nullable=True)
    battery_voltage = db.Column(db.Float, nullable=True)
    solar_voltage = db.Column(db.Float, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'temperature': self.temperature,
            'humidity': self.humidity,
            'air_quality': self.air_quality,
            'uv_index': self.uv_index,
            'battery_voltage': self.battery_voltage,
            'solar_voltage': self.solar_voltage,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


class BroadcastGroup(db.Model):
    """Groups for broadcast messaging"""
    __tablename__ = 'broadcast_groups'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    creator = db.relationship('User', backref='created_groups')
    members = db.relationship('GroupMember', backref='group', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_by': self.creator.to_dict() if self.creator else None,
            'member_count': self.members.count(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class GroupMember(db.Model):
    """Members of broadcast groups"""
    __tablename__ = 'group_members'
    
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('broadcast_groups.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='group_memberships')
