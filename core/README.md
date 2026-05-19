# Core
Files for runtime, source management, and orchestration.

- `surveillance_engine.py` ([surveillance_engine.py](../surveillance_engine.py)) — core engine, video manager, alert manager.
- `multi_source_coordinator.py` ([multi_source_coordinator.py](../multi_source_coordinator.py)) — manage multiple camera sources and zone processing.
- `surveillance_orchestrator.py` ([surveillance_orchestrator.py](../surveillance_orchestrator.py)) — high-level orchestrator that composes engine, notifications, and API.
- `main.py` ([main.py](../main.py)) — entry point for pipeline runs (YOLO → RAG → agent → evaluation).
