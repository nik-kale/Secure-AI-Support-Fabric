"""
Graceful shutdown handling for AI Support Fabric Lab

Ensures clean shutdown of services without data loss
"""
import signal
import sys
import logging
from typing import Callable, List

logger = logging.getLogger(__name__)


class GracefulShutdown:
    """
    Handles graceful shutdown on SIGTERM/SIGINT
    
    Allows services to clean up resources, close connections,
    and complete in-flight requests before exiting.
    """
    
    def __init__(self):
        self._shutdown_callbacks: List[Callable] = []
        self._is_shutting_down = False
    
    def register_callback(self, callback: Callable):
        """
        Register a cleanup callback to run on shutdown
        
        Args:
            callback: Function to call on shutdown (no arguments)
        """
        self._shutdown_callbacks.append(callback)
        logger.debug(f"Registered shutdown callback: {callback.__name__}")
    
    def is_shutting_down(self) -> bool:
        """Check if shutdown is in progress"""
        return self._is_shutting_down
    
    def shutdown(self, signum=None, frame=None):
        """
        Execute shutdown sequence
        
        Called when SIGTERM or SIGINT is received
        """
        if self._is_shutting_down:
            logger.warning("Shutdown already in progress")
            return
        
        self._is_shutting_down = True
        signal_name = signal.Signals(signum).name if signum else "MANUAL"
        
        logger.info(f"=== Starting graceful shutdown (signal={signal_name}) ===")
        
        # Execute all cleanup callbacks
        for i, callback in enumerate(self._shutdown_callbacks, 1):
            try:
                logger.info(f"Running shutdown callback {i}/{len(self._shutdown_callbacks)}: {callback.__name__}")
                callback()
                logger.debug(f"Completed: {callback.__name__}")
            except Exception as e:
                logger.error(f"Error in shutdown callback {callback.__name__}: {e}", exc_info=True)
        
        logger.info("=== Graceful shutdown complete ===")
        sys.exit(0)
    
    def register_signals(self):
        """Register signal handlers for SIGTERM and SIGINT"""
        signal.signal(signal.SIGTERM, self.shutdown)
        signal.signal(signal.SIGINT, self.shutdown)
        logger.info("Registered signal handlers for SIGTERM and SIGINT")


# Global shutdown handler
_shutdown_handler = GracefulShutdown()


def get_shutdown_handler() -> GracefulShutdown:
    """Get the global shutdown handler"""
    return _shutdown_handler


def setup_graceful_shutdown(cleanup_callbacks: List[Callable] = None):
    """
    Set up graceful shutdown for a service
    
    Usage:
        def cleanup_database():
            db.close()
        
        def cleanup_connections():
            connection_pool.shutdown()
        
        setup_graceful_shutdown([cleanup_database, cleanup_connections])
    
    Args:
        cleanup_callbacks: List of functions to call on shutdown
    """
    handler = get_shutdown_handler()
    
    if cleanup_callbacks:
        for callback in cleanup_callbacks:
            handler.register_callback(callback)
    
    handler.register_signals()
    logger.info(f"Graceful shutdown configured with {len(handler._shutdown_callbacks)} callbacks")
