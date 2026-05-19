"""Minimal configuration helpers for core package.

This mirrors the repository-level `config.py` where present, but keeps
lightweight defaults so importing `core.config` won't break the runtime.
"""
from pathlib import Path
import os

SURVEILLANCE_CONFIG_PATH = Path(os.getenv("SURVEILLANCE_CONFIG", "surveillance_config.json"))

# AI keys (read from env if available)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", None)
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.0")

YOLov8_MODEL_PATH = Path(os.getenv("YOL0V8_MODEL_PATH", "yolov8n.pt"))
