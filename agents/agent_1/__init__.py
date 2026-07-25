"""Agent A -- reads the case file and tags it.

Two layers, kept apart on purpose (RuleBook A D-1):

    markers.py    what to look for            (data)
    decision.py   what a finding means        (deterministic, no model)
    extractor.py  reading the sources         (model call)

Only the reading layer is probabilistic. Every judgement that affects the
outcome is made by fixed rules, so the same sources always produce the same
tags -- which is what lets a decision be defended a year later.
"""

from .decision import (
    UnknownMarkerError,
    build_payload,
    coverage_report,
    decide_all,
    decide_tag,
    explain,
    has_coverage,
)
from .ingestion import Ingestor, PageText, detect_format, grade_document, inventory
from .markers import BY_CONSTRUCT, BY_ID, MARKERS, Marker, markers_for

__all__ = [
    "MARKERS",
    "Marker",
    "BY_ID",
    "BY_CONSTRUCT",
    "markers_for",
    "decide_tag",
    "decide_all",
    "build_payload",
    "has_coverage",
    "explain",
    "coverage_report",
    "UnknownMarkerError",
    "Ingestor",
    "PageText",
    "detect_format",
    "grade_document",
    "inventory",
]
