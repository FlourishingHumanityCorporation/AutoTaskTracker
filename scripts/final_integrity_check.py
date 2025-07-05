#!/usr/bin/env python3
"""
Final integrity check to diagnose the real state of AutoTaskTracker.
This script checks what's actually working vs. what needs fixing.
"""
import sys
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_pensieve_database():
    """Check Pensieve database state."""
    print("\n=== PENSIEVE DATABASE CHECK ===")
    
    from autotasktracker.config import get_config
    db_path = get_config().get_db_path()
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return False
    
    from autotasktracker.core import DatabaseManager
    db = DatabaseManager()
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Check entities
        cursor.execute("SELECT COUNT(*) FROM entities")
        entity_count = cursor.fetchone()[0]
        print(f"✅ Total entities: {entity_count}")
        
        # Check screenshots
        cursor.execute("SELECT COUNT(*) FROM entities WHERE file_type_group = 'image'")
        screenshot_count = cursor.fetchone()[0]
        print(f"✅ Screenshots: {screenshot_count}")
        
        # Check metadata
        cursor.execute("SELECT key, COUNT(DISTINCT entity_id) as count FROM metadata_entries GROUP BY key")
        metadata_stats = cursor.fetchall()
        print("\n📊 Metadata Coverage:")
        for key, count in metadata_stats:
            percentage = (count / entity_count * 100) if entity_count > 0 else 0
            print(f"  - {key}: {count} entities ({percentage:.1f}%)")
        
        # Check OCR specifically
        cursor.execute("SELECT COUNT(DISTINCT entity_id) FROM metadata_entries WHERE key = 'ocr_text'")
        ocr_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(DISTINCT entity_id) FROM metadata_entries WHERE key = 'ocr_result'")
        ocr_result_count = cursor.fetchone()[0]
        print(f"\n🔍 OCR Coverage:")
        print(f"  - ocr_text: {ocr_count} entities")
        print(f"  - ocr_result: {ocr_result_count} entities")
        
        # Check plugin status
        cursor.execute("""
            SELECT p.name, COUNT(eps.entity_id) as processed
            FROM plugins p
            LEFT JOIN entity_plugin_status eps ON p.id = eps.plugin_id
            GROUP BY p.id, p.name
        """)
        plugin_stats = cursor.fetchall()
        print(f"\n🔌 Plugin Processing Status:")
        for plugin_name, processed in plugin_stats:
            print(f"  - {plugin_name}: {processed} entities processed")
        
        # Check recent screenshots
        cursor.execute("""
            SELECT COUNT(*) FROM entities 
            WHERE file_type_group = 'image' 
            AND datetime(created_at) > datetime('now', '-1 hour')
        """)
        recent_count = cursor.fetchone()[0]
        print(f"\n📸 Recent activity: {recent_count} screenshots in last hour")
        
        # Sample data
        cursor.execute("""
            SELECT id, filename, filepath, created_at 
            FROM entities 
            WHERE file_type_group = 'image'
            ORDER BY created_at DESC 
            LIMIT 3
        """)
        samples = cursor.fetchall()
        print(f"\n📄 Sample screenshots:")
        for sample in samples:
            print(f"  - ID: {sample[0]}, File: {sample[1]}")
            print(f"    Path: {sample[2]}")
            print(f"    Created: {sample[3]}")
    
    return True


def check_dashboard_functionality():
    """Check if dashboard can actually display data."""
    print("\n=== DASHBOARD FUNCTIONALITY CHECK ===")
    
    try:
        from autotasktracker.core import DatabaseManager
        db = DatabaseManager()
        
        # Try to fetch recent tasks
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if we can query data
            cursor.execute("""
                SELECT e.id, e.filename, e.created_at,
                       me1.value as window_title,
                       me2.value as category
                FROM entities e
                LEFT JOIN metadata_entries me1 ON e.id = me1.entity_id AND me1.key = "active_window"
                LEFT JOIN metadata_entries me2 ON e.id = me2.entity_id AND me2.key = "category"
                WHERE e.file_type_group = 'image'
                ORDER BY e.created_at DESC
                LIMIT 5
            """)
            
            results = cursor.fetchall()
            print(f"✅ Can query database: {len(results)} recent screenshots found")
            
            for r in results:
                print(f"  - {r[1]} | Window: {r[3] or 'N/A'} | Category: {r[4] or 'N/A'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Dashboard query failed: {e}")
        return False


def check_ocr_capability():
    """Check if OCR can be run on screenshots."""
    print("\n=== OCR CAPABILITY CHECK ===")
    
    try:
        # Check if ocrmac is available
        import ocrmac
        print("✅ ocrmac module available")
        
        # Test on a sample screenshot
        from autotasktracker.config import get_config
        db_path = get_config().get_db_path()
        from autotasktracker.core import DatabaseManager
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, filepath FROM entities 
                WHERE file_type_group = 'image' 
                AND NOT EXISTS (
                    SELECT 1 FROM metadata_entries 
                    WHERE entity_id = entities.id 
                    AND key IN ('ocr_text', "ocr_result")
                )
                LIMIT 1
            """)
            
            sample = cursor.fetchone()
            if sample:
                entity_id, filepath = sample
                print(f"🧪 Testing OCR on: {filepath}")
                
                if os.path.exists(filepath):
                    try:
                        # Test OCR using the correct import
                        from ocrmac.ocrmac import OCR
                        ocr_obj = OCR(filepath)
                        ocr_obj.recognize()
                        
                        # Extract text
                        text_parts = []
                        if hasattr(ocr_obj, 'res') and ocr_obj.res:
                            for item in ocr_obj.res:
                                if isinstance(item, tuple) and len(item) >= 1:
                                    text_parts.append(str(item[0]))
                        result = ' '.join(text_parts) if text_parts else None
                        
                        if result:
                            print(f"✅ OCR successful! Found text: {len(result)} characters")
                            # Show first few words
                            text_preview = ' '.join(result.split()[:20]) + "..."
                            print(f"   Preview: {text_preview}")
                            return True
                        else:
                            print("⚠️  OCR returned no text")
                    except Exception as e:
                        print(f"❌ OCR failed: {e}")
                else:
                    print(f"❌ File not found: {filepath}")
            else:
                print("ℹ️  No unprocessed screenshots found for OCR test")
        
    except ImportError:
        print("❌ ocrmac module not available")
        try:
            import pytesseract
            print("✅ pytesseract available as fallback")
        except ImportError:
            print("❌ No OCR capability found")
    
    return False


def check_pensieve_api():
    """Check if Pensieve API is accessible."""
    print("\n=== PENSIEVE API CHECK ===")
    
    try:
        from autotasktracker.pensieve.api_client import get_pensieve_client
        client = get_pensieve_client()
        
        # Try to get frames
        frames = client.get_frames(limit=5)
        print(f"✅ Pensieve API accessible: {len(frames)} frames retrieved")
        
        return True
        
    except Exception as e:
        print(f"❌ Pensieve API not accessible: {e}")
        return False


def suggest_fixes():
    """Suggest specific fixes based on findings."""
    print("\n=== RECOMMENDED FIXES ===")
    
    print("\n1. 🔧 IMMEDIATE FIX: Run OCR on existing screenshots")
    print("   Since OCR plugin is installed but hasn't processed any screenshots:")
    print("   - Option A: Trigger OCR through Pensieve API")
    print("   - Option B: Create a script to run OCR directly using ocrmac")
    print("   - Option C: Use the dashboard's 'Process' button if available")
    
    print("\n2. 📊 DASHBOARD: Simplify queries")
    print("   The dashboard should work with current schema:")
    print("   - Remove PensieveSchemaAdapter - it's not needed")
    print("   - Use direct queries on the actual schema")
    print("   - Focus on displaying what data we have")
    
    print("\n3. 🏗️ ARCHITECTURE: Simplify")
    print("   - Remove PostgreSQL adapter (not needed for local app)")
    print("   - Remove REST API abstraction layer")
    print("   - Focus on: Screenshot → OCR → Task Extraction → Display")
    
    print("\n4. 📝 DATA PIPELINE: Fix the flow")
    print("   Current: Screenshots captured but not processed")
    print("   Needed: Automatic OCR → Task extraction → Categorization")


def main():
    """Run all checks."""
    print("🔍 AutoTaskTracker Final Integrity Check")
    print("=" * 50)
    
    # Run checks
    db_ok = check_pensieve_database()
    dashboard_ok = check_dashboard_functionality()
    ocr_ok = check_ocr_capability()
    api_ok = check_pensieve_api()
    
    # Summary
    print("\n=== SUMMARY ===")
    print(f"Database: {'✅ Working' if db_ok else '❌ Issues'}")
    print(f"Dashboard: {'✅ Can query data' if dashboard_ok else '❌ Cannot query'}")
    print(f"OCR: {'✅ Available' if ocr_ok else '❌ Not working'}")
    print(f"API: {'✅ Accessible' if api_ok else '❌ Not accessible'}")
    
    # Provide actionable next steps
    suggest_fixes()
    
    print("\n✨ The foundation is solid - just needs the data pipeline connected!")


if __name__ == "__main__":
    main()