# HuriS Setup & Configuration

## Installation

### Prerequisites
- Python 3.9+
- Anthropic API key
- Git

### Quick Start

```bash
# Clone repository
git clone <repo-url>
cd huris-agents

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Configure environment
cp .env.example .env
# Edit .env and add your API key
```

## Configuration

### Environment Variables

Create `.env` file in project root:

```
ANTHROPIC_API_KEY=sk-...
HURIS_DATA_DIR=./data
HURIS_LOG_LEVEL=INFO
```

### Agent Configuration

Each agent has a `config.json` in its directory:

**agent_1/config.json** - Extraction settings
- Decision spec version
- OCR settings
- Source validation rules

**agent_2/config.json** - Interview settings  
- Protocol version
- Safety check intervals
- Engagement thresholds

**agent_3/config.json** - Analysis settings
- Guardrail strictness
- Report format
- Quality check level

## Running Tests

```bash
pytest tests/
pytest --cov=agents tests/
```

## API Usage

```python
from agents.agent_1 import Agent1
from agents.agent_2 import Agent2
from agents.agent_3 import Agent3

# Initialize agents
config = {...}
agent_1 = Agent1(config)
agent_2 = Agent2(config)
agent_3 = Agent3(config)

# Process case
extracted = await agent_1.extract_from_document(doc_path, spec)
interview = await agent_2.conduct_interview(subject_id, protocol)
report = await agent_3.generate_report(extracted, interview)
```

## Documentation

- **INTERFACES.md** - Data structures and schemas
- **GUARDRAILS.md** - Safety guidelines and compliance rules
- **../agents/agent_N/** - Agent-specific implementation docs

## Support

For issues or questions, refer to the development documentation in `docs/`.
