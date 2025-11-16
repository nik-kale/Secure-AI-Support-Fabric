"""
Machine Learning-based Anomaly Detection

Uses sklearn IsolationForest for unsupervised anomaly detection
"""
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib
from pathlib import Path

try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False
    import warnings
    warnings.warn("joblib not installed. Model persistence disabled. Install with: pip install joblib", ImportWarning)

try:
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


class MLAnomalyDetector:
    """
    ML-based anomaly detector using Isolation Forest

    Can be trained on normal telemetry and then detect deviations
    """

    def __init__(self, contamination: float = 0.1):
        """
        Initialize ML detector

        Args:
            contamination: Expected proportion of anomalies (0.0 to 0.5)
        """
        if not SKLEARN_AVAILABLE:
            raise ImportError("sklearn not installed. Install with: pip install scikit-learn")

        self.model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_names = []

    def extract_features(self, telemetry: List[Dict[str, Any]]) -> np.ndarray:
        """
        Extract numerical features from telemetry

        Args:
            telemetry: List of telemetry entries

        Returns:
            numpy array of features (n_samples, n_features)
        """
        features_list = []

        for entry in telemetry:
            telemetry_type = entry.get('telemetry_type')
            data = entry.get('data', {})

            if telemetry_type == 'metric':
                # Extract metrics
                metrics = data.get('metrics', {})
                feature_vec = [
                    metrics.get('cpu_percent', 0),
                    metrics.get('memory_percent', 0),
                    metrics.get('request_rate', 0),
                    metrics.get('error_rate', 0),
                    metrics.get('avg_latency_ms', 0)
                ]
                features_list.append(feature_vec)

            elif telemetry_type == 'log':
                # Extract log features
                feature_vec = [
                    1 if data.get('level') == 'ERROR' else 0,
                    1 if data.get('level') == 'WARNING' else 0,
                    data.get('duration_ms', 0),
                    0,  # placeholder
                    0   # placeholder
                ]
                features_list.append(feature_vec)

        if not features_list:
            return np.array([]).reshape(0, 5)

        self.feature_names = ['cpu', 'memory', 'req_rate', 'error_rate', 'latency']
        return np.array(features_list)

    def train(self, normal_telemetry: List[Dict[str, Any]]):
        """
        Train on normal (non-anomalous) telemetry

        Args:
            normal_telemetry: Telemetry representing normal behavior
        """
        features = self.extract_features(normal_telemetry)

        if len(features) == 0:
            raise ValueError("No features extracted from telemetry")

        # Fit scaler
        features_scaled = self.scaler.fit_transform(features)

        # Train model
        self.model.fit(features_scaled)
        self.is_trained = True

    def detect_anomalies(self, telemetry: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detect anomalies in telemetry

        Args:
            telemetry: Telemetry to analyze

        Returns:
            List of anomalous entries with scores
        """
        if not self.is_trained:
            raise RuntimeError("Model not trained. Call train() first")

        features = self.extract_features(telemetry)

        if len(features) == 0:
            return []

        features_scaled = self.scaler.transform(features)

        # Predict (-1 for anomalies, 1 for normal)
        predictions = self.model.predict(features_scaled)

        # Get anomaly scores (lower = more anomalous)
        scores = self.model.score_samples(features_scaled)

        # Collect anomalies
        anomalies = []
        for i, (pred, score) in enumerate(zip(predictions, scores)):
            if pred == -1:  # Anomaly
                anomalies.append({
                    'index': i,
                    'telemetry': telemetry[i] if i < len(telemetry) else None,
                    'anomaly_score': float(score),
                    'features': features[i].tolist()
                })

        return anomalies

    def create_finding(self, anomalies: List[Dict[str, Any]]) -> Optional['Finding']:
        """
        Create Finding object from detected anomalies

        Args:
            anomalies: List of anomalous entries

        Returns:
            Finding if anomalies detected, None otherwise
        """
        if not anomalies:
            return None

        # Avoid circular import
        try:
            from detectors import Finding
        except ImportError:
            return None

        # Analyze anomalies
        avg_score = np.mean([a['anomaly_score'] for a in anomalies])

        # Determine severity based on anomaly score and count
        if len(anomalies) > 20 or avg_score < -0.5:
            severity = 'HIGH'
        elif len(anomalies) > 10 or avg_score < -0.3:
            severity = 'MEDIUM'
        else:
            severity = 'LOW'

        return Finding(
            finding_id=f'ml-anomaly-{datetime.utcnow().timestamp()}',
            severity=severity,
            title='ML-Detected Anomalies',
            description=f'Machine learning model detected {len(anomalies)} anomalous telemetry entries with average anomaly score of {avg_score:.3f}',
            evidence=anomalies[:10],  # Include first 10
            recommendations=[
                'Investigate the anomalous telemetry entries',
                'Compare with historical patterns',
                'Check for recent deployments or changes',
                'Monitor for continued anomalies',
                'Consider retraining ML model if patterns have shifted'
            ]
        )

    def save(self, path: str):
        """
        Save trained model to disk with integrity verification

        Uses joblib instead of pickle for security and adds SHA-256 signature
        """
        if not self.is_trained:
            raise RuntimeError("Cannot save untrained model")

        if not JOBLIB_AVAILABLE:
            raise RuntimeError("joblib not installed. Cannot save model.")

        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'version': '3.0.0'
        }

        # Save with joblib (safer than pickle)
        joblib.dump(model_data, path)

        # Create SHA-256 signature for integrity verification
        with open(path, 'rb') as f:
            content = f.read()
        signature = hashlib.sha256(content).hexdigest()

        # Save signature alongside model
        signature_path = f'{path}.sig'
        with open(signature_path, 'w') as f:
            f.write(signature)

    def load(self, path: str):
        """
        Load trained model from disk with integrity verification

        Verifies SHA-256 signature before loading
        """
        if not JOBLIB_AVAILABLE:
            raise RuntimeError("joblib not installed. Cannot load model.")

        # Verify signature first
        signature_path = f'{path}.sig'

        # Read current file and compute signature
        with open(path, 'rb') as f:
            content = f.read()
        computed_signature = hashlib.sha256(content).hexdigest()

        # Compare with stored signature
        try:
            with open(signature_path, 'r') as f:
                expected_signature = f.read().strip()

            if computed_signature != expected_signature:
                raise SecurityError(
                    "Model file signature mismatch. File may be corrupted or tampered with."
                )
        except FileNotFoundError:
            raise SecurityError(
                "Model signature file not found. Cannot verify model integrity."
            )

        # Signature verified, safe to load
        model_data = joblib.load(path)

        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.feature_names = model_data['feature_names']
        self.is_trained = True


class SecurityError(Exception):
    """Raised when security checks fail"""
    pass


# Example usage
if __name__ == '__main__':
    # Create detector
    detector = MLAnomalyDetector(contamination=0.1)

    # Train on normal data (would come from real telemetry)
    normal_data = [
        {
            'telemetry_type': 'metric',
            'data': {
                'metrics': {
                    'cpu_percent': 30 + i,
                    'memory_percent': 40 + i,
                    'request_rate': 100,
                    'error_rate': 0.5,
                    'avg_latency_ms': 100
                }
            }
        }
        for i in range(100)
    ]

    detector.train(normal_data)

    # Detect anomalies
    test_data = normal_data[:50] + [
        {
            'telemetry_type': 'metric',
            'data': {
                'metrics': {
                    'cpu_percent': 95,  # Anomalous
                    'memory_percent': 90,
                    'request_rate': 500,
                    'error_rate': 15,
                    'avg_latency_ms': 5000
                }
            }
        }
    ]

    anomalies = detector.detect_anomalies(test_data)
    print(f"Detected {len(anomalies)} anomalies")

    finding = detector.create_finding(anomalies)
    if finding:
        print(f"Finding: {finding.title}")
