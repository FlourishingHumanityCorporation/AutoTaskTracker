"""Circuit breaker pattern for API failure detection and recovery."""

import logging
import time
from collections import defaultdict
from typing import Set, Dict, Any

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Implements circuit breaker pattern for API reliability."""
    
    def __init__(self, failure_threshold: int = 3, circuit_open_duration: int = 300):
        """Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            circuit_open_duration: Time in seconds to keep circuit open
        """
        self.failure_threshold = failure_threshold
        self.circuit_open_duration = circuit_open_duration
        
        # Circuit breaker state
        self.failed_endpoints: Set[str] = set()
        self.failure_counts: Dict[str, int] = defaultdict(int)
        self.last_failure_time: Dict[str, float] = {}
    
    def is_circuit_open(self, endpoint: str = 'general') -> bool:
        """Check if the circuit breaker is open (blocking calls).
        
        Args:
            endpoint: Specific endpoint to check (default: general)
            
        Returns:
            True if circuit is open, False otherwise
        """
        current_time = time.time()
        
        # Check if circuit should be closed (enough time has passed)
        if endpoint in self.last_failure_time:
            if current_time - self.last_failure_time[endpoint] > self.circuit_open_duration:
                # Reset the endpoint
                self.failed_endpoints.discard(endpoint)
                self.failure_counts[endpoint] = 0
                del self.last_failure_time[endpoint]
                return False
        
        # Circuit is open if endpoint is in failed set
        return endpoint in self.failed_endpoints
    
    def is_any_circuit_open(self) -> bool:
        """Check if any circuit breaker is open."""
        current_time = time.time()
        
        # Check if any circuits should be closed (enough time has passed)
        for endpoint, failure_time in list(self.last_failure_time.items()):
            if current_time - failure_time > self.circuit_open_duration:
                # Reset the endpoint
                self.failed_endpoints.discard(endpoint)
                self.failure_counts[endpoint] = 0
                del self.last_failure_time[endpoint]
        
        # Circuit is open if we have recent failures
        return len(self.failed_endpoints) > 0
    
    def record_failure(self, endpoint: str = 'general', error_message: str = '') -> None:
        """Record a failure for circuit breaker logic.
        
        Args:
            endpoint: Endpoint that failed
            error_message: Error message for logging
        """
        current_time = time.time()
        
        # Increment failure count
        self.failure_counts[endpoint] += 1
        
        # If we hit the threshold, open the circuit
        if self.failure_counts[endpoint] >= self.failure_threshold:
            self.failed_endpoints.add(endpoint)
            self.last_failure_time[endpoint] = current_time
            
            logger.warning(f"Circuit breaker opened for endpoint '{endpoint}' due to repeated failures: {error_message}")
    
    def record_success(self, endpoint: str = 'general') -> None:
        """Record a successful call and reset circuit breaker.
        
        Args:
            endpoint: Endpoint that succeeded
        """
        self.failure_counts[endpoint] = 0
        self.failed_endpoints.discard(endpoint)
        if endpoint in self.last_failure_time:
            del self.last_failure_time[endpoint]
    
    def reset_circuit(self, endpoint: str = 'general') -> None:
        """Manually reset circuit breaker for an endpoint.
        
        Args:
            endpoint: Endpoint to reset
        """
        self.failure_counts[endpoint] = 0
        self.failed_endpoints.discard(endpoint)
        if endpoint in self.last_failure_time:
            del self.last_failure_time[endpoint]
        
        logger.info(f"Circuit breaker manually reset for endpoint: {endpoint}")
    
    def reset_all_circuits(self) -> None:
        """Reset all circuit breakers."""
        self.failed_endpoints.clear()
        self.failure_counts.clear()
        self.last_failure_time.clear()
        
        logger.info("All circuit breakers reset")
    
    def get_circuit_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status.
        
        Returns:
            Dictionary with circuit breaker state information
        """
        current_time = time.time()
        
        status = {
            'failed_endpoints': list(self.failed_endpoints),
            'failure_counts': dict(self.failure_counts),
            'open_circuits': len(self.failed_endpoints),
            'total_endpoints_tracked': len(self.failure_counts),
            'circuit_open_duration': self.circuit_open_duration,
            'failure_threshold': self.failure_threshold
        }
        
        # Add time remaining for each open circuit
        status['time_remaining'] = {}
        for endpoint, failure_time in self.last_failure_time.items():
            remaining = self.circuit_open_duration - (current_time - failure_time)
            if remaining > 0:
                status['time_remaining'][endpoint] = remaining
        
        return status