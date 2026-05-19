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
                        from core.notification_system import NotificationChannel
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
        return """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Surveillance System Dashboard</title>
  <style>
    body { font-family: Arial, sans-serif; background:#f2f6fb; color:#222 }
    .container { max-width:1100px; margin:20px auto }
    header { display:flex; justify-content:space-between; align-items:center }
    .card { background:#fff; padding:16px; border-radius:8px; box-shadow:0 1px 6px rgba(0,0,0,0.06); margin-bottom:12px }
    .grid { display:grid; grid-template-columns: 1fr 1fr; gap:12px }
    .alert-item { padding:8px; border-left:4px solid #ccc; margin-bottom:8px }
    .controls button{ margin-left:8px }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>Surveillance Dashboard</h1>
      <div class="controls">
        <button onclick="fetch('/api/system/start',{method:'POST'})">Start</button>
        <button onclick="fetch('/api/system/stop',{method:'POST'})">Stop</button>
        <span id="status" style="margin-left:12px;color:#666">Status: idle</span>
      </div>
    </header>

    <div class="grid">
      <div class="card">
        <h3>System Status</h3>
        <pre id="system_status">Loading...</pre>
      </div>
      <div class="card">
        <h3>Recent Alerts</h3>
        <div id="alerts" class="alert-list">Loading...</div>
      </div>
    </div>

    <script>
      async function refresh(){
        try{
          const s = await fetch('/api/status').then(r=>r.json())
          document.getElementById('system_status').textContent = JSON.stringify(s,null,2)
          const a = await fetch('/api/alerts?count=10').then(r=>r.json())
          const list = document.getElementById('alerts')
          list.innerHTML = ''
          (a.alerts||[]).forEach(it=>{
            const div = document.createElement('div')
            div.className='alert-item'
            div.textContent = `${it.timestamp || ''} - ${it.event_type || it.type || 'alert'} - ${it.severity||''}`
            list.appendChild(div)
          })
        }catch(e){ console.warn(e) }
      }
      setInterval(refresh,3000)
      refresh()
    </script>
  </div>
</body>
</html>"""

    def run(self, host: str = "0.0.0.0", port: int = 5000, debug: bool = False):
        """Run the Flask app (simple wrapper)."""
        self.app.run(host=host, port=port, debug=debug)