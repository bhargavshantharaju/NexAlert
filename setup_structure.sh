#!/bin/bash
# NexAlert v3.0 - Project Structure Setup

BASE_DIR="/home/claude/nexalert_v3_rebuild"

# Create directory tree
mkdir -p "$BASE_DIR"/{backend,frontend_dashboard,frontend_phone,network_config,systemd_services,ssl_certs,database,scripts,logs}
mkdir -p "$BASE_DIR"/backend/{models,routes,services,utils,static,templates}
mkdir -p "$BASE_DIR"/frontend_dashboard/{static/{css,js,img},templates}
mkdir -p "$BASE_DIR"/frontend_phone/{static/{css,js},templates}
mkdir -p "$BASE_DIR"/database/migrations

echo "✓ Directory structure created"
tree -L 2 "$BASE_DIR" 2>/dev/null || find "$BASE_DIR" -type d | head -20
