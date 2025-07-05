"""Simplified intelligence engine focused on actionable insights.

This replaces the complex context-intelligence system with a straightforward
approach that focuses on answering: "What specific actions will improve test quality?"
"""

import logging
import os
import re
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# Import shared utilities
try:
    from .shared_utilities import ValidationLimits
except ImportError:
    from shared_utilities import ValidationLimits

# Configuration import with fallback
try:
    from .config import EffectivenessConfig
except ImportError:
    try:
        from config import EffectivenessConfig
    except ImportError:
        # Minimal fallback if config not available
        class EffectivenessConfig:
            def __init__(self):
                self.analysis = type('obj', (object,), {
                    'max_function_lines': 30,
                    'max_hardcoded_items': 3
                })()

logger = logging.getLogger(__name__)


class TestPurpose(Enum):
    """Simple test categorization based on actual purpose."""
    UNIT = "unit"                    # Tests single functions/classes
    INTEGRATION = "integration"      # Tests component interaction  
    E2E = "e2e"                     # Tests complete workflows
    INFRASTRUCTURE = "infrastructure" # Tests tooling/health


@dataclass
class ActionableInsight:
    """A specific, actionable insight for improving test quality."""
    issue: str
    impact: str  # "high", "medium", "low"
    action: str  # Specific thing to do
    example: Optional[str] = None  # Code example if helpful


class SimpleTestAnalyzer:
    """Simplified test analyzer focused on actionable feedback."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.test_dir = project_root / "tests"
        self.config = EffectivenessConfig()
        
    def analyze_test_file(self, test_file: Path) -> List[ActionableInsight]:
        """Analyze a test file and return specific, actionable insights."""
        insights = []
        
        try:
            content = test_file.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return [ActionableInsight(
                issue="Cannot read test file",
                impact="high",
                action="Fix file encoding or permissions"
            )]
        
        # Quick quality checks with specific actions
        insights.extend(self._check_basic_quality(test_file, content))
        insights.extend(self._check_effectiveness_patterns(test_file, content))
        insights.extend(self._check_maintainability(test_file, content))
        
        return insights
    
    def _check_basic_quality(self, test_file: Path, content: str) -> List[ActionableInsight]:
        """Check basic test quality with specific improvement actions."""
        insights = []
        
        # Check for trivial assertions
        if re.search(r'assert True\b|assert 1 == 1|assert "test" == "test"', content):
            insights.append(ActionableInsight(
                issue="Trivial assertions that can't fail",
                impact="high",
                action="Replace with assertions that test actual behavior",
                example="assert result.status == 'success'  # instead of assert True"
            ))
        
        # Check for tests without assertions
        test_functions = re.findall(r'def (test_\w+)\(', content)
        for test_func in test_functions:
            func_content = self._extract_function_content(content, test_func)
            if func_content and 'assert' not in func_content and 'raises' not in func_content:
                insights.append(ActionableInsight(
                    issue=f"Test '{test_func}' has no assertions",
                    impact="high", 
                    action="Add at least one assertion that validates the expected behavior"
                ))
        
        # Check for overly long test functions
        max_lines = getattr(self.config.analysis, 'max_function_lines', ValidationLimits.MAX_FUNCTION_LINES) if hasattr(self, 'config') else ValidationLimits.MAX_FUNCTION_LINES
        for test_func in test_functions:
            func_content = self._extract_function_content(content, test_func)
            if func_content and len(func_content.split('\n')) > max_lines:
                line_count = len(func_content.split('\n'))
                insights.append(ActionableInsight(
                    issue=f"Test '{test_func}' is too long ({line_count} lines)",
                    impact="medium",
                    action="Split into smaller, focused tests or extract helper functions"
                ))
        
        return insights
    
    def _check_effectiveness_patterns(self, test_file: Path, content: str) -> List[ActionableInsight]:
        """Check for patterns that indicate effective vs ineffective testing."""
        insights = []
        
        # Check if tests only validate mocks
        mock_count = len(re.findall(r'\.assert_called|\.call_count|Mock\(\)', content))
        business_assertions = len(re.findall(r'assert.*==.*[^)]', content)) - mock_count
        
        if mock_count > 0 and business_assertions == 0:
            insights.append(ActionableInsight(
                issue="Tests only validate that mocks were called",
                impact="high",
                action="Add assertions that validate actual business logic or return values",
                example="assert result.data['status'] == 'processed'  # Test the actual outcome"
            ))
        
        # Check for missing error condition testing
        has_complex_operations = any(keyword in content.lower() for keyword in [
            'database', 'api', 'request', 'file', 'network', 'connection'
        ])
        has_error_testing = any(pattern in content for pattern in [
            'pytest.raises', 'Exception', 'Error', 'try:', 'except'
        ])
        
        if has_complex_operations and not has_error_testing:
            insights.append(ActionableInsight(
                issue="Complex operations tested but no error conditions",
                impact="high", 
                action="Add tests for failure scenarios using pytest.raises",
                example="with pytest.raises(ConnectionError): api_call_with_bad_config()"
            ))
        
        # Check for missing boundary testing
        has_numeric_operations = bool(re.search(r'range\(|len\(|>\s*\d|<\s*\d', content))
        has_boundary_tests = any(boundary in content for boundary in ['0', '1', '-1', 'empty', '[]', 'max', 'min'])
        
        if has_numeric_operations and not has_boundary_tests:
            insights.append(ActionableInsight(
                issue="Numeric operations tested but no boundary values",
                impact="medium",
                action="Add tests with edge values: 0, 1, -1, empty collections, max values"
            ))
        
        return insights
    
    def _check_maintainability(self, test_file: Path, content: str) -> List[ActionableInsight]:
        """Check for maintainability issues with specific fixes."""
        insights = []
        
        # Check for hardcoded test data
        hardcoded_patterns = [
            r'"test_user_\d+"',
            r'"password123"', 
            r'"http://localhost:\d+"',
            r'"[a-zA-Z0-9]{32,}"'  # Long strings that look like keys/tokens
        ]
        
        hardcoded_count = sum(len(re.findall(pattern, content)) for pattern in hardcoded_patterns)
        max_hardcoded = getattr(self.config.analysis, 'max_hardcoded_items', ValidationLimits.MAX_HARDCODED_ITEMS) if hasattr(self, 'config') else ValidationLimits.MAX_HARDCODED_ITEMS
        if hardcoded_count > max_hardcoded:
            insights.append(ActionableInsight(
                issue=f"Too much hardcoded test data ({hardcoded_count} instances)",
                impact="medium",
                action="Extract test data to fixtures or factories for easier maintenance"
            ))
        
        # Check for test interdependencies
        if re.search(r'global\s+\w+|class.*:\s*\w+\s*=', content):
            insights.append(ActionableInsight(
                issue="Tests may share state through global/class variables",
                impact="medium",
                action="Use fixtures or function-local variables to ensure test independence"
            ))
        
        # Check for missing docstrings on complex tests
        test_functions = re.findall(r'def (test_\w+)\(', content)
        doc_threshold = ValidationLimits.MAX_FUNCTION_LINES // 3  # 1/3 of max function lines
        for test_func in test_functions:
            func_content = self._extract_function_content(content, test_func)
            if func_content and len(func_content.split('\n')) > doc_threshold and '"""' not in func_content:
                insights.append(ActionableInsight(
                    issue=f"Complex test '{test_func}' lacks documentation",
                    impact="low",
                    action="Add docstring explaining what this test validates and why"
                ))
        
        return insights
    
    def _extract_function_content(self, content: str, function_name: str) -> str:
        """Extract the content of a specific function."""
        lines = content.split('\n')
        start_line = None
        
        for i, line in enumerate(lines):
            if f'def {function_name}(' in line:
                start_line = i
                break
        
        if start_line is None:
            return ""
        
        # Extract function body
        function_body = []
        indent_level = None
        
        for i in range(start_line + 1, len(lines)):
            line = lines[i]
            if line.strip() == '':
                function_body.append(line)
                continue
            
            current_indent = len(line) - len(line.lstrip())
            if indent_level is None and line.strip():
                indent_level = current_indent
            
            if line.strip() and current_indent <= indent_level and not line.startswith('#'):
                break
                
            function_body.append(line)
        
        return '\n'.join(function_body)
    
    def get_file_purpose(self, test_file: Path) -> TestPurpose:
        """Determine the primary purpose of a test file."""
        file_path = str(test_file).lower()
        
        if '/e2e/' in file_path or 'end_to_end' in file_path:
            return TestPurpose.E2E
        elif '/integration/' in file_path or 'integration' in file_path:
            return TestPurpose.INTEGRATION
        elif '/health/' in file_path or 'infrastructure' in file_path:
            return TestPurpose.INFRASTRUCTURE
        else:
            return TestPurpose.UNIT
    
    def get_priority_insights(self, insights: List[ActionableInsight]) -> List[ActionableInsight]:
        """Return insights prioritized by impact and ease of fixing."""
        # Sort by impact (high first) then by specificity of action
        return sorted(insights, key=lambda x: (
            0 if x.impact == "high" else 1 if x.impact == "medium" else 2,
            len(x.action)  # More specific actions tend to be longer
        ))


class FocusedTestValidator:
    """Simplified validator that focuses on specific, actionable improvements."""
    
    def __init__(self, project_root: Path):
        self.analyzer = SimpleTestAnalyzer(project_root)
        
    def validate_test_file(self, test_file: Path) -> Dict[str, any]:
        """Validate a test file and return focused, actionable feedback."""
        insights = self.analyzer.analyze_test_file(test_file)
        priority_insights = self.analyzer.get_priority_insights(insights)
        
        # Group insights by impact
        high_impact = [i for i in insights if i.impact == "high"]
        medium_impact = [i for i in insights if i.impact == "medium"] 
        low_impact = [i for i in insights if i.impact == "low"]
        
        # Calculate simple effectiveness score
        total_issues = len(insights)
        high_issues = len(high_impact)
        
        # Use configurable thresholds for effectiveness rating
        poor_threshold = 3
        good_threshold = 2
        
        if high_issues >= poor_threshold:
            effectiveness = "poor"
        elif high_issues >= 1:
            effectiveness = "moderate"
        elif total_issues <= good_threshold:
            effectiveness = "good"
        else:
            effectiveness = "moderate"
        
        return {
            'test_file': test_file.name,
            'effectiveness': effectiveness,
            'total_issues': total_issues,
            'high_priority_actions': [i.action for i in high_impact],
            'medium_priority_actions': [i.action for i in medium_impact],
            'next_steps': self._generate_next_steps(priority_insights[:ValidationLimits.MAX_HARDCODED_ITEMS]),
            'purpose': self.analyzer.get_file_purpose(test_file).value,
            'detailed_insights': [
                {
                    'issue': i.issue,
                    'impact': i.impact,
                    'action': i.action,
                    'example': i.example
                } for i in priority_insights
            ]
        }
    
    def _generate_next_steps(self, top_insights: List[ActionableInsight]) -> List[str]:
        """Generate specific next steps based on top insights."""
        if not top_insights:
            return ["✓ No major issues found - test quality looks good"]
        
        steps = []
        for i, insight in enumerate(top_insights, 1):
            steps.append(f"{i}. {insight.action}")
            
        return steps