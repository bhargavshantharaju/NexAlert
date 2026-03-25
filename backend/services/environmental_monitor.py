#!/usr/bin/env python3
"""
NexAlert v3.0 - Environmental Sensor Service
Reads from BME680 (temp, humidity, air quality), UV sensor, PM2.5
Logs to database every 60 seconds
"""

import time
import sys
import json
import requests
from datetime import datetime

# Try to import sensor libraries
try:
    import board
    import busio
    import adafruit_bme680
    SENSORS_AVAILABLE = True
except ImportError:
    SENSORS_AVAILABLE = False
    print("⚠️  Sensor libraries not available - running in mock mode")

API_BASE = "http://127.0.0.1:5000"
INTERVAL = 60  # seconds

class MockSensor:
    """Mock sensor for testing without hardware"""
    def __init__(self):
        self.temperature = 25.0
        self.humidity = 60.0
        self.gas = 50000
        
    def read(self):
        import random
        # Simulate realistic variations
        self.temperature += random.uniform(-0.5, 0.5)
        self.humidity += random.uniform(-2, 2)
        self.gas += random.uniform(-1000, 1000)
        
        self.temperature = max(15, min(40, self.temperature))
        self.humidity = max(30, min(90, self.humidity))
        self.gas = max(10000, min(100000, self.gas))
        
        return {
            'temperature': round(self.temperature, 2),
            'humidity': round(self.humidity, 2),
            'gas': int(self.gas)
        }


class EnvironmentalMonitor:
    def __init__(self):
        self.bme680 = None
        self.initialize_sensors()
        
    def initialize_sensors(self):
        """Initialize I2C sensors"""
        if not SENSORS_AVAILABLE:
            print("Using mock sensors")
            self.bme680 = MockSensor()
            return
            
        try:
            i2c = busio.I2C(board.SCL, board.SDA)
            self.bme680 = adafruit_bme680.Adafruit_BME680_I2C(i2c)
            
            # Configure BME680
            self.bme680.sea_level_pressure = 1013.25
            
            print("✅ BME680 initialized")
        except Exception as e:
            print(f"❌ Failed to initialize BME680: {e}")
            print("Falling back to mock sensor")
            self.bme680 = MockSensor()
    
    def read_bme680(self):
        """Read temperature, humidity, gas from BME680"""
        try:
            if isinstance(self.bme680, MockSensor):
                return self.bme680.read()
            else:
                return {
                    'temperature': round(self.bme680.temperature, 2),
                    'humidity': round(self.bme680.humidity, 2),
                    'gas': int(self.bme680.gas)
                }
        except Exception as e:
            print(f"Error reading BME680: {e}")
            return None
    
    def read_uv_sensor(self):
        """Read UV index (placeholder for VEML6075 or similar)"""
        # TODO: Implement actual UV sensor reading
        import random
        return round(random.uniform(0, 11), 1)  # UV index 0-11
    
    def read_pm25_sensor(self):
        """Read PM2.5 concentration (placeholder for PMS5003 or similar)"""
        # TODO: Implement actual PM2.5 sensor reading
        import random
        return round(random.uniform(10, 150), 1)  # μg/m³
    
    def read_battery_voltage(self):
        """Read battery voltage via ADC"""
        try:
            # For INA219 or voltage divider on ADC
            # TODO: Implement actual voltage reading
            import random
            return round(random.uniform(11.5, 13.2), 2)  # 12V battery
        except:
            return None
    
    def read_solar_voltage(self):
        """Read solar panel voltage"""
        try:
            # TODO: Implement actual solar voltage reading
            import random
            return round(random.uniform(0, 18), 2)  # 0-18V from solar
        except:
            return None
    
    def get_all_readings(self):
        """Collect all sensor data"""
        bme_data = self.read_bme680()
        
        if not bme_data:
            return None
        
        return {
            'temperature': bme_data['temperature'],
            'humidity': bme_data['humidity'],
            'air_quality': bme_data['gas'],
            'uv_index': self.read_uv_sensor(),
            'pm25': self.read_pm25_sensor(),
            'battery_voltage': self.read_battery_voltage(),
            'solar_voltage': self.read_solar_voltage(),
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def send_to_api(self, data):
        """Send readings to Flask API"""
        try:
            response = requests.post(
                f"{API_BASE}/api/environmental",
                json=data,
                timeout=5
            )
            if response.status_code == 201:
                print(f"✅ Data logged: T={data['temperature']}°C H={data['humidity']}% "
                      f"AQ={data['air_quality']} UV={data['uv_index']}")
                return True
            else:
                print(f"❌ API error: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error: {e}")
            return False


def main():
    print("=" * 60)
    print("NexAlert Environmental Monitor Service")
    print("=" * 60)
    
    monitor = EnvironmentalMonitor()
    
    print(f"\n📊 Logging data every {INTERVAL} seconds")
    print("Press Ctrl+C to stop\n")
    
    while True:
        try:
            readings = monitor.get_all_readings()
            
            if readings:
                monitor.send_to_api(readings)
            else:
                print("⚠️  Failed to read sensors")
            
            time.sleep(INTERVAL)
            
        except KeyboardInterrupt:
            print("\n\n👋 Shutting down sensor service")
            sys.exit(0)
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
