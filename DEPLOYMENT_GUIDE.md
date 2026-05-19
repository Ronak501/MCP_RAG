# Autonomous Surveillance System - Deployment Guide

## Production Deployment Checklist

### Pre-Deployment

- [ ] Install all dependencies: `pip install -r requirements.txt`
- [ ] Configure .env with GEMINI_API_KEY for MCP-RAG integration
- [ ] Create surveillance_config.json with all camera sources
- [ ] Test with single video source (file-based)
- [ ] Verify dashboard at http://localhost:5000
- [ ] Test alert notifications
- [ ] Review alert history limits and adjust for your needs

### Configuration

#### 1. Environment Variables (.env)
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

#### 2. Camera Configuration (surveillance_config.json)
```json
{
  "sources": [
    {
      "source_id": "entrance_camera",
      "source_path": "rtsp://192.168.1.100:554/stream",
      "source_type": "rtsp",
      "location": "Main Entrance",
      "zone": "entrance",
      "enabled": true,
      "stride": 30
    }
  ]
}
```

### Deployment Scenarios

## Scenario 1: Single Machine Deployment

### Setup
```bash
# Install
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your API key

# Edit surveillance_config.json with your cameras
```

### Start System
```bash
python surveillance_examples.py rag
```

### Access
```
Dashboard: http://localhost:5000
API: http://localhost:5000/api/status
```

---

## Scenario 2: Multi-Zone Deployment (Multiple Servers)

### Central Server (API Server)
```python
from surveillance_orchestrator import create_surveillance_system

system = create_surveillance_system(
    config_file="surveillance_config.json",
    enable_api=True,
    api_port=5000
)
system.start()
```

### Edge Servers (Detection Only)
Each edge server processes its local cameras and sends alerts to central server:

```python
from surveillance_orchestrator import create_surveillance_system
from notification_system import WebhookNotificationHandler, NotificationChannel

system = create_surveillance_system(
    config_file="local_cameras.json",
    enable_api=False
)

# Send alerts to central server
webhook_handler = WebhookNotificationHandler(
    webhook_url="http://central-server:5000/api/alerts"
)
system.notification_manager.register_handler(webhook_handler)

system.start()
```

---

## Scenario 3: Docker Deployment

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=surveillance_orchestrator.py
ENV FLASK_ENV=production

EXPOSE 5000

CMD ["python", "surveillance_examples.py", "rag"]
```

### Docker Compose
```yaml
version: '3.8'

services:
  surveillance:
    build: .
    ports:
      - "5000:5000"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    volumes:
      - ./surveillance_config.json:/app/surveillance_config.json
      - ./alert_logs:/app/alert_logs
      - ./data:/app/data
    restart: always
```

### Run
```bash
docker-compose up -d
```

---

## Scenario 4: Kubernetes Deployment

### deployment.yaml
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: surveillance-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: surveillance
  template:
    metadata:
      labels:
        app: surveillance
    spec:
      containers:
      - name: surveillance
        image: surveillance-system:latest
        ports:
        - containerPort: 5000
        env:
        - name: GEMINI_API_KEY
          valueFrom:
            secretKeyRef:
              name: surveillance-secrets
              key: gemini-api-key
        volumeMounts:
        - name: config
          mountPath: /app/surveillance_config.json
          subPath: surveillance_config.json
        - name: logs
          mountPath: /app/alert_logs
      volumes:
      - name: config
        configMap:
          name: surveillance-config
      - name: logs
        persistentVolumeClaim:
          claimName: surveillance-logs
```

### Service
```yaml
apiVersion: v1
kind: Service
metadata:
  name: surveillance-service
spec:
  selector:
    app: surveillance
  ports:
  - protocol: TCP
    port: 80
    targetPort: 5000
  type: LoadBalancer
```

---

## Performance Tuning

### High CPU Usage
1. Increase stride (process fewer frames)
```json
{"stride": 60}  // Process every 60th frame
```

2. Reduce resolution
```json
{"resolution": [640, 480]}  // Lower resolution
```

3. Disable low-priority zones
```json
{"enabled": false}  // Disable camera
```

### High Memory Usage
1. Reduce alert history
```python
AlertManager(max_history=500)  # Instead of 1000
```

2. Use file notifications instead of console
3. Disable dashboard auto-refresh or increase interval

### Network Optimization
1. Use RTSP streams with adaptive bitrate
2. Configure stride to reduce bandwidth needs
3. Enable compression in webhook handlers

---

## Monitoring and Logging

### System Logs
```bash
# Real-time logs
tail -f logs/surveillance.log

# Search for errors
grep ERROR logs/surveillance.log

# Alert statistics
grep "Alert:" logs/surveillance.log | wc -l
```

### Alert Logs
```bash
# View critical alerts
tail -f alert_logs/alerts_CRITICAL_*.jsonl

# Search alerts by source
grep "camera_1" alert_logs/*.jsonl
```

### API Monitoring
```bash
# Check system health
curl http://localhost:5000/api/system/stats

# Monitor active cameras
curl http://localhost:5000/api/cameras

# Get alert summary
curl http://localhost:5000/api/alerts/summary
```

---

## Backup and Recovery

### Backup Alert History
```bash
# Daily backup
tar -czf alerts_backup_$(date +%Y%m%d).tar.gz alert_logs/
```

### Alert Database (Future Enhancement)
Consider adding database backing for:
- Persistent alert history
- Complex queries
- Long-term analytics

### Configuration Backup
```bash
# Backup configuration
cp surveillance_config.json surveillance_config.json.backup
```

---

## Security Considerations

### API Security

1. **Authentication** (Future Enhancement)
```python
@app.route('/api/status')
@require_auth
def get_status():
    return {...}
```

2. **HTTPS**
```python
ssl_context = ('cert.pem', 'key.pem')
app.run(ssl_context=ssl_context)
```

3. **Rate Limiting**
```python
from flask_limiter import Limiter
limiter = Limiter(app)

@app.route('/api/status')
@limiter.limit("100 per minute")
def get_status():
    return {...}
```

### Credential Security

1. Use environment variables for sensitive data
2. Never commit .env to version control
3. Rotate API keys regularly
4. Use separate credentials per deployment

### Network Security

1. Firewall API to trusted IPs only
2. Use VPN for remote monitoring
3. Encrypt webhook transmissions (HTTPS)
4. Validate webhook requests

---

## Troubleshooting

### Camera Connection Issues

**Problem**: Camera won't connect
```
Solution:
1. Check source path/URL
2. Verify network connectivity
3. Test RTSP URL: ffplay rtsp://...
4. Check firewall rules
```

### Alert Not Sending

**Problem**: Alerts not reaching notification channel
```
Solution:
1. Check handler is registered
2. Verify filter settings
3. Check webhook endpoint
4. Review system logs
```

### Dashboard Not Loading

**Problem**: Dashboard returns 404
```
Solution:
1. Check API server is running
2. Verify port 5000 is accessible
3. Check Flask is installed
4. Review error logs
```

### High Latency

**Problem**: Slow response from API
```
Solution:
1. Reduce alert history size
2. Limit camera count
3. Increase stride
4. Check system resources
```

---

## Scaling Guidelines

### Single Machine
- Up to 4-6 cameras
- Stride 30-60
- Resolution 1280x720

### Cluster (Multiple Machines)
- Each machine: 4-8 cameras
- Central API server
- Distributed processing

### Cloud Deployment
- Use managed services for storage
- Auto-scaling for traffic spikes
- Load balancing for API server

---

## Monitoring Dashboard Examples

### Real-time Statistics
```
Total Frames Processed: 125,432
Total Events Detected: 247
Active Cameras: 4/5
Recent Alerts: 12 (Critical: 2, High: 5, Medium: 5)
```

### Alert Breakdown
```
By Severity:
  Critical: 2 (1.6%)
  High:     5 (4.0%)
  Medium:   34 (27.4%)
  Low:      83 (66.9%)

By Source:
  Camera 1: 45 alerts
  Camera 2: 38 alerts
  Camera 3: 27 alerts
  Camera 4: 12 alerts

By Type:
  Assault: 52 (42%)
  Abuse: 38 (31%)
  Arson: 18 (15%)
  Arrest: 12 (10%)
  Other: 4 (2%)
```

---

## Maintenance Tasks

### Daily
- [ ] Check dashboard for any critical alerts
- [ ] Monitor system resources
- [ ] Verify all cameras are online

### Weekly
- [ ] Review alert trends
- [ ] Check for anomalies
- [ ] Backup alert logs
- [ ] Review performance metrics

### Monthly
- [ ] Rotate API keys
- [ ] Update camera firmware
- [ ] Analyze false positive rate
- [ ] Review and adjust thresholds
- [ ] Backup configuration

### Quarterly
- [ ] Security audit
- [ ] Performance optimization
- [ ] Capacity planning
- [ ] System upgrade

---

## Support and Troubleshooting

For issues:
1. Check logs: `tail -f logs/*.log`
2. Review API status: `curl http://localhost:5000/api/status`
3. Check configuration: `cat surveillance_config.json`
4. Test connectivity: `curl http://camera-ip/stream`

---

## Emergency Procedures

### System Crash
1. Restart service: `python surveillance_examples.py rag`
2. Check logs for errors
3. Verify camera connectivity
4. Review configuration

### Camera Failure
1. Camera status changes to ERROR
2. System continues processing other cameras
3. Alert is logged
4. Manual intervention may be needed

### Disk Full
1. Archive old alert logs
2. Clean up temporary files
3. Implement log rotation
4. Monitor disk space

---

## Post-Deployment

1. **Monitor 24/7** for first week
2. **Document any issues** encountered
3. **Adjust thresholds** based on false positives
4. **Optimize stride** based on CPU usage
5. **Plan for scaling** as needed

---

**Deployment Guide Complete**

For help: See SURVEILLANCE_README.md or BUILD_SUMMARY.md
