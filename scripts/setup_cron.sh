#!/bin/bash
# NexAlert Automated Maintenance - Add to crontab

NEXALERT_DIR="/home/pi/nexalert_v3"
PYTHON="$NEXALERT_DIR/venv/bin/python3"
DB_MANAGER="$NEXALERT_DIR/backend/utils/db_manager.py"

# Daily backup at 2 AM
# 0 2 * * * $PYTHON $DB_MANAGER backup >> $NEXALERT_DIR/logs/maintenance.log 2>&1

# Weekly cleanup at 3 AM Sunday
# 0 3 * * 0 $PYTHON $DB_MANAGER cleanup >> $NEXALERT_DIR/logs/maintenance.log 2>&1

# Monthly vacuum at 4 AM on 1st
# 0 4 1 * * $PYTHON $DB_MANAGER vacuum >> $NEXALERT_DIR/logs/maintenance.log 2>&1

# Full maintenance weekly at 2:30 AM Sunday
# 30 2 * * 0 $PYTHON $DB_MANAGER full-backup >> $NEXALERT_DIR/logs/maintenance.log 2>&1

echo "To enable automated maintenance, add the following to crontab (crontab -e):"
echo ""
echo "# NexAlert Automated Maintenance"
echo "30 2 * * 0 $PYTHON $DB_MANAGER full-backup >> $NEXALERT_DIR/logs/maintenance.log 2>&1"
echo ""
echo "This runs a full backup + cleanup + vacuum every Sunday at 2:30 AM"
