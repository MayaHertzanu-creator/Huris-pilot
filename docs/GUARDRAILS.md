# HuriS Safety Guardrails

Reference: `HuriS_AgentC_Guardrails.md`

## Overview

Guardrails ensure psychological reports meet safety, accuracy, and ethical standards. Agent 3 applies these checks before finalizing reports.

## Guardrail Checkpoints

### G0: Cross-Validation
**Ensures all findings have sources**

- Every finding must cite ≥1 evidence
- Evidence must reference actual source document/interview
- No unsourced claims permitted

### G1: Structural Integrity
**Validates internal consistency**

- All referenced sources exist
- Unknown/False findings don't masquerade as confirmed
- Coverage assessment matches claim confidence

Check:
```python
for finding in findings:
    if not finding.evidence:
        raise GuardrailError("Finding lacks sources")
    if finding.value == ValueType.UNKNOWN and finding.confidence != ConfidenceLevel.LOW:
        raise GuardrailError("Unknown marked as high confidence")
```

### G2: Anti-Overdiagnosis
**Prevents red-level findings without sufficient support**

- Red (high risk) requires:
  - ≥1 strong finding on core axis, OR
  - ≥2 medium findings converging, OR
  - Documented contradiction/inconsistency
- False positives downgraded if on blacklist-only sources

### G3: Red Floor
**Minimum criteria for red designation**

Red findings require **both**:
1. Construct present on core axis (base_weight ≥ 1)
2. Minimum evidence threshold met:
   - strong + unblacklisted sources, OR
   - 2+ medium + convergence, OR
   - documented contradiction with clinical mechanism

**Below red floor**: Downgrade to yellow_complex/yellow_caution

### G4: Statistical Claims
**Statistical findings need clinical basis**

Cannot stand alone on statistics without:
- Documented psychological mechanism
- Clinical observation corroboration
- Behavioral/interview evidence

Flagged for review if statistical-only.

### Output Integrity
**Final report quality**

Check all findings:
- S1: Sources exist ✓
- S2: Unknown-as-false absent ✓
- S3: Confidence ≠ color mixing ✓
- S4: Red findings ≥ floor ✓
- S5: Statistics ≠ sole basis ✓
- S6: No prohibited demographics ✓
- S7: Basis consistent (model agnostic) ✓
- S8: Interview termination coherent ✓
- S9: Yellow+ doesn't contradict passed ✓

## Blacklist Terms

Auto-flagged for review:
- SSRI (antidepressant reference)
- "boundary violation" (specific claim)
- Criminal history mention
- Substance dependence

Findings citing only blacklist sources: downgraded confidence.

## Demographic Safety

**Prohibited as finding basis:**
- Age
- Gender
- Race
- Religion

These coded as findings are caught and flagged.

## Correction Actions

When guardrails fail:

| Issue | Action | Details |
|-------|--------|---------|
| Unsourced finding | RERUN | Require source citation, re-extract |
| Red floor unmet | DOWNGRADE | red → yellow_complex; log reason |
| Blacklist-only | DOWNGRADE | confidence → low |
| Stats-only | BOUND | Add confidence ceiling; flag review |
| Demographic basis | STRIP | Remove finding; audit |

## Configuration

`agents/agent_3/config.json`:

```json
{
  "guardrails": {
    "enabled": true,
    "strictness": "high",
    "auto_downgrade": true,
    "require_review_on": ["red_floor_miss", "stats_only", "demographic_basis"]
  }
}
```

## Monitoring

All guardrail actions logged:
- Finding ID
- Issue detected
- Action taken
- Timestamp

Enable detailed logging:
```python
import logging
logging.getLogger("agents.agent_3.guardrails").setLevel(logging.DEBUG)
```

## Reference

- Full spec: `HuriS_AgentC_Guardrails.md`
- Example guardrails implementation: `agents/agent_3/guardrails.py`
