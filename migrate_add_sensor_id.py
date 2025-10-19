"""
Database Migration Script: Add sensor_id Column
Adds the sensor_id column to existing sensor_readings table
Safe to run - checks if column exists before adding
"""

from db_manager import get_db_manager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_add_sensor_id():
    """Add sensor_id column to sensor_readings table if it doesn't exist"""
    db = get_db_manager()
    conn = None
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='sensor_readings' 
            AND column_name='sensor_id';
        """)
        
        if cursor.fetchone():
            logger.info("✅ sensor_id column already exists - no migration needed")
            return
        
        # Add the column
        logger.info("🔧 Adding sensor_id column to sensor_readings table...")
        cursor.execute("""
            ALTER TABLE sensor_readings 
            ADD COLUMN sensor_id VARCHAR(100);
        """)
        
        # Create index for faster queries
        logger.info("🔧 Creating index on sensor_id...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sensor_readings_sensor_id 
            ON sensor_readings (sensor_id);
        """)
        
        conn.commit()
        logger.info("✅ Migration completed successfully!")
        logger.info("   - Added sensor_id column (VARCHAR(100))")
        logger.info("   - Created index on sensor_id")
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"❌ Migration failed: {e}")
        raise
    finally:
        if conn:
            cursor.close()
            db.return_connection(conn)

def check_schema():
    """Display current schema information"""
    db = get_db_manager()
    conn = None
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get column information
        cursor.execute("""
            SELECT column_name, data_type, character_maximum_length, is_nullable
            FROM information_schema.columns 
            WHERE table_name='sensor_readings'
            ORDER BY ordinal_position;
        """)
        
        columns = cursor.fetchall()
        
        print("\n" + "="*60)
        print("📋 Current sensor_readings table schema:")
        print("="*60)
        for col in columns:
            name, dtype, max_len, nullable = col
            max_len_str = f"({max_len})" if max_len else ""
            nullable_str = "NULL" if nullable == "YES" else "NOT NULL"
            print(f"  • {name:15} {dtype}{max_len_str:15} {nullable_str}")
        print("="*60 + "\n")
        
    except Exception as e:
        logger.error(f"❌ Failed to check schema: {e}")
    finally:
        if conn:
            cursor.close()
            db.return_connection(conn)

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🔄 Database Migration Tool")
    print("="*60)
    print("Task: Add sensor_id column to sensor_readings table")
    print("="*60 + "\n")
    
    # Show current schema
    check_schema()
    
    # Ask for confirmation
    response = input("Do you want to proceed with the migration? (yes/no): ")
    
    if response.lower() in ['yes', 'y']:
        print()
        migrate_add_sensor_id()
        print()
        # Show updated schema
        check_schema()
    else:
        print("\n❌ Migration cancelled by user\n")
