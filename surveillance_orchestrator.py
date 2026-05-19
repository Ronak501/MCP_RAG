"""
Integrated Surveillance Intelligence Orchestrator
Combines MCP-RAG with real-time surveillance capabilities
"""
import logging
import threading
from typing import Dict, Optional, Callable
from pathlib import Path
import numpy as np
from datetime import datetime

try:
    import cv2
except ImportError:
    cv2 = None

logger = logging.getLogger(__name__)


class SurveillanceIntelligenceOrchestrator:
    """
    Orchestrates the complete Autonomous Surveillance Intelligence system
    Integrates: Video capture, detection, MCP-RAG analysis, alerting, and monitoring
    """
    
    def __init__(self, agent=None):
        """
        Initialize the orchestrator
        
        Args:
            agent: Optional MCP-RAG agent for intelligent analysis
        """
        from surveillance_engine import SurveillanceEngine
        from multi_source_coordinator import MultiSourceCoordinator, ZoneBasedProcessor
        from notification_system import NotificationManager
        from surveillance_api import SurveillanceAPI
        
        self.engine = SurveillanceEngine(agent_module=agent)
        self.coordinator = MultiSourceCoordinator(self.engine)
        self.notification_manager = NotificationManager()
        self.zone_processor = ZoneBasedProcessor()
        self.agent = agent
        
        # API can be initialized later
        self.api = None
        self.api_thread = None
        
        self.is_running = False
        self.lock = threading.Lock()
        
        logger.info("Surveillance Intelligence Orchestrator initialized")
    
    def configure_notifications(self):
        """Setup notification handlers"""
        from notification_system import (
            NotificationChannel, LogNotificationHandler,
            FileNotificationHandler, ConsoleNotificationHandler
        )
        
        # Register handlers
        self.notification_manager.register_handler(LogNotificationHandler())
        self.notification_manager.register_handler(FileNotificationHandler(Path("alert_logs")))
        self.notification_manager.register_handler(ConsoleNotificationHandler())
        
        # Subscribe to alerts
        self.engine.subscribe_to_alerts(self._handle_alert)
        
        logger.info("Notification system configured")
    
    def load_sources_from_config(self, config_path: Path):
        """Load camera sources from configuration file"""
        self.coordinator.load_sources_from_file(config_path)
        logger.info(f"Loaded {len(self.coordinator.sources)} video sources")
    
    def add_camera(self, source_id: str, source_path: str, source_type: str, **kwargs):
        """Add a camera programmatically"""
        from multi_source_coordinator import SourceConfig
        
        config = SourceConfig(
            source_id=source_id,
            source_path=source_path,
            source_type=source_type,
            **kwargs
        )
        self.coordinator.add_source(config)
    
    def setup_api_server(self, host: str = "0.0.0.0", port: int = 5000):
        """Setup the REST API server"""
        from surveillance_api import SurveillanceAPI
        
        self.api = SurveillanceAPI(
            self.engine,
            self.notification_manager,
            self.coordinator
        )
        
        # Run API in background thread
        self.api_thread = threading.Thread(
            target=self.api.run,
            kwargs={"host": host, "port": port, "debug": False},
            daemon=True,
            name="api-server"
        )
        self.api_thread.start()
        
        logger.info(f"API server started on {host}:{port}")
        logger.info(f"Dashboard available at http://{host}:{port}/dashboard")
    
    def _create_detection_callback(self) -> Callable:
        """Create detection callback for frame processing"""
        
        def process_frame(frame, source_config):
            """Process a single frame"""
            try:
                if self.agent is None:
                    # Basic detection without MCP-RAG
                    self._basic_detection(frame, source_config)
                else:
                    # Full MCP-RAG analysis
                    self._rag_detection(frame, source_config)
                
                self.coordinator.update_source_stats(
                    source_config.source_id,
                    frames=1
                )
            
            except Exception as e:
                logger.error(f"Error processing frame: {e}")
                self.coordinator.update_source_stats(
                    source_config.source_id,
                    error=True
                )
        
        return process_frame
    
    def _basic_detection(self, frame, source_config):
        """Basic detection without MCP-RAG"""
        # This would integrate with YOLOv8 detection
        # For now, placeholder for basic detection
        pass
    
    def _rag_detection(self, frame, source_config):
        """Detection with MCP-RAG analysis"""
        # This would call the agent for intelligent analysis
        try:
            # Convert frame to bytes for processing
            frame_bytes = cv2.imencode('.jpg', frame)[1].tobytes() if cv2 else None
            
            # Call agent for analysis
            if self.agent and hasattr(self.agent, 'analyze'):
                result = self.agent.analyze(frame_bytes, source_config.source_id)
                
                if result and result.get("detections"):
                    for detection in result["detections"]:
                        self._process_detection(detection, source_config)
        
        except Exception as e:
            logger.error(f"Error in RAG detection: {e}")
    
    def _process_detection(self, detection: Dict, source_config):
        """Process a single detection"""
        try:
            from surveillance_engine import DetectionEvent, AlertSeverity
            
            event_type = detection.get("type", "Unknown")
            confidence = detection.get("confidence", 0.0)
            
            # Get zone if available
            zone = getattr(source_config, "zone", "default")
            
            # Create event
            event = self.zone_processor.process_zone_event(
                source_config.source_id,
                zone,
                event_type,
                confidence
            )
            
            if event:
                # Add to engine alerts
                self.engine.alert_manager.create_alert(event)
                
                # Send notification
                self._dispatch_notification(event)
                
                # Update stats
                self.coordinator.update_source_stats(
                    source_config.source_id,
                    events=1,
                    event_time=event.timestamp.isoformat()
                )
        
        except Exception as e:
            logger.error(f"Error processing detection: {e}")
    
    async def _dispatch_notification(self, event):
        """Dispatch notification for event"""
        try:
            await self.notification_manager.send_notification(event.to_dict())
        except Exception as e:
            logger.error(f"Error dispatching notification: {e}")
    
    def _handle_alert(self, event):
        """Handle alert from engine"""
        logger.info(f"Alert: {event.event_type} - {event.severity.value}")
    
    def start(self):
        """Start the surveillance system"""
        with self.lock:
            if self.is_running:
                logger.warning("System already running")
                return
            
            self.is_running = True
        
        self.engine.start()
        
        # Register detection callbacks
        detection_callback = self._create_detection_callback()
        for source_id in self.coordinator.sources:
            self.coordinator.register_detection_callback(source_id, detection_callback)
        
        # Start monitoring
        self.coordinator.start_all_sources()
        
        logger.info("Surveillance system started")
    
    def stop(self):
        """Stop the surveillance system"""
        with self.lock:
            if not self.is_running:
                logger.warning("System not running")
                return
            
            self.is_running = False
        
        self.engine.stop()
        self.coordinator.stop_all_sources()
        
        logger.info("Surveillance system stopped")
    
    def get_system_status(self) -> Dict:
        """Get comprehensive system status"""
        return {
            "running": self.is_running,
            "engine_status": self.engine.get_status(),
            "sources": self.coordinator.get_sources_status(),
            "notifications": self.notification_manager.get_stats(),
            "zones": self.zone_processor.get_zone_stats(),
            "recent_alerts": self.engine.get_recent_alerts(10)
        }
    
    def get_analytics(self) -> Dict:
        """Get system analytics and statistics"""
        engine_status = self.engine.get_status()
        zone_stats = self.zone_processor.get_zone_stats()
        notification_stats = self.notification_manager.get_stats()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "performance": {
                "total_frames": engine_status["stats"]["total_frames_processed"],
                "total_events": engine_status["stats"]["total_events_detected"],
                "active_sources": engine_status["stats"]["sources_active"],
            },
            "alerts": {
                "total": len(self.engine.alert_manager.alerts),
                "by_severity": notification_stats["by_severity"],
                "by_source": notification_stats["by_source"]
            },
            "zones": zone_stats,
            "notifications": notification_stats
        }


def create_surveillance_system(
    agent_module=None,
    config_file: Optional[Path] = None,
    enable_api: bool = True,
    api_port: int = 5000
) -> SurveillanceIntelligenceOrchestrator:
    """
    Factory function to create a complete surveillance system
    
    Args:
        agent_module: Optional MCP-RAG agent module
        config_file: Path to camera configuration file
        enable_api: Whether to enable REST API
        api_port: Port for REST API server
    
    Returns:
        Configured SurveillanceIntelligenceOrchestrator
    """
    orchestrator = SurveillanceIntelligenceOrchestrator(agent_module)
    
    # Configure notifications
    orchestrator.configure_notifications()
    
    # Load sources if config provided
    if config_file and Path(config_file).exists():
        orchestrator.load_sources_from_config(Path(config_file))
    
    # Setup API if enabled
    if enable_api:
        orchestrator.setup_api_server(port=api_port)
    
    logger.info("Surveillance system fully configured")
    
    return orchestrator
