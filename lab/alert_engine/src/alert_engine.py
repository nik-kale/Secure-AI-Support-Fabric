"""
Real-time Alerting Engine
Evaluates alert rules against incoming telemetry and metrics
"""
import os
import sys
import json
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Callable
from collections import defaultdict, deque
from apscheduler.schedulers.background import BackgroundScheduler

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from lab.common.logging_config import setup_logging

logger = setup_logging('alert_engine')


class AlertRule:
    """Alert rule definition"""
    
    def __init__(self, rule_id: str, name: str, condition: str, threshold: float,
                 window_minutes: int = 5, severity: str = 'WARNING',
                 enabled: bool = True, description: str = ''):
        self.rule_id = rule_id
        self.name = name
        self.condition = condition  # e.g., "cpu_usage > threshold"
        self.threshold = threshold
        self.window_minutes = window_minutes
        self.severity = severity
        self.enabled = enabled
        self.description = description
        self.last_triggered = None
        self.trigger_count = 0
    
    def to_dict(self) -> Dict:
        return {
            'rule_id': self.rule_id,
            'name': self.name,
            'condition': self.condition,
            'threshold': self.threshold,
            'window_minutes': self.window_minutes,
            'severity': self.severity,
            'enabled': self.enabled,
            'description': self.description,
            'last_triggered': self.last_triggered.isoformat() if self.last_triggered else None,
            'trigger_count': self.trigger_count
        }


class Alert:
    """Triggered alert"""
    
    def __init__(self, alert_id: str, rule_id: str, rule_name: str,
                 severity: str, message: str, value: float, threshold: float,
                 metadata: Dict = None):
        self.alert_id = alert_id
        self.rule_id = rule_id
        self.rule_name = rule_name
        self.severity = severity
        self.message = message
        self.value = value
        self.threshold = threshold
        self.metadata = metadata or {}
        self.triggered_at = datetime.utcnow()
        self.acknowledged = False
        self.resolved = False
    
    def to_dict(self) -> Dict:
        return {
            'alert_id': self.alert_id,
            'rule_id': self.rule_id,
            'rule_name': self.rule_name,
            'severity': self.severity,
            'message': self.message,
            'value': self.value,
            'threshold': self.threshold,
            'metadata': self.metadata,
            'triggered_at': self.triggered_at.isoformat(),
            'acknowledged': self.acknowledged,
            'resolved': self.resolved
        }


class AlertEngine:
    """Real-time alerting engine"""
    
    def __init__(self, storage_path: str = '/data/alerts.db'):
        self.storage_path = storage_path
        self.rules: Dict[str, AlertRule] = {}
        self.alerts = deque(maxlen=1000)  # Keep last 1000 alerts
        self.metrics_buffer = defaultdict(lambda: deque(maxlen=1000))
        self.alert_callbacks: List[Callable] = []
        self._lock = threading.Lock()
        
        self._init_db()
        self._load_rules()
        
        # Start background scheduler
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(
            self._evaluate_rules,
            'interval',
            seconds=30,  # Evaluate every 30 seconds
            id='rule_evaluation'
        )
        self.scheduler.start()
        logger.info("Alert engine started with background evaluation")
    
    def _init_db(self):
        """Initialize database"""
        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()
        
        # Alert rules table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alert_rules (
                rule_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                condition TEXT NOT NULL,
                threshold REAL NOT NULL,
                window_minutes INTEGER DEFAULT 5,
                severity TEXT DEFAULT 'WARNING',
                enabled INTEGER DEFAULT 1,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Alerts history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                alert_id TEXT PRIMARY KEY,
                rule_id TEXT NOT NULL,
                rule_name TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                value REAL NOT NULL,
                threshold REAL NOT NULL,
                metadata TEXT,
                triggered_at TIMESTAMP NOT NULL,
                acknowledged INTEGER DEFAULT 0,
                resolved INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_rule_id ON alerts(rule_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_triggered_at ON alerts(triggered_at)')
        
        conn.commit()
        conn.close()
        logger.info("Alert engine database initialized")
    
    def _load_rules(self):
        """Load rules from database"""
        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM alert_rules WHERE enabled = 1')
        rows = cursor.fetchall()
        
        for row in rows:
            rule = AlertRule(
                rule_id=row[0],
                name=row[1],
                condition=row[2],
                threshold=row[3],
                window_minutes=row[4],
                severity=row[5],
                enabled=bool(row[6]),
                description=row[7] or ''
            )
            self.rules[rule.rule_id] = rule
        
        conn.close()
        logger.info(f"Loaded {len(self.rules)} alert rules")
    
    def add_rule(self, rule: AlertRule) -> bool:
        """Add or update alert rule"""
        with self._lock:
            conn = sqlite3.connect(self.storage_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO alert_rules
                (rule_id, name, condition, threshold, window_minutes, severity, enabled, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (rule.rule_id, rule.name, rule.condition, rule.threshold,
                  rule.window_minutes, rule.severity, int(rule.enabled), rule.description))
            
            conn.commit()
            conn.close()
            
            self.rules[rule.rule_id] = rule
            logger.info(f"Alert rule added: {rule.name}")
            return True
    
    def ingest_metric(self, name: str, value: float, service: str = 'unknown', timestamp: datetime = None):
        """Ingest a metric for evaluation"""
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        metric_key = f"{service}:{name}"
        self.metrics_buffer[metric_key].append((timestamp, value))
    
    def _evaluate_rules(self):
        """Evaluate all rules against current metrics"""
        with self._lock:
            for rule in self.rules.values():
                if not rule.enabled:
                    continue
                
                try:
                    self._evaluate_rule(rule)
                except Exception as e:
                    logger.error(f"Error evaluating rule {rule.name}: {e}", exc_info=True)
    
    def _evaluate_rule(self, rule: AlertRule):
        """Evaluate a single rule"""
        # Simple condition parsing for demo (e.g., "cpu_usage > threshold")
        parts = rule.condition.split()
        if len(parts) < 3:
            return
        
        metric_name = parts[0]
        operator = parts[1]
        
        # Get recent metrics
        cutoff = datetime.utcnow() - timedelta(minutes=rule.window_minutes)
        
        # Check all services for this metric
        triggered = False
        for metric_key, values in self.metrics_buffer.items():
            if metric_name not in metric_key:
                continue
            
            # Filter by time window
            recent_values = [(ts, val) for ts, val in values if ts >= cutoff]
            if not recent_values:
                continue
            
            # Calculate aggregate (avg for now)
            avg_value = sum(val for _, val in recent_values) / len(recent_values)
            
            # Evaluate condition
            if operator == '>' and avg_value > rule.threshold:
                triggered = True
                self._trigger_alert(rule, avg_value, metric_key)
            elif operator == '<' and avg_value < rule.threshold:
                triggered = True
                self._trigger_alert(rule, avg_value, metric_key)
            elif operator == '==' and abs(avg_value - rule.threshold) < 0.01:
                triggered = True
                self._trigger_alert(rule, avg_value, metric_key)
    
    def _trigger_alert(self, rule: AlertRule, value: float, metric_key: str):
        """Trigger an alert"""
        # Prevent duplicate alerts within 5 minutes
        if rule.last_triggered and (datetime.utcnow() - rule.last_triggered).seconds < 300:
            return
        
        alert_id = f"alert-{rule.rule_id}-{int(datetime.utcnow().timestamp())}"
        
        message = f"{rule.name}: {metric_key} = {value:.2f} (threshold: {rule.threshold})"
        
        alert = Alert(
            alert_id=alert_id,
            rule_id=rule.rule_id,
            rule_name=rule.name,
            severity=rule.severity,
            message=message,
            value=value,
            threshold=rule.threshold,
            metadata={'metric_key': metric_key}
        )
        
        # Store alert
        self.alerts.append(alert)
        self._store_alert(alert)
        
        # Update rule
        rule.last_triggered = datetime.utcnow()
        rule.trigger_count += 1
        
        # Execute callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}", exc_info=True)
        
        logger.warning(f"ALERT TRIGGERED: {message} [Severity: {alert.severity}]")
    
    def _store_alert(self, alert: Alert):
        """Store alert in database"""
        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO alerts
            (alert_id, rule_id, rule_name, severity, message, value, threshold,
             metadata, triggered_at, acknowledged, resolved)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (alert.alert_id, alert.rule_id, alert.rule_name, alert.severity,
              alert.message, alert.value, alert.threshold, json.dumps(alert.metadata),
              alert.triggered_at.isoformat(), int(alert.acknowledged), int(alert.resolved)))
        
        conn.commit()
        conn.close()
    
    def register_callback(self, callback: Callable):
        """Register a callback to be called when alerts trigger"""
        self.alert_callbacks.append(callback)
    
    def get_alerts(self, limit: int = 100, acknowledged: bool = None) -> List[Dict]:
        """Get recent alerts"""
        alerts = list(self.alerts)
        
        if acknowledged is not None:
            alerts = [a for a in alerts if a.acknowledged == acknowledged]
        
        return [a.to_dict() for a in alerts[:limit]]
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                
                # Update database
                conn = sqlite3.connect(self.storage_path)
                cursor = conn.cursor()
                cursor.execute('UPDATE alerts SET acknowledged = 1 WHERE alert_id = ?', (alert_id,))
                conn.commit()
                conn.close()
                
                logger.info(f"Alert acknowledged: {alert_id}")
                return True
        
        return False
    
    def shutdown(self):
        """Shutdown the engine"""
        self.scheduler.shutdown()
        logger.info("Alert engine shutdown complete")
