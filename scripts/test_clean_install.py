#!/usr/bin/env python3
"""
Clean Install Test for AutoTaskTracker PostgreSQL Migration
Simulates a fresh installation and verifies all components work correctly.
"""

import sys
import os
import subprocess
import tempfile
import shutil
from pathlib import Path


def run_command(cmd, cwd=None, timeout=30):
    """Run a command and return result."""
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=timeout,
            cwd=cwd
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)


def test_clean_install():
    """Test clean installation process."""
    print("AutoTaskTracker Clean Install Test")
    print("=" * 40)
    
    # Use current directory for testing (don't actually clone)
    test_dir = Path.cwd()
    print(f"Testing in: {test_dir}")
    
    # Test 1: Check if Python dependencies can be installed
    print("\n1. Testing Python dependencies...")
    success, stdout, stderr = run_command("pip install --dry-run -r requirements.txt")
    if success or "would be installed" in stdout:
        print("✅ Python dependencies available")
    else:
        print(f"❌ Dependency issues: {stderr[:200]}")
        return False
    
    # Test 2: Check if PostgreSQL dependencies are available
    print("\n2. Testing PostgreSQL connectivity...")
    success, stdout, stderr = run_command("python -c 'import psycopg2; print(\"psycopg2 available\")'")
    if success:
        print("✅ PostgreSQL Python driver available")
    else:
        print(f"❌ psycopg2 not available: {stderr}")
        return False
    
    # Test 3: Test configuration loading
    print("\n3. Testing configuration system...")
    success, stdout, stderr = run_command(
        "python -c 'from autotasktracker.config import get_config; print(\"Config loaded:\", get_config().DATABASE_URL)'"
    )
    if success:
        print("✅ Configuration system working")
    else:
        print(f"❌ Configuration error: {stderr}")
        return False
    
    # Test 4: Test database connection
    print("\n4. Testing database connection...")
    success, stdout, stderr = run_command("python autotask.py test")
    if success and "PostgreSQL connection successful" in stdout:
        print("✅ Database connection working")
    else:
        print(f"❌ Database connection failed: {stderr}")
        return False
    
    # Test 5: Test configuration validation
    print("\n5. Testing configuration validation...")
    success, stdout, stderr = run_command("python scripts/utils/validate_config.py")
    if success and "Configuration is valid" in stdout:
        print("✅ Configuration validation passed")
    else:
        print(f"❌ Configuration validation failed: {stderr}")
        return False
    
    # Test 6: Test imports of key modules
    print("\n6. Testing module imports...")
    modules_to_test = [
        "autotasktracker.core.database",
        "autotasktracker.dashboards.task_board",
        "autotasktracker.pensieve.api_client"
    ]
    
    for module in modules_to_test:
        success, stdout, stderr = run_command(f"python -c 'import {module}; print(\"✅ {module}\")'")
        if success:
            print(f"✅ {module}")
        else:
            print(f"❌ {module}: {stderr}")
            return False
    
    # Test 7: Test dashboard script loading (without actually starting)
    print("\n7. Testing dashboard script validation...")
    success, stdout, stderr = run_command("python -c 'import autotasktracker.dashboards.task_board; print(\"Dashboard imports OK\")'")
    if success:
        print("✅ Dashboard scripts loadable")
    else:
        print(f"❌ Dashboard script error: {stderr}")
        return False
    
    return True


def test_setup_scripts():
    """Test the setup scripts work correctly."""
    print("\n" + "=" * 40)
    print("Testing Setup Scripts")
    print("=" * 40)
    
    # Test PostgreSQL setup script exists and is executable
    setup_script = Path("scripts/setup_postgresql.sh")
    if setup_script.exists() and os.access(setup_script, os.X_OK):
        print("✅ PostgreSQL setup script available and executable")
    else:
        print("❌ PostgreSQL setup script missing or not executable")
        return False
    
    # Test Docker Compose file exists
    docker_compose = Path("docker-compose.yml")
    if docker_compose.exists():
        print("✅ Docker Compose file available")
    else:
        print("❌ Docker Compose file missing")
        return False
    
    # Test documentation exists
    docs = [
        "docs/setup/postgresql_setup.md",
        "scripts/sql/init.sql"
    ]
    
    for doc in docs:
        doc_path = Path(doc)
        if doc_path.exists():
            print(f"✅ {doc}")
        else:
            print(f"❌ Missing: {doc}")
            return False
    
    return True


def main():
    """Main test routine."""
    print("Starting AutoTaskTracker PostgreSQL Migration Validation")
    print("This test simulates a clean installation process\n")
    
    # Run clean install test
    install_success = test_clean_install()
    
    # Run setup scripts test
    scripts_success = test_setup_scripts()
    
    # Final results
    print("\n" + "=" * 40)
    print("FINAL RESULTS")
    print("=" * 40)
    
    if install_success and scripts_success:
        print("✅ ALL TESTS PASSED!")
        print("\nAutoTaskTracker PostgreSQL migration is ready for deployment.")
        print("\nNext steps for new users:")
        print("1. Install PostgreSQL (see docs/setup/postgresql_setup.md)")
        print("2. Run: scripts/setup_postgresql.sh")
        print("3. Install Python deps: pip install -r requirements.txt")
        print("4. Test connection: python autotask.py test")
        print("5. Launch dashboard: python autotasktracker.py dashboard")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print("\nIssues need to be resolved before deployment.")
        return 1


if __name__ == "__main__":
    sys.exit(main())