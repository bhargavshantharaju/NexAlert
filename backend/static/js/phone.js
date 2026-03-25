// NexAlert Phone Interface - JavaScript

const API_BASE = window.location.origin;
let socket;
let currentUser = null;
let selectedAlertType = null;
let allUsers = [];
let userContacts = [];

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    // Check if user is already registered
    const storedUser = localStorage.getItem('nexalert_user');
    if (storedUser) {
        currentUser = JSON.parse(storedUser);
        showMainScreen();
    }
    
    // Setup event listeners
    setupEventListeners();
    
    // Initialize WebSocket
    initializeSocket();
    
    // Fetch alert types
    fetchAlertTypes();
});

function setupEventListeners() {
    // Registration
    document.getElementById('registration-form').addEventListener('submit', handleRegistration);
    
    // Tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });
    
    // Messaging
    document.getElementById('btn-send-message').addEventListener('click', sendMessage);
    document.getElementById('message-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
    document.getElementById('btn-refresh-users').addEventListener('click', fetchUsers);
    
    // SOS
    document.getElementById('btn-send-sos').addEventListener('click', sendSOSAlert);
    document.getElementById('btn-cancel-sos').addEventListener('click', cancelSOS);
    
    // Contacts
    document.getElementById('btn-sync-contacts').addEventListener('click', syncContacts);
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => filterContacts(btn.dataset.filter));
    });
    
    // Logout
    document.getElementById('btn-logout').addEventListener('click', logout);
}

// ============================================
// WEBSOCKET
// ============================================

function initializeSocket() {
    socket = io(API_BASE);
    
    socket.on('connect', () => {
        console.log('✅ Connected to NexAlert server');
        if (currentUser) {
            socket.emit('user_online', { user_id: currentUser.id });
        }
    });
    
    socket.on('disconnect', () => {
        console.log('❌ Disconnected from server');
    });
    
    socket.on('new_message', (message) => {
        displayMessage(message);
    });
    
    socket.on('new_alert', (alert) => {
        showAlertNotification(alert);
    });
    
    socket.on('user_status_changed', (data) => {
        updateUserStatus(data);
    });
    
    socket.on('new_user_joined', (user) => {
        showNotification(`${user.full_name} joined the network!`);
        fetchUsers();
    });
    
    socket.on('location_updated', (data) => {
        // Handle location updates if needed
        console.log('Location updated:', data);
    });
}

// ============================================
// REGISTRATION
// ============================================

async function handleRegistration(e) {
    e.preventDefault();
    
    const fullName = document.getElementById('full-name').value.trim();
    const phoneNumber = document.getElementById('phone-number').value.trim();
    const username = document.getElementById('username').value.trim();
    
    if (!fullName || !phoneNumber || !username) {
        showNotification('Please fill in all fields', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                full_name: fullName,
                phone_number: phoneNumber,
                username: username
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            currentUser = data.user;
            localStorage.setItem('nexalert_user', JSON.stringify(currentUser));
            
            showNotification(data.message, 'success');
            showMainScreen();
            
            // Start sending location updates if available
            startLocationTracking();
        } else {
            showNotification(data.error || 'Registration failed', 'error');
        }
    } catch (error) {
        console.error('Registration error:', error);
        showNotification('Network error. Please try again.', 'error');
    }
}

function showMainScreen() {
    document.getElementById('registration-screen').classList.remove('active');
    document.getElementById('main-screen').classList.add('active');
    
    // Update UI with user info
    document.getElementById('display-name').textContent = currentUser.full_name;
    
    // Load initial data
    fetchUsers();
    fetchMessages();
    loadContacts();
}

// ============================================
// TABS
// ============================================

function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });
    
    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${tabName}-tab`).classList.add('active');
}

// ============================================
// USERS
// ============================================

async function fetchUsers() {
    try {
        const response = await fetch(`${API_BASE}/api/users`);
        const data = await response.json();
        
        allUsers = data.users;
        updateRecipientSelect();
        
        console.log(`📊 ${data.online_count}/${data.count} users online`);
    } catch (error) {
        console.error('Error fetching users:', error);
    }
}

function updateRecipientSelect() {
    const select = document.getElementById('message-recipient');
    
    // Clear existing options except broadcast
    while (select.options.length > 1) {
        select.remove(1);
    }
    
    // Add online users
    allUsers
        .filter(u => u.id !== currentUser.id && u.is_online)
        .forEach(user => {
            const option = document.createElement('option');
            option.value = user.id;
            option.textContent = `${user.full_name} (${user.username})`;
            select.appendChild(option);
        });
}

function updateUserStatus(data) {
    const user = allUsers.find(u => u.id === data.user_id);
    if (user) {
        user.is_online = data.is_online;
        user.last_seen = data.last_seen;
        updateRecipientSelect();
    }
}

// ============================================
// MESSAGING
// ============================================

async function sendMessage() {
    const input = document.getElementById('message-input');
    const content = input.value.trim();
    
    if (!content) return;
    
    const recipientSelect = document.getElementById('message-recipient');
    const receiverId = recipientSelect.value === 'broadcast' ? null : parseInt(recipientSelect.value);
    
    try {
        const response = await fetch(`${API_BASE}/api/messages`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                sender_id: currentUser.id,
                receiver_id: receiverId,
                content: content,
                is_broadcast: receiverId === null
            })
        });
        
        if (response.ok) {
            input.value = '';
            // Message will be displayed via WebSocket
        } else {
            showNotification('Failed to send message', 'error');
        }
    } catch (error) {
        console.error('Error sending message:', error);
        showNotification('Network error', 'error');
    }
}

async function fetchMessages() {
    try {
        const response = await fetch(`${API_BASE}/api/messages?user_id=${currentUser.id}`);
        const data = await response.json();
        
        const container = document.getElementById('messages-container');
        container.innerHTML = '';
        
        data.messages.reverse().forEach(message => {
            displayMessage(message);
        });
        
        // Scroll to bottom
        container.scrollTop = container.scrollHeight;
    } catch (error) {
        console.error('Error fetching messages:', error);
    }
}

function displayMessage(message) {
    const container = document.getElementById('messages-container');
    const div = document.createElement('div');
    
    const isSent = message.sender && message.sender.id === currentUser.id;
    const isBroadcast = message.is_broadcast;
    
    div.className = `message ${isSent ? 'sent' : 'received'} ${isBroadcast ? 'broadcast' : ''}`;
    
    let html = '';
    if (!isSent && message.sender) {
        html += `<div class="message-sender">${message.sender.full_name}</div>`;
    }
    html += `<div class="message-text">${escapeHtml(message.content)}</div>`;
    html += `<div class="message-time">${formatTime(message.sent_at)}</div>`;
    
    div.innerHTML = html;
    container.appendChild(div);
    
    // Scroll to bottom
    container.scrollTop = container.scrollHeight;
}

// ============================================
// SOS/ALERTS
// ============================================

let alertTypes = {};

async function fetchAlertTypes() {
    try {
        const response = await fetch(`${API_BASE}/api/alert-types`);
        alertTypes = await response.json();
        renderSOSGrid();
    } catch (error) {
        console.error('Error fetching alert types:', error);
    }
}

function renderSOSGrid() {
    const grid = document.getElementById('sos-grid');
    grid.innerHTML = '';
    
    Object.entries(alertTypes).forEach(([type, config]) => {
        const card = document.createElement('div');
        card.className = 'sos-card';
        card.dataset.type = type;
        card.innerHTML = `
            <div class="sos-icon">${config.icon}</div>
            <div class="sos-label">${config.label}</div>
        `;
        
        card.addEventListener('click', () => selectSOSType(type));
        grid.appendChild(card);
    });
}

function selectSOSType(type) {
    selectedAlertType = type;
    
    // Highlight selected card
    document.querySelectorAll('.sos-card').forEach(card => {
        card.classList.toggle('active', card.dataset.type === type);
    });
    
    // Show details form
    document.getElementById('sos-details-form').style.display = 'block';
}

function cancelSOS() {
    selectedAlertType = null;
    document.querySelectorAll('.sos-card').forEach(card => {
        card.classList.remove('active');
    });
    document.getElementById('sos-details-form').style.display = 'none';
    document.getElementById('sos-description').value = '';
}

async function sendSOSAlert() {
    if (!selectedAlertType) {
        showNotification('Please select an emergency type', 'error');
        return;
    }
    
    const description = document.getElementById('sos-description').value.trim();
    
    // Get current location
    let latitude = null;
    let longitude = null;
    
    if (navigator.geolocation) {
        try {
            const position = await new Promise((resolve, reject) => {
                navigator.geolocation.getCurrentPosition(resolve, reject);
            });
            latitude = position.coords.latitude;
            longitude = position.coords.longitude;
        } catch (error) {
            console.error('Error getting location:', error);
        }
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/alerts`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: currentUser.id,
                alert_type: selectedAlertType,
                severity: 'high',
                description: description,
                latitude: latitude,
                longitude: longitude
            })
        });
        
        if (response.ok) {
            showNotification('🚨 Emergency alert sent!', 'success');
            cancelSOS();
        } else {
            showNotification('Failed to send alert', 'error');
        }
    } catch (error) {
        console.error('Error sending alert:', error);
        showNotification('Network error', 'error');
    }
}

function showAlertNotification(alert) {
    const config = alertTypes[alert.alert_type] || {};
    showNotification(
        `${config.icon} ${config.label} alert from ${alert.user.full_name}!`,
        'warning'
    );
}

// ============================================
// CONTACTS
// ============================================

async function syncContacts() {
    // In a real app, this would use the Contacts API
    // For demo, we'll use mock data or request permission
    
    showNotification('📱 Requesting contact access...', 'info');
    
    // Mock contacts for demo
    const mockContacts = [
        { name: 'Arjun Kumar', phone: '+919876543210' },
        { name: 'Priya Sharma', phone: '+919876543211' },
        { name: 'Rahul Gupta', phone: '+919876543212' },
        { name: 'Sneha Patel', phone: '+919876543213' },
        { name: 'Vikram Singh', phone: '+919876543214' }
    ];
    
    try {
        const response = await fetch(`${API_BASE}/api/users/${currentUser.id}/contacts/sync`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ contacts: mockContacts })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification(`✅ Synced ${data.count} contacts`, 'success');
            loadContacts();
        } else {
            showNotification('Failed to sync contacts', 'error');
        }
    } catch (error) {
        console.error('Error syncing contacts:', error);
        showNotification('Network error', 'error');
    }
}

async function loadContacts() {
    try {
        const response = await fetch(`${API_BASE}/api/users/${currentUser.id}/contacts`);
        const data = await response.json();
        
        userContacts = data.contacts;
        renderContacts(userContacts);
    } catch (error) {
        console.error('Error loading contacts:', error);
    }
}

function renderContacts(contacts) {
    const list = document.getElementById('contacts-list');
    
    if (contacts.length === 0) {
        list.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">👥</div>
                <p>No contacts yet</p>
                <p>Sync your phone contacts to see who's on the network</p>
            </div>
        `;
        return;
    }
    
    list.innerHTML = '';
    
    contacts.forEach(contact => {
        const div = document.createElement('div');
        div.className = 'contact-item';
        
        const isOnline = contact.network_user && contact.network_user.is_online;
        const isOnNetwork = contact.is_on_network;
        
        let statusHtml = '<span class="contact-status">Not on network</span>';
        if (isOnNetwork && isOnline) {
            statusHtml = '<span class="contact-status online">🟢 Online</span>';
        } else if (isOnNetwork) {
            statusHtml = '<span class="contact-status network">On Network</span>';
        }
        
        div.innerHTML = `
            <div class="contact-avatar">👤</div>
            <div class="contact-info">
                <div class="contact-name">${escapeHtml(contact.contact_name)}</div>
                <div class="contact-phone">${contact.contact_phone}</div>
            </div>
            ${statusHtml}
        `;
        
        list.appendChild(div);
    });
}

function filterContacts(filter) {
    // Update filter buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.filter === filter);
    });
    
    // Filter contacts
    let filtered = userContacts;
    
    if (filter === 'online') {
        filtered = userContacts.filter(c => c.network_user && c.network_user.is_online);
    } else if (filter === 'network') {
        filtered = userContacts.filter(c => c.is_on_network);
    }
    
    renderContacts(filtered);
}

// ============================================
// LOCATION TRACKING
// ============================================

function startLocationTracking() {
    if (!navigator.geolocation) {
        console.log('Geolocation not supported');
        return;
    }
    
    // Update location every 30 seconds
    setInterval(() => {
        navigator.geolocation.getCurrentPosition(
            (position) => {
                updateLocation(position.coords.latitude, position.coords.longitude);
            },
            (error) => {
                console.error('Location error:', error);
            }
        );
    }, 30000);
    
    // Initial location update
    navigator.geolocation.getCurrentPosition(
        (position) => {
            updateLocation(position.coords.latitude, position.coords.longitude);
        }
    );
}

async function updateLocation(lat, lng) {
    try {
        await fetch(`${API_BASE}/api/users/${currentUser.id}/location`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ latitude: lat, longitude: lng })
        });
    } catch (error) {
        console.error('Error updating location:', error);
    }
}

// ============================================
// UTILITIES
// ============================================

function logout() {
    if (confirm('Are you sure you want to leave the network?')) {
        if (socket) {
            socket.emit('user_offline', { user_id: currentUser.id });
            socket.disconnect();
        }
        
        localStorage.removeItem('nexalert_user');
        location.reload();
    }
}

function showNotification(message, type = 'info') {
    // Simple alert for now - could be replaced with toast notifications
    console.log(`[${type.toUpperCase()}] ${message}`);
    
    // You can implement a nicer toast notification system here
    if (type === 'error') {
        alert(`❌ ${message}`);
    } else if (type === 'success') {
        alert(`✅ ${message}`);
    } else if (type === 'warning') {
        alert(`⚠️ ${message}`);
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatTime(isoString) {
    if (!isoString) return '';
    const date = new Date(isoString);
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}
