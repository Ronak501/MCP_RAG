"""
REST API and Monitoring Dashboard for Surveillance System
Provides real-time status, alerts, and control interface
"""
from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS
from werkzeug.exceptions import BadRequest
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from pathlib import Path
import threading

logger = logging.getLogger(__name__)


class SurveillanceAPI:
    """REST API for surveillance system"""
    
    def __init__(self, surveillance_engine, notification_manager, multi_source_coordinator):
        self.app = Flask(__name__)
        CORS(self.app)
        self.engine = surveillance_engine
        self.notification_manager = notification_manager
        self.coordinator = multi_source_coordinator
        
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup API routes"""
        
        # System Status
        @self.app.route("/api/status", methods=["GET"])
        def get_status():
            """Get system status"""
            try:
                return jsonify({
                    "timestamp": datetime.now().isoformat(),
                    "system": self.engine.get_status(),
                    "sources": self.coordinator.get_sources_status(),
                    "notifications": self.notification_manager.get_stats()
                })
            except Exception as e:
                logger.error(f"Error getting status: {e}")
                return jsonify({"error": str(e)}), 500
        
        # Camera Management
        @self.app.route("/api/cameras", methods=["GET"])
        def list_cameras():
            """List all cameras"""
            try:
                return jsonify({
                    "cameras": self.coordinator.get_sources_status(),
                    "count": len(self.coordinator.sources)
                })
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        @self.app.route("/api/cameras/<source_id>/enable", methods=["POST"])
        def enable_camera(source_id):
            """Enable a camera"""
            try:
                self.coordinator.enable_source(source_id)
                return jsonify({"status": "enabled", "source_id": source_id})
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        @self.app.route("/api/cameras/<source_id>/disable", methods=["POST"])
        def disable_camera(source_id):
            """Disable a camera"""
            try:
                self.coordinator.disable_source(source_id)
                return jsonify({"status": "disabled", "source_id": source_id})
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        @self.app.route("/api/cameras/<source_id>/stats", methods=["GET"])
        def get_camera_stats(source_id):
            """Get camera statistics"""
            try:
                stats = self.coordinator.get_source_stats(source_id)
                return jsonify({
                    "source_id": source_id,
                    "stats": stats
                })
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        # Alerts Management
        @self.app.route("/api/alerts", methods=["GET"])
        def get_alerts():
            """Get recent alerts"""
            try:
                count = request.args.get("count", 50, type=int)
                severity = request.args.get("severity", None)
                
                if severity:
                    alerts = self.engine.alert_manager.get_alerts_by_severity(severity)
                else:
                    alerts = self.engine.alert_manager.get_recent_alerts(count)
                
                return jsonify({
                    "alerts": alerts,
                    "count": len(alerts)
                })
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        @self.app.route("/api/alerts/summary", methods=["GET"])
        def get_alerts_summary():
            """Get alert summary statistics"""
            try:
                all_alerts = list(self.engine.alert_manager.alerts)
                
                summary = {
                    "total": len(all_alerts),
                    "by_severity": {},
                    "by_source": {},
                    "by_type": {}
                }
                
                for alert in all_alerts:
                    # By severity
                    severity = alert.severity.value
                    summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1
                    
                    # By source
                    source = alert.source_id
                    summary["by_source"][source] = summary["by_source"].get(source, 0) + 1
                    
                    # By type
                    event_type = alert.event_type
                    summary["by_type"][event_type] = summary["by_type"].get(event_type, 0) + 1
                
                return jsonify(summary)
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        # Notifications Management
        @self.app.route("/api/notifications/config", methods=["GET"])
        def get_notification_config():
            """Get notification configuration"""
            try:
                config = {}
                for channel, handler in self.notification_manager.handlers.items():
                    config[channel.value] = {
                        "enabled": handler.enabled,
                        "severity_filter": list(handler.filter.enabled_severities)
                    }
                return jsonify(config)
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        @self.app.route("/api/notifications/config", methods=["POST"])
        def update_notification_config():
            """Update notification configuration"""
            try:
                data = request.json
                
                for channel_name, config in data.items():
                    try:
                        from notification_system import NotificationChannel
                        channel = NotificationChannel[channel_name.upper()]
                        
                        if channel in self.notification_manager.handlers:
                            handler = self.notification_manager.handlers[channel]
                            if "enabled" in config:
                                handler.enabled = config["enabled"]
                            if "severity_filter" in config:
                                handler.filter.enabled_severities = set(config["severity_filter"])
                    except Exception as e:
                        logger.error(f"Error updating {channel_name}: {e}")
                
                return jsonify({"status": "updated"})
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        # System Control
        @self.app.route("/api/system/start", methods=["POST"])
        def start_system():
            """Start surveillance system"""
            try:
                self.engine.start()
                self.coordinator.start_all_sources()
                return jsonify({"status": "started"})
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        @self.app.route("/api/system/stop", methods=["POST"])
        def stop_system():
            """Stop surveillance system"""
            try:
                self.engine.stop()
                self.coordinator.stop_all_sources()
                return jsonify({"status": "stopped"})
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        @self.app.route("/api/system/stats", methods=["GET"])
        def get_system_stats():
            """Get overall system statistics"""
            try:
                status = self.engine.get_status()
                notifications = self.notification_manager.get_stats()
                
                return jsonify({
                    "engine": status["stats"],
                    "notifications": notifications,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        # Dashboard HTML
        @self.app.route("/dashboard", methods=["GET"])
        def dashboard():
            """Serve monitoring dashboard"""
            html = self._get_dashboard_html()
            return render_template_string(html)
        
        # Error handlers
        @self.app.errorhandler(404)
        def not_found(e):
            return jsonify({"error": "Not found"}), 404
        
        @self.app.errorhandler(500)
        def internal_error(e):
            return jsonify({"error": "Internal server error"}), 500
    
    def _get_dashboard_html(self) -> str:
        """Get dashboard HTML"""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>Surveillance System Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: #333;
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        header {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        h1 {
            color: #1e3c72;
            font-size: 28px;
        }
        .control-buttons {
            display: flex;
            gap: 10px;
        }
        button {
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
            transition: all 0.3s;
        }
        .btn-start {
            background: #4CAF50;
            color: white;
        }
        .btn-start:hover {
            background: #45a049;
        }
        .btn-stop {
            background: #f44336;
            color: white;
        }
        .btn-stop:hover {
            background: #da190b;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .card h2 {
            font-size: 18px;
            color: #1e3c72;
            margin-bottom: 15px;
            border-bottom: 2px solid #2a5298;
            padding-bottom: 10px;
        }
        .stat {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }
        .stat:last-child {
            border-bottom: none;
        }
        .stat-label {
            font-weight: 600;
            color: #555;
        }
        .stat-value {
            color: #2a5298;
            font-weight: bold;
        }
        .status-badge {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
        }
        .badge-active {
            background: #4CAF50;
            color: white;
        }
        .badge-inactive {
            background: #999;
            color: white;
        }
        .badge-critical {
            background: #f44336;
            color: white;
        }
        .badge-high {
            background: #ff9800;
            color: white;
        }
        .badge-medium {
            background: #ffc107;
            color: white;
        }
        .alert-list {
            max-height: 400px;
            overflow-y: auto;
        }
        .alert-item {
            padding: 10px;
            margin-bottom: 10px;
            border-left: 4px solid #ddd;
            background: #f9f9f9;
            border-radius: 4px;
        }
        .alert-item.critical {
            border-left-color: #f44336;
        }
        .alert-item.high {
            border-left-color: #ff9800;
        }
        .alert-time {
            font-size: 12px;
            color: #999;
        }
        .refresh-indicator {
            color: #999;
            font-size: 12px;
        }
        .updating {
            animation: pulse 1s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎥 Surveillance System Dashboard</h1>
            <div class="control-buttons">
                <button class="btn-start" onclick="startSystem()">▶ Start</button>
                <button class="btn-stop" onclick="stopSystem()">⏹ Stop</button>
            </div>
        </header>
        
        <div class="grid">
            <div class="card">
                <h2>System Status</h2>
                <div id="system-status"></div>
            </div>
            
            <div class="card">
                <h2>Active Cameras</h2>
                <div id="cameras-status"></div>
            </div>
            
            <div class="card">
                <h2>Alert Summary</h2>
                <div id="alerts-summary"></div>
            </div>
            
            <div class="card" style="grid-column: 1 / -1;">
                <h2>Recent Alerts</h2>
                <div class="alert-list" id="alerts-list"></div>
            </div>
        </div>
        
        <div style="text-align: center; color: white;">
            Last updated: <span class="refresh-indicator" id="update-time">--:--:--</span>
        </div>
    </div>
    
    <script>
        async function updateDashboard() {
            try {
                const statusRes = await fetch('/api/status');
                const status = await statusRes.json();
                
                const alertsRes = await fetch('/api/alerts/summary');
                const alerts = await alertsRes.json();
                
                const alertsListRes = await fetch('/api/alerts?count=10');
                const alertsList = await alertsListRes.json();
                
                updateSystemStatus(status);
                updateCamerasStatus(status);
                updateAlertsStatus(alerts);
                updateAlertsList(alertsList);
                updateTime();
            } catch (error) {
                console.error('Error updating dashboard:', error);
            }
        }
        
        function updateSystemStatus(status) {
            const running = status.system.running;
            const stats = status.system.stats;
            
            const html = `
                <div class="stat">
                    <span class="stat-label">Status</span>
                    <span class="status-badge ${running ? 'badge-active' : 'badge-inactive'}">
                        ${running ? 'RUNNING' : 'STOPPED'}
                    </span>
                </div>
                <div class="stat">
                    <span class="stat-label">Frames Processed</span>
                    <span class="stat-value">${stats.total_frames_processed.toLocaleString()}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Events Detected</span>
                    <span class="stat-value">${stats.total_events_detected}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Active Sources</span>
                    <span class="stat-value">${stats.sources_active}</span>
                </div>
            `;
            document.getElementById('system-status').innerHTML = html;
        }
        
        function updateCamerasStatus(status) {
            const sources = status.sources;
            let html = '';
            
            for (const [sourceId, source] of Object.entries(sources)) {
                const statusBadge = source.status === 'active' 
                    ? 'badge-active' 
                    : source.status === 'error' 
                    ? 'badge-critical' 
                    : 'badge-inactive';
                
                html += `
                    <div class="stat">
                        <span class="stat-label">${sourceId}</span>
                        <span class="status-badge ${statusBadge}">${source.status.toUpperCase()}</span>
                    </div>
                `;
            }
            
            document.getElementById('cameras-status').innerHTML = html || '<p>No cameras configured</p>';
        }
        
        function updateAlertsStatus(alerts) {
            let html = `
                <div class="stat">
                    <span class="stat-label">Total Alerts</span>
                    <span class="stat-value">${alerts.total}</span>
                </div>
            `;
            
            for (const [severity, count] of Object.entries(alerts.by_severity)) {
                const badgeClass = 'badge-' + severity;
                html += `
                    <div class="stat">
                        <span class="stat-label">${severity.charAt(0).toUpperCase() + severity.slice(1)}</span>
                        <span class="status-badge ${badgeClass}">${count}</span>
                    </div>
                `;
            }
            
            document.getElementById('alerts-summary').innerHTML = html;
        }
        
        function updateAlertsList(data) {
            if (!data.alerts || data.alerts.length === 0) {
                document.getElementById('alerts-list').innerHTML = '<p style="color: #999;">No alerts</p>';
                return;
            }
            
            let html = '';
            for (const alert of data.alerts.slice().reverse()) {
                const time = new Date(alert.timestamp).toLocaleTimeString();
                const alertClass = alert.severity === 'critical' || alert.severity === 'high' ? alert.severity : '';
                
                html += `
                    <div class="alert-item ${alertClass}">
                        <strong>${alert.event_type}</strong> - ${alert.source_id}
                        <div style="margin-top: 5px;">
                            Confidence: ${(alert.confidence * 100).toFixed(1)}%
                        </div>
                        <div class="alert-time">${time}</div>
                    </div>
                `;
            }
            
            document.getElementById('alerts-list').innerHTML = html;
        }
        
        function updateTime() {
            const now = new Date();
            document.getElementById('update-time').textContent = now.toLocaleTimeString();
        }
        
        async function startSystem() {
            try {
                await fetch('/api/system/start', { method: 'POST' });
                updateDashboard();
            } catch (error) {
                console.error('Error starting system:', error);
            }
        }
        
        async function stopSystem() {
            try {
                await fetch('/api/system/stop', { method: 'POST' });
                updateDashboard();
            } catch (error) {
                console.error('Error stopping system:', error);
            }
        }
        
        // Update dashboard every 2 seconds
        updateDashboard();
        setInterval(updateDashboard, 2000);
    </script>
</body>
</html>
        """
    
    def run(self, host="0.0.0.0", port=5000, debug=False):
        """Run the API server"""
        logger.info(f"Starting API server on {host}:{port}")
        self.app.run(host=host, port=port, debug=debug, threaded=True)
