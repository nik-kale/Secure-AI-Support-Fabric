"""Simple plugin loader utility"""
from .manager import PluginManager


class PluginLoader:
    """Convenience class for plugin loading"""

    @staticmethod
    def load_from_directory(directory: str) -> PluginManager:
        """Load all plugins from a directory"""
        manager = PluginManager(plugin_dirs=[directory])
        manager.load_plugins()
        return manager

    @staticmethod
    def create_default_manager() -> PluginManager:
        """Create manager with default plugin directories"""
        manager = PluginManager()
        manager.load_plugins()
        return manager
