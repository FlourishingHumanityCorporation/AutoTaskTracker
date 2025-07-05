#!/usr/bin/env python3
"""
Pensieve API Endpoint Monitoring Script
Systematically checks all Pensieve API endpoints and reports availability status.
"""

import sys
import os
import json
import time
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import argparse

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autotasktracker.pensieve.api_client import get_pensieve_client, PensieveAPIError
from autotasktracker.config import get_config

logger = logging.getLogger(__name__)


@dataclass
class EndpointStatus:
    """Status information for a specific endpoint."""
    endpoint: str
    method: str
    available: bool
    status_code: Optional[int]
    response_time_ms: float
    error_message: Optional[str]
    last_check: datetime
    payload_example: Optional[Dict[str, Any]] = None


class PensieveAPIMonitor:
    """Monitor Pensieve API endpoint availability and performance."""
    
    def __init__(self):
        self.api_client = get_pensieve_client()
        self.endpoints_to_test = [
            # Health and basic info
            {"endpoint": "/api/health", "method": "GET", "description": "Health check"},
            {"endpoint": "/api/config", "method": "GET", "description": "Configuration info"},
            
            # Entity endpoints
            {"endpoint": "/api/entities", "method": "GET", "description": "List all entities"},
            {"endpoint": "/api/entities/1", "method": "GET", "description": "Get specific entity"},
            {"endpoint": "/api/entities", "method": "POST", "description": "Create entity"},
            {"endpoint": "/api/entities/1", "method": "PUT", "description": "Update entity"},
            {"endpoint": "/api/entities/1", "method": "DELETE", "description": "Delete entity"},
            
            # Search endpoints
            {"endpoint": "/api/search", "method": "GET", "description": "Search entities"},
            {"endpoint": "/api/search", "method": "POST", "description": "Advanced search"},
            
            # Metadata endpoints
            {"endpoint": "/api/metadata", "method": "GET", "description": "List metadata"},
            {"endpoint": "/api/metadata", "method": "POST", "description": "Create metadata"},
            {"endpoint": "/api/metadata/1", "method": "PUT", "description": "Update metadata"},
            {"endpoint": "/api/metadata/1", "method": "DELETE", "description": "Delete metadata"},
            
            # Library/folder structure
            {"endpoint": "/api/libraries", "method": "GET", "description": "List libraries"},
            {"endpoint": "/api/libraries/1/folders", "method": "GET", "description": "List folders"},
            {"endpoint": "/api/libraries/1/folders/1/entities", "method": "GET", "description": "List entities in folder"},
            
            # Vector/semantic search
            {"endpoint": "/api/vector/search", "method": "POST", "description": "Vector search"},
            {"endpoint": "/api/semantic/search", "method": "POST", "description": "Semantic search"},
            
            # Service management
            {"endpoint": "/api/service/status", "method": "GET", "description": "Service status"},
            {"endpoint": "/api/service/scan", "method": "POST", "description": "Trigger scan"},
            {"endpoint": "/api/service/reindex", "method": "POST", "description": "Trigger reindex"},
        ]
        
        self.results: List[EndpointStatus] = []
    
    def check_endpoint(self, endpoint_info: Dict[str, str]) -> EndpointStatus:
        """Check a specific endpoint and return status."""
        endpoint = endpoint_info["endpoint"]
        method = endpoint_info["method"]
        
        start_time = time.time()
        status = EndpointStatus(
            endpoint=endpoint,
            method=method,
            available=False,
            status_code=None,
            response_time_ms=0.0,
            error_message=None,
            last_check=datetime.now()
        )
        
        try:
            if method == "GET":
                response = self._execute_get_request(endpoint)
            elif method == "POST":
                response = self._execute_post_request(endpoint)
            elif method == "PUT":
                response = self._execute_put_request(endpoint)
            elif method == "DELETE":
                response = self._execute_delete_request(endpoint)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            status.response_time_ms = (time.time() - start_time) * 1000
            status.available = True
            status.status_code = getattr(response, 'status_code', 200)
            
            # Store sample payload if available
            if hasattr(response, 'json') and callable(response.json):
                try:
                    status.payload_example = response.json()
                except:
                    status.payload_example = {"sample": "response data available"}
            
        except Exception as e:
            status.response_time_ms = (time.time() - start_time) * 1000
            status.error_message = str(e)
            
            # Extract status code from error if available
            if hasattr(e, 'status_code'):
                status.status_code = e.status_code
            elif "404" in str(e):
                status.status_code = 404
            elif "405" in str(e):
                status.status_code = 405
            elif "500" in str(e):
                status.status_code = 500
        
        return status
    
    def _execute_get_request(self, endpoint: str):
        """Execute GET request."""
        if endpoint == "/api/health":
            return self.api_client.get_health()
        elif endpoint == "/api/config":
            return self.api_client.get_config()
        elif endpoint == "/api/entities":
            return self.api_client.get_entities(limit=5)
        elif endpoint.startswith("/api/entities/"):
            entity_id = int(endpoint.split("/")[-1])
            return self.api_client.get_entity(entity_id)
        elif endpoint == "/api/search":
            return self.api_client.search_entities("test", limit=5)
        elif endpoint == "/api/libraries":
            return self.api_client.get_libraries()
        elif endpoint == "/api/libraries/1/folders/1/entities":
            return self.api_client.get_entities(limit=5)
        else:
            # Generic request
            import requests
            url = f"{self.api_client.base_url}{endpoint}"
            response = requests.get(url, timeout=self.api_client.timeout)
            response.raise_for_status()
            return response
    
    def _execute_post_request(self, endpoint: str):
        """Execute POST request with sample data."""
        import requests
        url = f"{self.api_client.base_url}{endpoint}"
        
        # Sample payloads for different endpoints
        sample_data = {}
        if "search" in endpoint:
            sample_data = {"query": "test", "limit": 5}
        elif "entities" in endpoint:
            sample_data = {"filepath": "/test/path.png", "metadata": {"test": "data"}}
        elif "metadata" in endpoint:
            sample_data = {"key": "test_key", "value": "test_value", "entity_id": 1}
        elif "scan" in endpoint:
            sample_data = {"path": "/test/path"}
        
        response = requests.post(url, json=sample_data, timeout=self.api_client.timeout)
        response.raise_for_status()
        return response
    
    def _execute_put_request(self, endpoint: str):
        """Execute PUT request with sample data."""
        import requests
        url = f"{self.api_client.base_url}{endpoint}"
        
        sample_data = {"updated": True, "timestamp": datetime.now().isoformat()}
        
        response = requests.put(url, json=sample_data, timeout=self.api_client.timeout)
        response.raise_for_status()
        return response
    
    def _execute_delete_request(self, endpoint: str):
        """Execute DELETE request."""
        import requests
        url = f"{self.api_client.base_url}{endpoint}"
        
        response = requests.delete(url, timeout=self.api_client.timeout)
        response.raise_for_status()
        return response
    
    def check_all_endpoints(self) -> List[EndpointStatus]:
        """Check all endpoints and return results."""
        print("Checking Pensieve API endpoints...")
        self.results = []
        
        for i, endpoint_info in enumerate(self.endpoints_to_test, 1):
            print(f"[{i:2d}/{len(self.endpoints_to_test)}] Checking {endpoint_info['method']} {endpoint_info['endpoint']}")
            
            status = self.check_endpoint(endpoint_info)
            self.results.append(status)
            
            # Brief pause between requests
            time.sleep(0.1)
        
        return self.results
    
    def generate_report(self, format: str = "text") -> str:
        """Generate a report of endpoint status."""
        if format == "json":
            return self._generate_json_report()
        else:
            return self._generate_text_report()
    
    def _generate_text_report(self) -> str:
        """Generate text format report."""
        if not self.results:
            return "No endpoint checks performed yet."
        
        available_count = sum(1 for r in self.results if r.available)
        total_count = len(self.results)
        success_rate = (available_count / total_count) * 100
        
        report = []
        report.append("=" * 80)
        report.append("PENSIEVE API ENDPOINT MONITORING REPORT")
        report.append("=" * 80)
        report.append(f"Check performed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Total endpoints tested: {total_count}")
        report.append(f"Available endpoints: {available_count}")
        report.append(f"Success rate: {success_rate:.1f}%")
        report.append("")
        
        # Available endpoints
        available_endpoints = [r for r in self.results if r.available]
        if available_endpoints:
            report.append("✅ AVAILABLE ENDPOINTS:")
            report.append("-" * 40)
            for result in available_endpoints:
                report.append(f"  {result.method:6} {result.endpoint:40} ({result.response_time_ms:.1f}ms)")
            report.append("")
        
        # Unavailable endpoints  
        unavailable_endpoints = [r for r in self.results if not r.available]
        if unavailable_endpoints:
            report.append("❌ UNAVAILABLE ENDPOINTS:")
            report.append("-" * 40)
            for result in unavailable_endpoints:
                status_info = f"[{result.status_code}]" if result.status_code else "[ERR]"
                report.append(f"  {result.method:6} {result.endpoint:40} {status_info:6} {result.error_message or 'Unknown error'}")
            report.append("")
        
        # Performance summary
        if available_endpoints:
            avg_response_time = sum(r.response_time_ms for r in available_endpoints) / len(available_endpoints)
            max_response_time = max(r.response_time_ms for r in available_endpoints)
            report.append("📊 PERFORMANCE SUMMARY:")
            report.append("-" * 40)
            report.append(f"  Average response time: {avg_response_time:.1f}ms")
            report.append(f"  Maximum response time: {max_response_time:.1f}ms")
            report.append("")
        
        # Recommendations
        report.append("💡 RECOMMENDATIONS:")
        report.append("-" * 40)
        
        if success_rate >= 80:
            report.append("  • API integration is working well")
            report.append("  • Continue using API-first approach with database fallback")
        elif success_rate >= 50:
            report.append("  • Partial API availability - maintain hybrid approach")
            report.append("  • Monitor for additional endpoint availability")
        else:
            report.append("  • Low API availability - rely primarily on database fallback")
            report.append("  • Check Pensieve service status and configuration")
        
        # Check for specific missing endpoints
        missing_critical = [r for r in unavailable_endpoints if r.endpoint in ["/api/entities", "/api/metadata"]]
        if missing_critical:
            report.append("  • Critical data endpoints missing - database fallback is essential")
        
        missing_search = [r for r in unavailable_endpoints if "search" in r.endpoint]
        if missing_search:
            report.append("  • Search endpoints unavailable - use database search implementation")
        
        report.append("")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def _generate_json_report(self) -> str:
        """Generate JSON format report."""
        available_count = sum(1 for r in self.results if r.available)
        total_count = len(self.results)
        
        report_data = {
            "check_timestamp": datetime.now().isoformat(),
            "summary": {
                "total_endpoints": total_count,
                "available_endpoints": available_count,
                "success_rate": (available_count / total_count) * 100 if total_count > 0 else 0
            },
            "endpoints": []
        }
        
        for result in self.results:
            endpoint_data = {
                "endpoint": result.endpoint,
                "method": result.method,
                "available": result.available,
                "status_code": result.status_code,
                "response_time_ms": result.response_time_ms,
                "error_message": result.error_message,
                "last_check": result.last_check.isoformat()
            }
            
            if result.payload_example:
                endpoint_data["payload_example"] = result.payload_example
            
            report_data["endpoints"].append(endpoint_data)
        
        return json.dumps(report_data, indent=2)
    
    def save_report(self, filename: str = None, format: str = "text"):
        """Save report to file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            extension = "json" if format == "json" else "txt"
            filename = f"pensieve_api_report_{timestamp}.{extension}"
        
        report_content = self.generate_report(format)
        
        report_path = os.path.join(os.path.dirname(__file__), "..", filename)
        with open(report_path, "w") as f:
            f.write(report_content)
        
        print(f"Report saved to: {report_path}")
        return report_path
    
    def check_for_new_endpoints(self, previous_results: List[EndpointStatus]) -> List[str]:
        """Compare with previous results to detect newly available endpoints."""
        if not previous_results:
            return []
        
        previous_available = {r.endpoint for r in previous_results if r.available}
        current_available = {r.endpoint for r in self.results if r.available}
        
        newly_available = current_available - previous_available
        return list(newly_available)


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(description="Monitor Pensieve API endpoint availability")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("--save", action="store_true", help="Save report to file")
    parser.add_argument("--watch", action="store_true", help="Continuously monitor endpoints")
    parser.add_argument("--interval", type=int, default=300, help="Watch interval in seconds (default: 300)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Configure logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s')
    
    monitor = PensieveAPIMonitor()
    
    try:
        if args.watch:
            print(f"Monitoring Pensieve API endpoints every {args.interval} seconds...")
            print("Press Ctrl+C to stop")
            
            previous_results = []
            while True:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Checking endpoints...")
                
                results = monitor.check_all_endpoints()
                
                # Check for newly available endpoints
                newly_available = monitor.check_for_new_endpoints(previous_results)
                if newly_available:
                    print(f"🎉 NEW ENDPOINTS AVAILABLE: {', '.join(newly_available)}")
                
                # Show brief summary
                available = sum(1 for r in results if r.available)
                total = len(results)
                print(f"Status: {available}/{total} endpoints available ({available/total*100:.1f}%)")
                
                if args.verbose:
                    print(monitor.generate_report(args.format))
                
                previous_results = results.copy()
                time.sleep(args.interval)
        
        else:
            # Single check
            results = monitor.check_all_endpoints()
            report = monitor.generate_report(args.format)
            
            print(report)
            
            if args.save:
                monitor.save_report(format=args.format)
    
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")
    except Exception as e:
        logger.error(f"Error during monitoring: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())