"""
Multi-source Video Coordinator
Manages multiple concurrent video streams and coordinates processing
"""
import logging
import threading
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from pathlib import Path
import json
from collections import defaultdict
from datetime import datetime

from core.surveillance_engine import (
    CameraSource, SurveillanceEngine, DetectionEvent, AlertSeverity, CameraStatus
)

logger = logging.getLogger(__name__)


@dataclass
class SourceConfig:
    """Configuration for a video source"""
    source_id: str
    source_path: str
    source_type: str  # "file", "rtsp", "http", "device"
    enabled: bool = True
    fps: int = 30
    resolution: tuple = (1280, 720)
    stride: int = 30
    confidence_threshold: float = 0.5
    location: str = "unknown"  # Camera location description
    zone: str = "default"  # Zone/area identifier


class MultiSourceCoordinator:
    """Coordinates multiple video sources"""

    def __init__(self, engine: SurveillanceEngine):
        self.engine = engine
        self.sources: Dict[str, SourceConfig] = {}
        self.detection_callbacks: Dict[str, Callable] = {}
        self.source_stats: Dict[str, Dict] = defaultdict(lambda: {
            "frames_processed": 0,
            "events_detected": 0,
            "errors": 0,
            "last_event": None
        })
        self.lock = threading.Lock()

    def load_sources_from_file(self, config_file: Path):
        """Load source configuration from JSON file"""
        try:
            with open(config_file, "r") as f:
                config = json.load(f)

            for source_data in config.get("sources", []):
                source_config = SourceConfig(**source_data)
                self.add_source(source_config)

            logger.info(f"Loaded {len(self.sources)} sources from {config_file}")
        except Exception as e:
            logger.error(f"Error loading source config: {e}")

    def add_source(self, config: SourceConfig):
        """Add a new video source"""
        with self.lock:
            self.sources[config.source_id] = config

        # Register with engine
        camera_source = CameraSource(
            source_id=config.source_id,
            source_path=config.source_path,
            source_type=config.source_type,
            enabled=config.enabled,
            fps=config.fps,
            resolution=config.resolution,
            stride=config.stride,
            confidence_threshold=config.confidence_threshold
        )
        self.engine.add_camera(camera_source)
        logger.info(f"Added source: {config.source_id} ({config.location})")

    def remove_source(self, source_id: str):
        """Remove a video source"""
        with self.lock:
            if source_id in self.sources:
                del self.sources[source_id]

        self.engine.remove_camera(source_id)
        logger.info(f"Removed source: {source_id}")

    def register_detection_callback(self, source_id: str, callback: Callable):
        """Register detection callback for a source"""
        self.detection_callbacks[source_id] = callback

    def start_all_sources(self):
        """Start monitoring all enabled sources"""
        with self.lock:
            active_sources = [
                config for config in self.sources.values()
                if config.enabled
            ]

        for config in active_sources:
            callback = self.detection_callbacks.get(
                config.source_id,
                self._default_detection_handler
            )
            self.engine.start_monitoring(config.source_id, callback)

    def stop_all_sources(self):
        """Stop monitoring all sources"""
        with self.lock:
            source_ids = list(self.sources.keys())

        for source_id in source_ids:
            self.engine.remove_camera(source_id)

    def _default_detection_handler(self, frame, source: CameraSource):
        """Default frame processing handler"""
        # This will be overridden by specific implementations
        pass

    def update_source_stats(
        self,
        source_id: str,
        frames: int = 0,
        events: int = 0,
        error: bool = False,
        event_time: Optional[str] = None
    ):
        """Update statistics for a source"""
        with self.lock:
            if source_id not in self.source_stats:
                self.source_stats[source_id] = {
                    "frames_processed": 0,
                    "events_detected": 0,
                    "errors": 0,
                    "last_event": None
                }

            self.source_stats[source_id]["frames_processed"] += frames
            self.source_stats[source_id]["events_detected"] += events
            if error:
                self.source_stats[source_id]["errors"] += 1
            if event_time:
                self.source_stats[source_id]["last_event"] = event_time

    def get_source_stats(self, source_id: Optional[str] = None) -> Dict:
        """Get statistics for sources"""
        with self.lock:
            if source_id:
                return self.source_stats.get(source_id, {})
            return dict(self.source_stats)

    def get_sources_status(self) -> List[Dict]:
        """Get status of all sources"""
        with self.lock:
            return [
                {
                    "source_id": config.source_id,
                    "location": config.location,
                    "zone": config.zone,
                    "status": self.engine.video_manager.get_source_status(
                        config.source_id
                    ).value,
                    "stats": self.source_stats.get(config.source_id, {})
                }
                for config in self.sources.values()
            ]

    def enable_source(self, source_id: str):
        """Enable a source"""
        with self.lock:
            if source_id in self.sources:
                self.sources[source_id].enabled = True
                logger.info(f"Enabled source: {source_id}")

    def disable_source(self, source_id: str):
        """Disable a source"""
        with self.lock:
            if source_id in self.sources:
                self.sources[source_id].enabled = False
                logger.info(f"Disabled source: {source_id}")


class ZoneBasedProcessor:
    """Process events based on zones"""

    def __init__(self):
        self.zone_rules: Dict[str, Dict] = {}
        self.zone_stats: Dict[str, Dict] = defaultdict(lambda: {
            "events": 0,
            "alerts": 0,
            "last_alert": None
        })
        self.lock = threading.Lock()

    def register_zone_rule(self, zone: str, rule: Dict):
        """Register a processing rule for a zone"""
        self.zone_rules[zone] = rule

    def process_zone_event(
        self,
        source_id: str,
        zone: str,
        event_type: str,
        confidence: float
    ) -> Optional[DetectionEvent]:
        """Process an event in a zone"""
        with self.lock:
            if zone not in self.zone_rules:
                # No specific rule, create default event
                return DetectionEvent(
                    timestamp=datetime.now(),
                    source_id=source_id,
                    event_type=event_type,
                    confidence=confidence,
                    severity=AlertSeverity.MEDIUM
                )

            rule = self.zone_rules[zone]
            self.zone_stats[zone]["events"] += 1

            # Apply zone-specific logic
            severity = self._calculate_severity(event_type, confidence, rule)

            event = DetectionEvent(
                timestamp=datetime.now(),
                source_id=source_id,
                event_type=event_type,
                confidence=confidence,
                severity=severity
            )

            if severity in [AlertSeverity.HIGH, AlertSeverity.CRITICAL]:
                self.zone_stats[zone]["alerts"] += 1
                self.zone_stats[zone]["last_alert"] = datetime.now().isoformat()

            return event

    def _calculate_severity(
        self,
        event_type: str,
        confidence: float,
        zone_rule: Dict
    ) -> AlertSeverity:
        """Calculate severity based on zone rules"""
        # Base severity from event type
        event_severity_map = {
            "Abuse": AlertSeverity.CRITICAL,
            "Assault": AlertSeverity.CRITICAL,
            "Arson": AlertSeverity.CRITICAL,
            "Arrest": AlertSeverity.HIGH,
            "Robbery": AlertSeverity.CRITICAL,
            "Shoplifting": AlertSeverity.MEDIUM,
            "Unknown": AlertSeverity.LOW
        }

        base_severity = event_severity_map.get(event_type, AlertSeverity.MEDIUM)

        # Adjust based on confidence
        if confidence < 0.5:
            if base_severity == AlertSeverity.CRITICAL:
                return AlertSeverity.HIGH
            elif base_severity == AlertSeverity.HIGH:
                return AlertSeverity.MEDIUM
            else:
                return AlertSeverity.LOW
        elif confidence > 0.85:
            if base_severity == AlertSeverity.MEDIUM:
                return AlertSeverity.HIGH
            elif base_severity in [AlertSeverity.LOW, AlertSeverity.MEDIUM]:
                return AlertSeverity.HIGH

        return base_severity

    def get_zone_stats(self) -> Dict:
        """Get statistics for all zones"""
        with self.lock:
            return dict(self.zone_stats)


# Example configuration template
EXAMPLE_SOURCE_CONFIG = {
    "sources": [
        {
            "source_id": "camera_main_entrance",
            "source_path": "rtsp://192.168.1.100:554/stream",
            "source_type": "rtsp",
            "enabled": True,
            "fps": 30,
            "resolution": [1280, 720],
            "stride": 30,
            "confidence_threshold": 0.5,
            "location": "Main Entrance",
            "zone": "entrance"
        },
        {
            "source_id": "camera_parking_lot",
            "source_path": "data/ucf_crime/Arrest/Arrest001_x264.mp4",
            "source_type": "file",
            "enabled": True,
            "fps": 30,
            "resolution": [1280, 720],
            "stride": 30,
            "confidence_threshold": 0.5,
            "location": "Parking Lot",
            "zone": "parking"
        },
        {
            "source_id": "camera_corridor",
            "source_path": 0,
            "source_type": "device",
            "enabled": False,
            "fps": 30,
            "resolution": [1280, 720],
            "stride": 30,
            "confidence_threshold": 0.5,
            "location": "Corridor",
            "zone": "corridor"
        }
    ]
}
