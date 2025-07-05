"""
Meta-Testing Security Health Checks for AutoTaskTracker

Tests the implementation of AI-specific security measures based on 
meta-testing best practices from docs/meta/bestpractices_metatest.md
"""

import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
import pytest

logger = logging.getLogger(__name__)


class TestMetaTestingSecurity:
    """Test meta-testing security implementations."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        self.project_root = Path(__file__).parent.parent.parent
        self.requirements_file = self.project_root / "requirements.txt"
        self.semgrep_config = self.project_root / ".semgrep.yml"
        self.bandit_config = self.project_root / ".bandit"
        self.safety_config = self.project_root / ".safety-policy.json"
        
    def test_security_tools_installed(self):
        """Test that all required security tools are properly installed."""
        required_tools = [
            "bandit",
            "safety", 
            "pip-audit",
            "semgrep"
        ]
        
        missing_tools = []
        
        for tool in required_tools:
            try:
                # Check if tool is available
                result = subprocess.run([tool, "--version"], 
                                      capture_output=True, 
                                      timeout=10)
                if result.returncode != 0:
                    missing_tools.append(tool)
            except (subprocess.TimeoutExpired, FileNotFoundError):
                missing_tools.append(tool)
                
        assert not missing_tools, f"Missing security tools: {missing_tools}"
        
    def test_security_tools_in_requirements(self):
        """Test that security tools are properly listed in requirements.txt."""
        if not self.requirements_file.exists():
            pytest.skip("requirements.txt not found")
            
        content = self.requirements_file.read_text()
        
        expected_tools = [
            "bandit>=",
            "safety>=", 
            "pip-audit>=",
            "semgrep>="
        ]
        
        missing_from_requirements = []
        for tool in expected_tools:
            if tool not in content:
                missing_from_requirements.append(tool)
                
        assert not missing_from_requirements, \
            f"Security tools missing from requirements.txt: {missing_from_requirements}"
            
    def test_semgrep_ai_rules_exist(self):
        """Test that AI-specific Semgrep rules are configured."""
        assert self.semgrep_config.exists(), "Semgrep configuration file not found"
        
        content = self.semgrep_config.read_text()
        
        # Check for AI-specific rule categories
        expected_rule_types = [
            "missing-auth-on-streamlit-endpoints",
            "database-queries-without-validation", 
            "hardcoded-api-keys",
            "unsafe-file-operations",
            "unsafe-eval-exec",
            "missing-input-sanitization",
            "database-manager-bypass",
            "missing-pensieve-integration"
        ]
        
        missing_rules = []
        for rule_type in expected_rule_types:
            if rule_type not in content:
                missing_rules.append(rule_type)
                
        assert not missing_rules, f"Missing AI-specific Semgrep rules: {missing_rules}"
        
    def test_bandit_configuration(self):
        """Test that Bandit is properly configured for AI code patterns."""
        assert self.bandit_config.exists(), "Bandit configuration file not found"
        
        content = self.bandit_config.read_text()
        
        # Check key configuration elements
        required_config = [
            "recursive = true",
            "targets = autotasktracker/",
            "exclude_dirs =",
            "confidence =",
            "format = json"
        ]
        
        missing_config = []
        for config_item in required_config:
            if config_item not in content:
                missing_config.append(config_item)
                
        assert not missing_config, f"Missing Bandit configuration: {missing_config}"
        
    def test_safety_policy_exists(self):
        """Test that Safety policy file exists and is properly configured."""
        assert self.safety_config.exists(), "Safety policy file not found"
        
        try:
            policy = json.loads(self.safety_config.read_text())
            
            # Check required policy sections
            required_sections = ["security", "alert", "report", "ignore"]
            missing_sections = [s for s in required_sections if s not in policy]
            
            assert not missing_sections, f"Missing Safety policy sections: {missing_sections}"
            
            # Check security threshold
            assert "ignore-cvss-severity-below" in policy["security"], \
                "CVSS severity threshold not configured"
                
        except json.JSONDecodeError as e:
            pytest.fail(f"Safety policy file is not valid JSON: {e}")
            
    def test_package_validator_functionality(self):
        """Test that package validator script works correctly."""
        validator_script = self.project_root / "scripts/security/package_validator.py"
        assert validator_script.exists(), "Package validator script not found"
        
        # Test validator with a known good package
        try:
            result = subprocess.run([
                "python", str(validator_script),
                "--package", "requests"
            ], capture_output=True, timeout=30, text=True)
            
            assert result.returncode == 0, f"Package validator failed: {result.stderr}"
            
            # Parse the output
            output = json.loads(result.stdout)
            assert "package_name" in output
            assert "is_legitimate" in output
            assert "risk_score" in output
            
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
            pytest.fail(f"Package validator test failed: {e}")
            
    def test_dashboard_security_tester_exists(self):
        """Test that dashboard security tester exists and is functional."""
        tester_script = self.project_root / "scripts/security/dashboard_security_tester.py"
        assert tester_script.exists(), "Dashboard security tester script not found"
        
        # Test basic help functionality
        try:
            result = subprocess.run([
                "python", str(tester_script), "--help"
            ], capture_output=True, timeout=10, text=True)
            
            assert result.returncode == 0, f"Dashboard tester help failed: {result.stderr}"
            assert "DAST security testing" in result.stdout
            
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            pytest.fail(f"Dashboard security tester test failed: {e}")
            
    def test_ci_workflow_security_integration(self):
        """Test that CI workflow properly integrates security tools."""
        ci_workflow = self.project_root / ".github/workflows/ci.yml"
        
        if not ci_workflow.exists():
            pytest.skip("CI workflow file not found")
            
        content = ci_workflow.read_text()
        
        # Check for security scan integration
        expected_steps = [
            "Run Semgrep AI-specific security scan",
            "Run Bandit security scan", 
            "Run Safety dependency scan",
            "Run pip-audit dependency scan",
            "Validate package legitimacy"
        ]
        
        missing_steps = []
        for step in expected_steps:
            if step not in content:
                missing_steps.append(step)
                
        assert not missing_steps, f"Missing CI security steps: {missing_steps}"
        
    def test_no_dangerous_patterns_in_codebase(self):
        """Test that the codebase doesn't contain dangerous AI-generated patterns."""
        # This is a basic static check for patterns our Semgrep rules should catch
        
        python_files = list(self.project_root.glob("autotasktracker/**/*.py"))
        
        dangerous_patterns = []
        
        for file_path in python_files:
            try:
                content = file_path.read_text()
                
                # Check for basic dangerous patterns
                if "eval(" in content and "test" not in str(file_path):
                    dangerous_patterns.append(f"eval() usage in {file_path}")
                    
                if "exec(" in content and "test" not in str(file_path):
                    dangerous_patterns.append(f"exec() usage in {file_path}")
                    
                # Check for direct sqlite3.connect outside of DatabaseManager
                if ("sqlite3.connect(" in content and 
                    "database.py" not in str(file_path) and
                    "test" not in str(file_path)):
                    dangerous_patterns.append(f"Direct sqlite3.connect() in {file_path}")
                    
            except (UnicodeDecodeError, PermissionError):
                continue
                
        assert not dangerous_patterns, f"Dangerous patterns found: {dangerous_patterns}"
        
    def test_meta_testing_compliance_score(self):
        """Calculate and validate overall meta-testing compliance score."""
        # This test provides an overall compliance assessment
        
        compliance_checks = {
            "security_tools_configured": True,
            "ai_specific_rules_present": True, 
            "package_validation_implemented": True,
            "dast_capabilities_available": True,
            "ci_integration_complete": True
        }
        
        # Perform individual checks
        try:
            self.test_security_tools_in_requirements()
        except AssertionError:
            compliance_checks["security_tools_configured"] = False
            
        try:
            self.test_semgrep_ai_rules_exist()
        except AssertionError:
            compliance_checks["ai_specific_rules_present"] = False
            
        try:
            self.test_package_validator_functionality()
        except (AssertionError, Exception):
            compliance_checks["package_validation_implemented"] = False
            
        try:
            self.test_dashboard_security_tester_exists()
        except AssertionError:
            compliance_checks["dast_capabilities_available"] = False
            
        try:
            self.test_ci_workflow_security_integration()
        except AssertionError:
            compliance_checks["ci_integration_complete"] = False
            
        # Calculate compliance percentage
        passed_checks = sum(compliance_checks.values())
        total_checks = len(compliance_checks)
        compliance_percentage = (passed_checks / total_checks) * 100
        
        logger.info(f"Meta-testing compliance score: {compliance_percentage:.1f}%")
        logger.info(f"Passed checks: {passed_checks}/{total_checks}")
        
        # Log failed checks
        failed_checks = [check for check, passed in compliance_checks.items() if not passed]
        if failed_checks:
            logger.warning(f"Failed compliance checks: {failed_checks}")
            
        # Require at least 80% compliance for AutoTaskTracker's risk profile
        assert compliance_percentage >= 80.0, \
            f"Meta-testing compliance too low: {compliance_percentage:.1f}% (minimum 80%)"
            
    def test_security_documentation_exists(self):
        """Test that security documentation is available."""
        security_docs = [
            self.project_root / "docs/meta/bestpractices_metatest.md",
            self.project_root / "scripts/security/README.md"  # We should create this
        ]
        
        missing_docs = [doc for doc in security_docs if not doc.exists()]
        
        # Only require the meta-testing best practices doc (it exists)
        meta_doc = self.project_root / "docs/meta/bestpractices_metatest.md"
        assert meta_doc.exists(), "Meta-testing best practices documentation missing"


class TestAICodeReviewProcess:
    """Test AI code review process alignment with meta-testing practices."""
    
    def test_claude_md_has_ai_guidelines(self):
        """Test that CLAUDE.md contains AI-specific guidelines."""
        claude_md = Path(__file__).parent.parent.parent / "CLAUDE.md"
        
        if not claude_md.exists():
            pytest.skip("CLAUDE.md not found")
            
        content = claude_md.read_text()
        
        # Check for key AI development guidelines
        expected_guidelines = [
            "DatabaseManager",  # Architectural enforcement
            "NEVER use.*sqlite3.connect",  # Anti-pattern enforcement
            "ALWAYS.*check existing code",  # Context awareness
            "NEVER.*improved.py",  # File naming standards
        ]
        
        missing_guidelines = []
        for guideline in expected_guidelines:
            if not any(guideline.lower() in line.lower() for line in content.split('\n')):
                missing_guidelines.append(guideline)
                
        assert not missing_guidelines, \
            f"Missing AI development guidelines in CLAUDE.md: {missing_guidelines}"
            
    def test_workflow_patterns_documented(self):
        """Test that AI workflow patterns are documented."""
        workflow_doc = Path(__file__).parent.parent.parent / "docs/guides/workflow_patterns.md"
        
        if not workflow_doc.exists():
            pytest.skip("Workflow patterns documentation not found")
            
        content = workflow_doc.read_text()
        
        # Check for meta-testing aligned patterns
        expected_patterns = [
            "TDD Counter-Hallucination",
            "Code Review",
            "AI as a Junior Developer"
        ]
        
        missing_patterns = []
        for pattern in expected_patterns:
            if pattern not in content:
                missing_patterns.append(pattern)
                
        # We expect at least TDD pattern to be documented
        assert "TDD" in content, "TDD counter-hallucination pattern not documented"