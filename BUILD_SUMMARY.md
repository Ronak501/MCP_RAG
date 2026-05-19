# Flask Code Dashboard Build Summary

## What Changed

The repository now centers on a read-only Flask dashboard for browsing code and inspecting evaluation logs.

## Main Entry Point

- `app.py` - Flask app with three views:
  - `/` - code structure, file list, file type summary, and log summaries
  - `/file/<path>` - source viewer with line numbers
  - `/logs` - log summary and preview page

## Remaining Code Areas

- `ai/` - agent, RAG, MCP, orchestration, and research helpers
- `evaluation/` - evaluation metrics and log helpers
- `docs/` - documentation pages

## Removed Surveillance Code

The surveillance-specific folders and scripts were removed from the workspace:

- `core/`
- `api/`
- `tools/`
- `main.py`
- `surveillance_examples.py`
- `run_laptop_camera.py`
- `quickstart.py`
- `show_logs.py`
- `run_comparison.py`
- `analyze_logs.py`
- `surveillance_config.json`
- `surveillance_config_schema.json`
- `SURVEILLANCE_README.md`

## How To Run

```powershell
.\.venv\Scripts\python.exe app.py
```

Open:

- `http://127.0.0.1:5000/`
- `http://127.0.0.1:5000/logs`


### 4. With MCP-RAG
```bash
# Set GEMINI_API_KEY environment variable first
python surveillance_examples.py rag
```

### 5. Programmatic Usage
```python
from surveillance_orchestrator import create_surveillance_system

system = create_surveillance_system(
    config_file="surveillance_config.json",
    enable_api=True
)
system.start()
```

## Integration with Existing Project

### 1. Detection Pipeline
Uses existing YOLOv8 model for object/crime detection

### 2. MCP-RAG Integration
```python
from agent import CrimeAnalysisAgent
from surveillance_orchestrator import create_surveillance_system

agent = CrimeAnalysisAgent(api_key=os.getenv("GEMINI_API_KEY"))
system = create_surveillance_system(agent_module=agent)
```

### 3. Evaluation Framework
- Compatible with existing evaluation.py
- Can log results to eval_results directory
- Integrates with run comparison system

### 4. Configuration System
- Uses .env for API keys
- Same logging configuration
- Consistent with project structure

## Files Created

1. **surveillance_engine.py** - Core video processing engine
2. **multi_source_coordinator.py** - Multi-camera orchestration
3. **notification_system.py** - Alert notification system
4. **surveillance_api.py** - REST API and web dashboard
5. **surveillance_orchestrator.py** - Main system orchestrator
6. **surveillance_examples.py** - Usage examples
7. **SURVEILLANCE_README.md** - Detailed documentation
8. **surveillance_config_schema.json** - Configuration schema
9. **quickstart.py** - Quick start guide
10. **requirements.txt** - Updated with Flask, aiohttp, Flask-CORS

## Performance Characteristics

- **Multi-threading**: Separate thread per video source
- **Memory Efficient**: Bounded queues (maxlen=2 for frames)
- **Non-blocking**: Main thread never blocked by I/O
- **Frame Skipping**: Configurable stride for CPU efficiency
- **Alert Limiting**: Bounded alert history (1000 by default)

## API Reference

### System Control
```
POST /api/system/start
POST /api/system/stop
GET  /api/status
GET  /api/system/stats
```

### Cameras
```
GET  /api/cameras
POST /api/cameras/<id>/enable
POST /api/cameras/<id>/disable
GET  /api/cameras/<id>/stats
```

### Alerts
```
GET  /api/alerts
GET  /api/alerts/summary
```

### Dashboard
```
GET  /dashboard
```

## Next Steps

1. **Configure cameras** - Edit surveillance_config.json with your video sources
2. **Test basic system** - Run `python surveillance_examples.py basic`
3. **Enable MCP-RAG** - Run with agent: `python surveillance_examples.py rag`
4. **Deploy API** - Expose on network for remote monitoring
5. **Setup webhooks** - Configure alerts to external systems
6. **Add custom handlers** - Implement custom notification channels

## Monitoring Commands

### Check System Status
```bash
curl http://localhost:5000/api/status | python -m json.tool
```

### Get Recent Alerts
```bash
curl http://localhost:5000/api/alerts | python -m json.tool
```

### Get Alert Summary
```bash
curl http://localhost:5000/api/alerts/summary | python -m json.tool
```

## Troubleshooting

### Video Source Won't Connect
- Verify file path/URL
- Check network connectivity
- Verify camera permissions

### High CPU Usage
- Increase frame stride (process fewer frames)
- Reduce resolution
- Disable unnecessary sources

### Memory Issues
- Reduce alert_history_size
- Use file notifications instead of console
- Lower frame queue size

## Architecture Benefits

✅ **Modular Design** - Each component independently testable
✅ **Scalable** - Add cameras without system restart
✅ **Thread-Safe** - Proper locking throughout
✅ **Extensible** - Easy to add custom handlers/processors
✅ **Integration Ready** - Works seamlessly with MCP-RAG
✅ **Production Ready** - Error handling, logging, recovery

## Summary

You now have a **complete Autonomous Surveillance Intelligence System** that:

1. Monitors multiple video sources in real-time
2. Detects security events with YOLOv8 + MCP-RAG
3. Routes alerts through multiple notification channels
4. Provides REST API for integration
5. Offers web dashboard for monitoring
6. Integrates seamlessly with your existing project

The system is ready for deployment and can handle enterprise-scale surveillance requirements!

---

For detailed documentation, see: **SURVEILLANCE_README.md**
For quick setup, run: **python quickstart.py**
For examples, run: **python surveillance_examples.py [basic|rag|programmatic|alerts]**
