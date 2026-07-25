"""Constants and configuration for HuriS system.

Based on INTERFACES_master_v1.3 and RuleBook specifications.
"""

# Core psychological constructs (axes)
CORE_AXES = {
    "authority_conflict": {
        "base_weight": 2,
        "description": "Conflict/ambivalence regarding authority figures"
    },
    "boundary_blurring": {
        "base_weight": 2,
        "description": "Difficulty maintaining personal/professional boundaries"
    },
    "vulnerability_crisis": {
        "base_weight": 2,
        "description": "Acute vulnerability or crisis presentation"
    },
    "reliability_transparency": {
        "base_weight": 1,
        "description": "Reliability and transparency in communication"
    },
    "career_instability": {
        "base_weight": 1,
        "description": "Career instability or occupational concerns"
    },
    "discretion_leak_risk": {
        "base_weight": 1,
        "description": "Risk of discretion breach or information leak"
    },
    "peer_loyalty_bias": {
        "base_weight": 1,
        "description": "Bias in loyalty toward peers"
    },
    "social_attribution_bias": {
        "base_weight": 1,
        "description": "Hostile attribution bias"
    },
}

# Confidence modifiers
CONFIDENCE_MODIFIERS = {
    "single_source": 0.5,      # Only one evidence source
    "cross_validated": 2.0,    # Multiple independent sources agree
    "contradictory": 0.75,     # Sources contradict
    "statistical": 1.5,        # Based on statistical evidence
    "unknown_aware": 1.0,      # Coded as Unknown initially
}

# Question categories
QUESTION_TAGS = [
    "biographical",           # Background/demographic
    "normative_understanding", # How they understand norms
    "integrity_temptation",    # Integrity under pressure
    "analysis",               # Their analytical approach
    "pattern_note",           # Emergent patterns
]

# Color coding for risk/presentation
RISK_COLORS = {
    "red": "High risk / significant concern",
    "yellow": "Medium risk / caution needed",
    "green": "Low risk / normative presentation",
}

# Safety guardrail thresholds
GUARDRAILS = {
    "red_floor_minimum": {
        "description": "Minimum findings needed for red designation",
        "strong_construct_count": 1,     # At least 1 strong finding on core axis
        "medium_convergence": 2,          # Or 2+ medium findings converging
        "contradiction_risk": "Present",  # Contradictions flagged
    },
    "blacklist_terms": [
        # Terms that auto-flag for review
        "SSR[I]",  # Antidepressant reference
        "boundary violation",
        "criminal history",
        "substance dependence",
    ],
    "demographic_safety": [
        "age",
        "gender",
        "race",
        "religion",
    ],
    "statistical_inflation": {
        "enabled": False,
        "description": "Flag statistical-only findings without clinical mechanism"
    }
}

# Report output format templates
OUTPUT_FORMAT = {
    "sections": [
        "identifying_information",
        "referral_source",
        "interview_summary",
        "findings",
        "integration",
        "recommendations",
        "limitations",
    ],
    "confidence_notation": "high/medium/low + Unknown",
    "tag_style": "construct:value=True/False/Unknown; confidence=(high|medium|low)",
}

# Interview configuration
INTERVIEW_CONFIG = {
    "max_duration_minutes": 90,
    "safety_check_interval": 15,
    "termination_triggers": [
        "acute_crisis",
        "suicidal_ideation",
        "safety_concern",
    ],
    "engagement_threshold": 0.6,  # Minimum engagement before termination
}

# Version tracking
VERSION = "0.1.0"
SPEC_VERSION = "HuriS v1.21"
LAST_UPDATED = "2026-07-25"
