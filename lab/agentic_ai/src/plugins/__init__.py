"""
Plugin system for custom detectors
"""
from .base import DetectorPlugin, PluginMetadata
from .manager import PluginManager
from .loader import PluginLoader

__all__ = ['DetectorPlugin', 'PluginMetadata', 'PluginManager', 'PluginLoader']
