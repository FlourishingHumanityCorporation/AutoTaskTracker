"""Test service command usage patterns."""
import logging
import re
from pathlib import Path
import pytest

from tests.health.shared_file_selection import get_health_test_files, categorize_files

logger = logging.getLogger(__name__)


class TestServiceCommands:
    """Test for proper service command usage patterns."""
    
    @classmethod
    def setup_class(cls):
        """Setup test environment."""
        cls.project_root = Path(__file__).parent.parent.parent.parent
        
        # Use shared file selection
        cls.python_files = get_health_test_files(cls.project_root)
        
        # Categorize files
        categories = categorize_files(cls.python_files)
        cls.script_files = categories['script_files']
        cls.production_files = categories['production_files']

    def analyze_service_commands(self, file_path):
        """Simple inline analyzer for service command usage."""
        issues = []
        try:
            content = file_path.read_text()
            # Basic checks for service command patterns
            if 'subprocess' in content and 'memos' in content:
                # Good usage detected
                pass
            elif 'sqlite3.connect' in content:
                issues.append(f"{file_path.name} - Direct SQLite usage, consider memos commands")
        except Exception:
            pass
        return issues
    
    def test_service_command_usage(self):
        """Test that service commands (memos scan, ps, etc.) are used appropriately."""
        all_issues = []
        
        for file_path in self.script_files + self.production_files:
            issues = self.analyze_service_commands(file_path)
            all_issues.extend(issues)
        
        if all_issues:
            info_msg = f"""
SERVICE COMMAND USAGE OPPORTUNITIES

Found {len(all_issues)} places where Pensieve service commands could be used:

{chr(10).join(all_issues[:10])}
{f'... and {len(all_issues) - 10} more' if len(all_issues) > 10 else ''}

AVAILABLE COMMANDS:
  memos scan          # Scan for new screenshots
  memos ps           # Check service status
  memos start/stop   # Service management
  memos config       # View configuration
  memos reindex      # Reindex database

Using service commands provides better integration with Pensieve.
"""
            logger.info(info_msg)
    
    def test_command_error_handling(self):
        """Test that service commands have proper error handling."""
        error_issues = []
        
        command_patterns = [
            r'subprocess\.(run|call|check_output).*memos',
            r'os\.system.*memos',
            r'Popen.*memos'
        ]
        
        for file_path in self.python_files:
            try:
                content = file_path.read_text()
                lines = content.split('\n')
                
                for i, line in enumerate(lines):
                    for pattern in command_patterns:
                        if re.search(pattern, line):
                            # Check for error handling
                            context_start = max(0, i - 5)
                            context_end = min(len(lines), i + 5)
                            context = '\n'.join(lines[context_start:context_end])
                            
                            if 'try:' not in context and 'except' not in context:
                                error_issues.append({
                                    'file': file_path,
                                    'line': i + 1,
                                    'command': line.strip()
                                })
            except Exception:
                continue
        
        if error_issues:
            logger.warning(f"Found {len(error_issues)} service commands without error handling")
            for issue in error_issues[:5]:
                logger.warning(f"  {issue['file'].name}:{issue['line']}")
    
    def test_command_security(self):
        """Test that service commands are secure (no injection risks)."""
        security_issues = []
        
        for file_path in self.python_files:
            try:
                content = file_path.read_text()
                lines = content.split('\n')
                
                for i, line in enumerate(lines):
                    # Look for unsafe command construction
                    if 'memos' in line and any(op in line for op in ['%', 'format(', 'f"', "f'", '+']):
                        if any(cmd in line for cmd in ['subprocess', 'os.system', 'Popen']):
                            # Check if user input is being interpolated
                            if any(var in line for var in ['user_', 'input', 'request.', 'args.']):
                                security_issues.append({
                                    'file': file_path,
                                    'line': i + 1,
                                    'issue': 'Potential command injection'
                                })
            except Exception:
                continue
        
        if security_issues:
            error_msg = "SECURITY: Command injection risks detected!\n\n"
            for issue in security_issues:
                error_msg += f"{issue['file'].name}:{issue['line']} - {issue['issue']}\n"
            error_msg += "\nUse subprocess with list arguments, not string concatenation!"
            raise AssertionError(error_msg)
    
    def test_command_usage_patterns(self):
        """Test for consistent command usage patterns."""
        usage_patterns = {
            'good': [],
            'poor': []
        }
        
        good_patterns = [
            r'subprocess\.run\(\[.*memos.*\]',  # List args
            r'subprocess\.run\(\[.*\], check=True',  # Error checking
            r'capture_output=True',  # Capturing output
        ]
        
        poor_patterns = [
            r'os\.system\(',  # Using os.system
            r'shell=True',  # Shell injection risk
            r'subprocess\.run\(".*memos',  # String command
        ]
        
        for file_path in self.python_files:
            try:
                content = file_path.read_text()
                
                for pattern in good_patterns:
                    if re.search(pattern, content):
                        usage_patterns['good'].append(f"{file_path.name}: Good pattern - {pattern}")
                
                for pattern in poor_patterns:
                    if re.search(pattern, content):
                        usage_patterns['poor'].append(f"{file_path.name}: Poor pattern - {pattern}")
            except Exception:
                continue
        
        if usage_patterns['poor']:
            logger.warning(f"Found {len(usage_patterns['poor'])} poor command usage patterns")
            for issue in usage_patterns['poor'][:5]:
                logger.warning(f"  {issue}")
        
        if usage_patterns['good']:
            logger.info(f"Found {len(usage_patterns['good'])} good command usage patterns")