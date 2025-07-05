"""Integration testing validator that checks real component interaction.

This module validates whether integration tests actually test integration
between components, rather than just mocked interfaces.
"""

import logging
import ast
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class IntegrationType(Enum):
    """Types of integration that should be tested."""
    DATABASE_API = "database_api"        # Database to API layer
    SERVICE_SERVICE = "service_service"   # Service to service calls
    EXTERNAL_API = "external_api"        # External API integration
    FILE_SYSTEM = "file_system"          # File system operations
    COMPONENT_UI = "component_ui"        # Component to UI integration


@dataclass
class IntegrationIssue:
    """An issue with integration testing."""
    issue_type: str
    description: str
    severity: str  # "critical", "major", "minor"
    suggestion: str
    code_example: Optional[str] = None


@dataclass
class IntegrationQuality:
    """Assessment of integration test quality."""
    test_file: Path
    integration_types_tested: List[IntegrationType]
    integration_types_missing: List[IntegrationType]
    real_integration_percentage: float
    issues: List[IntegrationIssue]
    recommendations: List[str]


class RealIntegrationDetector:
    """Detects whether integration tests test real integration vs mocked interaction."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.src_dir = project_root / "autotasktracker"
        
    def analyze_integration_test(self, test_file: Path) -> IntegrationQuality:
        """Analyze whether an integration test actually tests real integration."""
        try:
            content = test_file.read_text(encoding='utf-8', errors='ignore')
        except (OSError, IOError, UnicodeDecodeError) as e:
            return self._create_error_result(test_file, f"Cannot read test file: {e}")
        
        # Detect what types of integration this test should cover
        expected_integrations = self._detect_expected_integrations(test_file, content)
        
        # Analyze what types are actually tested
        tested_integrations = self._analyze_real_integration_testing(content)
        
        # Find missing integrations
        missing_integrations = [it for it in expected_integrations if it not in tested_integrations]
        
        # Calculate real integration percentage
        real_integration_pct = self._calculate_real_integration_percentage(content)
        
        # Identify specific issues
        issues = self._identify_integration_issues(test_file, content)
        
        # Generate recommendations
        recommendations = self._generate_integration_recommendations(
            tested_integrations, missing_integrations, real_integration_pct, issues
        )
        
        return IntegrationQuality(
            test_file=test_file,
            integration_types_tested=tested_integrations,
            integration_types_missing=missing_integrations,
            real_integration_percentage=real_integration_pct,
            issues=issues,
            recommendations=recommendations
        )
    
    def _detect_expected_integrations(self, test_file: Path, content: str) -> List[IntegrationType]:
        """Detect what types of integration this test should cover based on file name and content."""
        expected = []
        
        file_name = test_file.name.lower()
        content_lower = content.lower()
        
        # Database integration
        if any(term in file_name or term in content_lower for term in [
            'database', 'db', 'repository', 'dao', 'sql', 'query'
        ]):
            expected.append(IntegrationType.DATABASE_API)
        
        # Service to service integration
        if any(term in file_name or term in content_lower for term in [
            'service', 'api', 'client', 'server', 'endpoint'
        ]):
            expected.append(IntegrationType.SERVICE_SERVICE)
        
        # External API integration
        if any(term in content_lower for term in [
            'requests', 'http', 'rest', 'graphql', 'webhook', 'external'
        ]):
            expected.append(IntegrationType.EXTERNAL_API)
        
        # File system integration
        if any(term in content_lower for term in [
            'file', 'path', 'directory', 'write', 'read', 'save', 'load'
        ]):
            expected.append(IntegrationType.FILE_SYSTEM)
        
        # Component to UI integration
        if any(term in file_name or term in content_lower for term in [
            'dashboard', 'ui', 'frontend', 'component', 'widget'
        ]):
            expected.append(IntegrationType.COMPONENT_UI)
        
        return expected
    
    def _analyze_real_integration_testing(self, content: str) -> List[IntegrationType]:
        """Analyze what types of real integration are actually being tested."""
        tested = []
        
        # Database integration patterns
        db_real_patterns = [
            r'with.*get_connection\(\)',  # Real database connection
            r'database.*execute',         # Real query execution
            r'session\.',                # Real database session
            r'\.commit\(\)',             # Real transaction
            # AutoTaskTracker-specific patterns
            r'DatabaseManager\(\)',      # AutoTaskTracker database manager
            r'fetch_tasks\(',           # AutoTaskTracker task queries
            r'entities.*metadata_entries',  # AutoTaskTracker schema
            r'pensieve.*database',      # Pensieve database integration
        ]
        if any(re.search(pattern, content) for pattern in db_real_patterns):
            tested.append(IntegrationType.DATABASE_API)
        
        # Service integration patterns
        service_real_patterns = [
            r'requests\.(get|post|put|delete)',  # Real HTTP calls
            r'\.call\(',                        # Real service calls (not mocked)
            r'subprocess\.',                    # Real process calls
            # AutoTaskTracker-specific patterns
            r'memos\s+(start|stop|ps)',        # Pensieve service commands
            r'pensieve.*api',                  # Pensieve API calls
            r'ollama.*api',                    # Ollama VLM API calls
            r'streamlit.*run',                 # Streamlit service integration
        ]
        # But exclude if heavily mocked
        mock_count = len(re.findall(r'mock|Mock|patch', content, re.IGNORECASE))
        real_call_count = sum(len(re.findall(pattern, content)) for pattern in service_real_patterns)
        
        if real_call_count > 0 and mock_count < real_call_count * 2:
            tested.append(IntegrationType.SERVICE_SERVICE)
        
        # External API integration
        if re.search(r'requests\.(get|post)', content) and 'mock' not in content.lower():
            tested.append(IntegrationType.EXTERNAL_API)
        
        # File system integration
        fs_real_patterns = [
            r'open\(',
            r'\.write\(',
            r'\.read\(',
            r'Path\(',
            r'os\.path',
        ]
        if any(re.search(pattern, content) for pattern in fs_real_patterns):
            # Check if it's not just mocked
            if 'tempfile' in content or 'tmp' in content or mock_count < 2:
                tested.append(IntegrationType.FILE_SYSTEM)
        
        # Component integration
        component_patterns = [
            'streamlit', 'render', 'component',
            # AutoTaskTracker-specific patterns
            'task_board', 'analytics', 'timetracker',  # Dashboard components
            'vlm_monitor', 'achievement_board',        # Specialized dashboards
            'websocket_client',                        # Real-time components
        ]
        if any(pattern in content for pattern in component_patterns):
            tested.append(IntegrationType.COMPONENT_UI)
        
        return tested
    
    def _calculate_real_integration_percentage(self, content: str) -> float:
        """Calculate what percentage of the test involves real integration vs mocking."""
        # Count real integration indicators
        real_indicators = [
            r'with.*connection',
            r'database.*execute',
            r'requests\.(get|post|put|delete)',
            r'subprocess\.',
            r'open\(',
            r'\.write\(',
            r'\.read\(',
            r'streamlit\.',
        ]
        
        real_count = sum(len(re.findall(pattern, content)) for pattern in real_indicators)
        
        # Count mocking indicators
        mock_indicators = [
            r'mock',
            r'Mock\(',
            r'patch',
            r'MagicMock',
            r'return_value',
            r'side_effect',
        ]
        
        mock_count = sum(len(re.findall(pattern, content, re.IGNORECASE)) for pattern in mock_indicators)
        
        total_integration_calls = real_count + mock_count
        if total_integration_calls == 0:
            return 0.0
        
        return (real_count / total_integration_calls) * 100
    
    def _identify_integration_issues(self, test_file: Path, content: str) -> List[IntegrationIssue]:
        """Identify specific issues with integration testing."""
        issues = []
        
        # Issue: All integration points are mocked
        mock_count = len(re.findall(r'mock|Mock|patch', content, re.IGNORECASE))
        integration_calls = len(re.findall(r'database|api|service|request|file', content, re.IGNORECASE))
        
        if mock_count > integration_calls:
            issues.append(IntegrationIssue(
                issue_type="over_mocking",
                description="All integration points are mocked - test may not catch real integration bugs",
                severity="major",
                suggestion="Replace some mocks with real integration (use test database, test files, etc.)",
                code_example="# Instead of: mock_db.execute.return_value = data\n# Use: with test_db.connection() as conn: result = conn.execute(query)"
            ))
        
        # Issue: No error condition testing for integration
        has_integration = any(term in content.lower() for term in ['database', 'api', 'request', 'file'])
        has_error_testing = any(term in content for term in ['pytest.raises', 'Exception', 'Error', 'timeout'])
        
        if has_integration and not has_error_testing:
            issues.append(IntegrationIssue(
                issue_type="missing_error_testing",
                description="Integration test doesn't test error conditions (network failures, timeouts, etc.)",
                severity="major",
                suggestion="Add tests for integration failure scenarios",
                code_example="with pytest.raises(ConnectionError): api_call_with_bad_network()"
            ))
        
        # Issue: No performance/timeout testing
        if has_integration and 'timeout' not in content.lower():
            issues.append(IntegrationIssue(
                issue_type="missing_timeout_testing",
                description="Integration test doesn't validate timeout behavior",
                severity="minor",
                suggestion="Add timeout testing for integration calls"
            ))
        
        # Issue: Hardcoded test data that won't test real scenarios
        hardcoded_patterns = [
            r'"test_"',
            r'"fake_"',
            r'"mock_"',
            r'"dummy_"'
        ]
        hardcoded_count = sum(len(re.findall(pattern, content)) for pattern in hardcoded_patterns)
        
        if hardcoded_count > 5:
            issues.append(IntegrationIssue(
                issue_type="unrealistic_test_data",
                description="Heavy use of obviously fake test data may not catch real integration issues",
                severity="minor",
                suggestion="Use more realistic test data that resembles production scenarios"
            ))
        
        return issues
    
    def _generate_integration_recommendations(self, tested: List[IntegrationType], 
                                            missing: List[IntegrationType],
                                            real_integration_pct: float,
                                            issues: List[IntegrationIssue]) -> List[str]:
        """Generate specific recommendations for improving integration testing."""
        recommendations = []
        
        # Overall assessment
        if real_integration_pct < 30:
            recommendations.append("🚨 CRITICAL: Less than 30% real integration - mostly testing mocks, not actual integration")
        elif real_integration_pct < 60:
            recommendations.append("⚠️ WARNING: Less than 60% real integration - some integration bugs may be missed")
        elif real_integration_pct >= 80:
            recommendations.append("✅ GOOD: High real integration percentage - test likely catches integration bugs")
        
        # Missing integration types
        for missing_type in missing:
            type_recommendations = {
                IntegrationType.DATABASE_API: "Add real database integration testing with test database",
                IntegrationType.SERVICE_SERVICE: "Add real service-to-service communication testing",
                IntegrationType.EXTERNAL_API: "Add external API integration testing (or proper API mocking)",
                IntegrationType.FILE_SYSTEM: "Add file system integration testing with temporary files",
                IntegrationType.COMPONENT_UI: "Add component integration testing with UI rendering"
            }
            recommendations.append(f"Add {type_recommendations[missing_type]}")
        
        # Issue-specific recommendations
        for issue in issues:
            if issue.severity in ["critical", "major"]:
                recommendations.append(f"{issue.suggestion}")
        
        return recommendations
    
    def _create_error_result(self, test_file: Path, error: str) -> IntegrationQuality:
        """Create an error result when analysis fails."""
        return IntegrationQuality(
            test_file=test_file,
            integration_types_tested=[],
            integration_types_missing=[],
            real_integration_percentage=0.0,
            issues=[IntegrationIssue(
                issue_type="analysis_error",
                description=error,
                severity="critical",
                suggestion="Fix the underlying issue to enable analysis"
            )],
            recommendations=[f"Cannot analyze integration: {error}"]
        )


class IntegrationTestValidator:
    """Validates integration tests for real component interaction."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.detector = RealIntegrationDetector(project_root)
        
    def validate_integration_tests(self, test_files: List[Path]) -> Dict[str, any]:
        """Validate integration tests across multiple files."""
        integration_files = [f for f in test_files if self._is_integration_test(f)]
        
        if not integration_files:
            return {
                'total_files': len(test_files),
                'integration_files': 0,
                'overall_quality': 'unknown',
                'recommendations': ['No integration test files found - consider adding integration tests']
            }
        
        results = []
        for test_file in integration_files:
            quality = self.detector.analyze_integration_test(test_file)
            results.append(quality)
        
        # Calculate overall metrics
        avg_real_integration = sum(r.real_integration_percentage for r in results) / len(results)
        total_issues = sum(len(r.issues) for r in results)
        critical_issues = sum(len([i for i in r.issues if i.severity == "critical"]) for r in results)
        
        # Overall quality assessment
        if critical_issues > 0 or avg_real_integration < 30:
            overall_quality = "poor"
        elif avg_real_integration < 60:
            overall_quality = "moderate"
        else:
            overall_quality = "good"
        
        # Compile recommendations
        all_recommendations = []
        for result in results:
            all_recommendations.extend(result.recommendations)
        
        # Deduplicate and prioritize recommendations
        unique_recommendations = list(set(all_recommendations))
        
        return {
            'total_files': len(test_files),
            'integration_files': len(integration_files),
            'overall_quality': overall_quality,
            'average_real_integration_percentage': avg_real_integration,
            'total_issues': total_issues,
            'critical_issues': critical_issues,
            'recommendations': unique_recommendations[:10],  # Top 10 most important
            'detailed_results': [
                {
                    'file': r.test_file.name,
                    'real_integration_pct': r.real_integration_percentage,
                    'tested_types': [t.value for t in r.integration_types_tested],
                    'missing_types': [t.value for t in r.integration_types_missing],
                    'issues': len(r.issues),
                    'top_recommendations': r.recommendations[:3]
                } for r in results
            ]
        }
    
    def _is_integration_test(self, test_file: Path) -> bool:
        """Determine if a test file is an integration test."""
        file_path = str(test_file).lower()
        return any(indicator in file_path for indicator in [
            'integration', 'e2e', 'end_to_end', 'api', 'database', 'service'
        ])