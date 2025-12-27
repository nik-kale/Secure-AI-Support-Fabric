"""
Simple web dashboard for AI Support Fabric Lab
Displays telemetry statistics, findings, and remediation plans
"""
import os
import sys
import secrets
from datetime import datetime
from flask import Flask, render_template_string, jsonify, g
from flask_cors import CORS
import requests

# Add parent directory to path for lab.common imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from lab.common.logging_config import setup_logging
from lab.common.security_headers import setup_security_headers

# Setup logging
logger = setup_logging('ui_dash')

app = Flask(__name__)
setup_security_headers(app)

@app.before_request
def generate_nonce():
    g.nonce = secrets.token_hex(16)

# Secure CORS - restrict to allowed origins only
allowed_origins = os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000').split(',')
CORS(app, resources={
    r"/*": {
        "origins": allowed_origins,
        "methods": ["GET"],
        "allow_headers": ["Content-Type"],
    }
})

# Gateway URL and API Key
GATEWAY_URL = os.getenv('GATEWAY_URL', 'http://gateway:8080')
API_KEY = os.getenv('API_KEY', '')

# HTML template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Support Fabric - Lab Dashboard</title>
    <style nonce="{{ nonce }}">
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            padding: 20px;
            min-height: 100vh;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        header {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }
        h1 {
            color: #667eea;
            margin-bottom: 10px;
        }
        .subtitle {
            color: #666;
            font-size: 14px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .card {
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .card h2 {
            color: #667eea;
            margin-bottom: 15px;
            font-size: 18px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        .stat {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }
        .stat:last-child {
            border-bottom: none;
        }
        .stat-label {
            color: #666;
            font-size: 14px;
        }
        .stat-value {
            font-weight: bold;
            font-size: 18px;
            color: #333;
        }
        .finding {
            background: #f8f9fa;
            padding: 15px;
            margin: 10px 0;
            border-radius: 8px;
            border-left: 4px solid #ffc107;
        }
        .finding.HIGH {
            border-left-color: #ff5722;
        }
        .finding.CRITICAL {
            border-left-color: #d32f2f;
        }
        .finding.MEDIUM {
            border-left-color: #ff9800;
        }
        .finding-title {
            font-weight: bold;
            margin-bottom: 5px;
            color: #333;
        }
        .finding-severity {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: bold;
            margin-bottom: 8px;
        }
        .severity-HIGH {
            background: #ff5722;
            color: white;
        }
        .severity-CRITICAL {
            background: #d32f2f;
            color: white;
        }
        .severity-MEDIUM {
            background: #ff9800;
            color: white;
        }
        .severity-LOW {
            background: #4caf50;
            color: white;
        }
        .finding-desc {
            font-size: 13px;
            color: #666;
            line-height: 1.5;
        }
        .remediation {
            background: #e3f2fd;
            padding: 15px;
            margin: 10px 0;
            border-radius: 8px;
            border-left: 4px solid #2196f3;
        }
        .remediation-title {
            font-weight: bold;
            margin-bottom: 10px;
            color: #1976d2;
        }
        .step {
            background: white;
            padding: 8px 12px;
            margin: 5px 0;
            border-radius: 4px;
            font-size: 13px;
        }
        .step-number {
            display: inline-block;
            background: #2196f3;
            color: white;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            text-align: center;
            line-height: 20px;
            font-size: 11px;
            margin-right: 8px;
        }
        .refresh-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
            transition: background 0.3s;
        }
        .refresh-btn:hover {
            background: #5568d3;
        }
        .analyze-btn {
            background: #4caf50;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
            margin-left: 10px;
            transition: background 0.3s;
        }
        .analyze-btn:hover {
            background: #45a049;
        }
        .no-data {
            text-align: center;
            color: #999;
            padding: 20px;
            font-style: italic;
        }
        .timestamp {
            color: #999;
            font-size: 12px;
            margin-top: 10px;
        }
        .controls {
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>AI Support Fabric - Lab Dashboard</h1>
            <p class="subtitle">Synthetic telemetry, agentic detection, and guided remediation</p>
        </header>

        <div class="controls">
            <button class="refresh-btn" onclick="loadData()">Refresh Data</button>
            <button class="analyze-btn" onclick="runAnalysis()">Run Analysis</button>
        </div>

        <div class="grid">
            <div class="card">
                <h2>System Status</h2>
                <div id="status-content">
                    <div class="no-data">Loading...</div>
                </div>
            </div>

            <div class="card">
                <h2>Telemetry Statistics</h2>
                <div id="telemetry-stats">
                    <div class="no-data">Loading...</div>
                </div>
            </div>

            <div class="card">
                <h2>Detection Summary</h2>
                <div id="detection-summary">
                    <div class="no-data">Loading...</div>
                </div>
            </div>
        </div>

        <div class="grid">
            <div class="card" style="grid-column: 1 / -1;">
                <h2>Recent Findings</h2>
                <div id="findings-content">
                    <div class="no-data">No findings yet</div>
                </div>
            </div>
        </div>

        <div class="grid">
            <div class="card" style="grid-column: 1 / -1;">
                <h2>Remediation Plans</h2>
                <div id="remediation-content">
                    <div class="no-data">No remediation plans yet</div>
                </div>
            </div>
        </div>
    </div>

    <script nonce="{{ nonce }}">
        const GATEWAY_URL = window.location.protocol + '//' + window.location.hostname + ':8080';
        const API_KEY = '{{ api_key }}';

        // XSS Protection Utility
        function escapeHtml(text) {
            if (text === null || text === undefined) return '';
            return String(text)
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
        }

        // Helper function to create headers with API key
        function getHeaders() {
            return {
                'Content-Type': 'application/json',
                'X-API-Key': API_KEY
            };
        }

        async function loadData() {
            try {
                // Load status
                const statusResp = await fetch(`${GATEWAY_URL}/api/status`, {
                    headers: getHeaders()
                });
                const statusData = await statusResp.json();
                displayStatus(statusData);

                // Load findings
                const findingsResp = await fetch(`${GATEWAY_URL}/api/ai/findings?limit=20`, {
                    headers: getHeaders()
                });
                const findingsData = await findingsResp.json();
                displayFindings(findingsData);

                // Load remediation
                const remediationResp = await fetch(`${GATEWAY_URL}/api/ai/remediation?limit=20`, {
                    headers: getHeaders()
                });
                const remediationData = await remediationResp.json();
                displayRemediation(remediationData);
            } catch (error) {
                console.error('Error loading data:', error);
            }
        }

        async function runAnalysis() {
            try {
                const btn = event.target;
                btn.disabled = true;
                btn.textContent = 'Running Analysis...';

                const resp = await fetch(`${GATEWAY_URL}/api/run-analysis`, {
                    method: 'POST',
                    headers: getHeaders()
                });
                const data = await resp.json();

                btn.disabled = false;
                btn.textContent = 'Run Analysis';

                // Reload data after analysis
                setTimeout(loadData, 1000);
            } catch (error) {
                console.error('Error running analysis:', error);
                event.target.disabled = false;
                event.target.textContent = 'Run Analysis';
            }
        }

        function displayStatus(data) {
            const telemetryStats = data.telemetry?.statistics || {};
            const statusHtml = `
                <div class="stat">
                    <span class="stat-label">Total Telemetry</span>
                    <span class="stat-value">${telemetryStats.total_count || 0}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Logs</span>
                    <span class="stat-value">${telemetryStats.count_by_type?.log || 0}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Metrics</span>
                    <span class="stat-value">${telemetryStats.count_by_type?.metric || 0}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Config Events</span>
                    <span class="stat-value">${telemetryStats.count_by_type?.config || 0}</span>
                </div>
            `;
            document.getElementById('status-content').innerHTML = statusHtml;

            const telemetryHtml = `
                <div class="stat">
                    <span class="stat-label">Total Count</span>
                    <span class="stat-value">${telemetryStats.total_count || 0}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Latest Update</span>
                    <span class="stat-value" style="font-size: 12px;">${telemetryStats.latest_telemetry || 'N/A'}</span>
                </div>
            `;
            document.getElementById('telemetry-stats').innerHTML = telemetryHtml;
        }

        function displayFindings(data) {
            const findings = data.findings || [];
            const summaryHtml = `
                <div class="stat">
                    <span class="stat-label">Total Findings</span>
                    <span class="stat-value">${findings.length}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Critical</span>
                    <span class="stat-value" style="color: #d32f2f;">${findings.filter(f => f.severity === 'CRITICAL').length}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">High</span>
                    <span class="stat-value" style="color: #ff5722;">${findings.filter(f => f.severity === 'HIGH').length}</span>
                </div>
            `;
            document.getElementById('detection-summary').innerHTML = summaryHtml;

            if (findings.length === 0) {
                document.getElementById('findings-content').innerHTML = '<div class="no-data">No findings detected</div>';
                return;
            }

            const findingsHtml = findings.map(f => `
                <div class="finding ${escapeHtml(f.severity)}">
                    <span class="finding-severity severity-${escapeHtml(f.severity)}">${escapeHtml(f.severity)}</span>
                    <div class="finding-title">${escapeHtml(f.title)}</div>
                    <div class="finding-desc">${escapeHtml(f.description)}</div>
                    <div class="timestamp">Detected: ${escapeHtml(f.detected_at)}</div>
                </div>
            `).join('');

            document.getElementById('findings-content').innerHTML = findingsHtml;
        }

        function displayRemediation(data) {
            const plans = data.remediation_plans || [];

            if (plans.length === 0) {
                document.getElementById('remediation-content').innerHTML = '<div class="no-data">No remediation plans</div>';
                return;
            }

            const remediationHtml = plans.map(plan => `
                <div class="remediation">
                    <div class="remediation-title">${escapeHtml(plan.title)}</div>
                    ${plan.steps.slice(0, 5).map(step => `
                        <div class="step">
                            <span class="step-number">${escapeHtml(step.step)}</span>
                            <strong>${escapeHtml(step.action)}</strong>: ${escapeHtml(step.description)}
                        </div>
                    `).join('')}
                    ${plan.steps.length > 5 ? `<div class="step">... and ${plan.steps.length - 5} more steps</div>` : ''}
                    <div class="timestamp">Created: ${escapeHtml(plan.created_at)}</div>
                </div>
            `).join('');

            document.getElementById('remediation-content').innerHTML = remediationHtml;
        }

        // Load data on page load
        loadData();

        // Auto-refresh every 30 seconds
        setInterval(loadData, 30000);
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    """Main dashboard page"""
    logger.info("Dashboard page accessed")
    return render_template_string(HTML_TEMPLATE, api_key=API_KEY, nonce=g.nonce)


@app.route('/health')
def health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'service': 'ui_dash',
        'timestamp': datetime.utcnow().isoformat()
    })


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=3000,
        debug=os.getenv('DEBUG', 'False').lower() == 'true'
    )
