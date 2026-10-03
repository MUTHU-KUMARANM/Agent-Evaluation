"""Batch processing via the Message Batches API.

The module normalises the provider's batch API, validates each returned extraction,
and permits exactly one follow-up batch for recoverable item failures.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from anthropic import Anthropic
from anthropic.types.messages import (
    MessageBatchErroredResult,
    MessageBatchExpiredResult,
    MessageBatchSucceededResult,
)

from policy_extractor.client import MessageClient
from policy_extractor.extractor import EXTRACT_POLICY_TOOL, build_extraction_messages
from policy_extractor.records import (
    ExtractionOutcome,
    PolicyExtraction,
    RetryFutileEscalation,
    ValidationError,
)
from policy_extractor.retry import build_extraction, extract_with_retry
from policy_extractor.summary import summarize_patterns
from policy_extractor.validator import validate_extraction

DEFAULT_EXTRACTOR_MODEL = "claude-haiku-4-5"
BATCH_POLL_INTERVAL_SECONDS = 5.0
BATCH_POLL_TIMEOUT_SECONDS = 86_400.0

BatchStatus = Literal["succeeded", "errored", "canceled", "expired"]


class SLATooTightError(ValueError):
    """Raised when the requested SLA is shorter than the batch completion ETA."""


@dataclass(frozen=True)
class BatchItemResult:
    custom_id: str
    status: BatchStatus
    tool_input: dict[str, Any] | None
    error: str | None


class BatchClient(Protocol):
    """Small interface that makes batch orchestration independently testable."""

    def submit(self, requests: list[dict[str, Any]]) -> str: ...
    def collect(self, batch_id: str) -> list[BatchItemResult]: ...


class AnthropicBatchClient:
    """Production adapter around anthropic.Anthropic().messages.batches."""

    def __init__(self, client: Anthropic) -> None:
        self._client = client

    def submit(self, requests: list[dict[str, Any]]) -> str:
        batch = self._client.messages.batches.create(requests=requests)  # type: ignore[arg-type]
        return batch.id

    def collect(self, batch_id: str) -> list[BatchItemResult]:
        deadline = time.monotonic() + BATCH_POLL_TIMEOUT_SECONDS
        while True:
            batch = self._client.messages.batches.retrieve(batch_id)
            if batch.processing_status == "ended":
                break
            if time.monotonic() > deadline:
                raise TimeoutError(f"Batch {batch_id} did not end within 24h.")
            time.sleep(BATCH_POLL_INTERVAL_SECONDS)

        results: list[BatchItemResult] = []
        for item in self._client.messages.batches.results(batch_id):
            result = item.result
            if isinstance(result, MessageBatchSucceededResult):
                results.append(BatchItemResult(
                    custom_id=item.custom_id,
                    status="succeeded",
                    tool_input=_extract_tool_input(result.message),
                    error=None,
                ))
            elif isinstance(result, MessageBatchErroredResult):
                results.append(BatchItemResult(
                    custom_id=item.custom_id, status="errored",
                    tool_input=None, error=str(result.error),
                ))
            elif isinstance(result, MessageBatchExpiredResult):
                results.append(BatchItemResult(
                    custom_id=item.custom_id, status="expired",
                    tool_input=None, error="expired",
                ))
            else:
                results.append(BatchItemResult(
                    custom_id=item.custom_id, status="canceled",
                    tool_input=None, error="canceled",
                ))
        return results


def _extract_tool_input(message: Any) -> dict[str, Any] | None:
    for block in message.content:
        if getattr(block, "type", None) == "tool_use":
            return dict(block.input)
    return None


def submission_frequency(*, sla_hours: float, batch_eta_hours: float) -> int:
    """Return the minimum whole batches per day needed to satisfy an SLA.

    A batch cannot satisfy an SLA shorter than its expected completion time;
    use the real-time Messages API for that case.
    """
    if sla_hours <= 0 or batch_eta_hours <= 0:
        raise ValueError("sla_hours and batch_eta_hours must be positive.")
    if sla_hours < batch_eta_hours:
        raise SLATooTightError(
            "The SLA is shorter than the batch ETA; use the real-time Messages API."
        )
    head_room = sla_hours - batch_eta_hours
    return max(1, math.ceil(24.0 / (head_room + batch_eta_hours)))


def _build_request(
    custom_id: str,
    document_text: str,
    *,
    prior_attempts: list[dict[str, Any]] | None = None,
    model: str = DEFAULT_EXTRACTOR_MODEL,
    max_tokens: int = 2048,
) -> dict[str, Any]:
    messages, system = build_extraction_messages(document_text, prior_attempts)
    return {
        "custom_id": custom_id,
        "params": {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": messages,
            "tools": [EXTRACT_POLICY_TOOL],
            "tool_choice": {"type": "tool", "name": "extract_policy"},
        },
    }


def _escalation(
    policy_id: str,
    *,
    field: str,
    pattern: str,
    reason: str,
) -> RetryFutileEscalation:
    # The current domain model represents all terminal escalation outcomes with
    # this type; the detected pattern preserves the actual failure category.
    return RetryFutileEscalation(
        policy_id=policy_id,
        field=field,
        category="missing_source",
        detected_pattern=pattern,
        reason=reason,
    )


def process_with_resubmission(
    *,
    batch_client: BatchClient,
    extractor_client: MessageClient,
    policies: list[tuple[str, str]],
    model: str = DEFAULT_EXTRACTOR_MODEL,
) -> dict[str, ExtractionOutcome]:
    """Process a batch, validate each result, and allow one retry batch.

    Missing-source failures escalate immediately. Format/consistency failures
    are retried with their prior extraction and validation feedback. Provider
    item failures are retried once without feedback; failures in the second
    batch become terminal escalations.
    """
    del extractor_client  # Reserved for a future real-time fallback.
    if not policies:
        return {}

    docs_by_id = {policy_id: document for policy_id, document in policies}
    final: dict[str, ExtractionOutcome] = {}
    queued: dict[str, dict[str, Any]] = {}

    first_requests = [
        _build_request(policy_id, document, model=model)
        for policy_id, document in policies
    ]
    first_batch_id = batch_client.submit(first_requests)
    first_results = {
        item.custom_id: item for item in batch_client.collect(first_batch_id)
    }

    for policy_id, _document in policies:
        item = first_results.get(policy_id)
        if item is None or item.status != "succeeded" or item.tool_input is None:
            status = item.status if item is not None else "missing_result"
            detail = item.error if item is not None and item.error else status
            queued[policy_id] = {
                "prior_attempts": [],
                "history": [],
                "last_error": None,
            }
            queued[policy_id]["batch_failure"] = (status, detail)
            continue

        extraction = item.tool_input
        error = validate_extraction(extraction)
        if error is None:
            final[policy_id] = build_extraction(
                policy_id=policy_id,
                extraction=extraction,
                attempt_index=0,
                history=[],
            )
        elif error.category == "missing_source":
            final[policy_id] = _escalation(
                policy_id,
                field=error.field,
                pattern=error.detected_pattern,
                reason=error.message,
            )
        else:
            feedback = {
                "extraction": extraction,
                "error_field": error.field,
                "error_category": error.category,
                "error_pattern": error.detected_pattern,
                "error_message": error.message,
            }
            queued[policy_id] = {
                "prior_attempts": [feedback],
                "history": [error],
                "last_error": error,
            }

    if not queued:
        return final

    retry_requests = [
        _build_request(
            policy_id,
            docs_by_id[policy_id],
            model=model,
            prior_attempts=state["prior_attempts"] or None,
        )
        for policy_id, state in queued.items()
    ]
    second_batch_id = batch_client.submit(retry_requests)
    second_results = {
        item.custom_id: item for item in batch_client.collect(second_batch_id)
    }

    for policy_id, state in queued.items():
        item = second_results.get(policy_id)
        if item is None or item.status != "succeeded" or item.tool_input is None:
            status = item.status if item is not None else "missing_result"
            detail = item.error if item is not None and item.error else status
            final[policy_id] = _escalation(
                policy_id,
                field="batch_item",
                pattern=f"batch_item_{status}",
                reason=f"Batch item failed after resubmission: {detail}",
            )
            continue

        extraction = item.tool_input
        error = validate_extraction(extraction)
        history: list[ValidationError] = list(state["history"])
        if error is None:
            final[policy_id] = build_extraction(
                policy_id=policy_id,
                extraction=extraction,
                attempt_index=1,
                history=history,
            )
        elif error.category == "missing_source":
            final[policy_id] = _escalation(
                policy_id,
                field=error.field,
                pattern=error.detected_pattern,
                reason=error.message,
            )
        else:
            history.append(error)
            final[policy_id] = _escalation(
                policy_id,
                field=error.field,
                pattern=f"retries_exhausted__{error.detected_pattern}",
                reason=(
                    f"Validation failed after the follow-up batch. "
                    f"Last failure: {error.message}"
                ),
            )

    return final


@dataclass
class DryRunSampleResult:
    sampled: int
    succeeded: int
    escalated: int
    first_pass_success_rate: float
    pattern_summary: dict[str, dict[str, Any]] = field(default_factory=dict)


def dry_run_sample(
    *,
    extractor_client: MessageClient,
    policies: list[tuple[str, str]],
    sample_size: int,
    model: str = DEFAULT_EXTRACTOR_MODEL,
) -> DryRunSampleResult:
    """Run a bounded sample through the real-time extractor and summarise it."""
    if sample_size < 0:
        raise ValueError("sample_size must be non-negative.")
    n = min(sample_size, len(policies))
    outcomes: list[ExtractionOutcome] = []
    for policy_id, document_text in policies[:n]:
        outcomes.append(extract_with_retry(
            client=extractor_client,
            policy_id=policy_id,
            document_text=document_text,
            model=model,
            max_retries=0,
        ))
    succeeded = sum(isinstance(outcome, PolicyExtraction) for outcome in outcomes)
    escalated = sum(isinstance(outcome, RetryFutileEscalation) for outcome in outcomes)
    return DryRunSampleResult(
        sampled=n,
        succeeded=succeeded,
        escalated=escalated,
        first_pass_success_rate=succeeded / n if n else 0.0,
        pattern_summary={
            pattern: dict(row)
            for pattern, row in summarize_patterns(outcomes).items()
        },
    )
