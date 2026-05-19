# Project structure — MCP_RAG

This document summarizes the purpose of the main files and folders in this repository to help you navigate and maintain the project.

**Entry Points:**
- [main.py](main.py): Primary pipeline — YOLO detection → RAG retrieval → MCP agent → orchestration and evaluation.
- [quickstart.py](quickstart.py): Interactive quick-start helper and instructions.
- [surveillance_examples.py](surveillance_examples.py): Example runs (basic, rag, programmatic, custom alerts).
- [run_laptop_camera.py](run_laptop_camera.py): Run the system using laptop webcam (basic or with RAG).
- [run_comparison.py](run_comparison.py): Run full system vs. baselines and collect evaluation results.

**Core System / Runtime:**
- [surveillance_engine.py](surveillance_engine.py): Core engine — video sources, monitoring threads, alert manager, camera lifecycle.
- [surveillance_orchestrator.py](surveillance_orchestrator.py): High-level orchestrator that composes engine, coordinator, notifications, and API.
- [multi_source_coordinator.py](multi_source_coordinator.py): Manage multiple camera sources, registration, and zone-based processing.
- [surveillance_api.py](surveillance_api.py): Flask-based REST API and lightweight dashboard for monitoring and control.

**AI / Reasoning / RAG:**
- [agent.py](agent.py): Gemini agent wrapper and reasoning utility functions that call the LLM for structured decisions.
- [rag.py](rag.py): RAG retrieval layer using sentence-transformers + FAISS over `rag_data/knowledge.json`.
- [mcp.py](mcp.py): Maps detected objects and RAG decisions to actionable responses (execute_action helpers).
- [research_gap.py](research_gap.py): Heuristics for anomaly scoring and temporal localization (TemporalLocalizer).
- [orchestrator.py](orchestrator.py): Adaptive tool orchestration logic (which analysis tools to run based on scene context).

**Notifications, Logging & Utilities:**
- [notification_system.py](notification_system.py): Notification handlers (log, file, webhook, console) and manager.
- [show_logs.py](show_logs.py): CLI utilities to view detection logs and recent alerts.
- [analyze_logs.py](analyze_logs.py): Inspect evaluation run summaries and list available runs.
- [utils.py](utils.py): Small utilities (frame extraction, discover videos, supported extensions).
- [config.py](config.py): Loads environment variables (e.g., `GEMINI_API_KEY`) and model selection.

**Evaluation & Experiments:**
- [evaluation.py](evaluation.py): Structured evaluation logger, frame-level metrics, and baseline evaluators.
- `eval_results/`: Stores per-run CSV/JSONL logs and summary JSON files.

**Data & Models:**
- `data/`: Video datasets (e.g., `ucf_crime/` class subfolders).
- `rag_data/knowledge.json`: RAG knowledge base used by `rag.py`.
- `models/` and `yolov8n.pt`: Local model weights used by YOLO detection.
- `alert_logs/`: Persisted alert JSONL files created by the notification file handler.

**Config & Deployment:**
- `surveillance_config.json`: Camera/source configuration (example template created by examples).
- `surveillance_config_schema.json`: JSON schema for configuration validation.
- [requirements.txt](requirements.txt): Python dependencies for the project.
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md): (existing) deployment instructions if present.

Notes & next steps
- If you want, I can:
  - Extract missing top-level docstrings into each module.
  - Add type hints or a small README per package area.
  - Reorganize into a `src/` package layout and update imports.

If you'd like changes, tell me the preferred layout (flat, package `src/`, or split into `core/`, `ai/`, `api/`, `tools/`) and I will reorganize files accordingly.

Suggested folder scaffolding (created)
- `core/`: Runtime engine, source manager, orchestrator. See [core/README.md](core/README.md)
- `ai/`: RAG, agent, decision logic. See [ai/README.md](ai/README.md)
- `api/`: REST API and dashboard. See [api/README.md](api/README.md)
- `tools/`: CLI helpers, quickstart, run scripts. See [tools/README.md](tools/README.md)
- `evaluation/`: Evaluation logger and results. See [evaluation/README.md](evaluation/README.md)
- `docs/`: Project documentation and guides. See [docs/README.md](docs/README.md)

These folders are indexes only (README files link to existing scripts). If you prefer I can actually move modules into these packages and update imports — tell me if you'd like me to proceed with that refactor.
