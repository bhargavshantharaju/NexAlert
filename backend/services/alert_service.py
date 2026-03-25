#!/usr/bin/env python3
"""
NexAlert v3.0 - SMS/Call Alert Service
Sends SMS and makes calls for emergency alerts
Integrates with Twilio or 4G modem
"""

import sys
import time
import json
import requests
from datetime import datetime

# Configuration
API_BASE = "http://127.0.0.1:5000"
CHECK_INTERVAL = 10  # seconds

# Twilio configuration (set these via environment variables or config file)
TWILIO_ENABLED = False
TWILIO_ACCOUNT_SID = "YOUR_TWILIO_ACCOUNT_SID"
TWILIO_AUTH_TOKEN = "YOUR_TWILIO_AUTH_TOKEN"
TWILIO_PHONE_NUMBER = "+1234567890"  # Your Twilio number

# 4G Modem configuration (alternative to Twilio)
USE_4G_MODEM = True
MODEM_PORT = "/dev/ttyUSB2"  # Typical for SIM7600

try:
    from twilio.rest import Client
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    print("⚠️  Twilio library not available")

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    print("⚠️  pyserial not available - modem calls disabled")


class AlertService:
    def __init__(self):
        self.twilio_client = None
        self.modem = None
        self.processed_alerts = set()
        
        self.initialize_services()
    
    def initialize_services(self):
        """Initialize Twilio or 4G modem"""
        if TWILIO_ENABLED and TWILIO_AVAILABLE:
            try:
                self.twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
                print("✅ Twilio initialized")
            except Exception as e:
                print(f"❌ Twilio initialization failed: {e}")
        
        if USE_4G_MODEM and SERIAL_AVAILABLE:
            try:
                self.modem = serial.Serial(MODEM_PORT, 115200, timeout=1)
                time.sleep(2)
                
                # Test AT command
                self.modem.write(b'AT\r\n')
                response = self.modem.read(100)
                
                if b'OK' in response:
                    print("✅ 4G Modem initialized")
                else:
                    print("⚠️  Modem not responding")
                    self.modem = None
            except Exception as e:
                print(f"❌ Modem initialization failed: {e}")
                self.modem = None
    
    def send_sms_twilio(self, to_number, message):
        """Send SMS via Twilio"""
        if not self.twilio_client:
            return False
        
        try:
            msg = self.twilio_client.messages.create(
                body=message,
                from_=TWILIO_PHONE_NUMBER,
                to=to_number
            )
            print(f"✅ SMS sent to {to_number} via Twilio (SID: {msg.sid})")
            return True
        except Exception as e:
            print(f"❌ Twilio SMS failed: {e}")
            return False
    
    def send_sms_modem(self, to_number, message):
        """Send SMS via 4G modem (AT commands)"""
        if not self.modem:
            return False
        
        try:
            # Set SMS text mode
            self.modem.write(b'AT+CMGF=1\r\n')
            time.sleep(0.5)
            
            # Set recipient
            self.modem.write(f'AT+CMGS="{to_number}"\r\n'.encode())
            time.sleep(0.5)
            
            # Send message + Ctrl+Z
            self.modem.write(message.encode() + b'\x1A')
            time.sleep(2)
            
            response = self.modem.read(200)
            
            if b'+CMGS' in response or b'OK' in response:
                print(f"✅ SMS sent to {to_number} via modem")
                return True
            else:
                print(f"❌ Modem SMS failed: {response}")
                return False
        except Exception as e:
            print(f"❌ Modem SMS error: {e}")
            return False
    
    def make_call_twilio(self, to_number, message):
        """Make voice call via Twilio"""
        if not self.twilio_client:
            return False
        
        try:
            # Use TwiML to speak the message
            twiml_url = f"http://twimlets.com/message?Message={requests.utils.quote(message)}"
            
            call = self.twilio_client.calls.create(
                url=twiml_url,
                to=to_number,
                from_=TWILIO_PHONE_NUMBER
            )
            print(f"✅ Call initiated to {to_number} (SID: {call.sid})")
            return True
        except Exception as e:
            print(f"❌ Twilio call failed: {e}")
            return False
    
    def make_call_modem(self, to_number):
        """Make voice call via 4G modem"""
        if not self.modem:
            return False
        
        try:
            # Dial command
            self.modem.write(f'ATD{to_number};\r\n'.encode())
            time.sleep(5)  # Wait for call to connect
            
            # Hang up after message (in real implementation, play audio)
            self.modem.write(b'ATH\r\n')
            
            print(f"✅ Call placed to {to_number} via modem")
            return True
        except Exception as e:
            print(f"❌ Modem call error: {e}")
            return False
    
    def fetch_unprocessed_alerts(self):
        """Get alerts from API that haven't been sent yet"""
        try:
            response = requests.get(
                f"{API_BASE}/api/alerts?resolved=false",
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                alerts = data.get('alerts', [])
                
                # Filter out already processed
                new_alerts = [a for a in alerts if a['id'] not in self.processed_alerts]
                return new_alerts
            else:
                return []
        except Exception as e:
            print(f"❌ API fetch error: {e}")
            return []
    
    def process_alert(self, alert):
        """Send SMS/call for an alert"""
        user = alert.get('user', {})
        phone = user.get('phone_number')
        
        if not phone:
            print(f"⚠️  Alert {alert['id']} has no phone number")
            return
        
        alert_type = alert.get('alert_type', 'emergency').replace('_', ' ').upper()
        location = f"({alert.get('latitude')}, {alert.get('longitude')})" if alert.get('latitude') else "Unknown"
        
        message = (
            f"🚨 NEXALERT EMERGENCY 🚨\n"
            f"Type: {alert_type}\n"
            f"From: {user.get('full_name', 'Unknown')}\n"
            f"Phone: {phone}\n"
            f"Location: {location}\n"
            f"Time: {datetime.fromisoformat(alert['created_at']).strftime('%H:%M:%S')}"
        )
        
        print(f"\n📱 Processing alert {alert['id']}:")
        print(message)
        
        # Try SMS first
        sms_sent = False
        if self.twilio_client:
            sms_sent = self.send_sms_twilio(phone, message)
        elif self.modem:
            sms_sent = self.send_sms_modem(phone, message)
        
        # If SMS fails or for critical alerts, make a call
        if not sms_sent or alert.get('severity') == 'critical':
            if self.twilio_client:
                self.make_call_twilio(phone, message)
            elif self.modem:
                self.make_call_modem(phone)
        
        # Mark as processed
        self.processed_alerts.add(alert['id'])


def main():
    print("=" * 60)
    print("NexAlert SMS/Call Alert Service")
    print("=" * 60)
    
    service = AlertService()
    
    if not service.twilio_client and not service.modem:
        print("\n⚠️  WARNING: No SMS/call method available!")
        print("Either configure Twilio or connect a 4G modem")
        print("Running in monitoring mode only...\n")
    
    print(f"\n📞 Checking for alerts every {CHECK_INTERVAL} seconds")
    print("Press Ctrl+C to stop\n")
    
    while True:
        try:
            alerts = service.fetch_unprocessed_alerts()
            
            if alerts:
                print(f"\n🚨 {len(alerts)} new alert(s) detected!")
                for alert in alerts:
                    service.process_alert(alert)
            
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            print("\n\n👋 Shutting down alert service")
            if service.modem:
                service.modem.close()
            sys.exit(0)
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
