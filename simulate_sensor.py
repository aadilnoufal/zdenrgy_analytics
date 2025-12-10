"""
Sensor Data Simulator for ZDEnergy Analytics
Generates random sensor data and sends it to the TCP server (port 6000)
Simulates realistic temperature, humidity, and light readings
"""

import socket
import json
import time
import random
from datetime import datetime
from zoneinfo import ZoneInfo

# Configuration
TCP_HOST = "localhost"
TCP_PORT = 6000
SENSOR_ID = "sim_sensor_001"
SEND_INTERVAL = 60  # seconds between readings
QATAR_TZ = ZoneInfo("Asia/Qatar")

# Realistic sensor ranges
TEMP_MIN = 20.0  # °C
TEMP_MAX = 45.0  # °C (Qatar can get hot!)
TEMP_VARIATION = 2.0  # Max change per reading

HUMIDITY_MIN = 20.0  # %
HUMIDITY_MAX = 80.0  # %
HUMIDITY_VARIATION = 5.0

LUX_MIN = 0  # lux (night)
LUX_MAX = 100000  # lux (bright sun)

# Starting values
current_temp = 25.0
current_humidity = 50.0
current_lux = 5000.0


def generate_realistic_lux():
    """Generate realistic lux values based on time of day (Qatar time)"""
    now = datetime.now(QATAR_TZ)
    hour = now.hour
    
    # Simulate day/night cycle
    if 6 <= hour < 7:  # Dawn
        return random.uniform(100, 5000)
    elif 7 <= hour < 8:  # Early morning
        return random.uniform(5000, 20000)
    elif 8 <= hour < 17:  # Daytime
        return random.uniform(30000, 100000)
    elif 17 <= hour < 18:  # Late afternoon
        return random.uniform(20000, 50000)
    elif 18 <= hour < 19:  # Dusk
        return random.uniform(5000, 20000)
    elif 19 <= hour < 20:  # Early evening
        return random.uniform(100, 5000)
    else:  # Night
        return random.uniform(0, 100)


def generate_reading():
    """Generate a random sensor reading with realistic variations"""
    global current_temp, current_humidity, current_lux
    
    # Temperature: gradual changes with small random walk
    temp_change = random.uniform(-TEMP_VARIATION, TEMP_VARIATION)
    current_temp = max(TEMP_MIN, min(TEMP_MAX, current_temp + temp_change))
    
    # Humidity: gradual changes, inverse correlation with temperature
    humidity_change = random.uniform(-HUMIDITY_VARIATION, HUMIDITY_VARIATION)
    if temp_change > 1:  # If temp increases, humidity tends to decrease
        humidity_change -= 2
    current_humidity = max(HUMIDITY_MIN, min(HUMIDITY_MAX, current_humidity + humidity_change))
    
    # Lux: based on time of day with some random variation
    base_lux = generate_realistic_lux()
    lux_variation = base_lux * 0.1  # 10% variation
    current_lux = max(0, base_lux + random.uniform(-lux_variation, lux_variation))
    
    # Create reading in the format expected by the server
    reading = {
        "id": SENSOR_ID,
        "time": datetime.now(QATAR_TZ).strftime("%Y-%m-%d %H:%M:%S"),
        "temp": round(current_temp, 2),
        "rh": round(current_humidity, 2),
        "lux": round(current_lux, 2)
    }
    
    return reading


def send_to_tcp_server(reading):
    """Send a reading to the TCP server"""
    try:
        # Create socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        
        # Connect to server
        sock.connect((TCP_HOST, TCP_PORT))
        
        # Send JSON data with newline (server expects newline-delimited JSON)
        message = json.dumps(reading) + "\n"
        sock.sendall(message.encode('utf-8'))
        
        # Close connection
        sock.close()
        
        return True
    except Exception as e:
        print(f"❌ Failed to send data: {e}")
        return False


def main():
    """Main simulation loop"""
    print("=" * 60)
    print("🌡️  ZDEnergy Sensor Simulator Started")
    print("=" * 60)
    print(f"📡 TCP Server: {TCP_HOST}:{TCP_PORT}")
    print(f"🆔 Sensor ID: {SENSOR_ID}")
    print(f"⏱️  Send Interval: {SEND_INTERVAL} seconds")
    print(f"🇶🇦 Timezone: Qatar (UTC+3)")
    print("=" * 60)
    print("\nPress Ctrl+C to stop\n")
    
    reading_count = 0
    success_count = 0
    
    try:
        while True:
            # Generate reading
            reading = generate_reading()
            reading_count += 1
            
            # Send to server
            if send_to_tcp_server(reading):
                success_count += 1
                print(f"✅ [{reading_count}] Sent: {reading['time']} | "
                      f"Temp: {reading['temp']}°C | "
                      f"RH: {reading['rh']}% | "
                      f"Lux: {reading['lux']:.0f}")
            else:
                print(f"⚠️  [{reading_count}] Failed to send reading")
            
            # Wait before next reading
            time.sleep(SEND_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n" + "=" * 60)
        print("🛑 Simulation stopped by user")
        print(f"📊 Statistics:")
        print(f"   Total readings: {reading_count}")
        print(f"   Successful: {success_count}")
        print(f"   Failed: {reading_count - success_count}")
        print(f"   Success rate: {(success_count/reading_count*100):.1f}%")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ Simulation error: {e}")


if __name__ == "__main__":
    main()
