#!/usr/bin/env python3
"""
Run Surveillance System with Laptop Webcam
Quick setup to use your laptop's built-in camera
"""
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_laptop_camera_basic():
    """Run surveillance with laptop camera - basic mode"""
    logger.info("Starting surveillance system with laptop webcam...")
    
    from core.surveillance_orchestrator import create_surveillance_system
    
    # Create system
    system = create_surveillance_system(
        enable_api=True,
        api_port=5000
    )
    
    # Add laptop camera
    system.add_camera(
        source_id="laptop_webcam",
        source_path="0",  # 0 = default webcam
        source_type="device",
        location="Laptop Webcam",
        zone="default",
        fps=30,
        resolution=(1280, 720),
        stride=15,  # Process more frequently for real-time feel
        confidence_threshold=0.5
    )
    
    logger.info("=" * 60)
    logger.info("Laptop Webcam Surveillance System")
    logger.info("=" * 60)
    logger.info("")
    logger.info("📷 Camera: Laptop Webcam (Device 0)")
    logger.info("🌐 Dashboard: http://localhost:5000/dashboard")
    logger.info("📊 API Status: http://localhost:5000/api/status")
    logger.info("")
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 60)
    
    # Start system
    system.start()
    
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\nShutting down...")
        system.stop()
        logger.info("Done!")


def run_laptop_camera_with_rag():
    """Run surveillance with laptop camera + MCP-RAG analysis"""
    logger.info("Starting surveillance with MCP-RAG analysis...")
    
    try:
        from ai.agent import CrimeAnalysisAgent
        import os
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEY not set. Using basic mode.")
            logger.warning("Set GEMINI_API_KEY environment variable for MCP-RAG integration.")
            run_laptop_camera_basic()
            return
        
        agent = CrimeAnalysisAgent(
            api_key=api_key,
            model="gemini-2.5-flash"
        )
        logger.info("✓ MCP-RAG agent loaded")
        
    except ImportError as e:
        logger.warning(f"MCP-RAG not available: {e}")
        logger.warning("Using basic surveillance mode")
        run_laptop_camera_basic()
        return
    
    from core.surveillance_orchestrator import create_surveillance_system
    
    # Create system with agent
    system = create_surveillance_system(
        agent_module=agent,
        enable_api=True,
        api_port=5000
    )
    
    # Add laptop camera
    system.add_camera(
        source_id="laptop_webcam",
        source_path="0",
        source_type="device",
        location="Laptop Webcam",
        zone="default",
        fps=30,
        resolution=(1280, 720),
        stride=15,
        confidence_threshold=0.5
    )
    
    logger.info("=" * 60)
    logger.info("Laptop Webcam + MCP-RAG Surveillance")
    logger.info("=" * 60)
    logger.info("")
    logger.info("📷 Camera: Laptop Webcam (Device 0)")
    logger.info("🤖 AI: Gemini 2.5 Flash")
    logger.info("🌐 Dashboard: http://localhost:5000/dashboard")
    logger.info("")
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 60)
    
    system.start()
    
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\nShutting down...")
        system.stop()
        logger.info("Done!")


def show_webcam_devices():
    """Show available webcam devices"""
    logger.info("Checking available webcam devices...")
    
    try:
        import cv2
        
        # Try to open devices 0-5
        available = []
        for i in range(6):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                fps = cap.get(cv2.CAP_PROP_FPS)
                
                available.append({
                    "id": i,
                    "resolution": f"{int(width)}x{int(height)}",
                    "fps": int(fps) if fps > 0 else "unknown"
                })
                
                cap.release()
        
        if available:
            logger.info("\nAvailable cameras:")
            for cam in available:
                logger.info(f"  Device {cam['id']}: {cam['resolution']} @ {cam['fps']} FPS")
            logger.info("")
        else:
            logger.warning("No cameras found!")
    
    except ImportError:
        logger.error("OpenCV not installed. Run: pip install opencv-python")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        
        if mode == "basic":
            run_laptop_camera_basic()
        elif mode == "rag":
            run_laptop_camera_with_rag()
        elif mode == "list":
            show_webcam_devices()
        else:
            print(f"Unknown mode: {mode}")
            print("Available modes: basic, rag, list")
    else:
        print("""
╔═══════════════════════════════════════════════════════════════╗
║     Laptop Webcam Surveillance System                         ║
╚═══════════════════════════════════════════════════════════════╝

Usage:
  python run_laptop_camera.py [mode]

Modes:
  basic   - Run with laptop camera (no AI analysis)
  rag     - Run with MCP-RAG analysis (requires GEMINI_API_KEY)
  list    - List available webcam devices

Examples:
  python run_laptop_camera.py basic
  python run_laptop_camera.py rag
  python run_laptop_camera.py list

Default (if no mode specified):
  python run_laptop_camera.py basic
        """)
        run_laptop_camera_basic()
