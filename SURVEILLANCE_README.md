# Autonomous Surveillance Intelligence System

A complete, production-ready surveillance system with real-time monitoring, multi-source video input, intelligent alerting, and integrated MCP-RAG analysis.

## Features

### Core Capabilities
- **Real-time Surveillance Monitoring**: Stream and process multiple video sources simultaneously
- **Multi-source Video Input**: Support for files, RTSP streams, HTTP streams, and device cameras
- **Intelligent Alert System**: Severity-based alerts with multiple notification channels
- **Zone-based Processing**: Define rules and behaviors for different monitored areas
- **MCP-RAG Integration**: Leverage Gemini AI for intelligent event analysis and context understanding
- **REST API**: Full API for system control and monitoring
- **Web Dashboard**: Real-time monitoring dashboard with live statistics

### Architecture Components

#### 1. Surveillance Engine (`surveillance_engine.py`)
Core video processing and event detection engine
- **VideoSourceManager**: Manages multiple concurrent video streams
- **AlertManager**: Centralized alert creation and management
- **SurveillanceEngine**: Main orchestrator for the system

```python
from surveillance_engine import SurveillanceEngine, CameraSource, AlertSeverity

engine = SurveillanceEngine()
source = CameraSource(
    source_id="camera_1",
    source_path="rtsp://camera.local/stream",
    source_type="rtsp"
)
engine.add_camera(source)
```

#### 2. Multi-Source Coordinator (`multi_source_coordinator.py`)
Manages multiple video sources and zone-based processing
- **MultiSourceCoordinator**: Coordinates multi-source video processing
- **ZoneBasedProcessor**: Apply rules and processing per monitored zone
- Load configurations from JSON

```python
from multi_source_coordinator import MultiSourceCoordinator

coordinator = MultiSourceCoordinator(engine)
coordinator.load_sources_from_file("surveillance_config.json")
coordinator.start_all_sources()
```

#### 3. Notification System (`notification_system.py`)
Flexible alerting with multiple delivery channels
- **NotificationManager**: Central notification hub
- **Handlers**: Log, File, Webhook, Console, Email
- **Filtering**: Filter alerts by severity, source, event type
- **Escalation**: Automatic escalation on repeated events

```python
from notification_system import NotificationManager, ConsoleNotificationHandler

manager = NotificationManager()
manager.register_handler(ConsoleNotificationHandler())
```

#### 4. Surveillance API (`surveillance_api.py`)
REST API and web dashboard
- **REST Endpoints**: Full API for system control
- **Dashboard**: Real-time web-based monitoring
- **WebSocket Support**: Live updates (via dashboard)

Available at: `http://localhost:5000/dashboard`

#### 5. Orchestrator (`surveillance_orchestrator.py`)
Integrates all components into a complete system
- **SurveillanceIntelligenceOrchestrator**: Main system orchestrator
- **Integration with MCP-RAG**: Connects with existing agent module
- **Factory function**: Easy system initialization

## Installation

### Prerequisites
- Python 3.8+
- OpenCV (cv2)
- Flask and Flask-CORS
- NumPy

### Setup

1. Install dependencies:
```bash
pip install opencv-python flask flask-cors numpy
```

2. Create camera configuration file (`surveillance_config.json`):
```json
{
  "sources": [
    {
      "source_id": "camera_main_entrance",
      "source_path": "rtsp://192.168.1.100:554/stream",
      "source_type": "rtsp",
      "enabled": true,
      "fps": 30,
      "resolution": [1280, 720],
      "stride": 30,
      "confidence_threshold": 0.5,
      "location": "Main Entrance",
      "zone": "entrance"
    }
  ]
}
```

## Usage

### Quick Start

```python
from surveillance_orchestrator import create_surveillance_system

# Create and configure system
system = create_surveillance_system(
    config_file="surveillance_config.json",
    enable_api=True,
    api_port=5000
)

# Start monitoring
system.start()

# Monitor status
print(system.get_system_status())
```

### With MCP-RAG Agent

```python
from agent import CrimeAnalysisAgent
from surveillance_orchestrator import create_surveillance_system
import os

# Setup agent
agent = CrimeAnalysisAgent(
    api_key=os.getenv("GEMINI_API_KEY"),
    model="gemini-2.5-flash"
)

# Create system with intelligent analysis
system = create_surveillance_system(
    agent_module=agent,
    config_file="surveillance_config.json",
    enable_api=True
)

system.start()
```

### Programmatic Configuration

```python
from surveillance_orchestrator import create_surveillance_system

system = create_surveillance_system(enable_api=True, api_port=5000)

# Add cameras
system.add_camera(
    source_id="camera_1",
    source_path="data/videos/entrance.mp4",
    source_type="file",
    location="Main Entrance",
    zone="entrance"
)

# Configure zone rules
system.zone_processor.register_zone_rule("entrance", {
    "high_priority": True,
    "alert_on_suspicious": True
})

system.start()
```

### Running Examples

```bash
# Basic surveillance (file-based)
python surveillance_examples.py basic

# With MCP-RAG integration
python surveillance_examples.py rag

# Programmatic setup
python surveillance_examples.py programmatic

# Custom alert handlers
python surveillance_examples.py alerts
```

## API Reference

### System Control

**GET** `/api/status`
- Get real-time system status

**POST** `/api/system/start`
- Start surveillance system

**POST** `/api/system/stop`
- Stop surveillance system

### Camera Management

**GET** `/api/cameras`
- List all cameras

**POST** `/api/cameras/<source_id>/enable`
- Enable a camera

**POST** `/api/cameras/<source_id>/disable`
- Disable a camera

**GET** `/api/cameras/<source_id>/stats`
- Get camera statistics

### Alerts

**GET** `/api/alerts`
- Get recent alerts (default: 50)
- Query params: `count=N`, `severity=<level>`

**GET** `/api/alerts/summary`
- Get alert statistics

### Dashboard

**GET** `/dashboard`
- Access web-based monitoring dashboard
- Real-time updates every 2 seconds

## Configuration

### Camera Source Types

#### File
```json
{
  "source_id": "video_file",
  "source_path": "path/to/video.mp4",
  "source_type": "file"
}
```

#### RTSP Stream
```json
{
  "source_id": "ip_camera",
  "source_path": "rtsp://192.168.1.100:554/stream",
  "source_type": "rtsp"
}
```

#### HTTP Stream
```json
{
  "source_id": "http_camera",
  "source_path": "http://192.168.1.100:8080/video.mjpeg",
  "source_type": "http"
}
```

#### Webcam Device
```json
{
  "source_id": "webcam",
  "source_path": "0",
  "source_type": "device"
}
```

### Alert Severity Levels

- **LOW**: Minor suspicious activity
- **MEDIUM**: Moderate concern
- **HIGH**: Significant security threat
- **CRITICAL**: Immediate action required

### Notification Channels

- **LOG**: System logger
- **FILE**: JSON-L files (daily per severity)
- **CONSOLE**: Terminal output (for high/critical)
- **WEBHOOK**: HTTP POST to external service
- **EMAIL**: Email alerts (custom handler)
- **DATABASE**: Database logging (custom handler)

## Performance

- **Multi-threading**: Non-blocking concurrent video processing
- **Frame Skipping**: Configurable stride for efficient processing
- **Memory Efficient**: Bounded queues and history limits
- **Thread-safe**: Lock-based synchronization throughout

## Monitoring

### System Statistics

```python
system.get_system_status()
# Returns:
{
  "running": true,
  "engine_status": {...},
  "sources": [...],
  "notifications": {...},
  "zones": {...},
  "recent_alerts": [...]
}
```

### Analytics

```python
system.get_analytics()
# Returns performance metrics, alert statistics, zone analytics
```

## Integration with Existing Project

The surveillance system integrates seamlessly with the existing MCP-RAG project:

1. **Detection Layer**: Uses YOLOv8 detection
2. **Analysis Layer**: Leverages MCP-RAG agent for intelligent understanding
3. **Evaluation**: Supports existing evaluation framework
4. **Logging**: Compatible with existing logging system

## Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│     Video Sources (File, RTSP, HTTP, Device)        │
└────────────────┬────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────┐
│     VideoSourceManager (Multi-stream handling)       │
└────────────────┬────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────┐
│   Detection Pipeline (YOLOv8 + Frame Processing)    │
└────────────────┬────────────────────────────────────┘
                 │
      ┌──────────┴──────────┐
      │                     │
┌─────▼──────┐    ┌────────▼────────┐
│  Basic     │    │   MCP-RAG       │
│ Detection  │    │   Analysis      │
└─────┬──────┘    └────────┬────────┘
      │                    │
      └─────────┬──────────┘
                │
        ┌───────▼────────┐
        │  ZoneProcessor │
        │  + Escalation  │
        └───────┬────────┘
                │
        ┌───────▼────────────┐
        │  AlertManager      │
        └───────┬────────────┘
                │
    ┌───────────┼───────────┐
    │           │           │
┌───▼──┐  ┌────▼───┐  ┌───▼────┐
│ Log  │  │ File   │  │Console  │
└──────┘  └────────┘  └────────┘

┌────────────────────────────────────┐
│  REST API + Web Dashboard          │
│  (Real-time monitoring)            │
└────────────────────────────────────┘
```

## Troubleshooting

### Video Source Connection Issues
- Check source path/URL is correct
- Verify network connectivity for remote sources
- Check camera/file permissions

### High CPU Usage
- Increase frame stride (process fewer frames)
- Reduce resolution
- Disable unnecessary video sources

### Memory Issues
- Reduce alert history size
- Lower notification queue size
- Use file-based notifications instead of in-memory

## Future Enhancements

- [ ] GPU acceleration for video processing
- [ ] Distributed processing across multiple servers
- [ ] Advanced analytics dashboard with graphs
- [ ] Machine learning-based anomaly detection
- [ ] Integration with external security systems
- [ ] Mobile app for remote monitoring
- [ ] Recording and playback functionality

## License

Integrated with existing MCP-RAG project

## Support

For issues or questions, refer to the main project documentation.
