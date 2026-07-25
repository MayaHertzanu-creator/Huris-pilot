"""Agent 1: Document extraction pipeline.

Processes documents and extracts structured data per DecisionSpec.
See: HuriS_AgentA_ExtractionPrompt_v0.1
"""

from typing import Dict, Any, List, Optional
from ..shared.interfaces import ExtractorAgent as BaseExtractor
from ..shared.schemas import Evidence


class ExtractorAgent(BaseExtractor):
    """Document extraction agent using Claude with decision specs."""

    async def extract_from_document(self, document_path: str, decision_spec: Dict) -> Dict[str, Any]:
        """
        Extract structured data from document.

        Args:
            document_path: Path to source document
            decision_spec: DecisionSpec defining what to extract

        Returns:
            Extracted data structured per spec
        """
        # TODO: Implement document loading
        # TODO: Implement Claude extraction call
        # TODO: Parse response into structured format
        raise NotImplementedError()

    async def validate_extraction(self, extracted: Dict, spec: Dict) -> List[str]:
        """
        Validate extracted data against spec.

        Returns:
            List of validation errors, empty if valid
        """
        errors = []

        # Validate required fields per spec
        required_fields = spec.get("required_fields", [])
        for field in required_fields:
            if field not in extracted:
                errors.append(f"Missing required field: {field}")

        # TODO: Validate data types and formats
        # TODO: Check source coverage (legibility)
        # TODO: Validate evidence sourcing

        return errors

    async def process(self, input_data: Any) -> Any:
        """Process document(s) and return extracted data."""
        # TODO: Implement
        raise NotImplementedError()

    def validate_output(self, output: Any) -> bool:
        """Validate extraction output."""
        # TODO: Implement
        return False
