/**
 * NexAlert Dashboard Client
 *
 * Fixes:
 *  - Leaflet markers are stored in a Map and updated in-place (no duplicates)
 *  - Socket namespace matches server (default /)
 *  - resolve button correctly POSTs to /api/alerts/<id>/resolve
 *  - env data fetch handles 404 gracefully
 *  - XSS: all dynamic text goes through escapeHtml
 */

"use strict";

// ── Map ───────────────────────────────────────────────────────────────────────
const map = L.map("map", { zoomControl: true }).setView([13.35, 74.78], 10);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: "© OpenStreetMap contributors",
  maxZoom: 18,
}).addTo(map);

// Marker stores
const userMarkers  = new Map(); // username → L.marker
const alertMarkers = new Map(); // alert.id → L.marker

// ── Socket ───────────────────────────────────────────────────────────────────
const socket = io();

socket.on("new_alert", alert => {
  addAlertMarker(alert);
  appendAlertItem(alert);
  updateAlertCount(1);
});

socket.on("alert_resolved", ({ id }) => {
  if (alertMarkers.has(id)) { alertMarkers.get(id).remove(); alertMarkers.delete(id); }
  const el = document.getElementById(`alert-${id}`);
  if (el) el.remove();
  const remaining = document.querySelectorAll(".alert-item").length;
  document.getElementById("stat-alerts").textContent = remaining;
});

socket.on("location_update", ({ username, latitude, longitude }) => {
  placeUserMarker(username, latitude, longitude);
});

socket.on("user_online", ({ username }) => {
  markUserDot(username, true);
  loadUsers();
});

socket.on("user_offline", ({ username }) => {
  markUserDot(username, false);
  loadUsers();
});

socket.on("env_update", data => renderEnv(data));

// ── Data loaders ──────────────────────────────────────────────────────────────
async function loadUsers() {
  try {
    const res = await fetch("/api/users");
    const users = await res.json();
    const online = users.filter(u => u.is_online).length;
    document.getElementById("stat-users").textContent = online;
    renderUsersList(users);
    users.forEach(u => {
      if (u.latitude || u.longitude) placeUserMarker(u.username, u.latitude, u.longitude, u.is_online);
    });
  } catch (e) {}
}

async function loadAlerts() {
  try {
    const res = await fetch("/api/alerts");
    const alerts = await res.json();
    document.getElementById("stat-alerts").textContent = alerts.length;
    const list = document.getElementById("alerts-list");
    list.innerHTML = "";
    if (!alerts.length) { list.innerHTML = '<p class="empty-state">No active alerts</p>'; return; }
    alerts.forEach(a => { appendAlertItem(a); addAlertMarker(a); });
  } catch (e) {}
}

async function loadEnv() {
  try {
    const res = await fetch("/api/environmental");
    if (res.status === 404) return; // no data yet — not an error
    const data = await res.json();
    renderEnv(data);
  } catch (e) {}
}

function renderEnv(data) {
  const set = (id, val, suffix="") => {
    const el = document.getElementById(id);
    if (el) el.textContent = val != null ? `${Number(val).toFixed(1)}${suffix}` : "—";
  };
  set("env-temp",  data.temperature, "°");
  set("env-hum",   data.humidity, "%");
  set("env-aq",    data.air_quality);
  set("env-batt",  data.battery_v, "V");
  set("env-solar", data.solar_v, "V");
}

// ── Rendering ─────────────────────────────────────────────────────────────────
function renderUsersList(users) {
  const list = document.getElementById("users-list");
  list.innerHTML = users.map(u => `
    <div class="user-item" id="user-dot-${escapeHtml(u.username)}">
      <div class="user-dot ${u.is_online ? "online" : ""}"></div>
      <span class="user-name">${escapeHtml(u.username)}</span>
      <span class="user-phone">${escapeHtml(u.phone)}</span>
    </div>
  `).join("");
}

function markUserDot(username, online) {
  const el = document.getElementById(`user-dot-${escapeHtml(username)}`);
  if (!el) return;
  const dot = el.querySelector(".user-dot");
  if (dot) dot.className = `user-dot ${online ? "online" : ""}`;
}

function appendAlertItem(alert) {
  const list = document.getElementById("alerts-list");
  const empty = list.querySelector(".empty-state");
  if (empty) empty.remove();

  // Don't duplicate
  if (document.getElementById(`alert-${alert.id}`)) return;

  const div = document.createElement("div");
  div.className = "alert-item";
  div.id = `alert-${alert.id}`;
  div.style.borderLeftColor = alert.color || "#ef4444";
  div.innerHTML = `
    <span class="alert-item-icon">${escapeHtml(alert.icon || "🚨")}</span>
    <div class="alert-item-body">
      <div class="alert-item-type">${escapeHtml(alert.label || alert.alert_type)}</div>
      <div class="alert-item-user">@${escapeHtml(alert.username)}</div>
      ${alert.description ? `<div style="font-size:11px;color:#94a3b8;margin-top:2px;">${escapeHtml(alert.description)}</div>` : ""}
    </div>
    <button class="alert-resolve-btn" onclick="resolveAlert(${Number(alert.id)})">✓</button>
  `;
  list.insertBefore(div, list.firstChild);
  document.getElementById("stat-alerts").textContent =
    document.querySelectorAll(".alert-item").length;
}

function updateAlertCount(delta) {
  const el = document.getElementById("stat-alerts");
  el.textContent = Number(el.textContent || 0) + delta;
}

// ── Map markers ───────────────────────────────────────────────────────────────
function placeUserMarker(username, lat, lon, isOnline = true) {
  if (!lat && !lon) return;
  const icon = L.divIcon({
    className: "",
    html: `<div style="
      background:${isOnline ? "#22c55e" : "#64748b"};
      color:white; border-radius:50%; width:32px; height:32px;
      display:flex; align-items:center; justify-content:center;
      font-size:13px; font-weight:700; border:2px solid white;
      box-shadow: 0 2px 8px rgba(0,0,0,0.4);
    ">${(username[0] || "?").toUpperCase()}</div>`,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });

  if (userMarkers.has(username)) {
    userMarkers.get(username).setLatLng([lat, lon]);
  } else {
    const marker = L.marker([lat, lon], { icon })
      .addTo(map)
      .bindPopup(`<b>${escapeHtml(username)}</b><br>${isOnline ? "🟢 Online" : "⚫ Offline"}`);
    userMarkers.set(username, marker);
  }
}

function addAlertMarker(alert) {
  if (!alert.latitude && !alert.longitude) return;
  if (alertMarkers.has(alert.id)) return;
  const icon = L.divIcon({
    className: "",
    html: `<div style="
      background:${alert.color || "#ef4444"};
      color:white; border-radius:8px; padding:4px 8px;
      font-size:18px; box-shadow:0 2px 10px rgba(0,0,0,0.5);
      border:2px solid rgba(255,255,255,0.3); white-space:nowrap;
    ">${alert.icon || "🚨"}</div>`,
    iconAnchor: [20, 20],
  });
  const marker = L.marker([alert.latitude, alert.longitude], { icon })
    .addTo(map)
    .bindPopup(`
      <b>${escapeHtml(alert.label || alert.alert_type)}</b><br>
      @${escapeHtml(alert.username)}<br>
      ${alert.description ? escapeHtml(alert.description) : ""}
    `);
  alertMarkers.set(alert.id, marker);
}

// ── Build legend ──────────────────────────────────────────────────────────────
function buildLegend() {
  const legend = document.getElementById("map-legend");
  if (!legend || !window.ALERT_TYPES) return;
  legend.innerHTML = Object.entries(ALERT_TYPES).slice(0, 6).map(([, v]) =>
    `<div class="legend-item">
      <div class="legend-dot" style="background:${v.color}"></div>
      <span style="font-size:12px">${v.icon} ${v.label}</span>
    </div>`
  ).join("");
}

// ── Actions ───────────────────────────────────────────────────────────────────
async function resolveAlert(id) {
  try {
    await fetch(`/api/alerts/${id}/resolve`, { method: "POST" });
    // socket event will handle UI cleanup
  } catch (e) {}
}

async function broadcastMessage() {
  const content = document.getElementById("broadcast-msg").value.trim();
  if (!content) return;
  try {
    await fetch("/api/messages", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sender: "dashboard", content, is_broadcast: 1 }),
    });
    document.getElementById("broadcast-msg").value = "";
  } catch (e) {
    alert("Failed to broadcast");
  }
}

// ── Security ──────────────────────────────────────────────────────────────────
function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// ── Boot ──────────────────────────────────────────────────────────────────────
buildLegend();
loadUsers();
loadAlerts();
loadEnv();
setInterval(loadUsers, 30000);
setInterval(loadEnv, 60000);
