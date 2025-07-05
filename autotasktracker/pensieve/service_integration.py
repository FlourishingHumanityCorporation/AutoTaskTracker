"""
Enhanced service command integration for AutoTaskTracker-Pensieve coordination.
Provides centralized service management, health monitoring, and automated maintenance.
"""

import logging
import os
import subprocess
import asyncio
import time
import json
from typing import Dict, Any, List, Optional, Tuple, Union, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import threading

logger = logging.getLogger(__name__)


@dataclass
class ServiceStatus:
    """Detailed service status information."""
    name: str
    running: bool
    pid: Optional[int]
    started_at: Optional[str]
    running_for: Optional[str]
    command: str
    health_score: float  # 0.0 to 1.0
    issues: List[str]
    performance_metrics: Dict[str, Any]


@dataclass  
class ServiceCommand:
    """Service command definition."""
    command: List[str]
    description: str
    timeout: int = 30
    retry_count: int = 3
    critical: bool = False


class PensieveServiceManager:
    """Enhanced service management for Pensieve integration."""
    
    def __init__(self, venv_path: Optional[str] = None):
        """Initialize service manager.
        
        Args:
            venv_path: Path to virtual environment (defaults to detecting current)
        """
        self.venv_path = venv_path or self._detect_venv_path()
        self.executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="ServiceManager")
        
        # Service command definitions
        self.commands = {
            'status': ServiceCommand(['ps'], 'Check service status'),
            'start': ServiceCommand(['start'], 'Start all services'),
            'stop': ServiceCommand(['stop'], 'Stop all services'),
            'restart': ServiceCommand(['restart'], 'Restart all services'),
            'scan': ServiceCommand(['scan'], 'Scan screenshots directory'),
            'reindex': ServiceCommand(['reindex'], 'Reindex library'),
            'config': ServiceCommand(['config'], 'Show configuration'),
            'health': ServiceCommand(['ps'], 'Health check', timeout=10),
            'migrate': ServiceCommand(['migrate'], 'Migrate to PostgreSQL', timeout=300),
            'version': ServiceCommand(['version'], 'Get version info', timeout=5)
        }
        
        # Health monitoring
        self.health_history: List[Tuple[datetime, Dict[str, Any]]] = []
        self.last_health_check = 0
        self.health_check_interval = 30  # seconds
        
        # Performance tracking
        self.command_stats = {cmd: {'calls': 0, 'failures': 0, 'avg_duration': 0.0} 
                             for cmd in self.commands}
        
        logger.info(f"Service manager initialized with venv: {self.venv_path}")
    
    def _detect_venv_path(self) -> str:
        """Detect virtual environment path."""
        # Check if we're in a venv
        venv_path = os.environ.get('VIRTUAL_ENV')
        if venv_path:
            return venv_path
        
        # Try common project locations
        project_root = Path(__file__).parent.parent.parent
        venv_candidates = [
            project_root / 'venv',
            project_root / '.venv',
            Path.home() / '.local' / 'venv' / 'autotasktracker'
        ]
        
        for candidate in venv_candidates:
            if candidate.exists() and (candidate / 'bin' / 'python').exists():
                return str(candidate)
        
        # Fallback to system python
        logger.warning("Could not detect virtual environment, using system python")
        return ""
    
    def _build_command(self, service_command: str) -> List[str]:
        """Build full command with virtual environment."""
        if self.venv_path:
            python_path = str(Path(self.venv_path) / 'bin' / 'python')
            return [python_path, '-m', 'memos.commands'] + self.commands[service_command].command
        else:
            return ['memos'] + self.commands[service_command].command
    
    async def execute_command_async(self, command_name: str, **kwargs) -> Dict[str, Any]:
        """Execute service command asynchronously."""
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, self.execute_command, command_name, kwargs
        )
    
    def execute_command(self, command_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a service command with enhanced error handling and monitoring."""
        if command_name not in self.commands:
            return {
                'success': False,
                'error': f'Unknown command: {command_name}',
                'output': '',
                'duration': 0.0
            }
        
        start_time = time.time()
        command_def = self.commands[command_name]
        full_command = self._build_command(command_name)
        
        # Add any additional arguments
        if kwargs.get('args'):
            full_command.extend(kwargs['args'])
        
        logger.debug(f"Executing: {' '.join(full_command)}")
        
        # Track command execution
        self.command_stats[command_name]['calls'] += 1
        
        try:
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=command_def.timeout,
                **kwargs.get('subprocess_kwargs', {})
            )
            
            duration = time.time() - start_time
            success = result.returncode == 0
            
            # Update stats
            if not success:
                self.command_stats[command_name]['failures'] += 1
            
            # Update average duration
            stats = self.command_stats[command_name]
            stats['avg_duration'] = (
                (stats['avg_duration'] * (stats['calls'] - 1) + duration) / stats['calls']
            )
            
            return {
                'success': success,
                'returncode': result.returncode,
                'output': result.stdout,
                'error': result.stderr,
                'duration': duration,
                'command': ' '.join(full_command)
            }
            
        except subprocess.TimeoutExpired as e:
            duration = time.time() - start_time
            self.command_stats[command_name]['failures'] += 1
            logger.error(f"Command {command_name} timed out after {command_def.timeout}s")
            
            return {
                'success': False,
                'error': f'Command timed out after {command_def.timeout}s',
                'output': '',
                'duration': duration,
                'timeout': True
            }
            
        except Exception as e:
            duration = time.time() - start_time
            self.command_stats[command_name]['failures'] += 1
            logger.error(f"Command {command_name} failed: {e}")
            
            return {
                'success': False,
                'error': str(e),
                'output': '',
                'duration': duration
            }
    
    def get_detailed_status(self) -> Dict[str, ServiceStatus]:
        """Get detailed status of all services."""
        status_result = self.execute_command('status')
        
        services = {}
        
        if status_result['success']:
            # Parse the ps command output
            lines = status_result['output'].strip().split('\n')
            
            # Skip header line if present
            if lines and 'Name' in lines[0]:
                lines = lines[1:]
            
            for line in lines:
                if line.strip():
                    parts = line.strip().split()
                    if len(parts) >= 4:
                        name = parts[0]
                        status = parts[1]
                        pid = parts[2] if parts[2].isdigit() else None
                        started_at = parts[3] if len(parts) > 3 else None
                        running_for = parts[4] if len(parts) > 4 else None
                        
                        # Calculate health score
                        health_score = 1.0 if status.lower() == 'running' else 0.0
                        issues = [] if status.lower() == 'running' else [f'Service {name} not running']
                        
                        services[name] = ServiceStatus(
                            name=name,
                            running=status.lower() == 'running',
                            pid=int(pid) if pid else None,
                            started_at=started_at,
                            running_for=running_for,
                            command=name,
                            health_score=health_score,
                            issues=issues,
                            performance_metrics={}
                        )
        
        return services
    
    def get_comprehensive_health(self) -> Dict[str, Any]:
        """Get comprehensive health assessment."""
        now = datetime.now()
        
        # Get service status
        services = self.get_detailed_status()
        
        # Calculate overall health
        running_services = sum(1 for s in services.values() if s.running)
        total_services = len(services)
        overall_health = running_services / total_services if total_services > 0 else 0.0
        
        # Get configuration info
        config_result = self.execute_command('config')
        config_available = config_result['success']
        
        # Performance assessment
        command_failures = sum(stats['failures'] for stats in self.command_stats.values())
        command_calls = sum(stats['calls'] for stats in self.command_stats.values())
        command_reliability = 1.0 - (command_failures / command_calls) if command_calls > 0 else 1.0
        
        health_report = {
            'timestamp': now.isoformat(),
            'overall_health': overall_health,
            'services': {name: asdict(status) for name, status in services.items()},
            'service_count': {
                'total': total_services,
                'running': running_services,
                'stopped': total_services - running_services
            },
            'configuration': {
                'accessible': config_available,
                'last_check': now.isoformat()
            },
            'performance': {
                'command_reliability': command_reliability,
                'total_commands': command_calls,
                'failed_commands': command_failures,
                'command_stats': self.command_stats
            },
            'recommendations': self._generate_health_recommendations(services, overall_health)
        }
        
        # Store in history
        self.health_history.append((now, health_report))
        
        # Keep only last 24 hours of history
        cutoff_time = now - timedelta(hours=24)
        self.health_history = [
            (timestamp, report) for timestamp, report in self.health_history
            if timestamp > cutoff_time
        ]
        
        return health_report
    
    def _generate_health_recommendations(self, services: Dict[str, ServiceStatus], 
                                       overall_health: float) -> List[str]:
        """Generate health improvement recommendations."""
        recommendations = []
        
        if overall_health < 1.0:
            stopped_services = [name for name, status in services.items() if not status.running]
            if stopped_services:
                recommendations.append(f"Start stopped services: {', '.join(stopped_services)}")
        
        # Check command reliability
        unreliable_commands = [
            cmd for cmd, stats in self.command_stats.items()
            if stats['calls'] > 0 and (stats['failures'] / stats['calls']) > 0.2
        ]
        if unreliable_commands:
            recommendations.append(f"Investigate unreliable commands: {', '.join(unreliable_commands)}")
        
        # Check for performance issues
        slow_commands = [
            cmd for cmd, stats in self.command_stats.items()
            if stats['avg_duration'] > 10.0
        ]
        if slow_commands:
            recommendations.append(f"Optimize slow commands: {', '.join(slow_commands)}")
        
        if not recommendations:
            recommendations.append("All services healthy")
        
        return recommendations
    
    def auto_maintain(self) -> Dict[str, Any]:
        """Perform automated maintenance tasks."""
        maintenance_report = {
            'timestamp': datetime.now().isoformat(),
            'tasks_performed': [],
            'issues_found': [],
            'issues_resolved': [],
            'performance_improvements': []
        }
        
        # Check and restart failed services
        services = self.get_detailed_status()
        failed_services = [name for name, status in services.items() if not status.running]
        
        if failed_services:
            maintenance_report['issues_found'].append(f"Failed services: {failed_services}")
            
            # Attempt to restart failed services
            restart_result = self.execute_command('restart')
            if restart_result['success']:
                maintenance_report['issues_resolved'].append("Restarted failed services")
                maintenance_report['tasks_performed'].append("Service restart")
            else:
                maintenance_report['issues_found'].append(f"Failed to restart services: {restart_result['error']}")
        
        # Perform scan to ensure database is up to date
        scan_result = self.execute_command('scan')
        if scan_result['success']:
            maintenance_report['tasks_performed'].append("Database scan")
        else:
            maintenance_report['issues_found'].append(f"Scan failed: {scan_result['error']}")
        
        return maintenance_report
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get detailed performance metrics."""
        return {
            'command_statistics': self.command_stats,
            'health_history_count': len(self.health_history),
            'average_health_score': (
                sum(report['overall_health'] for _, report in self.health_history) / len(self.health_history)
                if self.health_history else 0.0
            ),
            'service_uptime_analysis': self._analyze_service_uptime()
        }
    
    def _analyze_service_uptime(self) -> Dict[str, Any]:
        """Analyze service uptime from health history."""
        if not self.health_history:
            return {'insufficient_data': True}
        
        uptime_stats = {}
        
        # Analyze each service's uptime
        for timestamp, report in self.health_history:
            for service_name, service_data in report['services'].items():
                if service_name not in uptime_stats:
                    uptime_stats[service_name] = {'checks': 0, 'running': 0}
                
                uptime_stats[service_name]['checks'] += 1
                if service_data['running']:
                    uptime_stats[service_name]['running'] += 1
        
        # Calculate uptime percentages
        for service_name, stats in uptime_stats.items():
            stats['uptime_percentage'] = (stats['running'] / stats['checks']) * 100
        
        return uptime_stats
    
    def schedule_maintenance(self, interval_hours: int = 24) -> None:
        """Schedule periodic maintenance (would typically be run by a scheduler)."""
        def maintenance_worker():
            while True:
                try:
                    time.sleep(interval_hours * 3600)  # Convert hours to seconds
                    maintenance_report = self.auto_maintain()
                    logger.info(f"Automated maintenance completed: {maintenance_report}")
                except Exception as e:
                    logger.error(f"Automated maintenance failed: {e}")
        
        maintenance_thread = threading.Thread(target=maintenance_worker, daemon=True)
        maintenance_thread.start()
        logger.info(f"Scheduled maintenance every {interval_hours} hours")


# Singleton instance
_service_manager: Optional[PensieveServiceManager] = None


def get_service_manager() -> PensieveServiceManager:
    """Get singleton service manager instance."""
    global _service_manager
    if _service_manager is None:
        _service_manager = PensieveServiceManager()
    return _service_manager


def reset_service_manager():
    """Reset singleton service manager (useful for testing)."""
    global _service_manager
    if _service_manager:
        _service_manager.executor.shutdown(wait=False)
    _service_manager = None