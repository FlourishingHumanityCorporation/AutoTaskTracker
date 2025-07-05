#!/usr/bin/env python3
"""
Security Metrics Generator for AutoTaskTracker
Tracks and reports on meta-testing security implementation effectiveness.
"""

import json
import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import argparse
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SecurityMetricsGenerator:
    """Generate security metrics for AI code protection."""
    
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.reports_dir = self.project_root / "security-reports"
        self.reports_dir.mkdir(exist_ok=True)
        
    def generate_metrics(self) -> Dict:
        """Generate comprehensive security metrics."""
        logger.info("Generating security metrics...")
        
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "project": "AutoTaskTracker",
            "security_tools": self._analyze_tool_status(),
            "code_analysis": self._analyze_code_quality(),
            "dependency_analysis": self._analyze_dependencies(),
            "compliance_score": self._calculate_compliance_score(),
            "trends": self._analyze_trends(),
            "recommendations": []
        }
        
        # Generate recommendations based on metrics
        metrics["recommendations"] = self._generate_recommendations(metrics)
        
        return metrics
        
    def _analyze_tool_status(self) -> Dict:
        """Analyze security tool status and effectiveness."""
        tool_status = {}
        
        # Check Semgrep
        try:
            result = subprocess.run([
                "semgrep", "--config=.semgrep.yml", 
                "autotasktracker/", "--json", "--quiet"
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                tool_status["semgrep"] = {
                    "status": "active",
                    "findings": len(data.get("results", [])),
                    "rules_count": len(data.get("rules", [])),
                    "scan_time": data.get("time", {}).get("total_time", 0)
                }
            else:
                tool_status["semgrep"] = {"status": "error", "error": result.stderr}
                
        except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
            tool_status["semgrep"] = {"status": "failed", "error": str(e)}
            
        # Check Bandit
        try:
            result = subprocess.run([
                "bandit", "-r", "autotasktracker/", 
                "-f", "json", "--quiet"
            ], capture_output=True, text=True, timeout=60)
            
            if result.stdout:
                data = json.loads(result.stdout)
                tool_status["bandit"] = {
                    "status": "active",
                    "findings": len(data.get("results", [])),
                    "severity_counts": data.get("metrics", {}).get("severity", {}),
                    "confidence_counts": data.get("metrics", {}).get("confidence", {})
                }
            else:
                tool_status["bandit"] = {"status": "no_issues"}
                
        except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
            tool_status["bandit"] = {"status": "failed", "error": str(e)}
            
        # Check pip-audit
        try:
            result = subprocess.run([
                "pip-audit", "--format", "json"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                tool_status["pip_audit"] = {
                    "status": "active",
                    "vulnerabilities": len(data.get("vulnerabilities", [])),
                    "packages_scanned": len(data.get("dependencies", []))
                }
            else:
                tool_status["pip_audit"] = {"status": "error", "error": result.stderr}
                
        except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
            tool_status["pip_audit"] = {"status": "failed", "error": str(e)}
            
        return tool_status
        
    def _analyze_code_quality(self) -> Dict:
        """Analyze code quality metrics."""
        metrics = {
            "total_files": 0,
            "total_lines": 0,
            "ai_pattern_violations": 0,
            "security_hotspots": []
        }
        
        # Count Python files and lines
        python_files = list(self.project_root.glob("autotasktracker/**/*.py"))
        metrics["total_files"] = len(python_files)
        
        for file_path in python_files:
            try:
                content = file_path.read_text()
                metrics["total_lines"] += len(content.splitlines())
                
                # Check for AI anti-patterns
                if "sqlite3.connect(" in content and "database.py" not in str(file_path):
                    metrics["ai_pattern_violations"] += 1
                    metrics["security_hotspots"].append({
                        "file": str(file_path.relative_to(self.project_root)),
                        "issue": "Direct database connection"
                    })
                    
                if "eval(" in content or "exec(" in content:
                    metrics["ai_pattern_violations"] += 1
                    metrics["security_hotspots"].append({
                        "file": str(file_path.relative_to(self.project_root)),
                        "issue": "Unsafe eval/exec usage"
                    })
                    
            except (UnicodeDecodeError, PermissionError):
                continue
                
        # Calculate metrics
        if metrics["total_lines"] > 0:
            metrics["violations_per_kloc"] = (metrics["ai_pattern_violations"] / metrics["total_lines"]) * 1000
        else:
            metrics["violations_per_kloc"] = 0
            
        return metrics
        
    def _analyze_dependencies(self) -> Dict:
        """Analyze dependency security metrics."""
        metrics = {
            "total_dependencies": 0,
            "direct_dependencies": 0,
            "security_advisories": 0,
            "package_ages": {},
            "risk_distribution": {"low": 0, "medium": 0, "high": 0}
        }
        
        # Parse requirements.txt
        requirements_file = self.project_root / "requirements.txt"
        if requirements_file.exists():
            content = requirements_file.read_text()
            dependencies = [line.strip() for line in content.splitlines() 
                          if line.strip() and not line.startswith("#")]
            metrics["direct_dependencies"] = len(dependencies)
            
        # Run package validator for risk assessment
        try:
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent))
            from package_validator import PackageValidator
            validator = PackageValidator()
            
            for dep in dependencies:
                package_name = dep.split(">=")[0].split("==")[0].strip()
                result = validator.validate_package(package_name)
                
                risk_score = result.get("risk_score", 0)
                if risk_score < 3:
                    metrics["risk_distribution"]["low"] += 1
                elif risk_score < 7:
                    metrics["risk_distribution"]["medium"] += 1
                else:
                    metrics["risk_distribution"]["high"] += 1
                    
        except Exception as e:
            logger.warning(f"Could not analyze package risks: {e}")
            
        return metrics
        
    def _calculate_compliance_score(self) -> Dict:
        """Calculate meta-testing compliance score."""
        compliance_checks = {
            "sast_configured": False,
            "sca_configured": False,
            "dast_available": False,
            "ci_integrated": False,
            "documentation_complete": False,
            "git_hooks_enabled": False
        }
        
        # Check SAST configuration
        if (self.project_root / ".semgrep.yml").exists() and (self.project_root / ".bandit").exists():
            compliance_checks["sast_configured"] = True
            
        # Check SCA configuration
        if (self.project_root / ".safety-policy.json").exists():
            compliance_checks["sca_configured"] = True
            
        # Check DAST availability
        if (self.project_root / "scripts/security/dashboard_security_tester.py").exists():
            compliance_checks["dast_available"] = True
            
        # Check CI integration
        ci_file = self.project_root / ".github/workflows/ci.yml"
        if ci_file.exists() and "semgrep" in ci_file.read_text():
            compliance_checks["ci_integrated"] = True
            
        # Check documentation
        if (self.project_root / "docs/security/META_TESTING_IMPLEMENTATION.md").exists():
            compliance_checks["documentation_complete"] = True
            
        # Check git hooks
        if (self.project_root / ".githooks/pre-commit").exists():
            compliance_checks["git_hooks_enabled"] = True
            
        passed = sum(compliance_checks.values())
        total = len(compliance_checks)
        
        return {
            "score": (passed / total) * 100,
            "passed_checks": passed,
            "total_checks": total,
            "details": compliance_checks
        }
        
    def _analyze_trends(self) -> Dict:
        """Analyze security trends over time."""
        # This would normally read from historical data
        # For now, return placeholder data
        return {
            "findings_trend": "stable",
            "new_vulnerabilities_week": 0,
            "fixed_vulnerabilities_week": 0,
            "avg_time_to_fix": "< 24 hours"
        }
        
    def _generate_recommendations(self, metrics: Dict) -> List[str]:
        """Generate actionable recommendations based on metrics."""
        recommendations = []
        
        # Tool-based recommendations
        tool_status = metrics.get("security_tools", {})
        for tool, status in tool_status.items():
            if status.get("status") == "failed":
                recommendations.append(f"Fix {tool} configuration - currently failing")
            elif tool == "semgrep" and status.get("findings", 0) > 10:
                recommendations.append("High number of Semgrep findings - schedule remediation sprint")
                
        # Code quality recommendations
        code_metrics = metrics.get("code_analysis", {})
        if code_metrics.get("violations_per_kloc", 0) > 5:
            recommendations.append("High AI pattern violation rate - review coding standards")
            
        # Dependency recommendations
        dep_metrics = metrics.get("dependency_analysis", {})
        if dep_metrics.get("risk_distribution", {}).get("high", 0) > 0:
            recommendations.append("High-risk dependencies detected - review and replace if possible")
            
        # Compliance recommendations
        compliance = metrics.get("compliance_score", {})
        if compliance.get("score", 0) < 100:
            missing = [k for k, v in compliance.get("details", {}).items() if not v]
            recommendations.append(f"Complete missing compliance items: {', '.join(missing)}")
            
        return recommendations
        
    def generate_report(self, output_format: str = "json") -> str:
        """Generate and save security metrics report."""
        metrics = self.generate_metrics()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if output_format == "json":
            output_file = self.reports_dir / f"security_metrics_{timestamp}.json"
            output_file.write_text(json.dumps(metrics, indent=2))
            
        elif output_format == "markdown":
            output_file = self.reports_dir / f"security_metrics_{timestamp}.md"
            md_content = self._format_as_markdown(metrics)
            output_file.write_text(md_content)
            
        logger.info(f"Report generated: {output_file}")
        return str(output_file)
        
    def _format_as_markdown(self, metrics: Dict) -> str:
        """Format metrics as markdown report."""
        md = f"""# Security Metrics Report

**Generated:** {metrics['timestamp']}  
**Project:** {metrics['project']}

## Executive Summary

**Compliance Score:** {metrics['compliance_score']['score']:.1f}%  
**Active Security Tools:** {sum(1 for t in metrics['security_tools'].values() if t.get('status') == 'active')}  
**Code Quality:** {metrics['code_analysis']['violations_per_kloc']:.2f} violations per KLOC

## Security Tool Status

| Tool | Status | Findings |
|------|---------|----------|
"""
        
        for tool, status in metrics['security_tools'].items():
            findings = status.get('findings', status.get('vulnerabilities', 'N/A'))
            md += f"| {tool} | {status.get('status', 'unknown')} | {findings} |\n"
            
        md += f"""

## Code Analysis

- **Total Files:** {metrics['code_analysis']['total_files']}
- **Total Lines:** {metrics['code_analysis']['total_lines']:,}
- **AI Pattern Violations:** {metrics['code_analysis']['ai_pattern_violations']}

## Dependency Analysis

- **Direct Dependencies:** {metrics['dependency_analysis']['direct_dependencies']}
- **Risk Distribution:**
  - Low Risk: {metrics['dependency_analysis']['risk_distribution']['low']}
  - Medium Risk: {metrics['dependency_analysis']['risk_distribution']['medium']}
  - High Risk: {metrics['dependency_analysis']['risk_distribution']['high']}

## Recommendations

"""
        
        for i, rec in enumerate(metrics['recommendations'], 1):
            md += f"{i}. {rec}\n"
            
        return md


def main():
    parser = argparse.ArgumentParser(description="Generate security metrics report")
    parser.add_argument("--format", choices=["json", "markdown"], 
                       default="json", help="Output format")
    parser.add_argument("--output", help="Output file path")
    
    args = parser.parse_args()
    
    generator = SecurityMetricsGenerator()
    
    if args.output:
        metrics = generator.generate_metrics()
        Path(args.output).write_text(json.dumps(metrics, indent=2))
        print(f"Metrics saved to: {args.output}")
    else:
        report_path = generator.generate_report(args.format)
        print(f"Report generated: {report_path}")
        
        # Print summary
        metrics = generator.generate_metrics()
        print(f"\n📊 Security Metrics Summary:")
        print(f"Compliance Score: {metrics['compliance_score']['score']:.1f}%")
        print(f"Active Tools: {sum(1 for t in metrics['security_tools'].values() if t.get('status') == 'active')}")
        print(f"Code Violations: {metrics['code_analysis']['violations_per_kloc']:.2f} per KLOC")
        
        if metrics['recommendations']:
            print(f"\n📋 Top Recommendations:")
            for rec in metrics['recommendations'][:3]:
                print(f"  • {rec}")


if __name__ == "__main__":
    main()