#!/usr/bin/env python3
"""
Quick Start Guide for Autonomous Surveillance Intelligence System
Run this to get started immediately
"""
import json
from pathlib import Path
from multi_source_coordinator import EXAMPLE_SOURCE_CONFIG

def main():
    print("""
╔════════════════════════════════════════════════════════════════╗
║  Autonomous Surveillance Intelligence System - Quick Start     ║
╚════════════════════════════════════════════════════════════════╝

Welcome! This guide will help you get the surveillance system running.

What would you like to do?

1. Run basic surveillance (file-based demo)
2. Run with MCP-RAG integration (if available)
3. Setup and view configuration
4. View API documentation
5. Exit
    """)
    
    choice = input("Enter your choice (1-5): ").strip()
    
    if choice == "1":
        print("\n▶ Starting basic surveillance system...")
        print("  - Loading cameras from config")
        print("  - Starting real-time monitoring")
        print("  - Opening dashboard at http://localhost:5000")
        print("\nTo run: python surveillance_examples.py basic")
        
    elif choice == "2":
        print("\n▶ Starting surveillance with MCP-RAG...")
        print("  - Initializing Gemini 2.5 Flash agent")
        print("  - Setting up intelligent analysis")
        print("  - Starting monitoring")
        print("\nTo run: python surveillance_examples.py rag")
        
    elif choice == "3":
        print("\n▶ Viewing surveillance configuration...")
        
        config_file = Path("surveillance_config.json")
        if config_file.exists():
            with open(config_file) as f:
                config = json.load(f)
            print(f"\nFound {len(config.get('sources', []))} cameras configured:")
            for source in config.get('sources', []):
                print(f"  - {source['source_id']}: {source['location']}")
        else:
            print("\nNo configuration file found. Creating example...")
            with open(config_file, "w") as f:
                json.dump(EXAMPLE_SOURCE_CONFIG, f, indent=2)
            print(f"✓ Created {config_file}")
            print("\nExample cameras:")
            for source in EXAMPLE_SOURCE_CONFIG['sources']:
                print(f"  - {source['source_id']}: {source['location']}")
        
        print("\nEdit surveillance_config.json to add your cameras")
        
    elif choice == "4":
        print("\n▶ API Endpoints Reference:")
        print("""
Dashboard:
  http://localhost:5000/dashboard

System Control:
  GET    /api/status                      - System status
  POST   /api/system/start                - Start monitoring
  POST   /api/system/stop                 - Stop monitoring
  GET    /api/system/stats                - System statistics

Cameras:
  GET    /api/cameras                     - List cameras
  POST   /api/cameras/<id>/enable         - Enable camera
  POST   /api/cameras/<id>/disable        - Disable camera
  GET    /api/cameras/<id>/stats          - Camera stats

Alerts:
  GET    /api/alerts                      - Get alerts
  GET    /api/alerts/summary              - Alert summary

Example:
  curl http://localhost:5000/api/status | python -m json.tool
        """)
        
    elif choice == "5":
        print("\nGoodbye!")
        return
    
    print("\n" + "="*64)
    print("Next steps:")
    print("  1. Install dependencies: pip install -r requirements.txt")
    print("  2. Configure your cameras in surveillance_config.json")
    print("  3. Run surveillance system (see options above)")
    print("  4. Open dashboard at http://localhost:5000/dashboard")
    print("="*64 + "\n")


if __name__ == "__main__":
    main()
