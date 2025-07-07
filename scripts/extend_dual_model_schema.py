#!/usr/bin/env python3
"""
Extend Database Schema for Dual-Model Implementation
Adds new metadata fields for Llama3 session results and workflow analysis.
"""
import sys
import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autotasktracker.config import get_config
from autotasktracker.core.database import DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DualModelSchemaExtension:
    """Manages database schema extension for dual-model implementation."""
    
    def __init__(self):
        """Initialize schema extension manager."""
        self.config = get_config()
        self.db = DatabaseManager()
        
        # Define new metadata fields for dual-model processing
        self.new_metadata_fields = {
            'llama3_session_result': {
                'description': 'Llama3 session-level workflow analysis result',
                'data_type': 'json',
                'source_type': 'llama3',
                'example': {
                    'workflow_type': 'coding',
                    'main_activities': ['editing_code', 'testing'],
                    'efficiency': 'high',
                    'focus_level': 'focused',
                    'session_id': 'session_1',
                    'analysis_timestamp': '2025-01-01T12:00:00Z'
                }
            },
            'workflow_analysis': {
                'description': 'Overall workflow pattern analysis across sessions',
                'data_type': 'json',
                'source_type': 'dual_model',
                'example': {
                    'primary_workflow_type': 'mixed',
                    'session_boundaries': [],
                    'total_duration_minutes': 60,
                    'productivity_indicators': {},
                    'analysis_timestamp': '2025-01-01T12:00:00Z'
                }
            },
            'session_id': {
                'description': 'Session identifier for grouping related screenshots',
                'data_type': 'text',
                'source_type': 'dual_model',
                'example': 'session_20250101_120000'
            },
            'dual_model_processed': {
                'description': 'Flag indicating dual-model processing completion',
                'data_type': 'text',
                'source_type': 'dual_model',
                'example': 'true'
            },
            'dual_model_version': {
                'description': 'Version of dual-model processing used',
                'data_type': 'text',
                'source_type': 'dual_model',
                'example': 'v1.0_minicpmv8b_llama3_8b'
            }
        }
    
    def check_current_schema(self) -> Dict:
        """Check current database schema and existing metadata fields."""
        logger.info("Checking current database schema...")
        
        schema_info = {
            'tables_exist': False,
            'existing_metadata_keys': [],
            'sample_metadata_entries': [],
            'dual_model_entries': [],
            'schema_compatible': True
        }
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if required tables exist
                cursor.execute("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name IN ('entities', 'metadata_entries')
                """)
                tables = [row[0] for row in cursor.fetchall()]
                
                if 'entities' in tables and 'metadata_entries' in tables:
                    schema_info['tables_exist'] = True
                    logger.info("✓ Required tables (entities, metadata_entries) exist")
                else:
                    logger.error(f"✗ Missing required tables. Found: {tables}")
                    schema_info['schema_compatible'] = False
                    return schema_info
                
                # Get existing metadata keys
                cursor.execute("""
                    SELECT DISTINCT key, COUNT(*) as count
                    FROM metadata_entries 
                    GROUP BY key 
                    ORDER BY count DESC
                    LIMIT 20
                """)
                existing_keys = cursor.fetchall()
                schema_info['existing_metadata_keys'] = [
                    {'key': row[0], 'count': row[1]} for row in existing_keys
                ]
                
                logger.info(f"Found {len(existing_keys)} distinct metadata keys")
                for key, count in existing_keys[:10]:
                    logger.info(f"  {key}: {count} entries")
                
                # Check for any existing dual-model entries
                dual_model_keys = [key for key in self.new_metadata_fields.keys()]
                cursor.execute("""
                    SELECT key, COUNT(*) as count
                    FROM metadata_entries 
                    WHERE key = ANY(%s)
                    GROUP BY key
                """, (dual_model_keys,))
                
                dual_entries = cursor.fetchall()
                schema_info['dual_model_entries'] = [
                    {'key': row[0], 'count': row[1]} for row in dual_entries
                ]
                
                if dual_entries:
                    logger.warning("Found existing dual-model entries:")
                    for key, count in dual_entries:
                        logger.warning(f"  {key}: {count} entries")
                
                # Get sample metadata entries
                cursor.execute("""
                    SELECT entity_id, key, value, source_type, data_type, created_at
                    FROM metadata_entries 
                    ORDER BY created_at DESC 
                    LIMIT 5
                """)
                samples = cursor.fetchall()
                schema_info['sample_metadata_entries'] = [
                    {
                        'entity_id': row[0],
                        'key': row[1],
                        'value': row[2][:100] + "..." if len(str(row[2])) > 100 else str(row[2]),
                        'source_type': row[3],
                        'data_type': row[4],
                        'created_at': row[5].isoformat() if row[5] else None
                    }
                    for row in samples
                ]
                
                logger.info("Schema check completed successfully")
                
        except Exception as e:
            logger.error(f"Schema check failed: {e}")
            schema_info['schema_compatible'] = False
            schema_info['error'] = str(e)
        
        return schema_info
    
    def test_metadata_insertion(self) -> bool:
        """Test inserting sample dual-model metadata."""
        logger.info("Testing dual-model metadata insertion...")
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get an existing entity_id for testing
                cursor.execute("SELECT id FROM entities LIMIT 1")
                result = cursor.fetchone()
                if not result:
                    logger.warning("No existing entities found - creating test entity")
                    # Create a minimal test entity in entities table first
                    cursor.execute("""
                        INSERT INTO entities (filepath, timestamp, metadata) 
                        VALUES ('test_dual_model.png', NOW(), '{}')
                        RETURNING id
                    """)
                    test_entity_id = cursor.fetchone()[0]
                else:
                    test_entity_id = result[0]
                    
                logger.info(f"Using entity_id {test_entity_id} for testing")
                
                # Test each new metadata field
                for field_name, field_info in self.new_metadata_fields.items():
                    test_value = field_info['example']
                    
                    # Convert to JSON string if needed
                    if field_info['data_type'] == 'json':
                        test_value = json.dumps(test_value)
                    
                    # Insert test metadata (use unique key suffix to avoid conflicts)
                    test_key = f"{field_name}_test_{int(datetime.now().timestamp())}"
                    cursor.execute("""
                        INSERT INTO metadata_entries 
                        (entity_id, key, value, source_type, data_type, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                    """, (
                        test_entity_id,
                        test_key,
                        test_value,
                        field_info['source_type'],
                        field_info['data_type']
                    ))
                
                # Verify insertion
                cursor.execute("""
                    SELECT key, value, source_type, data_type
                    FROM metadata_entries 
                    WHERE entity_id = %s
                """, (test_entity_id,))
                
                inserted_records = cursor.fetchall()
                
                if len(inserted_records) == len(self.new_metadata_fields):
                    logger.info(f"✓ Successfully inserted {len(inserted_records)} test metadata entries")
                    
                    # Clean up test metadata (keys with test suffix)
                    cursor.execute("""
                        DELETE FROM metadata_entries 
                        WHERE entity_id = %s AND key LIKE '%_test_%'
                    """, (test_entity_id,))
                    
                    # Also clean up test entity if we created it
                    if result is None:  # We created the test entity
                        cursor.execute("DELETE FROM entities WHERE id = %s", (test_entity_id,))
                    
                    conn.commit()
                    logger.info("✓ Test data cleaned up")
                    return True
                else:
                    logger.error(f"✗ Expected {len(self.new_metadata_fields)} records, got {len(inserted_records)}")
                    return False
                    
        except Exception as e:
            logger.error(f"Metadata insertion test failed: {e}")
            return False
    
    def create_schema_migration_script(self) -> str:
        """Create migration script for dual-model schema extension."""
        migration_script = f"""-- Dual-Model Schema Extension Migration
-- Generated: {datetime.now().isoformat()}
-- Purpose: Add metadata support for dual-model VLM processing

-- Note: No schema changes required for PostgreSQL + Pensieve
-- The existing metadata_entries table supports the new dual-model fields

-- New metadata fields that will be used:
"""
        
        for field_name, field_info in self.new_metadata_fields.items():
            migration_script += f"""
-- Field: {field_name}
-- Description: {field_info['description']}
-- Data Type: {field_info['data_type']}
-- Source Type: {field_info['source_type']}
-- Example: {json.dumps(field_info['example'], indent=2)}
"""
        
        migration_script += """
-- Verification queries:

-- 1. Check for dual-model metadata entries
SELECT key, COUNT(*) as count
FROM metadata_entries 
WHERE key IN ('llama3_session_result', 'workflow_analysis', 'session_id', 'dual_model_processed', 'dual_model_version')
GROUP BY key;

-- 2. Sample dual-model entries
SELECT entity_id, key, LEFT(value::text, 100) as value_preview, source_type, created_at
FROM metadata_entries 
WHERE source_type IN ('llama3', 'dual_model')
ORDER BY created_at DESC 
LIMIT 10;

-- 3. Session grouping example
SELECT session_id_meta.value as session_id, COUNT(*) as screenshot_count
FROM metadata_entries session_id_meta
WHERE session_id_meta.key = 'session_id'
GROUP BY session_id_meta.value
ORDER BY screenshot_count DESC;
"""
        
        return migration_script
    
    def validate_dual_model_compatibility(self) -> Dict:
        """Validate that current database is compatible with dual-model processing."""
        logger.info("Validating dual-model compatibility...")
        
        validation_results = {
            'compatible': True,
            'checks_passed': [],
            'checks_failed': [],
            'recommendations': []
        }
        
        # Check 1: Schema compatibility
        schema_info = self.check_current_schema()
        if schema_info['schema_compatible']:
            validation_results['checks_passed'].append("Schema compatibility check")
        else:
            validation_results['checks_failed'].append("Schema compatibility check")
            validation_results['compatible'] = False
        
        # Check 2: Metadata insertion test
        if self.test_metadata_insertion():
            validation_results['checks_passed'].append("Metadata insertion test")
        else:
            validation_results['checks_failed'].append("Metadata insertion test")
            validation_results['compatible'] = False
        
        # Check 3: Existing VLM data
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM metadata_entries 
                    WHERE key LIKE '%vlm%' OR key = 'minicpm_v_result'
                """)
                vlm_count = cursor.fetchone()[0]
                
                if vlm_count > 0:
                    validation_results['checks_passed'].append(f"Existing VLM data found ({vlm_count} entries)")
                    validation_results['recommendations'].append(f"Consider migrating {vlm_count} existing VLM entries to dual-model format")
                else:
                    validation_results['checks_passed'].append("No conflicting VLM data")
        except Exception as e:
            validation_results['checks_failed'].append(f"VLM data check failed: {e}")
        
        # Check 4: Database performance
        try:
            start_time = datetime.now()
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM entities")
                entity_count = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM metadata_entries")
                metadata_count = cursor.fetchone()[0]
            
            query_time = (datetime.now() - start_time).total_seconds()
            
            validation_results['checks_passed'].append(f"Database performance check ({query_time:.2f}s)")
            validation_results['database_stats'] = {
                'entity_count': entity_count,
                'metadata_count': metadata_count,
                'query_time_seconds': query_time
            }
            
            if metadata_count > 100000:
                validation_results['recommendations'].append("Large metadata table - consider indexing optimization")
                
        except Exception as e:
            validation_results['checks_failed'].append(f"Database performance check failed: {e}")
        
        return validation_results
    
    def run_schema_extension(self) -> Dict:
        """Run complete schema extension process."""
        logger.info("Starting dual-model schema extension process...")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'schema_info': {},
            'validation_results': {},
            'migration_script': '',
            'recommendations': []
        }
        
        try:
            # Step 1: Check current schema
            results['schema_info'] = self.check_current_schema()
            
            # Step 2: Validate compatibility
            results['validation_results'] = self.validate_dual_model_compatibility()
            
            # Step 3: Generate migration script
            results['migration_script'] = self.create_schema_migration_script()
            
            # Step 4: Provide recommendations
            if results['validation_results']['compatible']:
                results['success'] = True
                results['recommendations'] = [
                    "✓ Database is compatible with dual-model processing",
                    "✓ No schema changes required - existing metadata_entries table supports new fields",
                    "✓ Begin implementing dual-model workflow",
                    "Consider adding database indexes for session_id queries if processing large volumes"
                ]
            else:
                results['recommendations'] = [
                    "✗ Database compatibility issues detected",
                    "Review failed checks and resolve issues before proceeding",
                    "Consider database backup before implementing fixes"
                ]
            
            logger.info("Schema extension process completed")
            
        except Exception as e:
            logger.error(f"Schema extension process failed: {e}")
            results['error'] = str(e)
            results['recommendations'] = [
                f"Process failed with error: {e}",
                "Check database connectivity and permissions",
                "Review logs for detailed error information"
            ]
        
        return results


def main():
    """Main schema extension function."""
    logger.info("Starting dual-model database schema extension...")
    
    try:
        # Create schema extension manager
        schema_manager = DualModelSchemaExtension()
        
        # Run schema extension process
        results = schema_manager.run_schema_extension()
        
        # Print results
        print("\n" + "="*70)
        print("DUAL-MODEL DATABASE SCHEMA EXTENSION RESULTS")
        print("="*70)
        print(f"Timestamp: {results['timestamp']}")
        print(f"Success: {'✓' if results['success'] else '✗'}")
        
        # Schema info
        schema_info = results.get('schema_info', {})
        if schema_info.get('tables_exist'):
            print(f"✓ Required tables exist")
            print(f"✓ Found {len(schema_info.get('existing_metadata_keys', []))} existing metadata keys")
        
        # Validation results
        validation = results.get('validation_results', {})
        if validation:
            passed = len(validation.get('checks_passed', []))
            failed = len(validation.get('checks_failed', []))
            print(f"Validation: {passed} passed, {failed} failed")
        
        # Recommendations
        recommendations = results.get('recommendations', [])
        if recommendations:
            print("\nRECOMMENDATIONS:")
            for i, rec in enumerate(recommendations, 1):
                print(f"{i:2d}. {rec}")
        
        # Save migration script
        if results.get('migration_script'):
            script_file = "dual_model_migration.sql"
            with open(script_file, 'w') as f:
                f.write(results['migration_script'])
            print(f"\nMigration script saved to: {script_file}")
        
        # Return appropriate exit code
        return 0 if results['success'] else 1
        
    except Exception as e:
        logger.error(f"Schema extension failed: {e}")
        print(f"\n✗ Schema extension failed: {e}")
        return 2


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)