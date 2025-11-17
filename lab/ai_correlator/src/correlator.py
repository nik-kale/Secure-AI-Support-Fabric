"""
Intelligent Alert Correlation Engine
Groups related alerts, deduplicates, and reduces noise
"""
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Set, Tuple
from collections import defaultdict
import hashlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from lab.common.logging_config import setup_logging

logger = setup_logging('ai_correlator')


class AlertCorrelator:
    """
    Intelligent alert correlation using multiple strategies:
    1. Time-based windowing
    2. Service/resource grouping
    3. Pattern matching
    4. Fingerprint deduplication
    """
    
    def __init__(self, correlation_window_seconds: int = 300):
        self.correlation_window = correlation_window_seconds
        self.alert_groups = {}
        self.fingerprint_cache = {}
        self.noise_reduction_stats = {
            'total_alerts': 0,
            'unique_incidents': 0,
            'noise_reduction_pct': 0.0
        }
    
    def correlate_alerts(self, alerts: List[Dict]) -> List[Dict]:
        """
        Correlate alerts into incidents
        
        Returns:
            List of incident dictionaries with grouped alerts
        """
        if not alerts:
            return []
        
        self.noise_reduction_stats['total_alerts'] += len(alerts)
        
        # Step 1: Deduplicate by fingerprint
        unique_alerts = self._deduplicate_alerts(alerts)
        
        # Step 2: Group by time windows
        time_grouped = self._group_by_time(unique_alerts)
        
        # Step 3: Correlate within groups
        incidents = []
        for group_alerts in time_grouped:
            incident = self._create_incident(group_alerts)
            incidents.append(incident)
        
        self.noise_reduction_stats['unique_incidents'] = len(incidents)
        
        if self.noise_reduction_stats['total_alerts'] > 0:
            self.noise_reduction_stats['noise_reduction_pct'] = (
                (1 - len(incidents) / self.noise_reduction_stats['total_alerts']) * 100
            )
        
        logger.info(
            f"Correlated {len(alerts)} alerts into {len(incidents)} incidents "
            f"({self.noise_reduction_stats['noise_reduction_pct']:.1f}% noise reduction)"
        )
        
        return incidents
    
    def _deduplicate_alerts(self, alerts: List[Dict]) -> List[Dict]:
        """Deduplicate alerts using fingerprinting"""
        unique = []
        seen_fingerprints = set()
        
        for alert in alerts:
            fingerprint = self._generate_fingerprint(alert)
            
            if fingerprint not in seen_fingerprints:
                unique.append(alert)
                seen_fingerprints.add(fingerprint)
                self.fingerprint_cache[alert.get('alert_id')] = fingerprint
        
        logger.debug(f"Deduplicated {len(alerts)} alerts to {len(unique)} unique")
        return unique
    
    def _generate_fingerprint(self, alert: Dict) -> str:
        """Generate unique fingerprint for alert"""
        # Fingerprint based on: rule_id, service, severity
        components = [
            alert.get('rule_id', ''),
            alert.get('metadata', {}).get('metric_key', ''),
            alert.get('severity', '')
        ]
        
        fingerprint_str = '|'.join(components)
        return hashlib.md5(fingerprint_str.encode()).hexdigest()
    
    def _group_by_time(self, alerts: List[Dict]) -> List[List[Dict]]:
        """Group alerts by time windows"""
        if not alerts:
            return []
        
        # Sort by time
        sorted_alerts = sorted(alerts, key=lambda x: x.get('triggered_at', ''))
        
        groups = []
        current_group = [sorted_alerts[0]]
        current_time = datetime.fromisoformat(sorted_alerts[0]['triggered_at'])
        
        for alert in sorted_alerts[1:]:
            alert_time = datetime.fromisoformat(alert['triggered_at'])

            if (alert_time - current_time).total_seconds() <= self.correlation_window:
                current_group.append(alert)
            else:
                groups.append(current_group)
                current_group = [alert]
                current_time = alert_time
        
        if current_group:
            groups.append(current_group)
        
        return groups
    
    def _create_incident(self, alerts: List[Dict]) -> Dict:
        """Create an incident from grouped alerts"""
        if not alerts:
            return {}
        
        # Determine severity (highest in group)
        severity_order = ['LOW', 'MEDIUM', 'WARNING', 'HIGH', 'CRITICAL']
        max_severity = max(
            alerts,
            key=lambda x: severity_order.index(x.get('severity', 'LOW'))
        )['severity']
        
        # Affected services
        services = set()
        for alert in alerts:
            metric_key = alert.get('metadata', {}).get('metric_key', '')
            if ':' in metric_key:
                service = metric_key.split(':')[0]
                services.add(service)
        
        # Root cause analysis (simple pattern matching)
        root_cause = self._identify_root_cause(alerts)
        
        incident = {
            'incident_id': f"incident-{int(datetime.utcnow().timestamp())}",
            'severity': max_severity,
            'alert_count': len(alerts),
            'alerts': [a['alert_id'] for a in alerts],
            'affected_services': list(services),
            'root_cause': root_cause,
            'first_seen': min(a['triggered_at'] for a in alerts),
            'last_seen': max(a['triggered_at'] for a in alerts),
            'status': 'open',
            'description': self._generate_description(alerts, root_cause)
        }
        
        return incident
    
    def _identify_root_cause(self, alerts: List[Dict]) -> str:
        """Simple root cause identification"""
        # Count alert types
        alert_types = defaultdict(int)
        for alert in alerts:
            rule_name = alert.get('rule_name', 'unknown')
            alert_types[rule_name] += 1
        
        # Most common alert type is likely root cause
        if alert_types:
            root_cause = max(alert_types.items(), key=lambda x: x[1])[0]
            return root_cause
        
        return "Unknown"
    
    def _generate_description(self, alerts: List[Dict], root_cause: str) -> str:
        """Generate human-readable incident description"""
        services = set()
        for alert in alerts:
            metric_key = alert.get('metadata', {}).get('metric_key', '')
            if ':' in metric_key:
                service = metric_key.split(':')[0]
                services.add(service)
        
        services_str = ', '.join(sorted(services)) if services else 'unknown services'
        
        return f"Incident affecting {services_str}: {len(alerts)} related alerts. Root cause: {root_cause}"
    
    def get_stats(self) -> Dict:
        """Get correlation statistics"""
        return self.noise_reduction_stats.copy()
