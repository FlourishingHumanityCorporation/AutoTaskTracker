#!/usr/bin/env python3
"""
Verify that AutoTaskTracker is using config_autotasktracker.yaml everywhere.
"""

import os
import sys
from pathlib import Path

def main():
    """Verify AutoTaskTracker configuration consistency."""
    print("🔍 Verifying AutoTaskTracker configuration consistency...")
    
    # Check that config_autotasktracker.yaml exists
    config_path = Path.home() / ".memos" / "config_autotasktracker.yaml"
    print(f"📁 AutoTaskTracker config file: {config_path}")
    print(f"✅ Exists: {config_path.exists()}")
    
    if config_path.exists():
        with open(config_path, 'r') as f:
            content = f.read()
            if 'autotasktracker' in content and '5432' in content:
                print("✅ Config contains correct database name and port")
            else:
                print("❌ Config may have incorrect database settings")
    
    # Test database connection
    try:
        import psycopg2
        conn = psycopg2.connect('postgresql://postgres:mysecretpassword@localhost:5432/autotasktracker')
        print("✅ PostgreSQL connection successful")
        conn.close()
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
    
    # Check that code references are updated
    print("\n📋 Checking code references...")
    
    import subprocess
    try:
        result = subprocess.run(
            ['grep', '-r', 'config_autotasktracker', 'autotasktracker/'],
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            references = result.stdout.strip().split('\n')
            print(f"✅ Found {len(references)} references to config_autotasktracker.yaml:")
            for ref in references:
                if ref.strip():
                    print(f"   {ref}")
        else:
            print("❌ No references found to config_autotasktracker.yaml")
    except Exception as e:
        print(f"❌ Error checking references: {e}")
    
    print("\n🎯 Configuration verification complete!")

if __name__ == "__main__":
    main()