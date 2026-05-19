#!/usr/bin/env python3
"""
Detection Log Viewer
View surveillance detection logs and alerts
"""
import json
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict


def print_header(title):
    """Print formatted header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def show_recent_alerts(count=20):
    """Show recent alerts from surveillance"""
    alert_dir = Path("alert_logs")
    
    if not alert_dir.exists():
        print("No alerts logged yet. Run surveillance system to generate logs.")
        return
    
    print_header(f"Recent Surveillance Alerts (Latest {count})")
    
    all_alerts = []
    
    # Collect all alert files
    for alert_file in sorted(alert_dir.glob("alerts_*.jsonl"), reverse=True):
        try:
            with open(alert_file) as f:
                for line in f:
                    if line.strip():
                        all_alerts.append(json.loads(line))
        except Exception as e:
            print(f"Error reading {alert_file}: {e}")
    
    if not all_alerts:
        print("No alerts found.")
        return
    
    # Show recent alerts
    for alert in all_alerts[-count:]:
        timestamp = alert.get("timestamp", "unknown")
        severity = alert.get("severity", "unknown").upper()
        source = alert.get("source_id", "unknown")
        event_type = alert.get("event_type", "unknown")
        confidence = alert.get("confidence", 0)
        
        # Color coding for severity
        severity_icon = {
            "CRITICAL": "🔴",
            "HIGH": "🟠",
            "MEDIUM": "🟡",
            "LOW": "🟢"
        }.get(severity, "⚪")
        
        print(f"\n{severity_icon} [{timestamp}] {severity}")
        print(f"   Source: {source}")
        print(f"   Event: {event_type}")
        print(f"   Confidence: {confidence:.1%}")
        if alert.get("details"):
            print(f"   Details: {alert['details']}")


def show_detection_logs(count=20):
    """Show detection logs from evaluation results"""
    eval_dir = Path("eval_results/runs")
    
    if not eval_dir.exists():
        print("No detection logs found.")
        return
    
    print_header(f"Recent Detection Logs (Latest {count})")
    
    # Get latest JSONL file
    jsonl_files = sorted(eval_dir.glob("*.jsonl"), reverse=True)
    
    if not jsonl_files:
        print("No detection logs found.")
        return
    
    latest_file = jsonl_files[0]
    print(f"📄 File: {latest_file.name}\n")
    
    detections = []
    try:
        with open(latest_file) as f:
            for line in f:
                if line.strip():
                    detections.append(json.loads(line))
    except Exception as e:
        print(f"Error reading log file: {e}")
        return
    
    if not detections:
        print("No detections in log file.")
        return
    
    # Show recent detections
    for i, det in enumerate(detections[-count:], 1):
        timestamp = det.get("timestamp", "unknown")
        frame_idx = det.get("frame_index", 0)
        severity = det.get("agent_severity", "unknown").upper()
        confidence = det.get("agent_confidence", 0)
        event_text = det.get("event_text", "no description")
        action = det.get("agent_primary_action", "")
        detections_obj = det.get("detections", [])
        
        # Severity icon
        severity_icon = {
            "CRITICAL": "🔴",
            "HIGH": "🟠",
            "MEDIUM": "🟡",
            "LOW": "🟢"
        }.get(severity, "⚪")
        
        print(f"\n{i}. {severity_icon} Frame {frame_idx} [{timestamp:.2f}]")
        print(f"   Severity: {severity}")
        print(f"   Confidence: {confidence:.1%}")
        print(f"   Event: {event_text}")
        if detections_obj:
            print(f"   Objects Detected: {', '.join(detections_obj)}")
        if action:
            print(f"   Action: {action}")


def show_statistics():
    """Show detection statistics"""
    print_header("Detection Statistics")
    
    eval_dir = Path("eval_results/runs")
    alert_dir = Path("alert_logs")
    
    stats = {
        "total_detections": 0,
        "by_severity": defaultdict(int),
        "by_event": defaultdict(int),
        "total_alerts": 0,
        "alerts_by_severity": defaultdict(int)
    }
    
    # Count detections
    if eval_dir.exists():
        for jsonl_file in eval_dir.glob("*.jsonl"):
            try:
                with open(jsonl_file) as f:
                    for line in f:
                        if line.strip():
                            det = json.loads(line)
                            stats["total_detections"] += 1
                            severity = det.get("agent_severity", "unknown").lower()
                            stats["by_severity"][severity] += 1
                            event = det.get("event_text", "unknown")[:30]
                            stats["by_event"][event] += 1
            except Exception as e:
                print(f"Error reading {jsonl_file}: {e}")
    
    # Count alerts
    if alert_dir.exists():
        for alert_file in alert_dir.glob("alerts_*.jsonl"):
            try:
                with open(alert_file) as f:
                    for line in f:
                        if line.strip():
                            alert = json.loads(line)
                            stats["total_alerts"] += 1
                            severity = alert.get("severity", "unknown").lower()
                            stats["alerts_by_severity"][severity] += 1
            except Exception as e:
                print(f"Error reading {alert_file}: {e}")
    
    print(f"\n📊 Total Detections: {stats['total_detections']}")
    print(f"🚨 Total Alerts: {stats['total_alerts']}")
    
    if stats["by_severity"]:
        print("\nDetections by Severity:")
        for severity in ["critical", "high", "medium", "low"]:
            count = stats["by_severity"].get(severity, 0)
            if count > 0:
                icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(severity, "⚪")
                print(f"  {icon} {severity.upper()}: {count}")
    
    if stats["alerts_by_severity"]:
        print("\nAlerts by Severity:")
        for severity in ["critical", "high", "medium", "low"]:
            count = stats["alerts_by_severity"].get(severity, 0)
            if count > 0:
                icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(severity, "⚪")
                print(f"  {icon} {severity.upper()}: {count}")
    
    if stats["by_event"]:
        print("\nTop Event Types:")
        sorted_events = sorted(stats["by_event"].items(), key=lambda x: x[1], reverse=True)
        for event, count in sorted_events[:5]:
            print(f"  • {event}: {count}")


def show_latest_run():
    """Show latest complete run summary"""
    print_header("Latest Run Summary")
    
    summaries_dir = Path("eval_results/summaries")
    
    if not summaries_dir.exists():
        print("No run summaries found.")
        return
    
    summary_files = sorted(summaries_dir.glob("*.json"), reverse=True)
    
    if not summary_files:
        print("No summaries found.")
        return
    
    latest = summary_files[0]
    
    try:
        with open(latest) as f:
            summary = json.load(f)
        
        print(f"📄 Run: {latest.stem}\n")
        
        # Print key metrics
        metrics = [
            ("Video", summary.get("video_path", "unknown")),
            ("Duration", f"{summary.get('total_runtime_seconds', 0):.2f}s"),
            ("Frames Processed", summary.get("total_frames_processed", 0)),
            ("Events Detected", summary.get("total_events", 0)),
            ("Average Confidence", f"{summary.get('avg_confidence', 0):.2%}"),
            ("Accuracy", f"{summary.get('accuracy', 0):.2%}"),
        ]
        
        for label, value in metrics:
            print(f"  {label}: {value}")
        
        # Actions
        if summary.get("actions_triggered"):
            print("\n  Actions Triggered:")
            for action in summary.get("actions_triggered", []):
                print(f"    • {action}")
    
    except Exception as e:
        print(f"Error reading summary: {e}")


def main():
    """Main menu"""
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        
        if cmd == "alerts":
            count = int(sys.argv[2]) if len(sys.argv) > 2 else 20
            show_recent_alerts(count)
        elif cmd == "detections":
            count = int(sys.argv[2]) if len(sys.argv) > 2 else 20
            show_detection_logs(count)
        elif cmd == "stats":
            show_statistics()
        elif cmd == "latest":
            show_latest_run()
        else:
            print(f"Unknown command: {cmd}")
            print("Available commands: alerts, detections, stats, latest")
    else:
        print("""
╔═══════════════════════════════════════════════════════════════╗
║          Detection Log Viewer                                 ║
╚═══════════════════════════════════════════════════════════════╝

Usage:
  python show_logs.py [command] [options]

Commands:
  alerts       - Show recent surveillance alerts
  detections   - Show recent detection logs
  stats        - Show detection statistics
  latest       - Show latest run summary

Examples:
  python show_logs.py alerts          # Show 20 latest alerts
  python show_logs.py alerts 50       # Show 50 latest alerts
  python show_logs.py detections      # Show 20 latest detections
  python show_logs.py detections 100  # Show 100 latest detections
  python show_logs.py stats           # Show statistics
  python show_logs.py latest          # Show latest run summary
        """)
        
        # Show summary by default
        show_statistics()
        show_latest_run()


if __name__ == "__main__":
    main()
