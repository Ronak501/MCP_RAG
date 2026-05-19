OBJECT_TO_ACTION_MAP = {
    "knife": ("WEAPON_DETECTED", "high", "Initiate police response and secure perimeter"),
    "gun": ("WEAPON_DETECTED", "critical", "Trigger emergency lockdown and call 911"),
    "baseball bat": ("WEAPON_DETECTED", "high", "Alert security and dispatch police"),
    "scissors": ("WEAPON_DETECTED", "medium", "Log incident and monitor closely"),
    "fire": ("FIRE_HAZARD", "critical", "Evacuate building and call fire services"),
    "smoke": ("FIRE_HAZARD", "high", "Alert occupants and initiate evacuation"),
    "person": ("PERSON_DETECTED", "low", "Passive monitoring enabled"),
    "car": ("VEHICLE_DETECTED", "low", "Log vehicle presence"),
    "truck": ("VEHICLE_DETECTED", "low", "Log vehicle presence"),
    "backpack": ("SUSPICIOUS_ITEM", "medium", "Investigate and secure area if unattended"),
    "suitcase": ("SUSPICIOUS_ITEM", "medium", "Monitor and investigate"),
}

ACTION_SEVERITY_LEVELS = {
    "critical": 5,
    "high": 4,
    "medium": 3,
    "low": 2,
    "minimal": 1,
}

ACTION_RESPONSE_TYPES = {
    "WEAPON_DETECTED": {
        "critical": "EMERGENCY_LOCKDOWN | POLICE_911_CALLED",
        "high": "POLICE_ALERT_TRIGGERED | PERIMETER_SECURED",
        "medium": "SECURITY_NOTIFIED | INCIDENT_LOGGED",
        "low": "PASSIVE_MONITORING",
    },
    "FIRE_HAZARD": {
        "critical": "FIRE_EMERGENCY_ALERT | FIRE_DEPT_CALLED | EVACUATION_INITIATED",
        "high": "EVACUATION_WARNING | FIRE_DEPT_CALLED",
        "medium": "FIRE_ALERT_SENT | MONITORING_ACTIVE",
        "low": "MONITORING",
    },
    "PERSON_DETECTED": {
        "critical": "ALERT_SUPERVISOR | HIGH_PRIORITY_RESPONSE",
        "high": "ALERT_SENT | MONITORING",
        "medium": "MONITORING",
        "low": "PASSIVE_MONITORING",
    },
    "SUSPICIOUS_ITEM": {
        "critical": "EVACUATION_ORDERED | BOMB_SQUAD_CALLED",
        "high": "AREA_SECURED | INVESTIGATION_INITIATED",
        "medium": "AREA_MONITORED | LOG_INCIDENT",
        "low": "MONITORING",
    },
    "VEHICLE_DETECTED": {
        "low": "LOG_VEHICLE",
        "medium": "MONITOR_VEHICLE",
    },
    "ABUSE_INCIDENT": {
        "critical": "POLICE_ALERT_TRIGGERED | SUPERVISOR_ALERT | EVIDENCE_LOG",
        "high": "SUPERVISOR_NOTIFIED | INCIDENT_LOGGED",
        "medium": "MONITOR_SITUATION | LOG_EVIDENCE",
        "low": "PASSIVE_MONITORING",
    },
    "ASSAULT_INCIDENT": {
        "critical": "POLICE_911_CALLED | MEDICAL_ALERT",
        "high": "POLICE_ALERT_TRIGGERED | SECURITY_RESPONSE",
        "medium": "SECURITY_NOTIFIED | MONITORING",
        "low": "MONITORING",
    },
    "ARREST_INCIDENT": {
        "high": "MONITOR_LAWFUL_INTERVENTION | LOG_ACTIVITY",
        "medium": "OBSERVE_AND_DOCUMENT",
        "low": "PASSIVE_MONITORING",
    },
    "ARSON_INCIDENT": {
        "critical": "FIRE_EMERGENCY_ALERT | FIRE_DEPT_CALLED | POLICE_CALLED | EVACUATION",
        "high": "FIRE_DEPT_CALLED | POLICE_ALERT | EVACUATION_WARNING",
        "medium": "INVESTIGATION_INITIATED | SCENE_SECURED",
    },
}


def derive_severity_from_detections(detections):
    """Map detected objects to severity level based on threat level."""
    max_severity = "minimal"
    for detection in detections:
        if detection in OBJECT_TO_ACTION_MAP:
            _, severity, _ = OBJECT_TO_ACTION_MAP[detection]
            if ACTION_SEVERITY_LEVELS.get(severity, 0) > ACTION_SEVERITY_LEVELS.get(
                max_severity, 0
            ):
                max_severity = severity
    return max_severity


def derive_actions_from_detections(detections):
    """Generate detailed action recommendations from detected objects."""
    actions = []
    for detection in detections:
        if detection in OBJECT_TO_ACTION_MAP:
            action_type, severity, description = OBJECT_TO_ACTION_MAP[detection]
            actions.append(
                {
                    "object": detection,
                    "type": action_type,
                    "severity": severity,
                    "description": description,
                }
            )
    return actions


def derive_action_from_rag_decision(rag_action_text, detections=None):
    """Convert RAG decision and detected objects into actionable response."""
    action_lower = rag_action_text.lower()

    incident_type = None
    if "abuse" in action_lower:
        incident_type = "ABUSE_INCIDENT"
    elif "assault" in action_lower:
        incident_type = "ASSAULT_INCIDENT"
    elif "arrest" in action_lower:
        incident_type = "ARREST_INCIDENT"
    elif "arson" in action_lower or "fire" in action_lower:
        incident_type = "ARSON_INCIDENT"
    elif "arrest" in action_lower:
        incident_type = "ARREST_INCIDENT"

    if incident_type and detections:
        severity = derive_severity_from_detections(detections)
        if incident_type in ACTION_RESPONSE_TYPES:
            response_map = ACTION_RESPONSE_TYPES[incident_type]
            if severity in response_map:
                return response_map[severity]

    action_text = rag_action_text.lower()
    if "fire" in action_text:
        return "FIRE_RESPONSE_TRIGGERED | EVACUATION_INITIATED"
    if "police" in action_text:
        return "POLICE_ALERT_TRIGGERED | INCIDENT_LOGGED"
    if "alert" in action_text:
        return "ALERT_SENT | MONITORING_ACTIVE"
    if "monitor" in action_text:
        return "MONITORING_ACTIVE"
    if "emergency" in action_text:
        return "EMERGENCY_RESPONSE_INITIATED"

    return f"ACTION_EXECUTED: {rag_action_text}"


def execute_action(action, detections=None):
    """Execute action based on RAG decision and optional detection list."""
    return derive_action_from_rag_decision(action, detections=detections)
