#!/usr/bin/env python3
"""
NexAlert v3.0 - Database Backup & Maintenance
Automatic backups, cleanup, and export utilities
"""

import os
import sys
import shutil
import sqlite3
import json
import csv
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = "/home/pi/nexalert_v3/database/nexalert.db"
BACKUP_DIR = "/home/pi/nexalert_v3/database/backups"
EXPORT_DIR = "/home/pi/nexalert_v3/exports"

# Auto-cleanup settings
KEEP_MESSAGES_DAYS = 30  # Delete messages older than 30 days
KEEP_RESOLVED_ALERTS_DAYS = 7  # Delete resolved alerts after 7 days
KEEP_ENV_DATA_DAYS = 90  # Keep 90 days of environmental data
MAX_BACKUPS = 10  # Keep last 10 backups


class DatabaseManager:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.backup_dir = Path(BACKUP_DIR)
        self.export_dir = Path(EXPORT_DIR)
        
        # Create directories
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.export_dir.mkdir(parents=True, exist_ok=True)
    
    def backup_database(self):
        """Create timestamped backup of the database"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"nexalert_backup_{timestamp}.db"
        
        try:
            shutil.copy2(self.db_path, backup_path)
            print(f"✅ Database backed up: {backup_path.name}")
            
            # Compress old backups
            self.cleanup_old_backups()
            
            return backup_path
        except Exception as e:
            print(f"❌ Backup failed: {e}")
            return None
    
    def cleanup_old_backups(self):
        """Keep only the most recent backups"""
        backups = sorted(self.backup_dir.glob("nexalert_backup_*.db"), reverse=True)
        
        if len(backups) > MAX_BACKUPS:
            for old_backup in backups[MAX_BACKUPS:]:
                old_backup.unlink()
                print(f"🗑️  Deleted old backup: {old_backup.name}")
    
    def cleanup_old_data(self):
        """Remove old messages, alerts, and sensor data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Calculate cutoff dates
            messages_cutoff = (datetime.now() - timedelta(days=KEEP_MESSAGES_DAYS)).isoformat()
            alerts_cutoff = (datetime.now() - timedelta(days=KEEP_RESOLVED_ALERTS_DAYS)).isoformat()
            env_cutoff = (datetime.now() - timedelta(days=KEEP_ENV_DATA_DAYS)).isoformat()
            
            # Delete old messages
            cursor.execute("DELETE FROM messages WHERE sent_at < ?", (messages_cutoff,))
            messages_deleted = cursor.rowcount
            
            # Delete old resolved alerts
            cursor.execute(
                "DELETE FROM alerts WHERE is_resolved = 1 AND resolved_at < ?",
                (alerts_cutoff,)
            )
            alerts_deleted = cursor.rowcount
            
            # Delete old environmental data
            cursor.execute("DELETE FROM environmental_data WHERE timestamp < ?", (env_cutoff,))
            env_deleted = cursor.rowcount
            
            conn.commit()
            
            print(f"🧹 Cleanup complete:")
            print(f"   - {messages_deleted} old messages")
            print(f"   - {alerts_deleted} resolved alerts")
            print(f"   - {env_deleted} environmental readings")
            
        except Exception as e:
            print(f"❌ Cleanup failed: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def export_to_json(self, table_name, output_file=None):
        """Export table to JSON"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            
            data = [dict(row) for row in rows]
            
            if not output_file:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = self.export_dir / f"{table_name}_{timestamp}.json"
            
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            print(f"✅ Exported {len(data)} rows from {table_name} to {output_file}")
            return output_file
            
        except Exception as e:
            print(f"❌ Export failed: {e}")
            return None
        finally:
            conn.close()
    
    def export_to_csv(self, table_name, output_file=None):
        """Export table to CSV"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            
            if not rows:
                print(f"⚠️  No data in {table_name}")
                return None
            
            if not output_file:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = self.export_dir / f"{table_name}_{timestamp}.csv"
            
            with open(output_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                
                for row in rows:
                    writer.writerow(dict(row))
            
            print(f"✅ Exported {len(rows)} rows from {table_name} to {output_file}")
            return output_file
            
        except Exception as e:
            print(f"❌ Export failed: {e}")
            return None
        finally:
            conn.close()
    
    def get_database_stats(self):
        """Get statistics about the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        try:
            # Users
            cursor.execute("SELECT COUNT(*) FROM users")
            stats['total_users'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM users WHERE is_online = 1")
            stats['online_users'] = cursor.fetchone()[0]
            
            # Messages
            cursor.execute("SELECT COUNT(*) FROM messages")
            stats['total_messages'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM messages WHERE is_broadcast = 1")
            stats['broadcast_messages'] = cursor.fetchone()[0]
            
            # Alerts
            cursor.execute("SELECT COUNT(*) FROM alerts")
            stats['total_alerts'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM alerts WHERE is_resolved = 0")
            stats['active_alerts'] = cursor.fetchone()[0]
            
            # Contacts
            cursor.execute("SELECT COUNT(*) FROM contacts")
            stats['total_contacts'] = cursor.fetchone()[0]
            
            # Environmental data
            cursor.execute("SELECT COUNT(*) FROM environmental_data")
            stats['env_readings'] = cursor.fetchone()[0]
            
            # Database size
            stats['database_size_mb'] = os.path.getsize(self.db_path) / (1024 * 1024)
            
            return stats
            
        except Exception as e:
            print(f"❌ Stats error: {e}")
            return {}
        finally:
            conn.close()
    
    def print_stats(self):
        """Print database statistics"""
        stats = self.get_database_stats()
        
        print("\n" + "=" * 60)
        print("DATABASE STATISTICS")
        print("=" * 60)
        print(f"Users:                {stats.get('total_users', 0)} (Online: {stats.get('online_users', 0)})")
        print(f"Messages:             {stats.get('total_messages', 0)} (Broadcasts: {stats.get('broadcast_messages', 0)})")
        print(f"Alerts:               {stats.get('total_alerts', 0)} (Active: {stats.get('active_alerts', 0)})")
        print(f"Contacts:             {stats.get('total_contacts', 0)}")
        print(f"Environmental Data:   {stats.get('env_readings', 0)} readings")
        print(f"Database Size:        {stats.get('database_size_mb', 0):.2f} MB")
        print("=" * 60 + "\n")
    
    def vacuum_database(self):
        """Optimize database (reclaim space)"""
        conn = sqlite3.connect(self.db_path)
        try:
            print("🔧 Optimizing database...")
            conn.execute("VACUUM")
            print("✅ Database optimized")
        except Exception as e:
            print(f"❌ Vacuum failed: {e}")
        finally:
            conn.close()


def main():
    if len(sys.argv) < 2:
        print("NexAlert Database Manager")
        print("\nUsage:")
        print("  python3 db_manager.py backup           - Create backup")
        print("  python3 db_manager.py cleanup          - Remove old data")
        print("  python3 db_manager.py stats            - Show statistics")
        print("  python3 db_manager.py export <table>   - Export table to JSON")
        print("  python3 db_manager.py export-csv <table> - Export table to CSV")
        print("  python3 db_manager.py vacuum           - Optimize database")
        print("  python3 db_manager.py full-backup      - Backup + cleanup + vacuum")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    manager = DatabaseManager()
    
    if command == "backup":
        manager.backup_database()
    
    elif command == "cleanup":
        manager.cleanup_old_data()
    
    elif command == "stats":
        manager.print_stats()
    
    elif command == "export" and len(sys.argv) > 2:
        table = sys.argv[2]
        manager.export_to_json(table)
    
    elif command == "export-csv" and len(sys.argv) > 2:
        table = sys.argv[2]
        manager.export_to_csv(table)
    
    elif command == "vacuum":
        manager.vacuum_database()
    
    elif command == "full-backup":
        print("Running full maintenance...\n")
        manager.print_stats()
        manager.backup_database()
        manager.cleanup_old_data()
        manager.vacuum_database()
        print("\n✅ Full maintenance complete!")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
