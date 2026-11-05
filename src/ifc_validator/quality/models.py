"""Pydantic models for the data quality check module.

These models describe the report structure returned by
:func:`ifc_validator.quality.run_quality_checks`: a flat list of
per-check results, each carrying a bounded list of findings.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Severity = Literal["error", "warning", "info"]
"""Severity level of a quality check."""

MAX_FINDINGS_PER_CHECK = 50
"""Maximum number of findings embedded per check result."""


class CheckFinding(BaseModel):
    """A single offending entity reported by a quality check.

    Attributes:
        entity_type: IFC class name of the offending entity.
        entity_name: ``Name`` attribute of the entity, if present.
        global_id: ``GlobalId`` of the entity, if present.
        message: Human-readable description of the problem.
    """

    entity_type: str
    entity_name: str | None = None
    global_id: str | None = None
    message: str


class CheckResult(BaseModel):
    """Outcome of a single quality check.

    Attributes:
        id: Stable check identifier (e.g. ``duplicate_globalids``).
        title: Human-readable check title.
        severity: Severity assigned to findings of this check.
        passed: ``True`` when the check produced no findings.
        finding_count: Total number of findings (before truncation).
        findings: Up to :data:`MAX_FINDINGS_PER_CHECK` example findings.
        findings_omitted: Number of findings dropped from ``findings``
            because the truncation limit was reached.
    """

    id: str
    title: str
    severity: Severity
    passed: bool
    finding_count: int = 0
    findings: list[CheckFinding] = Field(default_factory=list)
    findings_omitted: int = 0


class QualityReport(BaseModel):
    """Aggregated result of a data quality check run.

    Attributes:
        ifc_file: Path or name of the analysed IFC file.
        ifc_schema: Schema identifier of the model (e.g. ``IFC4``).
        checks: One :class:`CheckResult` per executed check.
        error_count: Total findings across error-severity checks.
        warning_count: Total findings across warning-severity checks.
    """

    ifc_file: str
    ifc_schema: str
    checks: list[CheckResult] = Field(default_factory=list)
    error_count: int = 0
    warning_count: int = 0
