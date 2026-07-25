"""Protocols the three agents implement.

Structural typing rather than inheritance: an agent satisfies these by having
the right shape, so a test double or an offline replay of a stored case works
without importing anything from the real implementations.

The reading layers are async because they call a model over the network. The
decision layers are not represented here at all -- they are plain functions,
which is the point of RuleBook A D-1.
"""

from typing import Protocol, Sequence, runtime_checkable

from .schemas import (
    AgentAToCPayload,
    AgentCOutput,
    InterviewRecord,
    Sign,
    SourceDocument,
)


@runtime_checkable
class SignExtractor(Protocol):
    """Agent A's reading layer: sources in, observed signs out.

    Reports what it saw and nothing more. It does not decide whether a tag is
    True, and it does not weigh anything -- returning an empty list is a valid
    and common result, not a failure.
    """

    async def extract_signs(self, sources: Sequence[SourceDocument]) -> list[Sign]:
        ...


@runtime_checkable
class Interviewer(Protocol):
    """Agent B: conducts the interview and returns what was said.

    Receives seven booleans and no more (INTERFACES 2), so it cannot be
    steered by Agent A's confidence.
    """

    async def conduct(
        self, subject_id: str, tags: dict[str, bool]
    ) -> InterviewRecord:
        ...


@runtime_checkable
class Integrator(Protocol):
    """Agent C: the only agent that sees both sides and may reach a verdict."""

    async def assess(
        self,
        case: AgentAToCPayload,
        interview: InterviewRecord | None = None,
    ) -> AgentCOutput:
        ...


@runtime_checkable
class CaseStore(Protocol):
    """Persistence for cases. Deliberately narrow.

    There is no delete: an assessment that informed a decision about a person
    should remain auditable, and retention belongs to policy rather than to
    whatever code happens to hold a reference.
    """

    async def save(self, case_id: str, payload: dict) -> None:
        ...

    async def load(self, case_id: str) -> dict | None:
        ...

    async def list_ids(self) -> list[str]:
        ...
