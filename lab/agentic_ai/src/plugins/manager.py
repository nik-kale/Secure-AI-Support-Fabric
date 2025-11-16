"""
Plugin Manager for loading and managing detector plugins
"""
import importlib.util
import sys
from pathlib import Path
from typing import Dict, List, Optional
import logging

from .base import DetectorPlugin, PluginMetadata, PluginLoadError, PluginValidationError

logger = logging.getLogger(__name__)


class PluginManager:
    """
    Manages detector plugins: loading, validation, and execution
    """

    def __init__(self, plugin_dirs: List[str] = None):
        """
        Initialize plugin manager

        Args:
            plugin_dirs: List of directories to search for plugins
        """
        self.plugins: Dict[str, DetectorPlugin] = {}
        self.plugin_dirs = plugin_dirs or ['./plugins', '/app/plugins']
        self.enabled_plugins: List[str] = []

    def load_plugins(self, plugin_dir: Optional[str] = None):
        """
        Load all plugins from specified directory

        Args:
            plugin_dir: Directory to load from (uses defaults if None)
        """
        dirs_to_search = [plugin_dir] if plugin_dir else self.plugin_dirs

        for directory in dirs_to_search:
            path = Path(directory)
            if not path.exists():
                logger.warning(f"Plugin directory not found: {directory}")
                continue

            # Find all Python files
            for plugin_file in path.glob('*.py'):
                if plugin_file.stem.startswith('_'):
                    continue  # Skip private files

                try:
                    self._load_plugin_from_file(plugin_file)
                except Exception as e:
                    logger.error(f"Failed to load plugin {plugin_file}: {e}")

        logger.info(f"Loaded {len(self.plugins)} plugins")

    def _load_plugin_from_file(self, plugin_file: Path):
        """Load a single plugin from file"""
        module_name = f"plugins.{plugin_file.stem}"

        # Load module
        spec = importlib.util.spec_from_file_location(module_name, plugin_file)
        if spec is None or spec.loader is None:
            raise PluginLoadError(f"Could not load spec for {plugin_file}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        # Find DetectorPlugin subclasses
        for attr_name in dir(module):
            attr = getattr(module, attr_name)

            if (isinstance(attr, type) and
                issubclass(attr, DetectorPlugin) and
                attr is not DetectorPlugin):

                # Instantiate plugin
                plugin = attr()

                # Validate
                self._validate_plugin(plugin)

                # Register
                metadata = plugin.metadata
                self.plugins[metadata.name] = plugin

                if metadata.enabled:
                    self.enabled_plugins.append(metadata.name)

                logger.info(f"Loaded plugin: {metadata.name} v{metadata.version}")

    def _validate_plugin(self, plugin: DetectorPlugin):
        """Validate plugin meets requirements"""
        # Check has metadata
        try:
            metadata = plugin.metadata
        except Exception as e:
            raise PluginValidationError(f"Plugin metadata invalid: {e}")

        # Check has analyze method
        if not hasattr(plugin, 'analyze') or not callable(plugin.analyze):
            raise PluginValidationError("Plugin must implement analyze() method")

        # Check metadata fields
        required_fields = ['name', 'version', 'author', 'description']
        for field in required_fields:
            if not getattr(metadata, field, None):
                raise PluginValidationError(f"Plugin metadata missing: {field}")

    def get_plugin(self, name: str) -> Optional[DetectorPlugin]:
        """Get plugin by name"""
        return self.plugins.get(name)

    def list_plugins(self) -> List[PluginMetadata]:
        """List all loaded plugins"""
        return [p.metadata for p in self.plugins.values()]

    def enable_plugin(self, name: str):
        """Enable a plugin"""
        if name in self.plugins:
            self.plugins[name].metadata.enabled = True
            if name not in self.enabled_plugins:
                self.enabled_plugins.append(name)

    def disable_plugin(self, name: str):
        """Disable a plugin"""
        if name in self.plugins:
            self.plugins[name].metadata.enabled = False
            if name in self.enabled_plugins:
                self.enabled_plugins.remove(name)

    def run_plugins(self, telemetry: List[Dict]) -> List:
        """
        Run all enabled plugins on telemetry

        Args:
            telemetry: Telemetry to analyze

        Returns:
            List of findings from all plugins
        """
        findings = []

        for plugin_name in self.enabled_plugins:
            plugin = self.plugins[plugin_name]

            try:
                # Validate telemetry
                if not plugin.validate_telemetry(telemetry):
                    logger.warning(f"Plugin {plugin_name} rejected telemetry")
                    continue

                # Pre-process
                processed_telemetry = plugin.pre_process(telemetry)

                # Analyze
                finding = plugin.analyze(processed_telemetry)

                # Post-process
                if finding:
                    finding = plugin.post_process(finding)
                    if finding:
                        findings.append(finding)

            except Exception as e:
                logger.error(f"Plugin {plugin_name} failed: {e}")

        return findings

    def reload_plugin(self, name: str):
        """Reload a specific plugin"""
        if name in self.plugins:
            # TODO: Implement plugin reloading
            pass

    def unload_plugin(self, name: str):
        """Unload a plugin"""
        if name in self.plugins:
            del self.plugins[name]
            if name in self.enabled_plugins:
                self.enabled_plugins.remove(name)
