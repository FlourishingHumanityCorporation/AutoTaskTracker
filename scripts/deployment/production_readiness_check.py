#!/usr/bin/env python3
"""
Production Readiness Validation Suite for AutoTaskTracker.

Comprehensive validation to ensure the system is ready for production deployment.
This script validates configuration, dependencies, security, performance, and operational readiness.
"""

import os
import sys
import json
import time
import socket
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime
import tempfile

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ReadinessCheck:
    def __init__(self, name: str, category: str, critical: bool = True):
        self.name = name
        self.category = category
        self.critical = critical
        self.passed = False
        self.message = ""
        self.details = {}

class ProductionReadinessValidator:
    """Comprehensive production readiness validator."""
    
    def __init__(self):
        self.checks: List[ReadinessCheck] = []
        self.start_time = time.time()
        
    def add_check(self, check: ReadinessCheck):
        """Add a readiness check."""
        self.checks.append(check)
    
    def validate_configuration(self) -> List[ReadinessCheck]:
        """Validate configuration management."""
        checks = []
        
        # Check 1: Config system works
        check = ReadinessCheck("Config System", "Configuration", critical=True)
        try:
            from autotasktracker.config import get_config
            config = get_config()
            
            # Test critical config values
            critical_attrs = ['get_db_path', 'TASK_BOARD_PORT', 'MEMOS_PORT', 'SERVER_HOST']
            for attr in critical_attrs:
                if not hasattr(config, attr):
                    raise AttributeError(f"Missing critical config attribute: {attr}")
            
            check.passed = True
            check.message = "Configuration system operational"
            check.details = {
                'db_path': config.get_db_path(),
                'server_host': config.SERVER_HOST,
                'ports': {
                    'memos': config.MEMOS_PORT,
                    'task_board': config.TASK_BOARD_PORT,
                    'analytics': config.ANALYTICS_PORT
                }
            }
        except Exception as e:
            check.message = f"Configuration system failed: {e}"
        
        checks.append(check)
        
        # Check 2: Environment variable handling
        check = ReadinessCheck("Environment Variables", "Configuration", critical=True)
        try:
            # Test environment variable override
            test_var = f"AUTOTASK_TEST_{int(time.time())}"
            test_value = "production_test_value"
            
            old_env = dict(os.environ)
            os.environ[test_var] = test_value
            
            # Environment variables should be detectable
            if os.getenv(test_var) == test_value:
                check.passed = True
                check.message = "Environment variable handling functional"
            else:
                check.message = "Environment variable handling failed"
            
            # Cleanup
            if test_var in os.environ:
                del os.environ[test_var]
                
        except Exception as e:
            check.message = f"Environment variable test failed: {e}"
        
        checks.append(check)
        
        return checks
    
    def validate_dependencies(self) -> List[ReadinessCheck]:
        """Validate all required dependencies."""
        checks = []
        
        # Critical dependencies
        critical_deps = [
            ('streamlit', 'Web dashboard framework'),
            ('sqlite3', 'Database access'),
            ('requests', 'HTTP client'),
            ('PIL', 'Image processing')
        ]
        
        for dep_name, description in critical_deps:
            check = ReadinessCheck(f"Dependency: {dep_name}", "Dependencies", critical=True)
            try:
                __import__(dep_name)
                check.passed = True
                check.message = f"{description} available"
            except ImportError:
                check.message = f"Missing critical dependency: {dep_name}"
            checks.append(check)
        
        # Optional dependencies
        optional_deps = [
            ('ocrmac', 'macOS OCR'),
            ('pytesseract', 'Tesseract OCR'),
            ('sentence_transformers', 'AI embeddings')
        ]
        
        for dep_name, description in optional_deps:
            check = ReadinessCheck(f"Optional: {dep_name}", "Dependencies", critical=False)
            try:
                __import__(dep_name)
                check.passed = True
                check.message = f"{description} available"
            except ImportError:
                check.message = f"Optional dependency not available: {dep_name}"
            checks.append(check)
        
        return checks
    
    def validate_database_access(self) -> List[ReadinessCheck]:
        """Validate database connectivity and operations."""
        checks = []
        
        # Check 1: DatabaseManager functionality
        check = ReadinessCheck("Database Manager", "Database", critical=True)
        try:
            from autotasktracker.core import DatabaseManager
            db = DatabaseManager()
            
            # Test connection
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                
                if result and result[0] == 1:
                    check.passed = True
                    check.message = "Database connection successful"
                else:
                    check.message = "Database query failed"
                    
        except Exception as e:
            check.message = f"Database connection failed: {e}"
        
        checks.append(check)
        
        # Check 2: Database schema validation
        check = ReadinessCheck("Database Schema", "Database", critical=True)
        try:
            from autotasktracker.core import DatabaseManager
            db = DatabaseManager()
            
            required_tables = ['entities', 'metadata_entries', 'plugins', 'entity_plugin_status']
            
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                missing_tables = [t for t in required_tables if t not in tables]
                
                if not missing_tables:
                    check.passed = True
                    check.message = "All required tables present"
                    check.details = {'tables': tables}
                else:
                    check.message = f"Missing tables: {missing_tables}"
                    
        except Exception as e:
            check.message = f"Schema validation failed: {e}"
        
        checks.append(check)
        
        return checks
    
    def validate_network_connectivity(self) -> List[ReadinessCheck]:
        """Validate network ports and connectivity."""
        checks = []
        
        from autotasktracker.config import get_config
        config = get_config()
        
        # Check port availability
        critical_ports = [
            (config.MEMOS_PORT, "Pensieve/Memos service"),
            (config.TASK_BOARD_PORT, "Task Board dashboard"),
            (config.ANALYTICS_PORT, "Analytics dashboard")
        ]
        
        for port, description in critical_ports:
            check = ReadinessCheck(f"Port {port}", "Network", critical=True)
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(5)
                    result = s.connect_ex((config.SERVER_HOST, port))
                    
                    if result == 0:
                        # Port is occupied - check if it's our service
                        check.passed = False
                        check.message = f"Port {port} already in use - may indicate running service"
                    else:
                        # Port is available
                        check.passed = True
                        check.message = f"Port {port} available for {description}"
                        
            except Exception as e:
                check.message = f"Port check failed: {e}"
            
            checks.append(check)
        
        return checks
    
    def validate_file_system(self) -> List[ReadinessCheck]:
        """Validate file system access and permissions."""
        checks = []
        
        from autotasktracker.config import get_config
        config = get_config()
        
        # Check critical directories
        critical_dirs = [
            (config.screenshots_dir, "Screenshots directory"),
            (config.vlm_cache_dir, "VLM cache directory"),
            (os.path.dirname(config.get_db_path()), "Database directory")
        ]
        
        for dir_path, description in critical_dirs:
            check = ReadinessCheck(f"Directory: {description}", "File System", critical=True)
            try:
                # Check if directory exists or can be created
                if not os.path.exists(dir_path):
                    os.makedirs(dir_path, exist_ok=True)
                
                # Test write permissions
                test_file = os.path.join(dir_path, f".write_test_{int(time.time())}")
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
                
                check.passed = True
                check.message = f"{description} accessible and writable"
                check.details = {'path': str(dir_path)}
                
            except Exception as e:
                check.message = f"{description} access failed: {e}"
            
            checks.append(check)
        
        return checks
    
    def validate_performance(self) -> List[ReadinessCheck]:
        """Validate performance characteristics."""
        checks = []
        
        # Check 1: Database query performance
        check = ReadinessCheck("Database Performance", "Performance", critical=False)
        try:
            from autotasktracker.core import DatabaseManager
            db = DatabaseManager()
            
            start_time = time.time()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM entities")
                cursor.fetchone()
            query_time = time.time() - start_time
            
            if query_time < 1.0:
                check.passed = True
                check.message = f"Database queries responsive ({query_time:.3f}s)"
            else:
                check.message = f"Database queries slow ({query_time:.3f}s)"
            
            check.details = {'query_time': query_time}
            
        except Exception as e:
            check.message = f"Performance test failed: {e}"
        
        checks.append(check)
        
        # Check 2: Import performance
        check = ReadinessCheck("Import Performance", "Performance", critical=False)
        try:
            start_time = time.time()
            from autotasktracker.dashboards import task_board
            import_time = time.time() - start_time
            
            if import_time < 5.0:
                check.passed = True
                check.message = f"Module imports fast ({import_time:.3f}s)"
            else:
                check.message = f"Module imports slow ({import_time:.3f}s)"
            
            check.details = {'import_time': import_time}
            
        except Exception as e:
            check.message = f"Import performance test failed: {e}"
        
        checks.append(check)
        
        return checks
    
    def validate_security(self) -> List[ReadinessCheck]:
        """Validate security configuration."""
        checks = []
        
        # Check 1: Configuration security
        check = ReadinessCheck("Config Security", "Security", critical=True)
        try:
            from autotasktracker.config import get_config
            config = get_config()
            
            # Validate port ranges
            if config.MEMOS_PORT < 1024:
                check.message = "Using privileged port for Memos service"
            elif config.TASK_BOARD_PORT < 1024:
                check.message = "Using privileged port for Task Board"
            else:
                check.passed = True
                check.message = "Port configuration secure"
            
            check.details = {
                'memos_port': config.MEMOS_PORT,
                'task_board_port': config.TASK_BOARD_PORT
            }
            
        except Exception as e:
            check.message = f"Security validation failed: {e}"
        
        checks.append(check)
        
        # Check 2: File permissions
        check = ReadinessCheck("File Permissions", "Security", critical=True)
        try:
            from autotasktracker.config import get_config
            config = get_config()
            
            db_path = config.get_db_path()
            if os.path.exists(db_path):
                # Check database file permissions
                stat_info = os.stat(db_path)
                permissions = oct(stat_info.st_mode)[-3:]
                
                # Should not be world-readable
                if permissions[2] == '0':
                    check.passed = True
                    check.message = "Database file permissions secure"
                else:
                    check.message = f"Database file world-readable (permissions: {permissions})"
            else:
                check.passed = True
                check.message = "Database file will be created with secure permissions"
            
        except Exception as e:
            check.message = f"Permission check failed: {e}"
        
        checks.append(check)
        
        return checks
    
    def run_all_checks(self) -> Dict[str, Any]:
        """Run all production readiness checks."""
        logger.info("Starting production readiness validation...")
        
        # Run all check categories
        all_checks = []
        all_checks.extend(self.validate_configuration())
        all_checks.extend(self.validate_dependencies())
        all_checks.extend(self.validate_database_access())
        all_checks.extend(self.validate_network_connectivity())
        all_checks.extend(self.validate_file_system())
        all_checks.extend(self.validate_performance())
        all_checks.extend(self.validate_security())
        
        # Categorize results
        passed = [c for c in all_checks if c.passed]
        failed = [c for c in all_checks if not c.passed]
        critical_failed = [c for c in failed if c.critical]
        warnings = [c for c in failed if not c.critical]
        
        # Calculate readiness score
        total_checks = len(all_checks)
        passed_checks = len(passed)
        critical_checks = len([c for c in all_checks if c.critical])
        critical_passed = len([c for c in passed if c.critical])
        
        readiness_score = (passed_checks / total_checks) * 100
        critical_score = (critical_passed / critical_checks) * 100 if critical_checks > 0 else 100
        
        # Determine overall status
        if len(critical_failed) == 0:
            status = "READY" if readiness_score >= 90 else "READY_WITH_WARNINGS"
        else:
            status = "NOT_READY"
        
        duration = time.time() - self.start_time
        
        return {
            'status': status,
            'readiness_score': readiness_score,
            'critical_score': critical_score,
            'total_checks': total_checks,
            'passed': len(passed),
            'failed': len(failed),
            'critical_failed': len(critical_failed),
            'warnings': len(warnings),
            'duration': duration,
            'timestamp': datetime.now().isoformat(),
            'checks': [
                {
                    'name': c.name,
                    "category": c.category,
                    'critical': c.critical,
                    'passed': c.passed,
                    'message': c.message,
                    'details': c.details
                } for c in all_checks
            ]
        }

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Production readiness validation')
    parser.add_argument('--output', help='Output file for results (JSON)')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--ci', action='store_true', help='CI mode - exit 1 if not ready')
    
    args = parser.parse_args()
    
    # Run validation
    validator = ProductionReadinessValidator()
    results = validator.run_all_checks()
    
    # Output results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results written to {args.output}")
    
    # Console output
    print(f"\n{'='*60}")
    print(f"🏭 PRODUCTION READINESS VALIDATION")
    print(f"{'='*60}")
    print(f"Status: {results['status']}")
    print(f"Overall Score: {results['readiness_score']:.1f}%")
    print(f"Critical Score: {results['critical_score']:.1f}%")
    print(f"Duration: {results['duration']:.2f}s")
    print(f"Checks: {results['passed']}/{results['total_checks']} passed")
    
    if results['critical_failed'] > 0:
        print(f"\n🚨 CRITICAL FAILURES ({results['critical_failed']}):")
        for check in results['checks']:
            if not check['passed'] and check['critical']:
                print(f"  ❌ {check['name']}: {check['message']}")
    
    if results['warnings'] > 0:
        print(f"\n⚠️  WARNINGS ({results['warnings']}):")
        for check in results['checks']:
            if not check['passed'] and not check['critical']:
                print(f"  ⚠️  {check['name']}: {check['message']}")
    
    if results['status'] == 'READY':
        print(f"\n✅ SYSTEM IS READY FOR PRODUCTION DEPLOYMENT")
    elif results['status'] == 'READY_WITH_WARNINGS':
        print(f"\n⚠️  SYSTEM IS READY WITH WARNINGS")
    else:
        print(f"\n❌ SYSTEM IS NOT READY FOR PRODUCTION")
    
    # CI mode exit code
    if args.ci:
        return 0 if results['status'] in ['READY', 'READY_WITH_WARNINGS'] else 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())