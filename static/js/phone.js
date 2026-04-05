/**
 * NexAlert v3.0 - Mobile Frontend (Phone Interface)
 * Handles registration, login, chat, SOS alerts, contacts management
 */

// Global state
const app = {
    userId: null,
    token: null,
    selectedSOSCategory: null,
    socket: null,
    userLocation: { lat: null, lon: null },
    currentTab: 'chat'
};

const SOS_CATEGORIES = {
    1: "Medical", 2: "Fire", 3: "Flood", 4: "Earthquake",
    5: "Accident", 6: "Violence", 7: "Natural Disaster",
    8: "Power Outage", 9: "Gas Leak", 10: "Missing Person",
    11: "Animal Attack", 12: "Other"
};

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('NexAlert Mobile App Initializing...');
    
    // Check if already logged in (stored in localStorage)
    const storedToken = localStorage.getItem('nexalert_token');
    const storedUserId = localStorage.getItem('nexalert_user_id');
    
    if (storedToken && storedUserId) {
        app.token = storedToken;
        app.userId = parseInt(storedUserId);
        initializeSocket();
        switchScreen('main');
        loadProfile();
        loadContacts();
    }
    
    // Event listeners
    document.getElementById('registration-form').addEventListener('submit', handleRegistration);
    document.getElementById('login-form').addEventListener('submit', handleLogin);
    document.getElementById('send-message-btn').addEventListener('click', sendMessage);
    document.getElementById('trigger-sos-btn').addEventListener('click', triggerSOS);
    
    // Get initial location
    if (navigator.geolocation) {
        navigator.geolocation.watchPosition(
            position => {
                app.userLocation = {
                    lat: position.coords.latitude,
                    lon: position.coords.longitude
                };
                console.log('Location updated:', app.userLocation);
            },
            error => console.warn('Geolocation error:', error),
            { enableHighAccuracy: true, timeout: 5000, maximumAge: 0 }
        );
    }
});

// ============================================================================
// AUTHENTICATION
// ============================================================================

async function handleRegistration(e) {
    e.preventDefault();
    
    const name = document.getElementById('reg-name').value;
    const phone = document.getElementById('reg-phone').value;
    const email = document.getElementById('reg-email').value;
    const password = document.getElementById('reg-password').value;
    
    try {
        const response = await fetch('/api/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ phone_number: phone, name, email, password })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            app.token = data.token;
            app.userId = data.user_id;
            
            // Store in localStorage for persistence
            localStorage.setItem('nexalert_token', app.token);
            localStorage.setItem('nexalert_user_id', app.userId);
            
            showNotification('Registration successful!', 'success');
            initializeSocket();
            switchScreen('main');
            loadProfile();
        } else {
            showNotification(data.error || 'Registration failed', 'error');
        }
    } catch (error) {
        console.error('Registration error:', error);
        showNotification('Network error', 'error');
    }
}

async function handleLogin(e) {
    e.preventDefault();
    
    const phone = document.getElementById('login-phone').value;
    const password = document.getElementById('login-password').value;
    
    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ phone_number: phone, password })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            app.token = data.token;
            app.userId = data.user_id;
            
            localStorage.setItem('nexalert_token', app.token);
            localStorage.setItem('nexalert_user_id', app.userId);
            
            showNotification('Login successful!', 'success');
            initializeSocket();
            switchScreen('main');
            loadProfile();
        } else {
            showNotification(data.error || 'Login failed', 'error');
        }
    } catch (error) {
        console.error('Login error:', error);
        showNotification('Network error', 'error');
    }
}

function logout() {
    app.token = null;
    app.userId = null;
    localStorage.removeItem('nexalert_token');
    localStorage.removeItem('nexalert_user_id');
    
    if (app.socket) {
        app.socket.disconnect();
    }
    
    switchScreen('registration');
    showNotification('Logged out', 'info');
}

// ============================================================================
// SCREEN & TAB NAVIGATION
// ============================================================================

function switchScreen(screenName) {
    document.querySelectorAll('.screen').forEach(screen => {
        screen.classList.remove('active');
    });
    document.getElementById(screenName + '-screen').classList.add('active');
}

function switchTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab
    document.getElementById(tabName + '-tab').classList.add('active');
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    app.currentTab = tabName;
}

// ============================================================================
// SOCKET.IO REAL-TIME COMMUNICATION
// ============================================================================

function initializeSocket() {
    if (app.socket) return;
    
    app.socket = io();
    
    app.socket.on('connect', () => {
        console.log('Connected to server');
        
        // Mark user as online
        app.socket.emit('user_online', { user_id: app.userId });
    });
    
    app.socket.on('new_message', (data) => {
        if (data.sender_id !== app.userId) { // Don't show own messages
            displayReceivedMessage(data);
        }
    });
    
    app.socket.on('sos_alert', (data) => {
        console.warn('SOS ALERT RECEIVED:', data);
        displaySOSAlert(data);
    });
    
    app.socket.on('sos_acknowledged', (data) => {
        console.log('SOS Acknowledged:', data);
        showNotification(`SOS acknowledged by ${data.responder_name}`, 'info');
    });
    
    app.socket.on('user_status_change', (data) => {
        console.log('User status changed:', data);
        updateContactStatus(data.user_id, data.status);
    });
    
    app.socket.on('sensor_data', (data) => {
        console.log('Sensor data received:', data);
    });
    
    app.socket.on('disconnect', () => {
        console.log('Disconnected from server');
    });
}

// ============================================================================
// CHAT & MESSAGING
// ============================================================================

async function sendMessage() {
    const messageInput = document.getElementById('message-input');
    const message = messageInput.value.trim();
    
    if (!message) return;
    
    try {
        const response = await fetch('/api/messages/send', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${app.token}`
            },
            body: JSON.stringify({
                recipient_id: 1, // TODO: Get selected recipient
                message: message
            })
        });
        
        if (response.ok) {
            messageInput.value = '';
            
            // Add message to chat UI
            const chatList = document.getElementById('chat-list');
            const msgElement = document.createElement('div');
            msgElement.className = 'message sent';
            msgElement.innerHTML = `
                <div class="message-content">${escapeHtml(message)}</div>
                <div class="message-time">${new Date().toLocaleTimeString()}</div>
            `;
            chatList.appendChild(msgElement);
            chatList.scrollTop = chatList.scrollHeight;
        }
    } catch (error) {
        console.error('Send message error:', error);
        showNotification('Failed to send message', 'error');
    }
}

function displayReceivedMessage(data) {
    const chatList = document.getElementById('chat-list');
    const msgElement = document.createElement('div');
    msgElement.className = 'message received';
    msgElement.innerHTML = `
        <div class="message-sender">${data.sender_name}</div>
        <div class="message-content">${escapeHtml(data.message)}</div>
        <div class="message-time">${new Date(data.timestamp).toLocaleTimeString()}</div>
    `;
    chatList.appendChild(msgElement);
    chatList.scrollTop = chatList.scrollHeight;
    
    showNotification(`Message from ${data.sender_name}`, 'info');
}

// ============================================================================
// SOS ALERT SYSTEM
// ============================================================================

function selectSOSCategory(categoryId) {
    app.selectedSOSCategory = categoryId;
    document.getElementById('selected-category').textContent = SOS_CATEGORIES[categoryId];
    document.getElementById('sos-form').style.display = 'block';
    
    // Highlight selected button
    document.querySelectorAll('.category-btn').forEach(btn => {
        btn.classList.remove('selected');
    });
    document.querySelector(`[data-category="${categoryId}"]`).classList.add('selected');
}

async function triggerSOS() {
    if (!app.selectedSOSCategory) {
        showNotification('Please select an emergency type', 'error');
        return;
    }
    
    if (!app.userLocation.lat || !app.userLocation.lon) {
        showNotification('Waiting for location...', 'error');
        return;
    }
    
    const description = document.getElementById('sos-description').value;
    const severity = parseInt(document.getElementById('severity-level').value);
    
    try {
        const response = await fetch('/api/sos/trigger', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${app.token}`
            },
            body: JSON.stringify({
                category: app.selectedSOSCategory,
                severity: severity,
                description: description,
                lat: app.userLocation.lat,
                lon: app.userLocation.lon
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification('🚨 SOS ALERT TRIGGERED! Help is on the way!', 'success');
            
            // Reset form
            document.getElementById('sos-description').value = '';
            document.getElementById('severity-level').value = '3';
            app.selectedSOSCategory = null;
            document.getElementById('sos-form').style.display = 'none';
            document.querySelectorAll('.category-btn').forEach(btn => {
                btn.classList.remove('selected');
            });
        } else {
            showNotification(data.error || 'Failed to trigger SOS', 'error');
        }
    } catch (error) {
        console.error('SOS trigger error:', error);
        showNotification('Network error', 'error');
    }
}

function displaySOSAlert(data) {
    // Create alert notification
    const alertDiv = document.createElement('div');
    alertDiv.className = 'sos-alert-notification';
    alertDiv.innerHTML = `
        <div class="alert-header">🚨 EMERGENCY ALERT</div>
        <div class="alert-details">
            <p><strong>Category:</strong> ${data.category}</p>
            <p><strong>Severity:</strong> ${data.severity_level}/4</p>
            <p><strong>Person:</strong> ${data.user_name}</p>
            <p><strong>Time:</strong> ${new Date(data.timestamp).toLocaleTimeString()}</p>
            <p><strong>Description:</strong> ${data.description || 'No description'}</p>
        </div>
        <button onclick="acknowledgeSOSAlert(${data.alert_id})">Acknowledge & Help</button>
    `;
    
    document.getElementById('chat-list').prepend(alertDiv);
}

async function acknowledgeSOSAlert(alertId) {
    try {
        const response = await fetch(`/api/sos/acknowledge/${alertId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${app.token}`
            },
            body: JSON.stringify({ response: 'On the way to help' })
        });
        
        if (response.ok) {
            showNotification('SOS alert acknowledged', 'success');
        }
    } catch (error) {
        console.error('Acknowledge error:', error);
    }
}

// ============================================================================
// CONTACTS MANAGEMENT
// ============================================================================

function showAddContactForm() {
    document.getElementById('add-contact-form').style.display = 'block';
}

function cancelAddContact() {
    document.getElementById('add-contact-form').style.display = 'none';
    document.getElementById('contact-name').value = '';
    document.getElementById('contact-phone').value = '';
    document.getElementById('contact-email').value = '';
}

async function addContact() {
    const name = document.getElementById('contact-name').value;
    const phone = document.getElementById('contact-phone').value;
    const email = document.getElementById('contact-email').value;
    const type = document.getElementById('contact-type').value;
    
    if (!name || !phone) {
        showNotification('Please fill in name and phone', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/contacts', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${app.token}`
            },
            body: JSON.stringify({
                name: name,
                phone_number: phone,
                email: email,
                type: type
            })
        });
        
        if (response.ok) {
            showNotification('Contact added!', 'success');
            cancelAddContact();
            loadContacts();
        } else {
            const data = await response.json();
            showNotification(data.error || 'Failed to add contact', 'error');
        }
    } catch (error) {
        console.error('Add contact error:', error);
        showNotification('Network error', 'error');
    }
}

async function loadContacts() {
    try {
        const response = await fetch('/api/contacts', {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${app.token}` }
        });
        
        const data = await response.json();
        const contactsList = document.getElementById('contacts-list');
        
        if (data.contacts && data.contacts.length > 0) {
            contactsList.innerHTML = data.contacts.map(contact => `
                <div class="contact-card">
                    <div class="contact-name">${contact.name}</div>
                    <div class="contact-phone">${contact.phone_number}</div>
                    <div class="contact-status ${contact.online ? 'online' : 'offline'}">
                        ${contact.online ? '🟢 Online' : '⚪ Offline'}
                    </div>
                </div>
            `).join('');
        } else {
            contactsList.innerHTML = '<div class="placeholder">No contacts yet. Add one to get started!</div>';
        }
    } catch (error) {
        console.error('Load contacts error:', error);
    }
}

function updateContactStatus(userId, status) {
    // Update contact status in UI
    const contacts = document.querySelectorAll('.contact-status');
    contacts.forEach(contact => {
        if (status === 'online') {
            contact.className = 'contact-status online';
            contact.textContent = '🟢 Online';
        } else {
            contact.className = 'contact-status offline';
            contact.textContent = '⚪ Offline';
        }
    });
}

// ============================================================================
// PROFILE
// ============================================================================

async function loadProfile() {
    try {
        const response = await fetch('/api/user/profile', {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${app.token}` }
        });
        
        const data = await response.json();
        
        if (data.user_id) {
            document.getElementById('profile-name').textContent = data.name;
            document.getElementById('profile-phone').textContent = data.phone_number;
            document.getElementById('profile-email').textContent = data.email || 'Not provided';
            
            // Update location to server
            if (app.userLocation.lat && app.userLocation.lon) {
                updateUserLocation();
            }
        }
    } catch (error) {
        console.error('Load profile error:', error);
    }
}

async function updateUserLocation() {
    try {
        await fetch('/api/user/location', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${app.token}`
            },
            body: JSON.stringify({
                lat: app.userLocation.lat,
                lon: app.userLocation.lon
            })
        });
    } catch (error) {
        console.error('Location update error:', error);
    }
}

// ============================================================================
// UTILITIES
// ============================================================================

function showNotification(message, type = 'info') {
    const notification = document.getElementById('notification');
    notification.textContent = message;
    notification.className = `notification show ${type}`;
    
    setTimeout(() => {
        notification.classList.remove('show');
    }, 3000);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Periodic location updates
setInterval(() => {
    if (app.userId && app.userLocation.lat) {
        updateUserLocation();
    }
}, 30000); // Every 30 seconds

// Send heartbeat to keep connection alive
setInterval(() => {
    if (app.socket && app.socket.connected) {
        app.socket.emit('heartbeat', { user_id: app.userId });
    }
}, 60000); // Every 60 seconds
