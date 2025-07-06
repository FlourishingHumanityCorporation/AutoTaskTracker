#!/usr/bin/env python3
"""
AutoTaskTracker Quality Assurance Script
Automated compliance checks for continuous quality assurance.
"""
import os
import sys
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from autotasktracker.config import get_config

logger = logging.getLogger(__name__)


class QualityAssuranceChecker:
    """Automated quality assurance checker for AutoTaskTracker."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.results = {}
        self.config = get_config()
    
    def run_health_tests(self) -> Dict[str, Any]:
        """Run all health tests and return results."""
        logger.info("Running health tests...")
        
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/health/", "-v", "--tb=short"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            return {
                'success': result.returncode == 0,
                'output': result.stdout,
                'errors': result.stderr,
                'return_code': result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'output': '',
                'errors': 'Health tests timed out',
                'return_code': -1
            }
        except Exception as e:
            return {
                'success': False,
                'output': '',
                'errors': str(e),
                'return_code': -1
            }
    
    def run_security_tests(self) -> Dict[str, Any]:
        """Run security tests and return results."""
        logger.info("Running security tests...")
        
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/security/", "-v", "--tb=short"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            return {
                'success': result.returncode == 0,
                'output': result.stdout,
                'errors': result.stderr,
                'return_code': result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'output': '',
                'errors': 'Security tests timed out',
                'return_code': -1
            }
        except Exception as e:
            return {
                'success': False,
                'output': '',
                'errors': str(e),
                'return_code': -1
            }
    
    def check_code_quality(self) -> Dict[str, Any]:
        """Check code quality with various tools."""
        logger.info("Checking code quality...")
        
        results = {}
        
        # Run bandit security check
        try:
            result = subprocess.run(
                ["bandit", "-r", "autotasktracker/", "-f", "json"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.stdout:
                bandit_results = json.loads(result.stdout)
                high_severity = [r for r in bandit_results.get('results', []) 
                               if r.get('issue_severity') == 'HIGH']
                results['bandit'] = {
                    'success': len(high_severity) == 0,
                    'high_severity_issues': len(high_severity),
                    'total_issues': len(bandit_results.get('results', [])),
                    'details': high_severity[:5]  # First 5 issues
                }
            else:
                results['bandit'] = {'success': True, 'message': 'No issues found'}
                
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
            results['bandit'] = {'success': False, 'error': str(e)}
        
        return results
    
    def check_import_compliance(self) -> Dict[str, Any]:
        """Check import pattern compliance."""
        logger.info("Checking import compliance...")
        
        violations = []
        
        # Check for relative imports in production code
        for py_file in self.project_root.glob("autotasktracker/**/*.py"):
            try:
                content = py_file.read_text()
                lines = content.split('\n')
                
                for i, line in enumerate(lines):
                    if 'from ...' in line and not line.strip().startswith('#'):
                        violations.append(f"{py_file.relative_to(self.project_root)}:{i+1}")
            except (UnicodeDecodeError, PermissionError):
                continue
        
        return {
            'success': len(violations) == 0,
            'violations': violations,
            'total_violations': len(violations)
        }
    
    def check_claude_md_compliance(self) -> Dict[str, Any]:
        """Check CLAUDE.md rule compliance."""
        logger.info("Checking CLAUDE.md compliance...")
        
        violations = []
        
        # Check for forbidden file patterns
        forbidden_patterns = ['*_improved.py', '*_enhanced.py', '*_v2.py']
        for pattern in forbidden_patterns:
            files = list(self.project_root.glob(f"**/{pattern}"))
            for file in files:
                if 'venv' not in str(file) and 'test' not in str(file):
                    violations.append(f"Forbidden file pattern: {file.relative_to(self.project_root)}")
        
        # Check for print statements in production code
        print_violations = []
        for py_file in self.project_root.glob("autotasktracker/**/*.py"):
            try:
                content = py_file.read_text()
                if 'print(' in content:
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if 'print(' in line and not line.strip().startswith('#'):
                            print_violations.append(f"{py_file.relative_to(self.project_root)}:{i+1}")
            except (UnicodeDecodeError, PermissionError):
                continue
        
        violations.extend(print_violations)
        
        return {
            'success': len(violations) == 0,
            'violations': violations,
            'total_violations': len(violations)
        }
    
    def check_dependency_health(self) -> Dict[str, Any]:
        """Check dependency health and conflicts."""
        logger.info("Checking dependency health...")
        
        try:
            # Check for dependency conflicts
            result = subprocess.run(
                [sys.executable, "-m", "pip", "check"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            conflicts = []
            if result.returncode != 0 and result.stdout:
                conflicts = result.stdout.strip().split('\n')
            
            return {
                'success': result.returncode == 0,
                'conflicts': conflicts,
                'total_conflicts': len(conflicts)
            }
            
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def check_performance_benchmarks(self) -> Dict[str, Any]:
        """Run basic performance benchmarks."""
        logger.info("Running performance benchmarks...")
        
        try:
            # Run performance tests
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/performance/", "-v", "--tb=short"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            return {
                'success': result.returncode == 0,
                'output': result.stdout,
                'errors': result.stderr,
                'return_code': result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'errors': 'Performance tests timed out'
            }
        except Exception as e:
            return {
                'success': False,
                'errors': str(e)
            }
    
    def run_comprehensive_qa(self) -> Dict[str, Any]:
        """Run comprehensive quality assurance checks."""
        logger.info("Starting comprehensive QA check...")
        
        results = {
            'timestamp': __import__('datetime').datetime.now().isoformat(),
            'checks': {}
        }
        
        # Run all checks
        checks = [
            ('health_tests', self.run_health_tests),
            ('security_tests', self.run_security_tests),
            ('code_quality', self.check_code_quality),
            ('import_compliance', self.check_import_compliance),
            ('claude_md_compliance', self.check_claude_md_compliance),
            ('dependency_health', self.check_dependency_health),
            ('performance_benchmarks', self.check_performance_benchmarks)
        ]
        
        for check_name, check_func in checks:
            try:
                logger.info(f"Running {check_name}...")
                results['checks'][check_name] = check_func()
                logger.info(f"Completed {check_name}: {'✅' if results['checks'][check_name].get('success') else '❌'}")
            except Exception as e:
                logger.error(f"Error in {check_name}: {e}")
                results['checks'][check_name] = {
                    'success': False,
                    'error': str(e)
                }
        
        # Calculate overall score
        successful_checks = sum(1 for check in results['checks'].values() if check.get('success'))
        total_checks = len(results['checks'])
        results['overall_score'] = successful_checks / total_checks if total_checks > 0 else 0
        results['summary'] = {
            'successful_checks': successful_checks,
            'total_checks': total_checks,
            'score_percentage': results['overall_score'] * 100
        }
        
        return results
    
    def print_results(self, results: Dict[str, Any]):
        """Print formatted QA results."""
        print("\n" + "="*80)
        print("🔍 AUTOTASKTRACKER QUALITY ASSURANCE REPORT")
        print("="*80)
        
        # Overall score
        score = results['summary']['score_percentage']
        score_icon = "🟢" if score >= 90 else "🟡" if score >= 70 else "🔴"
        print(f"\n{score_icon} Overall Score: {score:.1f}% ({results['summary']['successful_checks']}/{results['summary']['total_checks']} checks passed)")
        
        # Individual check results
        for check_name, check_result in results['checks'].items():
            success = check_result.get('success', False)
            icon = "✅" if success else "❌"
            print(f"\n{icon} {check_name.replace('_', ' ').title()}")
            
            if not success:
                if 'violations' in check_result:
                    print(f"   └─ {check_result['total_violations']} violations found")
                if 'conflicts' in check_result:
                    print(f"   └─ {check_result['total_conflicts']} conflicts found")
                if 'error' in check_result:
                    print(f"   └─ Error: {check_result['error']}")
        
        # Recommendations
        print(f"\n📋 RECOMMENDATIONS:")
        failed_checks = [name for name, result in results['checks'].items() if not result.get('success')]
        
        if not failed_checks:
            print("   🎉 All checks passed! Quality standards are maintained.")
        else:
            print("   Priority fixes needed:")
            for check in failed_checks:
                print(f"   • Fix {check.replace('_', ' ')}")
        
        print("\n" + "="*80)
    
    def save_results(self, results: Dict[str, Any], output_file: Optional[str] = None):
        """Save QA results to file."""
        if not output_file:
            output_file = f"qa_results_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        output_path = self.project_root / output_file
        with output_path.open('w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"QA results saved to {output_path}")


def main():
    """Main QA execution."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    qa_checker = QualityAssuranceChecker()
    
    try:
        results = qa_checker.run_comprehensive_qa()
        qa_checker.print_results(results)
        qa_checker.save_results(results)
        
        # Exit with appropriate code
        if results['overall_score'] >= 0.8:  # 80% threshold
            return 0
        else:
            return 1
            
    except Exception as e:
        logger.error(f"QA check failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())