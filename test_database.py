"""
Test script to verify database connection and operations
Run this before starting the main application
"""

import sys
from datetime import datetime, timedelta
from db_manager import get_db_manager

def test_database():
    """Test all database operations"""
    print("=" * 60)
    print("🧪 Testing Database Connection")
    print("=" * 60)
    
    try:
        # 1. Test connection
        print("\n1️⃣  Testing connection...")
        db = get_db_manager()
        print("   ✅ Connection successful!")
        
        # 2. Test schema initialization
        print("\n2️⃣  Testing schema initialization...")
        db.initialize_schema()
        print("   ✅ Schema initialized!")
        
        # 3. Test inserting sensor reading
        print("\n3️⃣  Testing sensor reading insertion...")
        record_id = db.insert_sensor_reading(
            temperature=25.5,
            humidity=60.0,
            lux=500.0,
            irradiance=3.94,
            timestamp=datetime.now()
        )
        print(f"   ✅ Inserted reading with ID: {record_id}")
        
        # 4. Test retrieving latest readings
        print("\n4️⃣  Testing latest readings retrieval...")
        readings = db.get_latest_readings(limit=5)
        print(f"   ✅ Retrieved {len(readings)} readings")
        if readings:
            latest = readings[0]
            print(f"   📊 Latest reading:")
            print(f"      - Timestamp: {latest.get('timestamp')}")
            print(f"      - Temperature: {latest.get('temperature')}°C")
            print(f"      - Humidity: {latest.get('humidity')}%")
            print(f"      - Lux: {latest.get('lux')}")
        
        # 5. Test time range query
        print("\n5️⃣  Testing time range query...")
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=1)
        range_readings = db.get_readings_by_time_range(start_time, end_time)
        print(f"   ✅ Retrieved {len(range_readings)} readings from last hour")
        
        # 6. Test window query
        print("\n6️⃣  Testing window query...")
        window_readings = db.get_readings_by_window(window_minutes=60)
        print(f"   ✅ Retrieved {len(window_readings)} readings from last 60 minutes")
        
        # 7. Test KPI snapshot insertion
        print("\n7️⃣  Testing KPI snapshot insertion...")
        kpi_id = db.insert_kpi_snapshot(
            kpi_name="solar_generation",
            value=2.5,
            unit="kW",
            metadata={"panel_area": 20, "efficiency": 0.18}
        )
        print(f"   ✅ Inserted KPI snapshot with ID: {kpi_id}")
        
        # 8. Test KPI history
        print("\n8️⃣  Testing KPI history retrieval...")
        kpi_history = db.get_kpi_history("solar_generation", hours=24)
        print(f"   ✅ Retrieved {len(kpi_history)} KPI snapshots")
        
        # 9. Get database statistics
        print("\n9️⃣  Testing database statistics...")
        stats = db.get_statistics()
        print("   ✅ Database Statistics:")
        print(f"      - Total readings: {stats.get('total_readings', 0)}")
        print(f"      - Total KPI snapshots: {stats.get('total_kpi_snapshots', 0)}")
        print(f"      - Oldest reading: {stats.get('oldest_reading', 'N/A')}")
        print(f"      - Newest reading: {stats.get('newest_reading', 'N/A')}")
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\n🚀 Your database is ready! You can now start the Flask app.")
        print("   Run: python readings.py")
        print("\n")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        print("\n🔧 Troubleshooting:")
        print("   1. Check your .env file has correct credentials")
        print("   2. Verify Digital Ocean database is running")
        print("   3. Check firewall allows connections from your IP")
        print("   4. Verify SSL mode is set to 'require'")
        return False

if __name__ == "__main__":
    success = test_database()
    sys.exit(0 if success else 1)
