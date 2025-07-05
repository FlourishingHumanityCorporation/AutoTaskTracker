"""Test backend detection and switching patterns."""
import logging
from pathlib import Path
import pytest

from tests.health.shared_file_selection import get_health_test_files, categorize_files

logger = logging.getLogger(__name__)


class TestBackendIntegration:
    """Test for backend detection and switching patterns."""
    
    @classmethod
    def setup_class(cls):
        """Setup test environment."""
        cls.project_root = Path(__file__).parent.parent.parent.parent
        
        # Use shared file selection
        cls.python_files = get_health_test_files(cls.project_root)
        
        # Categorize files
        categories = categorize_files(cls.python_files)
        cls.production_files = categories['production_files']
    
    def test_backend_detection(self):
        """Test that backend detection is implemented properly."""
        detection_issues = []
        
        # Check for backend detection patterns
        backend_files = []
        for file_path in self.production_files:
            try:
                content = file_path.read_text()
                
                if any(term in content for term in [
                    'PENSIEVE_BACKEND', 'backend', 'postgresql', 'sqlite',
                    'get_backend', 'detect_backend'
                ]):
                    backend_files.append(file_path)
                    
                    # Check for proper detection logic
                    has_detection = any(pattern in content for pattern in [
                        'os.environ.get', 'config.get', 
                        'if backend ==', 'backend_type'
                    ])
                    
                    if not has_detection:
                        detection_issues.append(file_path)
            except Exception:
                continue
        
        if detection_issues:
            logger.warning(f"Found {len(detection_issues)} files with backend references but no detection")
            for f in detection_issues[:5]:
                logger.warning(f"  {f.name}")
    
    def test_backend_abstraction(self):
        """Test that backend-specific code is properly abstracted."""
        abstraction_issues = []
        
        # Look for backend-specific code that should be abstracted
        backend_specific_patterns = [
            ('postgresql', ['psycopg2', 'ARRAY', 'jsonb', '::json']),
            ('sqlite', ['sqlite3', 'PRAGMA', 'sqlite_version']),
        ]
        
        for file_path in self.production_files:
            # Skip adapter files and pensieve modules
            if 'adapter' in file_path.name or 'pensieve' in str(file_path):
                continue
                
            try:
                content = file_path.read_text()
                
                for backend, patterns in backend_specific_patterns:
                    for pattern in patterns:
                        if pattern in content:
                            # Check if it's properly abstracted
                            if 'DatabaseManager' not in content and 'Adapter' not in content:
                                abstraction_issues.append({
                                    'file': file_path,
                                    'backend': backend,
                                    'pattern': pattern
                                })
                                break
            except Exception:
                continue
        
        if abstraction_issues:
            error_msg = "BACKEND ABSTRACTION ISSUES\n\n"
            error_msg += f"Found {len(abstraction_issues)} files with backend-specific code:\n\n"
            
            for issue in abstraction_issues[:5]:
                error_msg += f"{issue['file'].name}: {issue['backend']} specific - '{issue['pattern']}'\n"
            
            error_msg += "\nBackend-specific code should be in adapter classes!"
            raise AssertionError(error_msg)
    
    def test_multi_backend_support(self):
        """Test that multi-backend support is implemented consistently."""
        support_issues = []
        
        # Check DatabaseManager for multi-backend support
        db_manager_path = self.project_root / "autotasktracker" / "core" / "database.py"
        
        if db_manager_path.exists():
            content = db_manager_path.read_text()
            
            # Check for backend switching logic
            has_backend_support = any(pattern in content for pattern in [
                'backend', 'adapter', 'get_connection',
                'postgresql', 'sqlite'
            ])
            
            if not has_backend_support:
                support_issues.append("DatabaseManager lacks multi-backend support")
        
        # Check for adapter pattern implementation
        adapter_files = list(self.project_root.glob("**/*adapter*.py"))
        if not adapter_files:
            support_issues.append("No adapter pattern implementation found")
        
        if support_issues:
            logger.warning("Multi-backend support issues:")
            for issue in support_issues:
                logger.warning(f"  {issue}")
    
    def test_backend_configuration(self):
        """Test that backend configuration is handled properly."""
        config_issues = []
        
        # Check for backend configuration
        config_files = [
            self.project_root / "autotasktracker" / "core" / "config.py",
            self.project_root / "autotasktracker" / "core" / "config_manager.py",
        ]
        
        for config_path in config_files:
            if config_path.exists():
                content = config_path.read_text()
                
                # Check for backend configuration
                has_backend_config = any(term in content for term in [
                    'PENSIEVE_BACKEND', 'DATABASE_BACKEND',
                    'backend', 'postgresql', 'sqlite'
                ])
                
                if not has_backend_config:
                    config_issues.append(f"{config_path.name}: No backend configuration")
        
        if config_issues:
            logger.info("Backend configuration suggestions:")
            for issue in config_issues:
                logger.info(f"  {issue}")
    
    def test_migration_readiness(self):
        """Test that code is ready for backend migration."""
        migration_issues = []
        
        # Check for migration blockers
        for file_path in self.production_files:
            try:
                content = file_path.read_text()
                
                # Look for SQLite-specific features
                sqlite_specific = [
                    'AUTOINCREMENT',  # PostgreSQL uses SERIAL
                    'sqlite_sequence',  # SQLite internal
                    'typeof(',  # SQLite function
                    'julianday(',  # SQLite date function
                ]
                
                for feature in sqlite_specific:
                    if feature in content:
                        migration_issues.append({
                            'file': file_path,
                            'feature': feature,
                            'backend': 'SQLite'
                        })
                        break
            except Exception:
                continue
        
        if migration_issues:
            logger.info(f"Backend migration considerations: {len(migration_issues)} files")
            for issue in migration_issues[:5]:
                logger.info(f"  {issue['file'].name}: Uses {issue['backend']}-specific '{issue['feature']}'")
            logger.info("\nConsider using standard SQL or adapter pattern for portability!")