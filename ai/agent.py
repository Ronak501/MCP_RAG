import json
import re
import time

import google.genai as genai
from google.genai.types import GenerateContentConfig

from core.config import GEMINI_API_KEY, GEMINI_MODEL

client = genai.Client(api_key=GEMINI_API_KEY)


def reason_with_agent(
    event_text,
    detections,
    rag_action,
    class_hint=None,
    rag_metadata=None,
    anomaly_score=None,
    temporal_context=None,
):
    """Use Gemini Agent to reason about event and provide enhanced decision."""
    start_time = time.time()

    rag_metadata_text = json.dumps(rag_metadata or {}, ensure_ascii=True)
    temporal_context_text = json.dumps(temporal_context or {}, ensure_ascii=True)
    anomaly_text = f"{anomaly_score:.3f}" if anomaly_score is not None else "unknown"

    prompt = f"""You are a security incident response agent.

Analyze this security event and provide a structured response.

Event Description: {event_text}
Detected Objects: {', '.join(detections) if detections else 'none'}
Context (Incident Type): {class_hint if class_hint else 'unknown'}
Initial RAG Recommendation: {rag_action}
RAG Metadata: {rag_metadata_text}
Temporal Context: {temporal_context_text}
Current Anomaly Score: {anomaly_text}

Provide a JSON response with:
1. severity: (critical/high/medium/low) - threat level
2. confidence: (0.0-1.0) - how confident you are in this assessment
3. primary_action: (string) - main action to take
4. secondary_actions: (list) - supporting actions
5. justification: (string) - brief explanation
6. additional_notes: (string) - context or warnings

Example format:
{{
  "severity": "high",
  "confidence": 0.92,
  "primary_action": "call police immediately",
  "secondary_actions": ["secure perimeter", "preserve evidence"],
  "justification": "Multiple threat indicators present",
  "additional_notes": "Potential weapon detected"
}}

Respond ONLY with valid JSON, no markdown, no extra text."""

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=GenerateContentConfig(temperature=0.3),
        )
        
        response_text = response.text.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()

        decision = json.loads(response_text)
        inference_time = time.time() - start_time

        decision["inference_time_ms"] = round(inference_time * 1000, 2)
        return decision

    except Exception as e:
        inference_time = time.time() - start_time
        fallback_decision = {
            "severity": "medium",
            "confidence": 0.5,
            "primary_action": rag_action,
            "secondary_actions": [],
            "justification": f"Agent reasoning failed, using RAG fallback: {str(e)}",
            "additional_notes": "Fallback decision",
            "inference_time_ms": round(inference_time * 1000, 2),
            "error": str(e),
        }
        return fallback_decision


def format_agent_response(agent_decision):
    """Format agent decision for display."""
    return (
        f"Severity: {agent_decision.get('severity', '?').upper()} | "
        f"Confidence: {agent_decision.get('confidence', 0):.2%} | "
        f"Action: {agent_decision.get('primary_action', 'N/A')} | "
        f"Anomaly: {agent_decision.get('anomaly_score', 0):.2f} | "
        f"Time: {agent_decision.get('inference_time_ms', 0)}ms"
    )
