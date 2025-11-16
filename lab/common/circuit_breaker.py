"""
Circuit Breaker pattern for AI Support Fabric Lab

Prevents cascading failures when backend services are unavailable
"""
import time
import threading
from enum import Enum
from typing import Callable, Any, Optional
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerError(Exception):
    """Raised when circuit is open"""
    pass


class CircuitBreaker:
    """
    Circuit breaker implementation
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, reject requests immediately
    - HALF_OPEN: Testing recovery, allow limited requests
    
    Args:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before trying recovery
        success_threshold: Successes needed in HALF_OPEN to close circuit
        timeout: Request timeout in seconds
    """
    
    def __init__(
        self,
        name: str = "default",
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2,
        timeout: float = 30.0
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.timeout = timeout
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._lock = threading.Lock()
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state"""
        return self._state
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self._last_failure_time is None:
            return False
        return time.time() - self._last_failure_time >= self.recovery_timeout
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker
        
        Args:
            func: Function to call
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
        
        Returns:
            Function result
        
        Raises:
            CircuitBreakerError: If circuit is open
        """
        with self._lock:
            # Check if circuit is open
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    logger.info(f"Circuit '{self.name}': Attempting recovery (HALF_OPEN)")
                    self._state = CircuitState.HALF_OPEN
                    self._success_count = 0
                else:
                    raise CircuitBreakerError(
                        f"Circuit breaker '{self.name}' is OPEN. "
                        f"Service unavailable. Retry after {self.recovery_timeout}s."
                    )
        
        # Execute the function
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """Handle successful request"""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                logger.debug(
                    f"Circuit '{self.name}': Success in HALF_OPEN "
                    f"({self._success_count}/{self.success_threshold})"
                )
                
                if self._success_count >= self.success_threshold:
                    logger.info(f"Circuit '{self.name}': Recovered, closing circuit")
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
            elif self._state == CircuitState.CLOSED:
                # Reset failure count on success
                self._failure_count = 0
    
    def _on_failure(self):
        """Handle failed request"""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            if self._state == CircuitState.HALF_OPEN:
                logger.warning(f"Circuit '{self.name}': Failed in HALF_OPEN, reopening circuit")
                self._state = CircuitState.OPEN
                self._success_count = 0
            elif self._failure_count >= self.failure_threshold:
                logger.error(
                    f"Circuit '{self.name}': Failure threshold reached "
                    f"({self._failure_count}/{self.failure_threshold}), opening circuit"
                )
                self._state = CircuitState.OPEN
    
    def reset(self):
        """Manually reset circuit to CLOSED state"""
        with self._lock:
            logger.info(f"Circuit '{self.name}': Manual reset")
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = None


# Global circuit breaker registry
_circuit_breakers = {}
_registry_lock = threading.Lock()


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    success_threshold: int = 2,
    timeout: float = 30.0
) -> CircuitBreaker:
    """
    Get or create a circuit breaker
    
    Args:
        name: Unique name for the circuit
        failure_threshold: Failures before opening
        recovery_timeout: Seconds before attempting recovery
        success_threshold: Successes needed to close
        timeout: Request timeout
    
    Returns:
        CircuitBreaker instance
    """
    with _registry_lock:
        if name not in _circuit_breakers:
            _circuit_breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                success_threshold=success_threshold,
                timeout=timeout
            )
            logger.info(f"Created circuit breaker '{name}'")
        
        return _circuit_breakers[name]


def circuit(
    name: str = None,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    success_threshold: int = 2,
    timeout: float = 30.0
):
    """
    Decorator to wrap function with circuit breaker
    
    Usage:
        @circuit(name='backend_api', failure_threshold=3, recovery_timeout=30)
        def call_backend_api():
            return requests.get('http://backend/api')
    
    Args:
        name: Circuit breaker name (defaults to function name)
        failure_threshold: Failures before opening
        recovery_timeout: Seconds before attempting recovery
        success_threshold: Successes needed to close
        timeout: Request timeout
    """
    def decorator(func: Callable) -> Callable:
        circuit_name = name or func.__name__
        breaker = get_circuit_breaker(
            circuit_name,
            failure_threshold,
            recovery_timeout,
            success_threshold,
            timeout
        )
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)
        
        return wrapper
    return decorator
