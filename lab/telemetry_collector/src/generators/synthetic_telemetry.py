"""
Synthetic telemetry generators for lab scenarios
"""
import random
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List

class TelemetryGenerator:
    """Base class for telemetry generators"""

    def __init__(self, service_name: str = "test-service"):
        self.service_name = service_name

    def generate_timestamp(self, offset_seconds: int = 0) -> str:
        """Generate ISO timestamp with optional offset"""
        ts = datetime.utcnow() - timedelta(seconds=offset_seconds)
        return ts.isoformat() + 'Z'


class LogGenerator(TelemetryGenerator):
    """Generate synthetic log entries"""

    LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

    def generate_normal_log(self) -> Dict[str, Any]:
        """Generate a normal log entry"""
        return {
            'timestamp': self.generate_timestamp(),
            'service': self.service_name,
            'level': random.choice(['INFO', 'DEBUG']),
            'message': random.choice([
                'Request processed successfully',
                'Database query completed',
                'Cache hit for key',
                'User authentication successful'
            ]),
            'request_id': f'req-{random.randint(1000, 9999)}',
            'duration_ms': random.randint(10, 200)
        }

    def generate_latency_spike_logs(self, count: int = 10) -> List[Dict[str, Any]]:
        """Generate logs indicating latency spikes"""
        logs = []
        for i in range(count):
            logs.append({
                'timestamp': self.generate_timestamp(offset_seconds=i*2),
                'service': self.service_name,
                'level': 'WARNING',
                'message': 'Request took longer than expected',
                'request_id': f'req-spike-{i}',
                'duration_ms': random.randint(5000, 15000),  # 5-15 seconds
                'expected_duration_ms': 200
            })
        return logs

    def generate_auth_failure_logs(self, count: int = 20) -> List[Dict[str, Any]]:
        """Generate authentication failure logs"""
        logs = []
        for i in range(count):
            logs.append({
                'timestamp': self.generate_timestamp(offset_seconds=i),
                'service': self.service_name,
                'level': 'ERROR',
                'message': 'Authentication failed',
                'request_id': f'req-auth-{i}',
                'user': f'user_{random.randint(1, 5)}',
                'reason': 'Invalid credentials',
                'source_ip': f'192.168.1.{random.randint(1, 255)}'
            })
        return logs


class MetricGenerator(TelemetryGenerator):
    """Generate synthetic metrics"""

    def generate_normal_metrics(self) -> Dict[str, Any]:
        """Generate normal metrics"""
        return {
            'timestamp': self.generate_timestamp(),
            'service': self.service_name,
            'metrics': {
                'cpu_percent': random.uniform(20, 40),
                'memory_percent': random.uniform(30, 50),
                'request_rate': random.randint(50, 150),
                'error_rate': random.uniform(0.1, 1.0),
                'avg_latency_ms': random.randint(50, 200)
            }
        }

    def generate_high_cpu_metrics(self, count: int = 5) -> List[Dict[str, Any]]:
        """Generate metrics showing high CPU usage"""
        metrics = []
        for i in range(count):
            metrics.append({
                'timestamp': self.generate_timestamp(offset_seconds=i*10),
                'service': self.service_name,
                'metrics': {
                    'cpu_percent': random.uniform(85, 99),
                    'memory_percent': random.uniform(30, 50),
                    'request_rate': random.randint(200, 400),
                    'error_rate': random.uniform(5.0, 15.0),
                    'avg_latency_ms': random.randint(2000, 8000)
                }
            })
        return metrics

    def generate_memory_leak_metrics(self, count: int = 10) -> List[Dict[str, Any]]:
        """Generate metrics showing gradual memory increase"""
        metrics = []
        base_memory = 40.0
        for i in range(count):
            metrics.append({
                'timestamp': self.generate_timestamp(offset_seconds=i*30),
                'service': self.service_name,
                'metrics': {
                    'cpu_percent': random.uniform(25, 35),
                    'memory_percent': base_memory + (i * 5),  # Gradual increase
                    'request_rate': random.randint(50, 150),
                    'error_rate': random.uniform(0.1, 1.0),
                    'avg_latency_ms': random.randint(50, 200)
                }
            })
        return metrics


class ConfigGenerator(TelemetryGenerator):
    """Generate synthetic configuration change events"""

    def generate_normal_config(self) -> Dict[str, Any]:
        """Generate baseline configuration"""
        return {
            'timestamp': self.generate_timestamp(),
            'service': self.service_name,
            'config_version': '1.0.0',
            'configuration': {
                'debug_mode': False,
                'log_level': 'INFO',
                'max_connections': 100,
                'timeout_seconds': 30,
                'rate_limit': 1000,
                'enable_auth': True,
                'tls_enabled': True
            },
            'changed_by': 'system',
            'change_reason': 'Initial configuration'
        }

    def generate_config_drift(self, drift_type: str = 'debug_enabled') -> Dict[str, Any]:
        """Generate configuration drift event"""
        config = self.generate_normal_config()
        config['timestamp'] = self.generate_timestamp()
        config['config_version'] = '1.0.1-drift'
        config['changed_by'] = 'unknown'
        config['change_reason'] = 'Unauthorized change detected'

        if drift_type == 'debug_enabled':
            config['configuration']['debug_mode'] = True
            config['configuration']['log_level'] = 'DEBUG'
        elif drift_type == 'auth_disabled':
            config['configuration']['enable_auth'] = False
        elif drift_type == 'tls_disabled':
            config['configuration']['tls_enabled'] = False
        elif drift_type == 'excessive_connections':
            config['configuration']['max_connections'] = 10000

        return config


class ScenarioGenerator:
    """Generate complete scenario telemetry"""

    def __init__(self, service_name: str = "test-service"):
        self.log_gen = LogGenerator(service_name)
        self.metric_gen = MetricGenerator(service_name)
        self.config_gen = ConfigGenerator(service_name)

    def generate_latency_spike_scenario(self) -> Dict[str, List[Dict[str, Any]]]:
        """Generate complete latency spike scenario"""
        return {
            'logs': self.log_gen.generate_latency_spike_logs(count=15),
            'metrics': self.metric_gen.generate_high_cpu_metrics(count=5),
            'configs': []
        }

    def generate_config_drift_scenario(self, drift_type: str = 'debug_enabled') -> Dict[str, List[Dict[str, Any]]]:
        """Generate configuration drift scenario"""
        return {
            'logs': [self.log_gen.generate_normal_log() for _ in range(5)],
            'metrics': [self.metric_gen.generate_normal_metrics()],
            'configs': [self.config_gen.generate_config_drift(drift_type)]
        }

    def generate_auth_error_storm_scenario(self) -> Dict[str, List[Dict[str, Any]]]:
        """Generate authentication error storm scenario"""
        return {
            'logs': self.log_gen.generate_auth_failure_logs(count=30),
            'metrics': self.metric_gen.generate_high_cpu_metrics(count=3),
            'configs': []
        }
