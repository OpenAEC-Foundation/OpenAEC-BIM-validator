"""Data quality checks for IFC models.

Public API for running structural data-quality checks (duplicate
GlobalIds, unclassified proxies, missing materials/storeys/psets,
unhosted openings, …) against an IFC model.

Example:
    >>> from ifc_validator.quality import run_quality_checks
    >>> report = run_quality_checks("model.ifc")
    >>> report.error_count
    0
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Union

import ifcopenshell

from ifc_validator.quality.checks import CHECK_REGISTRY, QualityCheck
from ifc_validator.quality.models import (
    MAX_FINDINGS_PER_CHECK,
    CheckFinding,
    CheckResult,
    QualityReport,
    Severity,
)

__all__ = [
    "CHECK_REGISTRY",
    "CheckFinding",
    "CheckResult",
    "QualityCheck",
    "QualityReport",
    "Severity",
    "list_checks",
    "run_quality_checks",
]

IfcSource = Union[str, Path, ifcopenshell.file]
"""Accepted inputs for :func:`run_quality_checks`."""


def list_checks() -> list[dict[str, str]]:
    """List all registered quality checks.

    Returns:
        One dict per check with ``id``, ``title``, and ``severity`` keys,
        in registry order.
    """
    return [
        {"id": check.id, "title": check.title, "severity": check.severity}
        for check in CHECK_REGISTRY
    ]


def _select_checks(checks: Iterable[str] | None) -> list[QualityCheck]:
    """Resolve a check-id filter against the registry.

    Args:
        checks: Iterable of check ids, or ``None`` for all checks.

    Returns:
        The selected checks in registry order.

    Raises:
        ValueError: If any requested id is not a registered check.
    """
    if checks is None:
        return list(CHECK_REGISTRY)
    requested = list(checks)
    known = {check.id for check in CHECK_REGISTRY}
    unknown = [check_id for check_id in requested if check_id not in known]
    if unknown:
        raise ValueError(
            f"Unknown check id(s): {', '.join(unknown)}. "
            f"Available: {', '.join(sorted(known))}"
        )
    requested_set = set(requested)
    return [check for check in CHECK_REGISTRY if check.id in requested_set]


def run_quality_checks(
    ifc: IfcSource,
    checks: Iterable[str] | None = None,
) -> QualityReport:
    """Run data quality checks against an IFC model.

    Args:
        ifc: Path to an IFC file, or an already-open
            :class:`ifcopenshell.file` instance.
        checks: Optional iterable of check ids to run (see
            :func:`list_checks`). ``None`` runs all registered checks.

    Returns:
        A :class:`QualityReport` with one :class:`CheckResult` per
        executed check. Findings per check are truncated to
        :data:`MAX_FINDINGS_PER_CHECK`; the full count is preserved in
        ``finding_count`` and ``findings_omitted``.

    Raises:
        ValueError: If ``checks`` contains an unknown check id.
        Exception: Propagated from ifcopenshell when the file cannot
            be opened or parsed.
    """
    selected = _select_checks(checks)

    if isinstance(ifc, (str, Path)):
        model = ifcopenshell.open(str(ifc))
        ifc_file = str(ifc)
    else:
        model = ifc
        ifc_file = "<in-memory>"

    schema = getattr(model, "schema_identifier", None) or model.schema

    results: list[CheckResult] = []
    for check in selected:
        findings = check.run(model)
        results.append(
            CheckResult(
                id=check.id,
                title=check.title,
                severity=check.severity,
                passed=not findings,
                finding_count=len(findings),
                findings=findings[:MAX_FINDINGS_PER_CHECK],
                findings_omitted=max(0, len(findings) - MAX_FINDINGS_PER_CHECK),
            )
        )

    return QualityReport(
        ifc_file=ifc_file,
        ifc_schema=str(schema),
        checks=results,
        error_count=sum(
            r.finding_count for r in results if r.severity == "error"
        ),
        warning_count=sum(
            r.finding_count for r in results if r.severity == "warning"
        ),
    )
