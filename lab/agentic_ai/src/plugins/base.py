"""
Base classes for detector plugins
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class PluginMetadata:
    """Metadata for a detector plugin"""
    name: str
    version: str
    author: str
    description: str
    category: str  # e.g., 'performance', 'security', 'availability'
    enabled: bool = True
    dependencies: List[str] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class DetectorPlugin(ABC):
    """
    Base class for all detector plugins

    Custom detectors must inherit from this class and implement:
    - metadata property
    - analyze() method
    """

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata"""
        pass

    @abstractmethod
    def analyze(self, telemetry: List[Dict[str, Any]]) -> Optional['Finding']:
        """
        Analyze telemetry and return Finding if anomaly detected

        Args:
            telemetry: List of telemetry entries

        Returns:
            Finding object if anomaly detected, None otherwise
        """
        pass

    def validate_telemetry(self, telemetry: List[Dict[str, Any]]) -> bool:
        """
        Validate that telemetry is in expected format

        Override this for custom validation logic

        Args:
            telemetry: Telemetry to validate

        Returns:
            True if valid, False otherwise
        """
        if not telemetry or not isinstance(telemetry, list):
            return False

        # Basic validation: check structure
        for entry in telemetry[:10]:  # Sample first 10
            if not isinstance(entry, dict):
                return False
            if 'telemetry_type' not in entry and 'data' not in entry:
                return False

        return True

    def pre_process(self, telemetry: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Pre-process telemetry before analysis

        Override to filter, transform, or enrich telemetry

        Args:
            telemetry: Raw telemetry

        Returns:
            Processed telemetry
        """
        return telemetry

    def post_process(self, finding: Optional['Finding']) -> Optional['Finding']:
        """
        Post-process findings before returning

        Override to enrich, validate, or filter findings

        Args:
            finding: Raw finding

        Returns:
            Processed finding
        """
        return finding

    def get_config_schema(self) -> Dict[str, Any]:
        """
        Return JSON schema for plugin configuration

        Override to support configurable plugins

        Returns:
            JSON schema dict
        """
        return {
            "type": "object",
            "properties": {},
            "additionalProperties": False
        }

    def configure(self, config: Dict[str, Any]):
        """
        Configure the plugin with provided settings

        Override to support runtime configuration

        Args:
            config: Configuration dict matching schema
        """
        pass


# Import Finding from detectors to avoid circular import issues
# In a real implementation, Finding would be in a shared models module
try:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))
    from detectors import Finding
except ImportError:
    # Fallback: define minimal Finding here
    from dataclasses import dataclass as _dataclass
    from typing import List as _List, Dict as _Dict, Any as _Any

    @_dataclass
    class Finding:
        finding_id: str
        severity: str
        title: str
        description: str
        evidence: _List[_Dict[str, _Any]]
        recommendations: _List[str]
        detected_at: str = None

        def __post_init__(self):
            if self.detected_at is None:
                self.detected_at = datetime.utcnow().isoformat()

        def to_dict(self) -> _Dict[str, _Any]:
            return {
                'finding_id': self.finding_id,
                'severity': self.severity,
                'title': self.title,
                'description': self.description,
                'evidence': self.evidence,
                'recommendations': self.recommendations,
                'detected_at': self.detected_at
            }


class PluginError(Exception):
    """Base exception for plugin errors"""
    pass


class PluginLoadError(PluginError):
    """Plugin failed to load"""
    pass


class PluginValidationError(PluginError):
    """Plugin validation failed"""
    pass
