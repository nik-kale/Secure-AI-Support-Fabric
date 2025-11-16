"""
Rate limiting middleware for AI Support Fabric Lab

Provides tiered rate limiting for different endpoint types
"""
import time
import threading
from collections import defaultdict, deque
from functools import wraps
from flask import request, jsonify
from typing import Callable, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter with per-IP tracking
    
    Supports tiered rate limiting for different endpoint types
    """
    
    def __init__(self):
        # Store: {ip_address: {tier: deque of timestamps}}
        self._requests: Dict[str, Dict[str, deque]] = defaultdict(lambda: defaultdict(deque))
        self._lock = threading.Lock()
        
        # Cleanup old entries every 60 seconds
        self._last_cleanup = time.time()
        self._cleanup_interval = 60
    
    def _cleanup_old_entries(self):
        """Remove old request timestamps to prevent memory growth"""
        now = time.time()
        
        if now - self._last_cleanup < self._cleanup_interval:
            return
        
        with self._lock:
            for ip_requests in self._requests.values():
                for tier, timestamps in ip_requests.items():
                    # Remove timestamps older than 1 hour
                    cutoff = now - 3600
                    while timestamps and timestamps[0] < cutoff:
                        timestamps.popleft()
            
            self._last_cleanup = now
    
    def is_allowed(self, ip_address: str, tier: str, max_requests: int, window_seconds: int) -> Tuple[bool, Dict]:
        """
        Check if request is allowed based on rate limit
        
        Args:
            ip_address: Client IP address
            tier: Rate limit tier (e.g., 'query', 'analyze', 'ingest')
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
        
        Returns:
            Tuple of (is_allowed, metadata_dict)
        """
        self._cleanup_old_entries()
        
        now = time.time()
        cutoff = now - window_seconds
        
        with self._lock:
            timestamps = self._requests[ip_address][tier]
            
            # Remove timestamps outside the window
            while timestamps and timestamps[0] < cutoff:
                timestamps.popleft()
            
            # Check if under limit
            if len(timestamps) < max_requests:
                timestamps.append(now)
                remaining = max_requests - len(timestamps)
                return True, {
                    'limit': max_requests,
                    'remaining': remaining,
                    'reset_at': int(cutoff + window_seconds)
                }
            else:
                # Rate limited
                reset_at = int(timestamps[0] + window_seconds)
                return False, {
                    'limit': max_requests,
                    'remaining': 0,
                    'reset_at': reset_at,
                    'retry_after': reset_at - int(now)
                }


# Global rate limiter instance
_rate_limiter = RateLimiter()


def rate_limit(tier: str = 'default', max_requests: int = 100, window_seconds: int = 3600):
    """
    Decorator to add rate limiting to Flask endpoints
    
    Usage:
        @app.route('/api/query')
        @rate_limit(tier='query', max_requests=100, window_seconds=3600)
        def query_endpoint():
            return {'data': ...}
    
    Args:
        tier: Rate limit tier name
        max_requests: Maximum requests allowed in window
        window_seconds: Time window in seconds
    
    Common tiers:
        - 'analyze': 5 requests/hour (expensive operations)
        - 'query': 100 requests/hour (read operations)
        - 'ingest': 1000 requests/hour (telemetry ingestion)
        - 'default': 60 requests/hour
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Get client IP
            ip_address = request.remote_addr or 'unknown'
            
            # Check rate limit
            allowed, metadata = _rate_limiter.is_allowed(
                ip_address,
                tier,
                max_requests,
                window_seconds
            )
            
            if not allowed:
                logger.warning(
                    f"Rate limit exceeded for {ip_address} on tier '{tier}'. "
                    f"Retry after {metadata['retry_after']}s"
                )
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'limit': metadata['limit'],
                    'retry_after': metadata['retry_after']
                }), 429
            
            # Add rate limit headers to response
            response = f(*args, **kwargs)
            
            # If response is a tuple (response, status_code), unpack it
            if isinstance(response, tuple):
                response_obj, status_code = response[0], response[1]
            else:
                response_obj, status_code = response, 200
            
            # Add rate limit headers
            if hasattr(response_obj, 'headers'):
                response_obj.headers['X-RateLimit-Limit'] = str(metadata['limit'])
                response_obj.headers['X-RateLimit-Remaining'] = str(metadata['remaining'])
                response_obj.headers['X-RateLimit-Reset'] = str(metadata['reset_at'])
            
            return response_obj, status_code
        
        return wrapped
    return decorator


# Preset rate limit decorators for common use cases
def rate_limit_analyze(f: Callable) -> Callable:
    """Rate limit for expensive analysis operations: 5/hour"""
    return rate_limit(tier='analyze', max_requests=5, window_seconds=3600)(f)


def rate_limit_query(f: Callable) -> Callable:
    """Rate limit for query operations: 100/hour"""
    return rate_limit(tier='query', max_requests=100, window_seconds=3600)(f)


def rate_limit_ingest(f: Callable) -> Callable:
    """Rate limit for telemetry ingestion: 1000/hour"""
    return rate_limit(tier='ingest', max_requests=1000, window_seconds=3600)(f)
