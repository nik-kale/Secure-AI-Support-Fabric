"""
Security headers middleware for AI Support Fabric Lab

Adds security headers to all HTTP responses
"""
from flask import Flask
from typing import Callable


def add_security_headers(response):
    """
    Add security headers to Flask response
    
    Headers added:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Strict-Transport-Security: max-age=31536000; includeSubDomains
    - Content-Security-Policy: default-src 'self'
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy: geolocation=(), microphone=(), camera=()
    """
    # Prevent MIME type sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    # Prevent clickjacking
    response.headers['X-Frame-Options'] = 'DENY'
    
    # Enable XSS protection
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Force HTTPS (only in production)
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    # Content Security Policy
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
    
    # Referrer policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Permissions policy (disable unnecessary features)
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    
    # Remove server header
    response.headers.pop('Server', None)
    
    return response


def setup_security_headers(app: Flask):
    """
    Configure security headers for Flask app
    
    Usage:
        from lab.common.security_headers import setup_security_headers
        
        app = Flask(__name__)
        setup_security_headers(app)
    
    Args:
        app: Flask application instance
    """
    @app.after_request
    def apply_security_headers(response):
        return add_security_headers(response)
    
    app.logger.info("Security headers configured")
