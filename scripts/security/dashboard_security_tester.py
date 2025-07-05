#!/usr/bin/env python3
"""
Basic DAST (Dynamic Application Security Testing) for AutoTaskTracker dashboards.
Tests running Streamlit applications for common security vulnerabilities.

Based on meta-testing best practices for AI-generated code runtime security.
"""

import json
import logging
import requests
import time
import sys
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse
import argparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DashboardSecurityTester:
    """Lightweight DAST scanner for AutoTaskTracker Streamlit dashboards."""
    
    def __init__(self, base_url: str = "http://localhost", timeout: int = 10):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AutoTaskTracker-SecurityTester/1.0'
        })
        
        # Common security test payloads
        self.xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "'\"><script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
        ]
        
        self.injection_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "../../../etc/passwd",
            "../../../../windows/system32/drivers/etc/hosts",
        ]
        
    def test_dashboard_security(self, port: int) -> Dict:
        """Test a single dashboard for security vulnerabilities."""
        dashboard_url = f"{self.base_url}:{port}"
        results = {
            "dashboard_url": dashboard_url,
            "port": port,
            "accessible": False,
            "vulnerabilities": [],
            "security_headers": {},
            "test_results": {},
            "risk_score": 0.0
        }
        
        try:
            # Test 1: Basic connectivity and accessibility
            accessibility_result = self._test_accessibility(dashboard_url)
            results.update(accessibility_result)
            
            if not results["accessible"]:
                logger.warning(f"Dashboard at {dashboard_url} is not accessible")
                return results
                
            # Test 2: Security headers
            headers_result = self._test_security_headers(dashboard_url)
            results["security_headers"] = headers_result
            
            # Test 3: XSS vulnerability testing
            xss_result = self._test_xss_vulnerabilities(dashboard_url)
            results["test_results"]["xss"] = xss_result
            
            # Test 4: Directory traversal testing
            traversal_result = self._test_directory_traversal(dashboard_url)
            results["test_results"]["directory_traversal"] = traversal_result
            
            # Test 5: Information disclosure testing
            info_disclosure_result = self._test_information_disclosure(dashboard_url)
            results["test_results"]["information_disclosure"] = info_disclosure_result
            
            # Test 6: HTTP method testing
            http_methods_result = self._test_http_methods(dashboard_url)
            results["test_results"]["http_methods"] = http_methods_result
            
            # Calculate overall risk score
            results["risk_score"] = self._calculate_risk_score(results)
            
            logger.info(f"Dashboard {dashboard_url}: risk_score={results['risk_score']:.1f}")
            
        except Exception as e:
            logger.error(f"Error testing dashboard {dashboard_url}: {e}")
            results["error"] = str(e)
            results["risk_score"] = 5.0  # Moderate risk for unknown state
            
        return results
        
    def _test_accessibility(self, url: str) -> Dict:
        """Test if the dashboard is accessible."""
        try:
            response = self.session.get(url, timeout=self.timeout)
            return {
                "accessible": response.status_code == 200,
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds()
            }
        except requests.RequestException as e:
            logger.debug(f"Accessibility test failed for {url}: {e}")
            return {
                "accessible": False,
                "error": str(e)
            }
            
    def _test_security_headers(self, url: str) -> Dict:
        """Test for security-related HTTP headers."""
        try:
            response = self.session.get(url, timeout=self.timeout)
            headers = response.headers
            
            security_headers = {
                "Content-Security-Policy": headers.get("Content-Security-Policy"),
                "X-Frame-Options": headers.get("X-Frame-Options"),
                "X-Content-Type-Options": headers.get("X-Content-Type-Options"),
                "X-XSS-Protection": headers.get("X-XSS-Protection"),
                "Strict-Transport-Security": headers.get("Strict-Transport-Security"),
                "Referrer-Policy": headers.get("Referrer-Policy")
            }
            
            missing_headers = [k for k, v in security_headers.items() if v is None]
            
            return {
                "headers": security_headers,
                "missing_headers": missing_headers,
                "security_score": max(0, 10 - len(missing_headers) * 2)
            }
            
        except requests.RequestException as e:
            logger.debug(f"Security headers test failed for {url}: {e}")
            return {"error": str(e)}
            
    def _test_xss_vulnerabilities(self, url: str) -> Dict:
        """Test for XSS vulnerabilities in Streamlit components."""
        vulnerabilities = []
        
        # Test common Streamlit endpoints that might reflect input
        test_endpoints = [
            "/?q=",
            "/component/",
            "/_stcore/",
        ]
        
        for endpoint in test_endpoints:
            for payload in self.xss_payloads:
                try:
                    test_url = f"{url}{endpoint}{payload}"
                    response = self.session.get(test_url, timeout=self.timeout)
                    
                    if payload in response.text and response.status_code == 200:
                        vulnerabilities.append({
                            "type": "Reflected XSS",
                            "endpoint": endpoint,
                            "payload": payload,
                            "severity": "HIGH"
                        })
                        
                except requests.RequestException:
                    continue
                    
        return {
            "vulnerabilities": vulnerabilities,
            "vulnerable": len(vulnerabilities) > 0
        }
        
    def _test_directory_traversal(self, url: str) -> Dict:
        """Test for directory traversal vulnerabilities."""
        vulnerabilities = []
        
        # Test file access patterns that might be exposed
        test_paths = [
            "/static/../../../etc/passwd",
            "/component/../../config.py",
            "/../../../requirements.txt",
            "/assets/../../../.env"
        ]
        
        for path in test_paths:
            try:
                test_url = f"{url}{path}"
                response = self.session.get(test_url, timeout=self.timeout)
                
                # Look for signs of successful traversal
                suspicious_content = [
                    "root:x:",  # /etc/passwd
                    "import ",  # Python files
                    "API_KEY",  # Environment files
                ]
                
                for content in suspicious_content:
                    if content in response.text and response.status_code == 200:
                        vulnerabilities.append({
                            "type": "Directory Traversal",
                            "path": path,
                            "evidence": content,
                            "severity": "HIGH"
                        })
                        break
                        
            except requests.RequestException:
                continue
                
        return {
            "vulnerabilities": vulnerabilities,
            "vulnerable": len(vulnerabilities) > 0
        }
        
    def _test_information_disclosure(self, url: str) -> Dict:
        """Test for information disclosure vulnerabilities."""
        vulnerabilities = []
        
        # Test for common information disclosure endpoints
        test_endpoints = [
            "/debug",
            "/config",
            "/status",
            "/health",
            "/.env",
            "/requirements.txt",
            "/logs",
            "/error"
        ]
        
        for endpoint in test_endpoints:
            try:
                test_url = f"{url}{endpoint}"
                response = self.session.get(test_url, timeout=self.timeout)
                
                if response.status_code == 200:
                    # Check for sensitive information patterns
                    sensitive_patterns = [
                        "API_KEY",
                        "SECRET",
                        "PASSWORD",
                        "TOKEN",
                        "Traceback",
                        "Exception",
                        "sqlite3",
                        "database.db"
                    ]
                    
                    for pattern in sensitive_patterns:
                        if pattern.lower() in response.text.lower():
                            vulnerabilities.append({
                                "type": "Information Disclosure",
                                "endpoint": endpoint,
                                "pattern": pattern,
                                "severity": "MEDIUM"
                            })
                            break
                            
            except requests.RequestException:
                continue
                
        return {
            "vulnerabilities": vulnerabilities,
            "vulnerable": len(vulnerabilities) > 0
        }
        
    def _test_http_methods(self, url: str) -> Dict:
        """Test for dangerous HTTP methods."""
        dangerous_methods = ["TRACE", "DELETE", "PUT", "PATCH"]
        allowed_methods = []
        
        for method in dangerous_methods:
            try:
                response = self.session.request(method, url, timeout=self.timeout)
                if response.status_code not in [405, 501]:  # Method not allowed/not implemented
                    allowed_methods.append(method)
            except requests.RequestException:
                continue
                
        return {
            "dangerous_methods_allowed": allowed_methods,
            "vulnerable": len(allowed_methods) > 0
        }
        
    def _calculate_risk_score(self, results: Dict) -> float:
        """Calculate overall risk score based on test results."""
        risk_score = 0.0
        
        # Security headers score (inverted - missing headers increase risk)
        headers_score = results.get("security_headers", {}).get("security_score", 5)
        risk_score += max(0, 10 - headers_score)
        
        # Vulnerability scores
        test_results = results.get("test_results", {})
        
        for test_name, test_data in test_results.items():
            if test_data.get("vulnerable", False):
                vulnerabilities = test_data.get("vulnerabilities", [])
                for vuln in vulnerabilities:
                    severity = vuln.get("severity", "LOW")
                    if severity == "HIGH":
                        risk_score += 3.0
                    elif severity == "MEDIUM":
                        risk_score += 2.0
                    else:
                        risk_score += 1.0
                        
        return min(risk_score, 10.0)
        
    def test_all_dashboards(self) -> Dict:
        """Test all known AutoTaskTracker dashboard ports."""
        dashboard_ports = {
            8502: "Task Board",
            8503: "Analytics", 
            8505: "Time Tracker",
            8506: "VLM Monitor",
            8507: "Integration Health"
        }
        
        results = {
            "test_timestamp": time.time(),
            "dashboards_tested": len(dashboard_ports),
            "dashboards_accessible": 0,
            "total_vulnerabilities": 0,
            "high_risk_dashboards": [],
            "dashboard_results": []
        }
        
        for port, name in dashboard_ports.items():
            logger.info(f"Testing {name} dashboard on port {port}")
            
            dashboard_result = self.test_dashboard_security(port)
            dashboard_result["dashboard_name"] = name
            results["dashboard_results"].append(dashboard_result)
            
            if dashboard_result.get("accessible", False):
                results["dashboards_accessible"] += 1
                
            # Count vulnerabilities
            for test_data in dashboard_result.get("test_results", {}).values():
                results["total_vulnerabilities"] += len(test_data.get("vulnerabilities", []))
                
            # Track high-risk dashboards
            if dashboard_result.get("risk_score", 0) >= 7.0:
                results["high_risk_dashboards"].append({
                    "name": name,
                    "port": port,
                    "risk_score": dashboard_result["risk_score"]
                })
                
        return results


def main():
    parser = argparse.ArgumentParser(description="DAST security testing for AutoTaskTracker dashboards")
    parser.add_argument("--port", type=int, help="Test specific dashboard port")
    parser.add_argument("--all", action="store_true", help="Test all known dashboard ports")
    parser.add_argument("--base-url", default="http://localhost", help="Base URL for testing")
    parser.add_argument("--output", help="Output file for results")
    parser.add_argument("--fail-on-high-risk", action="store_true", 
                       help="Exit with non-zero code if high-risk vulnerabilities found")
    
    args = parser.parse_args()
    
    tester = DashboardSecurityTester(base_url=args.base_url)
    
    if args.port:
        print(f"🔍 Testing dashboard on port {args.port}")
        result = tester.test_dashboard_security(args.port)
        
        if args.output:
            Path(args.output).write_text(json.dumps(result, indent=2))
        else:
            print(json.dumps(result, indent=2))
            
        if args.fail_on_high_risk and result.get("risk_score", 0) >= 7.0:
            print(f"\n❌ High-risk vulnerabilities found (risk score: {result['risk_score']}/10)")
            sys.exit(1)
            
    elif args.all:
        print(f"🔍 Testing all AutoTaskTracker dashboards")
        results = tester.test_all_dashboards()
        
        if args.output:
            Path(args.output).write_text(json.dumps(results, indent=2))
        else:
            print(json.dumps(results, indent=2))
            
        # Print summary
        print(f"\n📊 Dashboard Security Test Summary:")
        print(f"Dashboards accessible: {results['dashboards_accessible']}/{results['dashboards_tested']}")
        print(f"Total vulnerabilities found: {results['total_vulnerabilities']}")
        print(f"High-risk dashboards: {len(results['high_risk_dashboards'])}")
        
        if results["high_risk_dashboards"]:
            print(f"\n⚠️  High-risk dashboards:")
            for dashboard in results["high_risk_dashboards"]:
                print(f"   - {dashboard['name']} (port {dashboard['port']}, risk: {dashboard['risk_score']}/10)")
                
        if args.fail_on_high_risk and results["high_risk_dashboards"]:
            print(f"\n❌ High-risk vulnerabilities found in dashboards")
            sys.exit(1)
        else:
            print(f"\n✅ Dashboard security test completed")
            
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()