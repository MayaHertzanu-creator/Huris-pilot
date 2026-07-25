# HuriS Data Interfaces & Schemas

Reference: `HuriS_INTERFACES_master_v1.3`

## Core Concepts

### Confidence Levels
- **high** (1/2/≥3 sources independently agree)
- **medium** (1-2 sources with some convergence)
- **low** (Single source or weak convergence)
- **unknown** (Insufficient data or coverage gap)

### Value Types
- **True** - Finding present/confirmed
- **False** - Finding absent/excluded
- **Unknown** - Insufficient evidence or deliberate ambiguity

### Evidence Model

Each finding is backed by one or more Evidence objects:

```python
class Evidence:
    source_id: str        # Document/interview ID
    quote: Optional[str]  # Direct quote
    page: Optional[int]   # Page number
    timestamp: Optional[str]  # Interview timestamp
```

## Data Models

### Finding

Core data structure representing a single psychological finding:

| Field | Type | Description |
|-------|------|-------------|
| id | str | Unique ID |
| construct | str | Psychological axis (e.g., `authority_conflict`) |
| value | ValueType | True/False/Unknown |
| confidence | ConfidenceLevel | Assessment confidence |
| evidence | List[Evidence] | Supporting evidence |
| notes | Optional[str] | Analyst annotations |
| tagged | bool | Cross-validation flag |

### Interview

Structured interview data from Agent 2:

| Field | Type | Description |
|-------|------|-------------|
| interview_id | str | Unique ID |
| subject_id | str | Subject being interviewed |
| date | datetime | Interview date/time |
| responses | List[InterviewResponse] | Question-response pairs |
| raw_transcript | Optional[str] | Full transcript |
| completion_status | str | completed_normally / terminated_safety / terminated_other |

### Report

Final psychological report from Agent 3:

| Field | Type | Description |
|-------|------|-------------|
| report_id | str | Unique ID |
| subject_id | str | Subject of report |
| date_generated | datetime | Report creation time |
| findings | List[Finding] | Analyzed findings |
| analysis | str | Narrative analysis |
| recommendations | Optional[str] | Recommendations (if any) |
| guardrail_status | str | passed / needs_review / failed |
| metadata | Dict | Additional metadata |

### CaseFile

Complete case combining all outputs:

| Field | Type | Description |
|-------|------|-------------|
| case_id | str | Unique case ID |
| subject_id | str | Subject ID |
| extracted_data | Dict | Agent 1 outputs |
| interview | Optional[Interview] | Agent 2 output |
| report | Optional[Report] | Agent 3 output |
| status | str | in_progress / completed / archived |

## Psychological Constructs (Core Axes)

Weighted by clinical significance:

| Construct | Weight | Description |
|-----------|--------|-------------|
| authority_conflict | 2 | Conflict/ambivalence re: authority |
| boundary_blurring | 2 | Boundary maintenance difficulty |
| vulnerability_crisis | 2 | Acute vulnerability/crisis |
| reliability_transparency | 1 | Reliability in communication |
| career_instability | 1 | Occupational concerns |
| discretion_leak_risk | 1 | Privacy/confidentiality risk |
| peer_loyalty_bias | 1 | Peer loyalty bias |
| social_attribution_bias | 1 | Hostile attribution bias |

## Serialization

All schemas serialize to/from JSON:

```python
from agents.shared.schemas import Finding, Report

# Serialize
finding_json = finding.model_dump_json()

# Deserialize
finding = Finding.model_validate_json(finding_json)
```

## Extensions

Additional domain-specific schemas can be defined in agent directories:
- `agents/agent_1/schemas.py` - Extraction-specific models
- `agents/agent_2/schemas.py` - Interview-specific models
- `agents/agent_3/schemas.py` - Report-specific models
