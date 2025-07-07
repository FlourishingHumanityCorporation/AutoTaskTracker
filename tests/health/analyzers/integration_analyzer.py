"""
Pensieve integration pattern analyzer for health tests.

Analyzes code for proper Pensieve integration patterns including:
- REST API utilization
- Metadata key consistency
- Service command usage
- Cache management
- Service status checks
"""

import re
import os
from pathlib import Path
from typing import List, Dict, Set, Tuple
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class PensieveIntegrationAnalyzer:
    """Analyzer for Pensieve integration patterns."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
    
    def analyze_rest_api_usage(self, file_path: Path) -> List[Tuple[Path, str]]:
        """Analyze REST API utilization patterns."""
        api_usage = []
        
        api_patterns = [
            r'http[s]?://.*:8841',  # Pensieve default port
            r'localhost:8841',
            r'127\.0\.0\.1:8841',
            r'memos.*api',
            r'/api/screenshots',
            r'/api/metadata',
        ]
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Skip test files
            if 'test_' in file_path.name:
                return api_usage
                
            for pattern in api_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    api_usage.append((file_path, pattern))
                    break
                    
        except Exception as e:
            logger.warning(f"Error analyzing REST API usage in {file_path}: {e}")
        
        return api_usage
    
    def analyze_metadata_consistency(self, file_path: Path) -> Dict[str, Set[Path]]:
        """Analyze metadata key consistency patterns."""
        inconsistent_keys = defaultdict(set)
        
        # Define canonical keys
        canonical_keys = {
            "ocr_result": ["ocr_result", 'text', 'extracted_text'],
            "active_window": ["active_window", 'window', 'app_window'],
            "vlm_structured": ["vlm_structured", 'vlm_description', 'vlm_output'],
            "tasks": ["tasks", 'extracted_tasks', 'task_list'],
            "category": ["category", 'task_category', 'task_type']
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for metadata key usage
            for canonical, variants in canonical_keys.items():
                for variant in variants:
                    # Look for the variant in quotes
                    if re.search(f'["\']({variant})["\']', content):
                        inconsistent_keys[variant].add(file_path)
                        
        except Exception as e:
            logger.warning(f"Error analyzing metadata consistency in {file_path}: {e}")
        
        return inconsistent_keys
    
    def analyze_command_usage(self, file_path: Path) -> List[Tuple[Path, str]]:
        """Analyze memos command usage patterns."""
        command_issues = []
        
        # Look for hardcoded paths or improper command usage
        problematic_patterns = [
            r'subprocess.*["\'].*python.*memos',  # Wrong Python path
            r'os\.system.*memos',  # Using os.system instead of subprocess
            r'["\']memos["\'].*shell=True',  # Shell=True security risk
            r'anaconda3.*memos',  # Wrong environment
        ]
        
        try:
            # Skip the health test file itself to avoid detecting its own examples
            if 'test_pensieve_integration_health.py' in str(file_path):
                return command_issues
                
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            for pattern in problematic_patterns:
                if re.search(pattern, content):
                    command_issues.append((file_path, pattern))
                    
        except Exception as e:
            logger.warning(f"Error analyzing command usage in {file_path}: {e}")
        
        return command_issues
    
    def analyze_cache_management(self, file_path: Path) -> List[Path]:
        """Analyze cache directory management patterns."""
        cache_issues = []
        
        # Look for cache directory usage without cleanup
        cache_patterns = [
            r'vlm_cache',
            r'\.memos/cache',
            r'cache_dir',
        ]
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            for pattern in cache_patterns:
                if re.search(pattern, content):
                    # Check if there's cleanup logic
                    if not any(cleanup in content for cleanup in 
                             ['cleanup', 'clear_cache', 'remove_old', 'cache_size']):
                        cache_issues.append(file_path)
                        break
                        
        except Exception as e:
            logger.warning(f"Error analyzing cache management in {file_path}: {e}")
        
        return cache_issues
    
    def analyze_service_checks(self, file_path: Path) -> List[Path]:
        """Analyze Pensieve service status check patterns."""
        missing_checks = []
        
        # Files that should check memos status but don't
        should_check = ['dashboard', 'task_board', 'analytics', 'autotasktracker.py']
        
        try:
            if any(name in str(file_path) for name in should_check):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Look for service checks
                if not any(check in content for check in 
                         ['memos ps', 'check_memos', 'test_connection', 'is_running']):
                    missing_checks.append(file_path)
                    
        except Exception as e:
            logger.warning(f"Error analyzing service checks in {file_path}: {e}")
        
        return missing_checks
    
    def get_unused_features_report(self) -> Dict[str, str]:
        """Get report of unused Pensieve features."""
        unused_features = {
            'REST API': 'Port 8841 API endpoints',
            'Webhooks': 'Real-time screenshot events',
            'Tagging': 'Entity tagging system',
            'Export/Import': 'Data portability features',
            'Multi-user': 'User management capabilities',
            'Plugins': 'Pensieve plugin system',
            'Advanced Search': 'Full-text search capabilities',
            'Backup': 'Automated backup features',
        }
        return unused_features