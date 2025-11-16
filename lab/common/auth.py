"""
Authentication middleware for AI Support Fabric Lab

Provides API key-based authentication for all services
"""
import os
import logging
from functools import wraps
from flask import request, jsonify
from typing import Set, Callable, Any

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Authentication failed"""
    def __init__(self, message: str = "Unauthorized"):
        self.message = message
        self.status_code = 401
        super().__init__(self.message)


class APIKeyAuth:
    """API Key authentication manager"""

    def __init__(self, api_keys: Set[str] = None):
        """
        Initialize authentication with valid API keys

        Args:
            api_keys: Set of valid API keys. If None, loads from environment.
        """
        if api_keys is None:
            # Load from environment variable
            keys_str = os.getenv('API_KEYS', '')
            if keys_str:
                self.valid_keys = set(k.strip() for k in keys_str.split(',') if k.strip())
            else:
                # Development mode: use a default key with warning
                logger.warning("No API_KEYS configured. Using development key only. DO NOT USE IN PRODUCTION!")
                self.valid_keys = {'dev-key-DO-NOT-USE-IN-PRODUCTION'}
        else:
            self.valid_keys = api_keys

    def verify_api_key(self, api_key: str) -> bool:
        """
        Verify if provided API key is valid

        Args:
            api_key: API key to verify

        Returns:
            True if valid, False otherwise
        """
        if not api_key:
            return False
        return api_key in self.valid_keys

    def require_auth(self, f: Callable) -> Callable:
        """
        Decorator to require authentication for endpoint

        Usage:
            @app.route('/api/protected')
            @require_auth
            def protected_endpoint():
                return {'message': 'authenticated'}

        Args:
            f: Function to wrap

        Returns:
            Wrapped function with authentication check
        """
        @wraps(f)
        def decorated(*args: Any, **kwargs: Any) -> Any:
            # Extract API key from request headers
            api_key = request.headers.get('X-API-Key')

            if not api_key:
                return jsonify({
                    'error': 'Missing API key',
                    'message': 'Please provide X-API-Key header'
                }), 401

            if not self.verify_api_key(api_key):
                return jsonify({
                    'error': 'Invalid API key',
                    'message': 'The provided API key is not valid'
                }), 401

            # Authentication successful, proceed with request
            return f(*args, **kwargs)

        return decorated


def setup_auth_error_handlers(app):
    """
    Register authentication error handlers with Flask app

    Args:
        app: Flask application instance
    """
    @app.errorhandler(AuthenticationError)
    def handle_auth_error(error):
        return jsonify({
            'error': error.message,
            'authenticated': False
        }), error.status_code


# Singleton instance for convenience
_auth_instance = None


def get_auth() -> APIKeyAuth:
    """
    Get or create singleton auth instance

    Returns:
        APIKeyAuth instance
    """
    global _auth_instance
    if _auth_instance is None:
        _auth_instance = APIKeyAuth()
    return _auth_instance


def require_auth(f: Callable) -> Callable:
    """
    Convenience decorator using singleton auth instance

    Usage:
        from lab.common.auth import require_auth

        @app.route('/api/protected')
        @require_auth
        def my_endpoint():
            return {'message': 'success'}

    Args:
        f: Function to wrap

    Returns:
        Wrapped function
    """
    return get_auth().require_auth(f)


# Example usage and testing
if __name__ == '__main__':
    # Test authentication
    auth = APIKeyAuth(api_keys={'test-key-1', 'test-key-2'})

    print("Testing authentication...")
    print(f"Valid key 'test-key-1': {auth.verify_api_key('test-key-1')}")  # True
    print(f"Valid key 'test-key-2': {auth.verify_api_key('test-key-2')}")  # True
    print(f"Invalid key 'wrong-key': {auth.verify_api_key('wrong-key')}")  # False
    print(f"Empty key: {auth.verify_api_key('')}")  # False
    print("Authentication tests passed!")
