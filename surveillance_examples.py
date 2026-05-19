"""
Example integration of Surveillance Intelligence System with MCP-RAG
Shows how to use the complete autonomous surveillance system
"""
import logging
import json
from pathlib import Path
from core.surveillance_orchestrator import create_surveillance_system
from core.multi_source_coordinator import EXAMPLE_SOURCE_CONFIG

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_example_configuration():
    """Create example camera configuration"""
    config_file = Path("surveillance_config.json")
    
    with open(config_file, "w") as f:
        json.dump(EXAMPLE_SOURCE_CONFIG, f, indent=2)
    
    logger.info(f"Created example configuration: {config_file}")
    return config_file


def example_basic_surveillance():
    """Example 1: Basic surveillance without MCP-RAG"""
    logger.info("=== Example 1: Basic Surveillance ===")
    
    # Setup configuration
    config_file = setup_example_configuration()
    
    # Create surveillance system
    system = create_surveillance_system(
        agent_module=None,  # No MCP-RAG agent
        config_file=config_file,
        enable_api=True,
        api_port=5000
    )
    
    # Start the system
    system.start()
    
    logger.info("Surveillance system running")
    logger.info("Dashboard: http://localhost:5000/dashboard")
    logger.info("API Status: http://localhost:5000/api/status")
    logger.info("Press Ctrl+C to stop")
    
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping surveillance system...")
        system.stop()


def example_with_mcp_rag():
    """Example 2: Surveillance with MCP-RAG integration"""
    logger.info("=== Example 2: Surveillance with MCP-RAG ===")
    
    try:
        # Try to import the agent
        from ai.agent import CrimeAnalysisAgent
        import os
        
        # Setup agent
        agent = CrimeAnalysisAgent(
            api_key=os.getenv("GEMINI_API_KEY"),
            model="gemini-2.5-flash"
        )
        
        logger.info("MCP-RAG agent loaded")
        
    except ImportError:
        logger.warning("MCP-RAG agent not available, using basic surveillance")
        agent = None
    
    # Setup configuration
    config_file = setup_example_configuration()
    
    # Create surveillance system with agent
    system = create_surveillance_system(
        agent_module=agent,
        config_file=config_file,
        enable_api=True,
        api_port=5000
    )
    
    # Start the system
    system.start()
    
    logger.info("Surveillance system with MCP-RAG running")
    logger.info("Dashboard: http://localhost:5000/dashboard")
    
    try:
        import time
        while True:
            # Periodically log status
            time.sleep(30)
            status = system.get_system_status()
            analytics = system.get_analytics()
            
            logger.info(f"System Status: {status['running']}")
            logger.info(f"Frames Processed: {analytics['performance']['total_frames']}")
            logger.info(f"Events Detected: {analytics['performance']['total_events']}")
            
    except KeyboardInterrupt:
        logger.info("Stopping surveillance system...")
        system.stop()


def example_programmatic_setup():
    """Example 3: Programmatic camera configuration"""
    logger.info("=== Example 3: Programmatic Setup ===")
    
    system = create_surveillance_system(
        enable_api=True,
        api_port=5001
    )
    
    # Add cameras programmatically
    system.add_camera(
        source_id="camera_1",
        source_path="data/ucf_crime/Arrest/Arrest001_x264.mp4",
        source_type="file",
        location="Main Entrance",
        zone="entrance",
        stride=30
    )
    
    system.add_camera(
        source_id="camera_2",
        source_path="data/ucf_crime/Assault/Assault001_x264.mp4",
        source_type="file",
        location="Corridor",
        zone="corridor",
        stride=30
    )
    
    # Configure zone rules
    from core.multi_source_coordinator import ZoneBasedProcessor
    system.zone_processor.register_zone_rule("entrance", {
        "high_priority": True,
        "alert_on_suspicious": True
    })
    
    system.start()
    
    logger.info("Surveillance system started with programmatic configuration")
    logger.info("Dashboard: http://localhost:5001/dashboard")
    
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        system.stop()


def example_custom_alert_handlers():
    """Example 4: Custom alert handlers"""
    logger.info("=== Example 4: Custom Alert Handlers ===")
    
    from core.notification_system import NotificationHandler, NotificationChannel
    
    # Custom email handler (example)
    class EmailAlertHandler(NotificationHandler):
        def __init__(self, email_config):
            super().__init__(NotificationChannel.EMAIL)
            self.email_config = email_config
        
        async def _send_impl(self, event):
            logger.info(f"Would send email alert: {event['event_type']}")
            return True
    
    # Create system
    system = create_surveillance_system(enable_api=True)
    
    # Register custom handler
    email_handler = EmailAlertHandler({"recipient": "admin@example.com"})
    system.notification_manager.register_handler(email_handler)
    
    # Configure which alerts trigger email
    system.notification_manager.configure_handler(
        NotificationChannel.EMAIL,
        severity_filter=["high", "critical"]
    )
    
    logger.info("Custom alert handlers registered")
    
    # Add a sample camera
    system.add_camera(
        source_id="test_camera",
        source_path="data/ucf_crime/Robbery/Robbery001_x264.mp4" if Path("data/ucf_crime/Robbery").exists() else "data/ucf_crime/Assault/Assault001_x264.mp4",
        source_type="file",
        location="Test Location",
        zone="test"
    )
    
    system.start()
    
    logger.info("System running with custom alert handlers")
    
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        system.stop()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        example = sys.argv[1]
        
        if example == "basic":
            example_basic_surveillance()
        elif example == "rag":
            example_with_mcp_rag()
        elif example == "programmatic":
            example_programmatic_setup()
        elif example == "alerts":
            example_custom_alert_handlers()
        else:
            print(f"Unknown example: {example}")
            print("Available examples: basic, rag, programmatic, alerts")
    else:
        print("Autonomous Surveillance Intelligence System - Examples")
        print("\nUsage: python surveillance_examples.py [example]")
        print("\nAvailable examples:")
        print("  basic         - Basic surveillance without MCP-RAG")
        print("  rag           - Surveillance with MCP-RAG integration")
        print("  programmatic  - Programmatic camera configuration")
        print("  alerts        - Custom alert handlers")
        print("\nExample: python surveillance_examples.py basic")
