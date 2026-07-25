"""Base interfaces and abstract classes for HuriS agents."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from .schemas import CaseFile, Finding, Interview, Report


class Agent(ABC):
    """Base class for HuriS agents."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = config.get("name", "unnamed_agent")
        self.version = config.get("version", "0.1.0")

    @abstractmethod
    async def process(self, input_data: Any) -> Any:
        """Process input and return output."""
        pass

    @abstractmethod
    def validate_output(self, output: Any) -> bool:
        """Validate agent output against schema."""
        pass


class DataStore(ABC):
    """Abstract interface for persistent data storage."""

    @abstractmethod
    async def save_case(self, case: CaseFile) -> str:
        """Save case file and return case ID."""
        pass

    @abstractmethod
    async def load_case(self, case_id: str) -> Optional[CaseFile]:
        """Load case file by ID."""
        pass

    @abstractmethod
    async def update_case(self, case_id: str, updates: Dict[str, Any]) -> bool:
        """Update case file."""
        pass

    @abstractmethod
    async def list_cases(self, filter: Optional[Dict[str, Any]] = None) -> List[str]:
        """List case IDs matching optional filter."""
        pass


class ExtractorAgent(Agent):
    """Interface for Agent 1: Data Extraction."""

    @abstractmethod
    async def extract_from_document(self, document_path: str, decision_spec: Dict) -> Dict[str, Any]:
        """Extract structured data from document."""
        pass

    @abstractmethod
    async def validate_extraction(self, extracted: Dict, spec: Dict) -> List[str]:
        """Validate extracted data against spec. Return list of errors or empty if valid."""
        pass


class InterviewAgent(Agent):
    """Interface for Agent 2: Interview Conductor."""

    @abstractmethod
    async def start_interview(self, subject_id: str, protocol: Dict) -> str:
        """Start interview and return interview_id."""
        pass

    @abstractmethod
    async def ask_question(self, interview_id: str, question: str) -> Dict[str, Any]:
        """Ask question and get response."""
        pass

    @abstractmethod
    async def end_interview(self, interview_id: str, status: str) -> Interview:
        """End interview and return structured Interview object."""
        pass

    @abstractmethod
    async def check_safety(self, interview_id: str) -> bool:
        """Check if interview should continue (safety check)."""
        pass


class AnalyzerAgent(Agent):
    """Interface for Agent 3: Analysis & Reporting."""

    @abstractmethod
    async def analyze_findings(self, case_data: Dict[str, Any]) -> List[Finding]:
        """Extract findings from case data."""
        pass

    @abstractmethod
    async def apply_guardrails(self, findings: List[Finding]) -> List[str]:
        """Apply safety guardrails. Return list of issues or empty if passed."""
        pass

    @abstractmethod
    async def generate_report(self, findings: List[Finding], interview: Interview) -> Report:
        """Generate final psychological report."""
        pass


class Orchestrator:
    """Coordinates all three agents."""

    def __init__(
        self,
        agent_1: ExtractorAgent,
        agent_2: InterviewAgent,
        agent_3: AnalyzerAgent,
        data_store: DataStore,
    ):
        self.agent_1 = agent_1
        self.agent_2 = agent_2
        self.agent_3 = agent_3
        self.data_store = data_store

    @abstractmethod
    async def process_case(
        self,
        case_id: str,
        documents: List[str],
        interview_protocol: Dict,
        specs: Dict[str, Any],
    ) -> CaseFile:
        """Orchestrate full case processing through all three agents."""
        pass
