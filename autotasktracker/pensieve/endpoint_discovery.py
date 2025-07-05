"""
Automated endpoint discovery for Pensieve API integration.
Dynamically discovers and monitors API endpoints for enhanced integration visibility.
"""

import logging
import json
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from urllib.parse import urljoin, urlparse
import re
import requests
from collections import defaultdict, deque

from autotasktracker.pensieve.api_client import get_pensieve_client, PensieveAPIError
from autotasktracker.pensieve.health_monitor import get_health_monitor
from autotasktracker.config import get_config

logger = logging.getLogger(__name__)


@dataclass
class EndpointInfo:
    """Information about a discovered API endpoint."""
    path: str
    method: str
    description: str
    parameters: List[str]
    response_schema: Optional[Dict[str, Any]]
    requires_auth: bool
    rate_limited: bool
    deprecation_info: Optional[str]
    discovered_at: datetime
    last_tested: Optional[datetime] = None
    availability_score: float = 0.0
    average_response_time_ms: float = 0.0
    success_count: int = 0
    failure_count: int = 0


@dataclass
class EndpointGroup:
    """Grouped endpoints by functionality."""
    name: str
    description: str
    endpoints: List[EndpointInfo]
    integration_priority: str  # high, medium, low
    implementation_status: str  # implemented, partial, missing
    notes: str


@dataclass
class DiscoveryStats:
    """Statistics for endpoint discovery process."""
    total_endpoints_discovered: int = 0
    endpoints_tested: int = 0
    endpoints_available: int = 0
    endpoints_implemented: int = 0
    discovery_duration_seconds: float = 0.0
    last_discovery_time: Optional[datetime] = None
    coverage_percentage: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'total_endpoints_discovered': self.total_endpoints_discovered,
            'endpoints_tested': self.endpoints_tested,
            'endpoints_available': self.endpoints_available,
            'endpoints_implemented': self.endpoints_implemented,
            'discovery_duration_seconds': self.discovery_duration_seconds,
            'last_discovery_time': self.last_discovery_time.isoformat() if self.last_discovery_time else None,
            'coverage_percentage': self.coverage_percentage
        }


class EndpointDiscovery:
    """Automated endpoint discovery and monitoring for Pensieve API."""
    
    def __init__(self):
        """Initialize endpoint discovery system."""
        self.api_client = get_pensieve_client()
        self.health_monitor = get_health_monitor()
        
        # Discovery state
        self.discovered_endpoints: Dict[str, EndpointInfo] = {}
        self.endpoint_groups: Dict[str, EndpointGroup] = {}
        self.stats = DiscoveryStats()
        
        # Test results history
        self.test_history: deque = deque(maxlen=1000)
        
        # Known endpoint patterns for proactive discovery
        self.endpoint_patterns = self._get_common_api_patterns()
        
        # Implementation tracking
        self.implemented_endpoints = self._get_implemented_endpoints()
        
        logger.info("Endpoint discovery system initialized")
    
    async def discover_endpoints(self, deep_scan: bool = False) -> Dict[str, Any]:
        """Discover available API endpoints.
        
        Args:
            deep_scan: Whether to perform comprehensive endpoint discovery
            
        Returns:
            Discovery results with endpoint information
        """
        start_time = time.time()
        discovery_results = {
            'endpoints': {},
            'groups': {},
            'stats': {},
            'recommendations': []
        }
        
        try:
            logger.info(f"Starting endpoint discovery (deep_scan={deep_scan})")
            
            # Method 1: Try to get OpenAPI/Swagger spec
            openapi_endpoints = await self._discover_from_openapi()
            
            # Method 2: Probe common REST patterns
            pattern_endpoints = await self._discover_from_patterns()
            
            # Method 3: Deep scan if requested
            deep_endpoints = {}
            if deep_scan:
                deep_endpoints = await self._deep_scan_endpoints()
            
            # Combine all discoveries
            all_endpoints = {**openapi_endpoints, **pattern_endpoints, **deep_endpoints}
            
            # Test discovered endpoints
            tested_endpoints = await self._test_discovered_endpoints(all_endpoints)
            
            # Group endpoints by functionality
            grouped_endpoints = self._group_endpoints(tested_endpoints)
            
            # Analyze implementation gaps
            implementation_analysis = self._analyze_implementation_gaps(tested_endpoints)
            
            # Update internal state
            self.discovered_endpoints = tested_endpoints
            self.endpoint_groups = grouped_endpoints
            
            # Update statistics
            self.stats.total_endpoints_discovered = len(tested_endpoints)
            self.stats.endpoints_tested = len([e for e in tested_endpoints.values() if e.last_tested])
            self.stats.endpoints_available = len([e for e in tested_endpoints.values() if e.availability_score > 0.5])
            self.stats.endpoints_implemented = len([e for e in tested_endpoints.values() if e.path in self.implemented_endpoints])
            self.stats.discovery_duration_seconds = time.time() - start_time
            self.stats.last_discovery_time = datetime.now()
            self.stats.coverage_percentage = (self.stats.endpoints_implemented / max(self.stats.total_endpoints_discovered, 1)) * 100
            
            # Prepare results
            discovery_results = {
                'endpoints': {path: asdict(info) for path, info in tested_endpoints.items()},
                'groups': {name: asdict(group) for name, group in grouped_endpoints.items()},
                'stats': self.stats.to_dict(),
                'implementation_analysis': implementation_analysis,
                'recommendations': self._generate_integration_recommendations(tested_endpoints)
            }
            
            logger.info(f"Discovery completed: {len(tested_endpoints)} endpoints found in {self.stats.discovery_duration_seconds:.2f}s")
            return discovery_results
            
        except Exception as e:
            logger.error(f"Endpoint discovery failed: {e}")
            self.stats.discovery_duration_seconds = time.time() - start_time
            return {'error': str(e), 'stats': self.stats.to_dict()}
    
    async def monitor_endpoints_continuous(self, interval_minutes: int = 15):
        """Continuously monitor discovered endpoints.
        
        Args:
            interval_minutes: Monitoring interval in minutes
        """
        logger.info(f"Starting continuous endpoint monitoring (interval: {interval_minutes}m)")
        
        while True:
            try:
                # Test all discovered endpoints
                if self.discovered_endpoints:
                    await self._test_discovered_endpoints(self.discovered_endpoints)
                
                # Update health scores
                self._update_health_scores()
                
                # Check for new endpoints periodically
                if len(self.test_history) % 4 == 0:  # Every 4th cycle
                    new_endpoints = await self._discover_from_patterns()
                    for path, info in new_endpoints.items():
                        if path not in self.discovered_endpoints:
                            logger.info(f"New endpoint discovered: {path}")
                            self.discovered_endpoints[path] = info
                
                await asyncio.sleep(interval_minutes * 60)
                
            except asyncio.CancelledError:
                logger.info("Continuous monitoring cancelled")
                break
            except Exception as e:
                logger.error(f"Monitoring cycle failed: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def get_integration_status(self) -> Dict[str, Any]:
        """Get comprehensive integration status report.
        
        Returns:
            Integration status with recommendations
        """
        try:
            # Calculate integration metrics
            total_endpoints = len(self.discovered_endpoints)
            available_endpoints = len([e for e in self.discovered_endpoints.values() if e.availability_score > 0.5])
            implemented_endpoints = len([e for e in self.discovered_endpoints.values() if e.path in self.implemented_endpoints])
            
            integration_score = (implemented_endpoints / max(total_endpoints, 1)) * 100
            availability_score = (available_endpoints / max(total_endpoints, 1)) * 100
            
            # Group analysis
            group_status = {}
            for group_name, group in self.endpoint_groups.items():
                group_total = len(group.endpoints)
                group_available = len([e for e in group.endpoints if e.availability_score > 0.5])
                group_implemented = len([e for e in group.endpoints if e.path in self.implemented_endpoints])
                
                group_status[group_name] = {
                    'total_endpoints': group_total,
                    'available_endpoints': group_available,
                    'implemented_endpoints': group_implemented,
                    'availability_percentage': (group_available / max(group_total, 1)) * 100,
                    'implementation_percentage': (group_implemented / max(group_total, 1)) * 100,
                    'priority': group.integration_priority,
                    'status': group.implementation_status
                }
            
            # Recent performance
            recent_tests = list(self.test_history)[-50:]  # Last 50 tests
            avg_response_time = sum(t.get('response_time_ms', 0) for t in recent_tests) / max(len(recent_tests), 1)
            success_rate = len([t for t in recent_tests if t.get('success', False)]) / max(len(recent_tests), 1) * 100
            
            return {
                'overall_metrics': {
                    'integration_score_percentage': round(integration_score, 1),
                    'availability_score_percentage': round(availability_score, 1),
                    'total_endpoints_discovered': total_endpoints,
                    'endpoints_available': available_endpoints,
                    'endpoints_implemented': implemented_endpoints,
                    'recent_success_rate_percentage': round(success_rate, 1),
                    'average_response_time_ms': round(avg_response_time, 1)
                },
                'group_analysis': group_status,
                'discovery_stats': self.stats.to_dict(),
                'performance_trends': self._get_performance_trends(),
                'next_actions': self._get_integration_next_actions(),
                'health_status': {
                    'api_client_healthy': self.api_client.is_healthy() if self.api_client else False,
                    'monitoring_active': self.health_monitor.is_monitoring_active() if self.health_monitor else False,
                    'last_discovery': self.stats.last_discovery_time.isoformat() if self.stats.last_discovery_time else None
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get integration status: {e}")
            return {'error': str(e)}
    
    async def _discover_from_openapi(self) -> Dict[str, EndpointInfo]:
        """Attempt to discover endpoints from OpenAPI/Swagger spec."""
        endpoints = {}
        
        try:
            # Common OpenAPI spec locations
            openapi_paths = [
                '/api/docs/openapi.json',
                '/api/v1/openapi.json',
                '/api/swagger.json',
                '/docs/openapi.json',
                '/openapi.json',
                '/swagger.json'
            ]
            
            for path in openapi_paths:
                try:
                    url = f"{self.api_client.base_url}{path}"
                    response = requests.get(url, timeout=10)
                    
                    if response.status_code == 200:
                        spec = response.json()
                        logger.info(f"Found OpenAPI spec at {path}")
                        
                        # Parse OpenAPI spec
                        if 'paths' in spec:
                            for endpoint_path, methods in spec['paths'].items():
                                for method, info in methods.items():
                                    if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                                        endpoint_info = EndpointInfo(
                                            path=endpoint_path,
                                            method=method.upper(),
                                            description=info.get('summary', info.get('description', 'API endpoint')),
                                            parameters=self._extract_parameters(info),
                                            response_schema=info.get('responses', {}),
                                            requires_auth='security' in info,
                                            rate_limited=False,
                                            deprecation_info=info.get('deprecated', None),
                                            discovered_at=datetime.now()
                                        )
                                        endpoints[f"{method.upper()} {endpoint_path}"] = endpoint_info
                        
                        return endpoints  # Return first successful spec
                        
                except Exception as e:
                    logger.debug(f"OpenAPI spec not found at {path}: {e}")
                    continue
            
        except Exception as e:
            logger.debug(f"OpenAPI discovery failed: {e}")
        
        return endpoints
    
    async def _discover_from_patterns(self) -> Dict[str, EndpointInfo]:
        """Discover endpoints using common REST API patterns."""
        endpoints = {}
        
        try:
            for pattern in self.endpoint_patterns:
                try:
                    url = f"{self.api_client.base_url}{pattern['path']}"
                    method = pattern['method']
                    
                    # Test if endpoint exists
                    response = None
                    if method == 'GET':
                        response = requests.get(url, timeout=5)
                    elif method == 'POST':
                        response = requests.post(url, json={}, timeout=5)
                    elif method == 'HEAD':
                        response = requests.head(url, timeout=5)
                    
                    if response and response.status_code not in [404, 405]:
                        endpoint_info = EndpointInfo(
                            path=pattern['path'],
                            method=method,
                            description=pattern['description'],
                            parameters=pattern.get('parameters', []),
                            response_schema=None,
                            requires_auth=pattern.get('requires_auth', False),
                            rate_limited=pattern.get('rate_limited', False),
                            deprecation_info=None,
                            discovered_at=datetime.now()
                        )
                        endpoints[f"{method} {pattern['path']}"] = endpoint_info
                        
                except Exception as e:
                    logger.debug(f"Pattern test failed for {pattern['path']}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Pattern discovery failed: {e}")
        
        return endpoints
    
    async def _deep_scan_endpoints(self) -> Dict[str, EndpointInfo]:
        """Perform deep scan for additional endpoints."""
        endpoints = {}
        
        try:
            # Common endpoint variations
            base_paths = ['/api', '/api/v1', '/api/v2', '']
            resources = ['entities', 'metadata', 'search', 'libraries', 'folders', 'files', 'users', 'admin']
            
            for base in base_paths:
                for resource in resources:
                    # Test resource endpoints
                    test_paths = [
                        f"{base}/{resource}",
                        f"{base}/{resource}/1",
                        f"{base}/{resource}/search",
                        f"{base}/{resource}/count",
                        f"{base}/{resource}/stats"
                    ]
                    
                    for path in test_paths:
                        try:
                            url = f"{self.api_client.base_url}{path}"
                            response = requests.head(url, timeout=3)
                            
                            if response.status_code not in [404, 405]:
                                endpoint_info = EndpointInfo(
                                    path=path,
                                    method='GET',
                                    description=f"Deep scan discovered: {resource} endpoint",
                                    parameters=[],
                                    response_schema=None,
                                    requires_auth=False,
                                    rate_limited=False,
                                    deprecation_info=None,
                                    discovered_at=datetime.now()
                                )
                                endpoints[f"GET {path}"] = endpoint_info
                                
                        except Exception:
                            continue
        
        except Exception as e:
            logger.error(f"Deep scan failed: {e}")
        
        return endpoints
    
    async def _test_discovered_endpoints(self, endpoints: Dict[str, EndpointInfo]) -> Dict[str, EndpointInfo]:
        """Test discovered endpoints and update their status."""
        tested_endpoints = {}
        
        for key, endpoint in endpoints.items():
            try:
                start_time = time.time()
                
                url = f"{self.api_client.base_url}{endpoint.path}"
                response = None
                
                # Test endpoint based on method
                if endpoint.method == 'GET':
                    response = requests.get(url, timeout=10)
                elif endpoint.method == 'POST':
                    response = requests.post(url, json={}, timeout=10)
                elif endpoint.method == 'HEAD':
                    response = requests.head(url, timeout=10)
                
                response_time = (time.time() - start_time) * 1000
                
                # Update endpoint info
                endpoint.last_tested = datetime.now()
                endpoint.average_response_time_ms = response_time
                
                if response and response.status_code < 500:
                    endpoint.success_count += 1
                    endpoint.availability_score = min(1.0, endpoint.success_count / max(endpoint.success_count + endpoint.failure_count, 1))
                else:
                    endpoint.failure_count += 1
                    endpoint.availability_score = endpoint.success_count / max(endpoint.success_count + endpoint.failure_count, 1)
                
                # Record test result
                test_result = {
                    'endpoint': endpoint.path,
                    'method': endpoint.method,
                    'timestamp': datetime.now().isoformat(),
                    'success': response and response.status_code < 500,
                    'status_code': response.status_code if response else None,
                    'response_time_ms': response_time
                }
                self.test_history.append(test_result)
                
                tested_endpoints[key] = endpoint
                
            except Exception as e:
                logger.debug(f"Endpoint test failed for {endpoint.path}: {e}")
                endpoint.failure_count += 1
                endpoint.last_tested = datetime.now()
                tested_endpoints[key] = endpoint
        
        return tested_endpoints
    
    def _group_endpoints(self, endpoints: Dict[str, EndpointInfo]) -> Dict[str, EndpointGroup]:
        """Group endpoints by functionality."""
        groups = {}
        
        # Define endpoint groups
        group_definitions = {
            'core_data': {
                'name': 'Core Data Management',
                'description': 'Entity and metadata management endpoints',
                'patterns': ['/api/entities', '/api/metadata', '/api/libraries'],
                'priority': 'high'
            },
            'search': {
                'name': 'Search and Query',
                'description': 'Search and query functionality',
                'patterns': ['/api/search', '/search'],
                'priority': 'high'
            },
            'health': {
                'name': 'Health and Monitoring',
                'description': 'System health and monitoring endpoints',
                'patterns': ['/api/health', '/health', '/status', '/metrics'],
                'priority': 'medium'
            },
            'configuration': {
                'name': 'Configuration Management',
                'description': 'System configuration endpoints',
                'patterns': ['/api/config', '/config', '/settings'],
                'priority': 'medium'
            },
            'admin': {
                'name': 'Administration',
                'description': 'Administrative and management endpoints',
                'patterns': ['/api/admin', '/admin', '/api/users'],
                'priority': 'low'
            }
        }
        
        # Group endpoints
        for group_key, group_def in group_definitions.items():
            group_endpoints = []
            
            for endpoint_key, endpoint in endpoints.items():
                for pattern in group_def['patterns']:
                    if pattern in endpoint.path:
                        group_endpoints.append(endpoint)
                        break
            
            if group_endpoints:
                # Determine implementation status
                implemented_count = len([e for e in group_endpoints if e.path in self.implemented_endpoints])
                if implemented_count == len(group_endpoints):
                    status = 'implemented'
                elif implemented_count > 0:
                    status = 'partial'
                else:
                    status = 'missing'
                
                groups[group_key] = EndpointGroup(
                    name=group_def['name'],
                    description=group_def['description'],
                    endpoints=group_endpoints,
                    integration_priority=group_def['priority'],
                    implementation_status=status,
                    notes=f"{implemented_count}/{len(group_endpoints)} endpoints implemented"
                )
        
        return groups
    
    def _get_common_api_patterns(self) -> List[Dict[str, Any]]:
        """Get common API endpoint patterns to test."""
        return [
            {'path': '/api/health', 'method': 'GET', 'description': 'Health check endpoint'},
            {'path': '/api/config', 'method': 'GET', 'description': 'Configuration endpoint'},
            {'path': '/api/entities', 'method': 'GET', 'description': 'List entities'},
            {'path': '/api/entities', 'method': 'POST', 'description': 'Create entity'},
            {'path': '/api/entities/1', 'method': 'GET', 'description': 'Get entity by ID'},
            {'path': '/api/search', 'method': 'GET', 'description': 'Search entities'},
            {'path': '/api/search', 'method': 'POST', 'description': 'Advanced search'},
            {'path': '/api/metadata', 'method': 'GET', 'description': 'List metadata'},
            {'path': '/api/libraries', 'method': 'GET', 'description': 'List libraries'},
            {'path': '/api/folders', 'method': 'GET', 'description': 'List folders'},
            {'path': '/api/users', 'method': 'GET', 'description': 'List users'},
            {'path': '/api/admin/stats', 'method': 'GET', 'description': 'System statistics'},
        ]
    
    def _get_implemented_endpoints(self) -> Set[str]:
        """Get set of endpoints that are already implemented in the API client."""
        # Extract from api_client.py methods
        implemented = {
            '/api/health',
            '/api/config',
            '/api/entities',
            '/api/search',
            '/api/libraries',
            '/api/metadata'
        }
        return implemented
    
    def _extract_parameters(self, endpoint_info: Dict[str, Any]) -> List[str]:
        """Extract parameter names from OpenAPI endpoint info."""
        parameters = []
        
        if 'parameters' in endpoint_info:
            for param in endpoint_info['parameters']:
                if 'name' in param:
                    parameters.append(param['name'])
        
        return parameters
    
    def _analyze_implementation_gaps(self, endpoints: Dict[str, EndpointInfo]) -> Dict[str, Any]:
        """Analyze gaps between discovered and implemented endpoints."""
        available_endpoints = [e for e in endpoints.values() if e.availability_score > 0.5]
        implemented_paths = self.implemented_endpoints
        
        gaps = {
            'missing_implementations': [],
            'priority_gaps': [],
            'opportunity_score': 0.0
        }
        
        for endpoint in available_endpoints:
            if endpoint.path not in implemented_paths:
                gap_info = {
                    'path': endpoint.path,
                    'method': endpoint.method,
                    'description': endpoint.description,
                    'availability_score': endpoint.availability_score,
                    'response_time_ms': endpoint.average_response_time_ms
                }
                
                gaps['missing_implementations'].append(gap_info)
                
                # Determine if this is a priority gap
                if any(pattern in endpoint.path for pattern in ['/api/entities', '/api/search', '/api/metadata']):
                    gaps['priority_gaps'].append(gap_info)
        
        # Calculate opportunity score
        total_available = len(available_endpoints)
        total_implemented = len([e for e in available_endpoints if e.path in implemented_paths])
        gaps['opportunity_score'] = ((total_available - total_implemented) / max(total_available, 1)) * 100
        
        return gaps
    
    def _generate_integration_recommendations(self, endpoints: Dict[str, EndpointInfo]) -> List[Dict[str, Any]]:
        """Generate integration recommendations based on discovered endpoints."""
        recommendations = []
        
        # Analyze implementation gaps
        gaps = self._analyze_implementation_gaps(endpoints)
        
        # Priority recommendations
        if gaps['priority_gaps']:
            recommendations.append({
                'priority': 'high',
                'category': 'missing_core_endpoints',
                'title': 'Implement missing core API endpoints',
                'description': f"Found {len(gaps['priority_gaps'])} high-priority endpoints that could enhance integration",
                'endpoints': gaps['priority_gaps'][:3],  # Top 3
                'estimated_impact': 'High performance and functionality improvements'
            })
        
        # Performance recommendations
        slow_endpoints = [e for e in endpoints.values() if e.average_response_time_ms > 1000]
        if slow_endpoints:
            recommendations.append({
                'priority': 'medium',
                'category': 'performance_optimization',
                'title': 'Optimize slow endpoint performance',
                'description': f"Found {len(slow_endpoints)} endpoints with >1s response time",
                'endpoints': [{'path': e.path, 'response_time_ms': e.average_response_time_ms} for e in slow_endpoints[:3]],
                'estimated_impact': 'Improved user experience and system responsiveness'
            })
        
        # Coverage recommendations
        if gaps['opportunity_score'] > 30:
            recommendations.append({
                'priority': 'medium',
                'category': 'coverage_expansion',
                'title': 'Expand API integration coverage',
                'description': f"Integration coverage at {100 - gaps['opportunity_score']:.1f}%, opportunity to add {len(gaps['missing_implementations'])} endpoints",
                'estimated_impact': 'Enhanced functionality and better Pensieve utilization'
            })
        
        return recommendations
    
    def _update_health_scores(self):
        """Update health scores based on recent test results."""
        for endpoint in self.discovered_endpoints.values():
            if endpoint.success_count + endpoint.failure_count > 0:
                endpoint.availability_score = endpoint.success_count / (endpoint.success_count + endpoint.failure_count)
    
    def _get_performance_trends(self) -> Dict[str, Any]:
        """Get performance trend analysis."""
        recent_tests = list(self.test_history)[-100:]  # Last 100 tests
        
        if not recent_tests:
            return {'trend': 'no_data'}
        
        # Calculate trends
        response_times = [t.get('response_time_ms', 0) for t in recent_tests if 'response_time_ms' in t]
        success_rates = [1 if t.get('success', False) else 0 for t in recent_tests]
        
        avg_response_time = sum(response_times) / max(len(response_times), 1)
        success_rate = sum(success_rates) / max(len(success_rates), 1) * 100
        
        return {
            'average_response_time_ms': round(avg_response_time, 1),
            'success_rate_percentage': round(success_rate, 1),
            'sample_size': len(recent_tests),
            'trend': 'stable'  # Could implement trend analysis here
        }
    
    def _get_integration_next_actions(self) -> List[Dict[str, str]]:
        """Get recommended next actions for integration improvement."""
        actions = []
        
        # Check if discovery was recent
        if not self.stats.last_discovery_time or (datetime.now() - self.stats.last_discovery_time).days > 7:
            actions.append({
                'action': 'run_endpoint_discovery',
                'description': 'Run endpoint discovery to find new API capabilities',
                'priority': 'medium'
            })
        
        # Check implementation coverage
        if self.stats.coverage_percentage < 70:
            actions.append({
                'action': 'improve_api_coverage',
                'description': f'Implement additional endpoints to improve coverage from {self.stats.coverage_percentage:.1f}%',
                'priority': 'high'
            })
        
        # Check availability issues
        if self.stats.endpoints_available < self.stats.total_endpoints_discovered * 0.8:
            actions.append({
                'action': 'investigate_endpoint_issues',
                'description': 'Investigate why some discovered endpoints are not available',
                'priority': 'medium'
            })
        
        return actions


# Singleton instance
_endpoint_discovery: Optional[EndpointDiscovery] = None


def get_endpoint_discovery() -> EndpointDiscovery:
    """Get singleton endpoint discovery instance."""
    global _endpoint_discovery
    if _endpoint_discovery is None:
        _endpoint_discovery = EndpointDiscovery()
    return _endpoint_discovery


def reset_endpoint_discovery():
    """Reset endpoint discovery for testing."""
    global _endpoint_discovery
    _endpoint_discovery = None


async def run_automated_discovery() -> Dict[str, Any]:
    """Run automated endpoint discovery and return results."""
    try:
        discovery = get_endpoint_discovery()
        results = await discovery.discover_endpoints(deep_scan=True)
        
        logger.info(f"Automated discovery completed: {results.get('stats', {}).get('total_endpoints_discovered', 0)} endpoints found")
        return results
        
    except Exception as e:
        logger.error(f"Automated discovery failed: {e}")
        return {'error': str(e)}


async def start_continuous_monitoring(interval_minutes: int = 15):
    """Start continuous endpoint monitoring."""
    try:
        discovery = get_endpoint_discovery()
        await discovery.monitor_endpoints_continuous(interval_minutes)
    except Exception as e:
        logger.error(f"Continuous monitoring failed: {e}")
        raise