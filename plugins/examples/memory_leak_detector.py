"""
Example Custom Plugin: Memory Leak Detector

This detector identifies gradual memory increases that may indicate a leak.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lab/agentic_ai/src'))

from plugins.base import DetectorPlugin, PluginMetadata, Finding
from typing import List, Dict, Any, Optional
from datetime import datetime


class MemoryLeakDetector(DetectorPlugin):
    """Detect potential memory leaks via gradual memory increases"""

    def __init__(self):
        self.increase_threshold = 5.0  # % increase per sample
        self.min_samples = 5
        self._metadata = PluginMetadata(
            name="memory_leak_detector",
            version="1.0.0",
            author="AI Fabric Lab",
            description="Detects gradual memory increases indicating potential leaks",
            category="performance"
        )

    @property
    def metadata(self) -> PluginMetadata:
        return self._metadata

    def analyze(self, telemetry: List[Dict[str, Any]]) -> Optional[Finding]:
        """Analyze for memory leak patterns"""
        memory_samples = []

        # Extract memory metrics
        for entry in telemetry:
            if entry.get('telemetry_type') == 'metric':
                data = entry.get('data', {})
                metrics = data.get('metrics', {})
                memory_pct = metrics.get('memory_percent')

                if memory_pct is not None:
                    memory_samples.append({
                        'timestamp': data.get('timestamp', ''),
                        'memory_percent': memory_pct,
                        'service': data.get('service', 'unknown')
                    })

        if len(memory_samples) < self.min_samples:
            return None  # Not enough data

        # Sort by timestamp
        memory_samples.sort(key=lambda x: x['timestamp'])

        # Check for consistent increases
        increases = 0
        for i in range(1, len(memory_samples)):
            current = memory_samples[i]['memory_percent']
            previous = memory_samples[i-1]['memory_percent']

            if current > previous + self.increase_threshold:
                increases += 1

        # Detect leak if consistent increases
        if increases >= self.min_samples - 2:
            start_memory = memory_samples[0]['memory_percent']
            end_memory = memory_samples[-1]['memory_percent']
            total_increase = end_memory - start_memory

            return Finding(
                finding_id=f'memory-leak-{datetime.utcnow().timestamp()}',
                severity='MEDIUM',
                title='Potential Memory Leak Detected',
                description=f'Memory usage increased from {start_memory:.1f}% to {end_memory:.1f}% ({total_increase:.1f}% total increase) across {len(memory_samples)} samples. This may indicate a memory leak.',
                evidence=memory_samples,
                recommendations=[
                    'Profile application memory usage with a tool like py-spy or memory_profiler',
                    'Check for unclosed file handles or database connections',
                    'Review recent code changes for potential leaks',
                    'Monitor garbage collection metrics',
                    'Consider restarting the service if memory continues to grow',
                    'Enable detailed memory logging'
                ]
            )

        return None

    def configure(self, config: Dict[str, Any]):
        """Configure detector thresholds"""
        if 'increase_threshold' in config:
            self.increase_threshold = config['increase_threshold']
        if 'min_samples' in config:
            self.min_samples = config['min_samples']

    def get_config_schema(self) -> Dict[str, Any]:
        """Return configuration schema"""
        return {
            "type": "object",
            "properties": {
                "increase_threshold": {
                    "type": "number",
                    "minimum": 0,
                    "default": 5.0,
                    "description": "Memory increase percentage to trigger detection"
                },
                "min_samples": {
                    "type": "integer",
                    "minimum": 2,
                    "default": 5,
                    "description": "Minimum number of samples required"
                }
            }
        }
