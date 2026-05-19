"""
Alert and Notification System for Surveillance
Handles different notification channels and severity-based routing
"""
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional, Callable
from pathlib import Path
from enum import Enum
import threading
from collections import defaultdict

logger = logging.getLogger(__name__)


class NotificationChannel(Enum):
    """Notification delivery channels"""
    LOG = "log"
    FILE = "file"
    EMAIL = "email"
    WEBHOOK = "webhook"
    DATABASE = "database"
    CONSOLE = "console"


class NotificationFilter:
    """Filter for notifications based on severity, source, event type"""
    
    def __init__(self):
        self.enabled_severities: set = {"low", "medium", "high", "critical"}
        self.enabled_sources: Optional[set] = None  # None = all sources
        self.enabled_event_types: Optional[set] = None  # None = all types
        self.event_rate_limit: Dict[str, int] = {}  # source -> max per minute
    
    def matches(self, event: Dict) -> bool:
        """Check if event matches filter criteria"""
        if event["severity"] not in self.enabled_severities:
            return False
        
        if self.enabled_sources and event["source_id"] not in self.enabled_sources:
            return False
        
        if self.enabled_event_types and event["event_type"] not in self.enabled_event_types:
            return False
        
        return True


class NotificationHandler:
    """Base handler for notifications"""
    
    def __init__(self, channel: NotificationChannel):
        self.channel = channel
        self.enabled = True
        self.filter = NotificationFilter()
    
    async def send(self, event: Dict):
        """Send notification for event"""
        if not self.enabled or not self.filter.matches(event):
            return False
        return await self._send_impl(event)
    
    async def _send_impl(self, event: Dict):
        """Implementation-specific send"""
        raise NotImplementedError


class LogNotificationHandler(NotificationHandler):
    """Log-based notifications"""
    
    def __init__(self):
        super().__init__(NotificationChannel.LOG)
    
    async def _send_impl(self, event: Dict):
        severity_level = {
            "low": logging.INFO,
            "medium": logging.WARNING,
            "high": logging.ERROR,
            "critical": logging.CRITICAL
        }.get(event["severity"], logging.INFO)
        
        logger.log(
            severity_level,
            f"[{event['source_id']}] {event['event_type']}: {event.get('details', {})}"
        )
        return True


class FileNotificationHandler(NotificationHandler):
    """File-based notifications"""
    
    def __init__(self, log_dir: Path = Path("alert_logs")):
        super().__init__(NotificationChannel.FILE)
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True, parents=True)
    
    async def _send_impl(self, event: Dict):
        try:
            severity = event["severity"].upper()
            timestamp = event["timestamp"]
            
            # Create daily log file per severity
            date_str = timestamp.split("T")[0]
            log_file = self.log_dir / f"alerts_{severity}_{date_str}.jsonl"
            
            with open(log_file, "a") as f:
                f.write(json.dumps(event) + "\n")
            
            return True
        except Exception as e:
            logger.error(f"Error writing notification to file: {e}")
            return False


class WebhookNotificationHandler(NotificationHandler):
    """Webhook-based notifications"""
    
    def __init__(self, webhook_url: str):
        super().__init__(NotificationChannel.WEBHOOK)
        self.webhook_url = webhook_url
    
    async def _send_impl(self, event: Dict):
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=event,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Error sending webhook notification: {e}")
            return False


class ConsoleNotificationHandler(NotificationHandler):
    """Console-based notifications for high severity alerts"""
    
    def __init__(self):
        super().__init__(NotificationChannel.CONSOLE)
    
    async def _send_impl(self, event: Dict):
        severity = event["severity"].upper()
        source = event["source_id"]
        event_type = event["event_type"]
        confidence = event.get("confidence", 0)
        
        message = f"""
╔════════════════════════════════════════════╗
║ 🚨 SECURITY ALERT - {severity:<22} ║
╠════════════════════════════════════════════╣
║ Source:    {source:<29} ║
║ Type:      {event_type:<29} ║
║ Confidence: {confidence:.1%}                           ║
║ Time:      {event['timestamp']:<28} ║
╚════════════════════════════════════════════╝
"""
        print(message)
        return True


class NotificationManager:
    """Central notification manager"""
    
    def __init__(self):
        self.handlers: Dict[NotificationChannel, NotificationHandler] = {}
        self.notification_history: List[Dict] = []
        self.max_history = 10000
        self.lock = threading.Lock()
        self.stats = {
            "total_sent": 0,
            "by_severity": defaultdict(int),
            "by_channel": defaultdict(int),
            "by_source": defaultdict(int)
        }
    
    def register_handler(self, handler: NotificationHandler):
        """Register a notification handler"""
        self.handlers[handler.channel] = handler
        logger.info(f"Registered handler: {handler.channel.value}")
    
    def unregister_handler(self, channel: NotificationChannel):
        """Unregister a notification handler"""
        if channel in self.handlers:
            del self.handlers[channel]
            logger.info(f"Unregistered handler: {channel.value}")
    
    async def send_notification(self, event: Dict):
        """Send notification through all registered handlers"""
        with self.lock:
            self.notification_history.append({
                "timestamp": datetime.now().isoformat(),
                "event": event
            })
            if len(self.notification_history) > self.max_history:
                self.notification_history.pop(0)
            
            self.stats["total_sent"] += 1
            self.stats["by_severity"][event["severity"]] += 1
            self.stats["by_source"][event["source_id"]] += 1
        
        tasks = []
        for handler in self.handlers.values():
            tasks.append(handler.send(event))
            self.stats["by_channel"][handler.channel.value] += 1
    
    def configure_handler(
        self,
        channel: NotificationChannel,
        severity_filter: List[str] = None,
        source_filter: List[str] = None,
        event_type_filter: List[str] = None
    ):
        """Configure filtering for a handler"""
        if channel not in self.handlers:
            logger.warning(f"Handler {channel.value} not registered")
            return
        
        handler = self.handlers[channel]
        if severity_filter:
            handler.filter.enabled_severities = set(severity_filter)
        if source_filter:
            handler.filter.enabled_sources = set(source_filter)
        if event_type_filter:
            handler.filter.enabled_event_types = set(event_type_filter)
    
    def get_stats(self) -> Dict:
        """Get notification statistics"""
        with self.lock:
            return {
                "total_sent": self.stats["total_sent"],
                "by_severity": dict(self.stats["by_severity"]),
                "by_channel": dict(self.stats["by_channel"]),
                "by_source": dict(self.stats["by_source"])
            }
    
    def get_notification_history(self, count: int = 100) -> List[Dict]:
        """Get recent notifications"""
        with self.lock:
            return self.notification_history[-count:]


class AlertEscalation:
    """Handle alert escalation based on patterns"""
    
    def __init__(self, escalation_threshold: int = 5, time_window_seconds: int = 300):
        self.escalation_threshold = escalation_threshold
        self.time_window = time_window_seconds
        self.event_history: Dict[str, List[datetime]] = defaultdict(list)
        self.lock = threading.Lock()
    
    def should_escalate(self, source_id: str, event_type: str) -> bool:
        """Check if alert should be escalated based on frequency"""
        event_key = f"{source_id}:{event_type}"
        
        with self.lock:
            now = datetime.now()
            
            # Remove old events outside time window
            self.event_history[event_key] = [
                ts for ts in self.event_history[event_key]
                if (now - ts).total_seconds() < self.time_window
            ]
            
            # Add current event
            self.event_history[event_key].append(now)
            
            # Check if threshold exceeded
            return len(self.event_history[event_key]) >= self.escalation_threshold
    
    def get_event_frequency(self, source_id: str, event_type: str) -> int:
        """Get number of events in current time window"""
        event_key = f"{source_id}:{event_type}"
        with self.lock:
            now = datetime.now()
            return len([
                ts for ts in self.event_history[event_key]
                if (now - ts).total_seconds() < self.time_window
            ])
