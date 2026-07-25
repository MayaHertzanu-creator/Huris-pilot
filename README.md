# HuriS - Three-Agent Psychological Case Analysis System

A coordinated multi-agent system for comprehensive psychological case analysis and documentation.

## Architecture

### Agent 1: Data Extractor
- **Role**: File ingestion & information extraction
- **Input**: Documents, questionnaires, case materials
- **Output**: Structured extracted data with sources
- **Responsibilities**: OCR, text extraction, field mapping per DecisionSpec

### Agent 2: Chat Interviewer
- **Role**: Psychological interview conductor
- **Input**: Structured questions, interview protocol
- **Output**: Interview transcript with tagged responses
- **Responsibilities**: Real-time conversation, prompt-based questioning, response logging

### Agent 3: Analyzer & Reporter
- **Role**: Findings analysis & report generation
- **Input**: Agent 1 extracts + Agent 2 interview data
- **Output**: Comprehensive psychological report
- **Responsibilities**: Pattern analysis, guardrail compliance, report composition

## Setup

```bash
pip install -e .
```

## Usage

See `docs/SETUP.md` for detailed configuration.

## Project Structure

```
huris-agents/
├── agents/
│   ├── agent_1/       # Extraction pipeline
│   ├── agent_2/       # Interview handler
│   ├── agent_3/       # Analysis & reporting
│   └── shared/        # Common interfaces & schemas
├── tests/             # Unit & integration tests
├── docs/              # Detailed documentation
└── pyproject.toml     # Project configuration
```

## Documentation

- **INTERFACES.md** - Data structures & schemas
- **GUARDRAILS.md** - Safety & compliance rules
- **SETUP.md** - Installation & configuration

## Version

v0.1.0
