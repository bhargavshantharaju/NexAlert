/**
 * NexAlert v3.0 - Admin Dashboard
 * Real-time emergency alert visualization with Google Maps integration
 */

// Global state
const dashboard = {
    map: null,
    markers: {},
    alertMarkers: {},
    socket: null,
    allAlerts: [],
    allUsers: [],
    selectedView: 'live-map'
};

// SOS Categories
const SOS_CATEGORIES = {
    'Medical': '🏥',
    'Fire': '🔥',
    'Flood': '💧',
    'Earthquake': '⛰️',
    'Accident': '🚗',
    'Violence': '⚔️',
    'Natural Disaster': '🌪️',
    'Power Outage': '💡',
    'Gas Leak': '💨',
    'Missing Person': '👤',
    'Animal Attack': '🐾',
    'Other': '❓'
};

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard Initializing...');
    
    // Initialize map
    initializeMap();
    
    // Initialize SocketIO
    initializeSocket();
    
    // Setup navigation
    setupNavigation();
    
    // Load initial data
    loadAlerts();
    loadUsers();
    loadSensorData();
    
    // Periodic refresh
    setInterval(refreshData, 30000); // Every 30 seconds
});

// ============================================================================
// GOOGLE MAPS INITIALIZATION
// ============================================================================

function initializeMap() {
    const mapOptions = {
        zoom: 13,
        center: { lat: 0, lon: 0 }, // Will be updated when data loads
        mapTypeId: google.maps.MapTypeId.ROADMAP,
        styles: [
            {
                "featureType": "water",
                "elementType": "geometry",
                "stylers": [{"color": "#e9e9e9"}, {"lightness": 17}]
            },
            {
                "featureType": "landscape",
                "elementType": "geometry",
                "stylers": [{"color": "#f3f3f3"}, {"lightness": 20}]
            }
        ]
    };
    
    dashboard.map = new google.maps.Map(document.getElementById('live-map'), mapOptions);
}

// ============================================================================
// MARKER MANAGEMENT
// ============================================================================

function addUserMarker(user) {
    if (!user.location_lat || !user.location_lon) return;
    
    const markerId = `user_${user.id}`;
    
    // Remove old marker if exists
    if (dashboard.markers[markerId]) {
        dashboard.markers[markerId].setMap(null);
    }
    
    const markerColor = user.online_status ? '#2ECC71' : '#95A5A6';
    const icon = {
        path: google.maps.SymbolPath.CIRCLE,
        scale: 10,
        fillColor: markerColor,
        fillOpacity: 0.8,
        strokeColor: '#ffffff',
        strokeWeight: 2
    };
    
    const marker = new google.maps.Marker({
        position: {
            lat: parseFloat(user.location_lat),
            lng: parseFloat(user.location_lon)
        },
        map: dashboard.map,
        icon: icon,
        title: user.name,
        animation: user.online_status ? google.maps.Animation.DROP : null
    });
    
    const infoWindow = new google.maps.InfoWindow({
        content: `
            <div style="padding: 10px;">
                <h3>${user.name}</h3>
                <p><strong>Phone:</strong> ${user.phone_number}</p>
                <p><strong>Status:</strong> ${user.online_status ? '🟢 Online' : '⚪ Offline'}</p>
                <p><strong>Last Seen:</strong> ${new Date(user.last_seen).toLocaleTimeString()}</p>
            </div>
        `
    });
    
    marker.addListener('click', () => {
        infoWindow.open(dashboard.map, marker);
    });
    
    dashboard.markers[markerId] = marker;
}

function addSOSMarker(alert) {
    if (!alert.location_lat || !alert.location_lon) return;
    
    const markerId = `sos_${alert.id}`;
    
    // Remove old marker if resolved
    if (dashboard.alertMarkers[markerId] && alert.status === 'resolved') {
        dashboard.alertMarkers[markerId].setMap(null);
        delete dashboard.alertMarkers[markerId];
        return;
    }
    
    if (dashboard.alertMarkers[markerId]) {
        dashboard.alertMarkers[markerId].setMap(null);
    }
    
    // Color based on severity
    let markerColor = '#FF6B6B';
    if (alert.severity === 2) markerColor = '#FFB347';
    if (alert.severity === 1) markerColor = '#FFD700';
    
    const icon = {
        path: 'M 0, 0 C -2.67, -16.5 -10, -33.3 -24, -33.3 C -37.3, -33.3 -48, -24.3 -48, -11.5 C -48, 15.6 0, 48 0, 48 C 0, 48 48, 15.6 48, -11.5 C 48, -24.3 37.3, -33.3 24, -33.3 C 10, -33.3 2.67, -16.5 0, 0 Z',
        fillColor: markerColor,
        fillOpacity: 0.9,
        strokeColor: '#fff',
        strokeWeight: 2,
        scale: 0.5,
        anchor: new google.maps.Point(0, 48)
    };
    
    const marker = new google.maps.Marker({
        position: {
            lat: parseFloat(alert.location_lat),
            lng: parseFloat(alert.location_lon)
        },
        map: dashboard.map,
        icon: icon,
        title: `${alert.category} - ${alert.severity_level}/4`,
        animation: alert.status === 'active' ? google.maps.Animation.BOUNCE : null
    });
    
    const infoWindow = new google.maps.InfoWindow({
        content: `
            <div style="padding: 10px; color: #333;">
                <h3>🚨 ${alert.category}</h3>
                <p><strong>Reported by:</strong> ${alert.user_name}</p>
                <p><strong>Severity:</strong> ${alert.severity_level}/4</p>
                <p><strong>Status:</strong> ${alert.status}</p>
                <p><strong>Time:</strong> ${new Date(alert.timestamp).toLocaleTimeString()}</p>
                <p><strong>Description:</strong> ${alert.description || 'N/A'}</p>
            </div>
        `
    });
    
    marker.addListener('click', () => {
        infoWindow.open(dashboard.map, marker);
    });
    
    dashboard.alertMarkers[markerId] = marker;
}

// ============================================================================
// DATA LOADING
// ============================================================================

async function loadAlerts() {
    try {
        const response = await fetch('/api/sos/alerts');
        const data = await response.json();
        
        if (data.alerts) {
            dashboard.allAlerts = data.alerts;
            
            // Update map markers
            data.alerts.forEach(alert => {
                addSOSMarker(alert);
            });
            
            // Update stats
            updateAlertStats(data.alerts);
            
            // Render alerts list
            renderAlertsList(data.alerts);
        }
    } catch (error) {
        console.error('Load alerts error:', error);
    }
}

async function loadUsers() {
    try {
        // Note: This would need a /api/users endpoint
        // For now, we'll get users from alerts data
        const users = Array.from(new Map(
            dashboard.allAlerts.map(alert => [alert.user_id, alert])
        ).values());
        
        dashboard.allUsers = users;
        
        // Update map markers
        users.forEach(user => {
            addUserMarker(user);
        });
        
        // Render users table
        renderUsersTable(users);
    } catch (error) {
        console.error('Load users error:', error);
    }
}

async function loadSensorData() {
    try {
        // Fetch sensor data for each user
        const sensorPromises = dashboard.allUsers.map(user =>
            fetch(`/api/sensors/data/${user.id}`)
                .then(r => r.json())
                .catch(() => null)
        );
        
        const sensorData = await Promise.all(sensorPromises);
        
        // Filter out failed requests
        const validData = sensorData.filter(d => d && d.user_id);
        
        renderSensorCards(validData);
    } catch (error) {
        console.error('Load sensor data error:', error);
    }
}

// ============================================================================
// RENDERING FUNCTIONS
// ============================================================================

function updateAlertStats(alerts) {
    const activeAlerts = alerts.filter(a => a.status === 'active');
    const criticalAlerts = alerts.filter(a => a.status === 'active' && a.severity === 4);
    const onlineUsers = dashboard.allUsers.filter(u => u.online_status).length;
    
    document.getElementById('active-count').textContent = activeAlerts.length;
    document.getElementById('critical-count').textContent = criticalAlerts.length;
    document.getElementById('online-count').textContent = onlineUsers;
}

function renderAlertsList(alerts) {
    const activeAlerts = alerts.filter(a => a.status === 'active');
    const alertsList = document.getElementById('alerts-list');
    
    if (activeAlerts.length === 0) {
        alertsList.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 2rem; color: #999;">✅ No active alerts</div>';
        return;
    }
    
    alertsList.innerHTML = activeAlerts.map(alert => `
        <div class="alert-card">
            <div class="alert-header">
                <div>
                    <div class="alert-title">${SOS_CATEGORIES[alert.category] || '⚠️'} ${alert.category}</div>
                </div>
                <span class="severity-badge severity-${alert.severity}">Level ${alert.severity}</span>
            </div>
            <div class="alert-info">
                <strong>Reporter:</strong> ${alert.user_name}<br>
                <strong>Phone:</strong> ${alert.user_phone}<br>
                <strong>Time:</strong> ${new Date(alert.timestamp).toLocaleTimeString()}
            </div>
            <div class="alert-location">
                📍 ${alert.location.lat.toFixed(4)}, ${alert.location.lon.toFixed(4)}
            </div>
            <p>${alert.description || 'No description provided'}</p>
            <div class="alert-actions">
                <button class="btn-small btn-acknowledge" onclick="acknowledgeAlert(${alert.id})">✓ Acknowledge</button>
                <button class="btn-small" style="background-color: #3498DB; color: white; border: none; cursor: pointer;">📞 Call</button>
            </div>
        </div>
    `).join('');
}

function renderUsersTable(users) {
    const tbody = document.getElementById('users-table-body');
    
    if (users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5">No users found</td></tr>';
        return;
    }
    
    tbody.innerHTML = users.map(user => `
        <tr>
            <td>${user.name}</td>
            <td>${user.phone_number}</td>
            <td>
                <span class="online-badge ${user.online_status ? 'online' : 'offline'}"></span>
                ${user.online_status ? 'Online' : 'Offline'}
            </td>
            <td>${new Date(user.last_seen).toLocaleString()}</td>
            <td>${user.location_lat ? `📍 ${user.location_lat.toFixed(4)}, ${user.location_lon.toFixed(4)}` : 'N/A'}</td>
        </tr>
    `).join('');
}

function renderSensorCards(sensorData) {
    const sensorsList = document.getElementById('sensors-list');
    
    if (sensorData.length === 0) {
        sensorsList.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 2rem; color: #999;">No sensor data available</div>';
        return;
    }
    
    sensorsList.innerHTML = sensorData.map(data => `
        <div class="sensor-card">
            <div class="sensor-title">📍 User #${data.user_id}</div>
            <div>
                <div class="sensor-value">${data.temperature}°C</div>
                <div class="sensor-label">Temperature</div>
            </div>
            <hr style="margin: 1rem 0; border: none; border-top: 1px solid #e0e0e0;">
            <div>
                <div class="sensor-value">${data.humidity}%</div>
                <div class="sensor-label">Humidity</div>
            </div>
            <hr style="margin: 1rem 0; border: none; border-top: 1px solid #e0e0e0;">
            <div>
                <div class="sensor-value">${data.battery_voltage}V</div>
                <div class="sensor-label">Battery</div>
            </div>
            <div style="margin-top: 0.5rem;">
                <div class="sensor-value" style="font-size: 1.5rem;">${data.solar_panel_voltage}V</div>
                <div class="sensor-label">Solar Panel</div>
            </div>
            <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #e0e0e0;">
                <div class="sensor-label">Last Update</div>
                <div style="font-size: 0.9rem; color: #666;">${new Date(data.timestamp).toLocaleTimeString()}</div>
            </div>
        </div>
    `).join('');
}

// ============================================================================
// SOCKET.IO REAL-TIME UPDATES
// ============================================================================

function initializeSocket() {
    dashboard.socket = io();
    
    dashboard.socket.on('connect', () => {
        console.log('Connected to server');
    });
    
    dashboard.socket.on('sos_alert', (data) => {
        console.warn('NEW SOS ALERT:', data);
        dashboard.allAlerts.push(data);
        addSOSMarker(data);
        renderAlertsList(dashboard.allAlerts.filter(a => a.status === 'active'));
        updateAlertStats(dashboard.allAlerts);
        
        // Play notification sound
        playNotificationSound();
    });
    
    dashboard.socket.on('location_update', (data) => {
        // Update user location in real-time
        loadAlerts();
    });
    
    dashboard.socket.on('user_status_change', (data) => {
        loadUsers();
    });
    
    dashboard.socket.on('sensor_data', (data) => {
        console.log('Sensor data update:', data);
        loadSensorData();
    });
}

// ============================================================================
// ACTIONS
// ============================================================================

async function acknowledgeAlert(alertId) {
    try {
        const response = await fetch(`/api/sos/acknowledge/${alertId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                response: 'Acknowledged from dashboard'
            })
        });
        
        if (response.ok) {
            alert('Alert acknowledged');
            loadAlerts();
        }
    } catch (error) {
        console.error('Acknowledge error:', error);
    }
}

function sendBroadcast() {
    const title = document.getElementById('broadcast-title').value;
    const message = document.getElementById('broadcast-message').value;
    const target = document.getElementById('broadcast-target').value;
    
    if (!title || !message) {
        alert('Please fill in all fields');
        return;
    }
    
    // This would call an API to send broadcast
    alert(`Broadcast sent to: ${target}\n\nTitle: ${title}\nMessage: ${message}`);
    
    document.getElementById('broadcast-title').value = '';
    document.getElementById('broadcast-message').value = '';
}

// ============================================================================
// NAVIGATION
// ============================================================================

function setupNavigation() {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => {
            const view = item.getAttribute('data-view');
            switchView(view);
            
            // Update active state
            document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
            item.classList.add('active');
            
            // Update header title
            const titles = {
                'live-map': 'Live Map',
                'active-alerts': 'Active Alerts',
                'users': 'Users',
                'sensors': 'Sensor Data',
                'broadcast': 'Broadcast Messages'
            };
            document.getElementById('view-title').textContent = titles[view];
        });
    });
}

function switchView(viewName) {
    document.querySelectorAll('.view').forEach(view => {
        view.classList.remove('active');
    });
    document.getElementById(viewName + '-view').classList.add('active');
    dashboard.selectedView = viewName;
    
    // Trigger map resize if switching to map view
    if (viewName === 'live-map' && dashboard.map) {
        setTimeout(() => {
            google.maps.event.trigger(dashboard.map, 'resize');
        }, 100);
    }
}

// ============================================================================
// UTILITIES
// ============================================================================

function playNotificationSound() {
    // Create a simple beep using Web Audio API
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    
    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);
    
    oscillator.frequency.value = 800;
    oscillator.type = 'sine';
    
    gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
    
    oscillator.start(audioContext.currentTime);
    oscillator.stop(audioContext.currentTime + 0.5);
}

function refreshData() {
    console.log('Refreshing data...');
    loadAlerts();
    loadUsers();
    loadSensorData();
}

function logout() {
    if (confirm('Are you sure you want to logout?')) {
        window.location.href = '/';
    }
}

// Center map on first load
setTimeout(() => {
    if (dashboard.allAlerts.length > 0) {
        const firstAlert = dashboard.allAlerts[0];
        dashboard.map.setCenter({
            lat: parseFloat(firstAlert.location.lat),
            lng: parseFloat(firstAlert.location.lon)
        });
    }
}, 2000);
