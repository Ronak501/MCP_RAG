"""
Autonomous Surveillance Intelligence Engine
Handles real-time monitoring, multi-source video input, and alert management
"""
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable
import threading
from dataclasses import dataclass, asdict
from enum import Enum

import cv2
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CameraStatus(Enum):
    """Camera/source status"""
    INACTIVE = "inactive"
    CONNECTING = "connecting"
    ACTIVE = "active"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class DetectionEvent:
    """Represents a single detection event"""
    timestamp: datetime
    source_id: str
    event_type: str
    confidence: float
    severity: AlertSeverity
    frame_data: Optional[str] = None  # Base64 encoded frame
    details: Dict = None

    def to_dict(self):
        return {
            "timestamp": self.timestamp.isoformat(),
            "source_id": self.source_id,
            "event_type": self.event_type,
            "confidence": self.confidence,
            "severity": self.severity.value,
            "frame_data": self.frame_data,
            "details": self.details or {}
        }


@dataclass
class CameraSource:
    """Video source configuration"""
    source_id: str
    source_path: str  # File path, URL, or device index
    source_type: str  # "file", "rtsp", "http", "device"
    enabled: bool = True
    fps: int = 30
    resolution: tuple = (1280, 720)
    stride: int = 30
    confidence_threshold: float = 0.5


class VideoSourceManager:
    """Manages multiple video sources"""

    def __init__(self):
        self.sources: Dict[str, CameraSource] = {}
        self.captures: Dict[str, cv2.VideoCapture] = {}
        self.status: Dict[str, CameraStatus] = {}
        self.frame_queues: Dict[str, deque] = defaultdict(lambda: deque(maxlen=2))
        self.lock = threading.Lock()

    def add_source(self, source: CameraSource):
        """Add a video source"""
        with self.lock:
            self.sources[source.source_id] = source
            self.status[source.source_id] = CameraStatus.INACTIVE
            logger.info(f"Added source: {source.source_id}")

    def remove_source(self, source_id: str):
        """Remove a video source"""
        with self.lock:
            if source_id in self.captures:
                self.captures[source_id].release()
                del self.captures[source_id]
            if source_id in self.sources:
                del self.sources[source_id]
            logger.info(f"Removed source: {source_id}")

    def get_frame(self, source_id: str) -> Optional[tuple]:
        """Get latest frame from source (frame, timestamp)"""
        with self.lock:
            if source_id in self.frame_queues and len(self.frame_queues[source_id]) > 0:
                return self.frame_queues[source_id][-1]
        return None

    def set_source_status(self, source_id: str, status: CameraStatus):
        """Update source status"""
        with self.lock:
            self.status[source_id] = status

    def get_source_status(self, source_id: str) -> CameraStatus:
        """Get source status"""
        with self.lock:
            return self.status.get(source_id, CameraStatus.INACTIVE)


class AlertManager:
    """Manages alerts and notifications"""

    def __init__(self, max_history: int = 1000):
        self.alerts: deque = deque(maxlen=max_history)
        self.subscribers: List[Callable] = []
        self.alert_lock = threading.Lock()
        self.suppress_duration: Dict[str, int] = {}  # Alert suppression in seconds

    def subscribe(self, callback: Callable):
        """Subscribe to alerts"""
        self.subscribers.append(callback)

    def unsubscribe(self, callback: Callable):
        """Unsubscribe from alerts"""
        if callback in self.subscribers:
            self.subscribers.remove(callback)

    def create_alert(self, event: DetectionEvent):
        """Create and dispatch an alert"""
        with self.alert_lock:
            self.alerts.append(event)

            # Notify all subscribers
            for callback in self.subscribers:
                try:
                    callback(event)
                except Exception as e:
                    logger.error(f"Error in alert callback: {e}")

    def get_recent_alerts(self, count: int = 50) -> List[Dict]:
        """Get recent alerts"""
        with self.alert_lock:
            return [alert.to_dict() for alert in list(self.alerts)[-count:]]

    def get_alerts_by_severity(self, severity: AlertSeverity) -> List[Dict]:
        """Get alerts by severity level"""
        with self.alert_lock:
            return [
                alert.to_dict() for alert in self.alerts 
                if alert.severity == severity
            ]


class SurveillanceEngine:
    """Main surveillance intelligence engine"""

    def __init__(self, agent_module=None):
        self.video_manager = VideoSourceManager()
        self.alert_manager = AlertManager()
        self.agent = agent_module  # Optional MCP-RAG agent
        self.running = False
        self.monitor_threads: Dict[str, threading.Thread] = {}
        self.stats = {
            "total_frames_processed": 0,
            "total_events_detected": 0,
            "sources_active": 0,
            "start_time": None
        }
        self.stats_lock = threading.Lock()

    def add_camera(self, source: CameraSource):
        """Register a camera/video source"""
        self.video_manager.add_source(source)

    def remove_camera(self, source_id: str):
        """Unregister a camera"""
        self.video_manager.remove_source(source_id)
        if source_id in self.monitor_threads:
            self.monitor_threads[source_id].join(timeout=5)
            del self.monitor_threads[source_id]

    def start_monitoring(self, source_id: str, detection_callback: Callable):
        """Start monitoring a specific source"""
        if source_id not in self.video_manager.sources:
            raise ValueError(f"Source {source_id} not registered")

        thread = threading.Thread(
            target=self._monitor_source,
            args=(source_id, detection_callback),
            daemon=True,
            name=f"monitor-{source_id}"
        )
        thread.start()
        self.monitor_threads[source_id] = thread
        logger.info(f"Started monitoring source: {source_id}")

    def _monitor_source(self, source_id: str, detection_callback: Callable):
        """Monitor a single video source"""
        source = self.video_manager.sources[source_id]
        cap = None
        frame_count = 0

        try:
            self.video_manager.set_source_status(source_id, CameraStatus.CONNECTING)

            # Open video source
            if source.source_type == "device":
                cap = cv2.VideoCapture(int(source.source_path))
            else:
                cap = cv2.VideoCapture(source.source_path)

            if not cap.isOpened():
                raise RuntimeError(f"Failed to open source: {source.source_path}")

            self.video_manager.captures[source_id] = cap
            self.video_manager.set_source_status(source_id, CameraStatus.ACTIVE)

            with self.stats_lock:
                self.stats["sources_active"] += 1

            logger.info(f"Connected to {source_id}")

            while self.running and cap.isOpened():
                ret, frame = cap.read()

                if not ret:
                    logger.warning(f"Failed to read frame from {source_id}")
                    break

                frame_count += 1

                # Process every Nth frame based on stride
                if frame_count % source.stride == 0:
                    try:
                        # Resize to configured resolution
                        frame = cv2.resize(frame, source.resolution)

                        # Run detection callback
                        detection_callback(frame, source)

                        with self.stats_lock:
                            self.stats["total_frames_processed"] += 1

                    except Exception as e:
                        logger.error(f"Error processing frame from {source_id}: {e}")

        except Exception as e:
            logger.error(f"Error monitoring {source_id}: {e}")
            self.video_manager.set_source_status(source_id, CameraStatus.ERROR)

        finally:
            if cap:
                cap.release()
            self.video_manager.set_source_status(source_id, CameraStatus.INACTIVE)
            with self.stats_lock:
                self.stats["sources_active"] -= 1
            logger.info(f"Stopped monitoring {source_id}")

    def start(self):
        """Start the surveillance engine"""
        self.running = True
        with self.stats_lock:
            self.stats["start_time"] = datetime.now().isoformat()
        logger.info("Surveillance engine started")

    def stop(self):
        """Stop the surveillance engine"""
        self.running = False
        # Clean up all monitoring threads
        for source_id in list(self.monitor_threads.keys()):
            self.monitor_threads[source_id].join(timeout=5)
        logger.info("Surveillance engine stopped")

    def get_status(self) -> Dict:
        """Get system status"""
        with self.stats_lock:
            return {
                "running": self.running,
                "stats": dict(self.stats),
                "sources": {
                    sid: {
                        "status": self.video_manager.get_source_status(sid).value,
                        "config": asdict(self.video_manager.sources[sid])
                    }
                    for sid in self.video_manager.sources
                },
                "alert_count": len(self.alert_manager.alerts)
            }

    def subscribe_to_alerts(self, callback: Callable):
        """Subscribe to alert notifications"""
        self.alert_manager.subscribe(callback)

    def get_recent_alerts(self, count: int = 50) -> List[Dict]:
        """Get recent alerts"""
        return self.alert_manager.get_recent_alerts(count)
