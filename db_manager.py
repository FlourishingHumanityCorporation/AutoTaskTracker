#!/usr/bin/env python3
"""
Database Manager CLI for AutoTaskTracker.
Manage database backend switching and configuration.
"""

import argparse
import sys
import os
from pathlib import Path

# Add package to path
sys.path.insert(0, str(Path(__file__).parent))

def show_status():
    """Show current database configuration status."""
    try:
        from autotasktracker.config import get_config
        config = get_config()
        
        print("=== AutoTaskTracker Database Status ===")
        print(f"Backend: PostgreSQL")
        print(f"URL: {config.get_database_url()}")
        print()
        
        # Test PostgreSQL
        pg_status = "✅ Connected" if config.test_database_connection() else "❌ Failed"
        print(f"PostgreSQL: {pg_status}")
        print(f"  URL: {config.get_database_url()}")
        
        print()
        print("=== Configuration ===")
        print(f"PostgreSQL URL: {config.POSTGRESQL_URL}")
        
    except Exception as e:
        print(f"Failed to get database status: {e}")
        return 1
    
    return 0

def test_connection():
    """Test PostgreSQL database connection."""
    try:
        from autotasktracker.config import get_config
        config = get_config()
        
        print("Testing PostgreSQL connection...")
        if config.test_database_connection():
            print("✅ PostgreSQL connection successful")
            return 0
        else:
            print("❌ PostgreSQL connection failed")
            return 1
        
    except Exception as e:
        print(f"Failed to test connection: {e}")
        return 1

def get_database_stats():
    """Get PostgreSQL database statistics."""
    try:
        from autotasktracker.config import get_config
        config = get_config()
        
        print("=== PostgreSQL Database Statistics ===")
        
        # Test PostgreSQL
        print("Connecting to PostgreSQL...")
        if config.test_database_connection():
            print("✅ PostgreSQL connection successful")
            
            # Get some basic stats
            try:
                import psycopg2
                from psycopg2.extras import RealDictCursor
                
                with psycopg2.connect(config.get_database_url()) as conn:
                    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                        cursor.execute("SELECT COUNT(*) as count FROM entities")
                        result = cursor.fetchone()
                        print(f"  - Entities: {result['count']:,}")
                        
                        cursor.execute("SELECT COUNT(*) as count FROM metadata_entries")
                        result = cursor.fetchone()
                        print(f"  - Metadata entries: {result['count']:,}")
                        
                        cursor.execute("SELECT COUNT(DISTINCT e.id) as count FROM entities e JOIN metadata_entries me ON e.id = me.entity_id WHERE me.key = 'ocr_result'")
                        result = cursor.fetchone()
                        print(f"  - Screenshots with OCR: {result['count']:,}")
                        
            except Exception as e:
                print(f"  - Could not get stats: {e}")
        else:
            print("❌ PostgreSQL connection failed")
            
    except Exception as e:
        print(f"Failed to get database stats: {e}")
        return 1
    
    return 0

def show_config():
    """Show current configuration in detail."""
    try:
        from autotasktracker.config import get_config
        config = get_config()
        
        print("=== AutoTaskTracker Configuration ===")
        config_dict = config.to_dict()
        
        for key, value in config_dict.items():
            if isinstance(value, dict):
                print(f"{key}:")
                for sub_key, sub_value in value.items():
                    print(f"  {sub_key}: {sub_value}")
            else:
                print(f"{key}: {value}")
                
    except Exception as e:
        print(f"Failed to show configuration: {e}")
        return 1
    
    return 0

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="AutoTaskTracker Database Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python db_manager.py status              # Show current status
  python db_manager.py test                # Test PostgreSQL connection
  python db_manager.py stats               # Show database statistics
  python db_manager.py config              # Show full configuration
        """
    )
    
    parser.add_argument(
        'command',
        choices=['status', 'test', 'stats', 'config'],
        help='Command to execute'
    )
    
    args = parser.parse_args()
    
    if args.command == 'status':
        return show_status()
    elif args.command == 'test':
        return test_connection()
    elif args.command == 'stats':
        return get_database_stats()
    elif args.command == 'config':
        return show_config()

if __name__ == "__main__":
    sys.exit(main())