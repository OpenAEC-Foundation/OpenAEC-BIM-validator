"""Data quality check implementations and registry.

Ported from the ClashControl data-quality addon (``runDataQualityChecks``
check registry). Each check receives an open :class:`ifcopenshell.file`
and returns a list of :class:`~ifc_validator.quality.models.CheckFinding`
instances — one per offending entity.

Checks operate on model structure only (attributes and relationships);
no geometry is evaluated, so they are cheap even on large models.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

import ifcopenshell

from ifc_validator.quality.models import CheckFinding, Severity

#: Generic / placeholder element names, e.g. "Wall 1", "beam_02", "Default".
GENERIC_NAME_RE = re.compile(
    r"^(wall|slab|beam|column|door|window|object|element|body|solid"
    r"|standard|default)[\s_-]*\d*$",
    re.IGNORECASE,
)

#: Maximum decomposition depth followed when resolving a storey host.
_MAX_AGGREGATION_DEPTH = 16


@dataclass(frozen=True)
class QualityCheck:
    """A registered quality check.

    Attributes:
        id: Stable identifier used in reports and the ``checks`` filter.
        title: Human-readable title.
        severity: Severity assigned to findings of this check.
        run: Callable executing the check against an open model.
    """

    id: str
    title: str
    severity: Severity
    run: Callable[[ifcopenshell.file], list[CheckFinding]]


# ── Helpers ─────────────────────────────────────────────────────────


def _finding(entity: ifcopenshell.entity_instance, message: str) -> CheckFinding:
    """Build a finding for an IFC entity.

    Args:
        entity: The offending IFC entity.
        message: Human-readable problem description.

    Returns:
        A populated :class:`CheckFinding`.
    """
    name = getattr(entity, "Name", None)
    global_id = getattr(entity, "GlobalId", None)
    return CheckFinding(
        entity_type=entity.is_a(),
        entity_name=name if isinstance(name, str) else None,
        global_id=global_id if isinstance(global_id, str) else None,
        message=message,
    )


def _inverse(entity: ifcopenshell.entity_instance, attr: str) -> tuple:
    """Return an inverse attribute as a tuple, tolerating absence.

    Args:
        entity: Entity to read from.
        attr: Inverse attribute name (e.g. ``HasAssociations``).

    Returns:
        The inverse relationships as a tuple (possibly empty).
    """
    value = getattr(entity, attr, None)
    if value is None:
        return ()
    if isinstance(value, tuple):
        return value
    return (value,)


def _building_elements(model: ifcopenshell.file) -> list[ifcopenshell.entity_instance]:
    """Return all building elements in the model.

    Uses ``IfcBuildingElement`` (IFC2X3/IFC4) and falls back to
    ``IfcBuiltElement`` for IFC4X3-family schemas.

    Args:
        model: Open IFC model.

    Returns:
        All building element instances (including subtypes).
    """
    for class_name in ("IfcBuildingElement", "IfcBuiltElement"):
        try:
            return list(model.by_type(class_name))
        except RuntimeError:
            continue
    return []


def _has_storey(entity: ifcopenshell.entity_instance, depth: int = 0) -> bool:
    """Check whether an element resolves to an IfcBuildingStorey container.

    Follows ``ContainedInStructure`` directly, and ``Decomposes``
    (aggregation) upwards so that e.g. a beam inside an
    ``IfcElementAssembly`` counts as contained when its host is.

    Args:
        entity: Element (or aggregation host) to resolve.
        depth: Current recursion depth guard.

    Returns:
        ``True`` when a storey container is found.
    """
    if depth > _MAX_AGGREGATION_DEPTH:
        return False
    for rel in _inverse(entity, "ContainedInStructure"):
        structure = getattr(rel, "RelatingStructure", None)
        if structure is not None and structure.is_a("IfcBuildingStorey"):
            return True
    for rel in _inverse(entity, "Decomposes"):
        host = getattr(rel, "RelatingObject", None)
        if host is not None and _has_storey(host, depth + 1):
            return True
    return False


# ── Check implementations ───────────────────────────────────────────


def check_duplicate_globalids(model: ifcopenshell.file) -> list[CheckFinding]:
    """Find IfcRoot entities sharing a GlobalId with an earlier entity."""
    findings: list[CheckFinding] = []
    seen: dict[str, ifcopenshell.entity_instance] = {}
    for entity in model.by_type("IfcRoot"):
        guid = getattr(entity, "GlobalId", None)
        if not isinstance(guid, str) or not guid.strip():
            continue
        first = seen.get(guid)
        if first is not None:
            findings.append(
                _finding(
                    entity,
                    f"GlobalId '{guid}' is also used by {first.is_a()} "
                    f"'{getattr(first, 'Name', None) or '(unnamed)'}'",
                )
            )
        else:
            seen[guid] = entity
    return findings


def check_missing_globalid(model: ifcopenshell.file) -> list[CheckFinding]:
    """Find IfcRoot entities with an empty or missing GlobalId."""
    findings: list[CheckFinding] = []
    for entity in model.by_type("IfcRoot"):
        guid = getattr(entity, "GlobalId", None)
        if not isinstance(guid, str) or not guid.strip():
            findings.append(_finding(entity, "Entity has no GlobalId"))
    return findings


def check_unclassified_proxies(model: ifcopenshell.file) -> list[CheckFinding]:
    """Find IfcBuildingElementProxy instances (unclassified elements)."""
    return [
        _finding(
            proxy,
            "IfcBuildingElementProxy used — element is not classified as a "
            "specific IFC type",
        )
        for proxy in model.by_type("IfcBuildingElementProxy")
    ]


def check_generic_names(model: ifcopenshell.file) -> list[CheckFinding]:
    """Find elements with a missing, empty, or generic placeholder name.

    Feature elements (openings, projections) and virtual elements are
    skipped — they are commonly unnamed by convention.
    """
    findings: list[CheckFinding] = []
    for element in model.by_type("IfcElement"):
        if element.is_a("IfcFeatureElement") or element.is_a("IfcVirtualElement"):
            continue
        name = getattr(element, "Name", None)
        if not isinstance(name, str) or not name.strip():
            findings.append(_finding(element, "Element has no Name"))
        elif GENERIC_NAME_RE.match(name.strip()):
            findings.append(
                _finding(element, f"Generic element name: '{name.strip()}'")
            )
    return findings


def check_no_material(model: ifcopenshell.file) -> list[CheckFinding]:
    """Find building elements without any material association."""
    findings: list[CheckFinding] = []
    for element in _building_elements(model):
        has_material = any(
            rel.is_a("IfcRelAssociatesMaterial")
            for rel in _inverse(element, "HasAssociations")
        )
        if not has_material:
            findings.append(_finding(element, "No material assigned"))
    return findings


def check_no_storey(model: ifcopenshell.file) -> list[CheckFinding]:
    """Find building elements not contained in an IfcBuildingStorey.

    Containment counts when direct (``IfcRelContainedInSpatialStructure``)
    or inherited via an aggregation host (``IfcRelAggregates``).
    """
    findings: list[CheckFinding] = []
    for element in _building_elements(model):
        if not _has_storey(element):
            findings.append(
                _finding(element, "Element is not contained in a building storey")
            )
    return findings


def check_no_psets(model: ifcopenshell.file) -> list[CheckFinding]:
    """Find building elements without any property set relationship."""
    findings: list[CheckFinding] = []
    for element in _building_elements(model):
        has_psets = any(
            rel.is_a("IfcRelDefinesByProperties")
            for rel in _inverse(element, "IsDefinedBy")
        )
        if not has_psets:
            findings.append(_finding(element, "Element has no property sets"))
    return findings


def check_unhosted_openings(model: ifcopenshell.file) -> list[CheckFinding]:
    """Find doors/windows not hosted in a voided element.

    A door or window counts as hosted when it fills an
    ``IfcOpeningElement`` (via ``IfcRelFillsElement``) whose opening in
    turn voids a host element (via ``IfcRelVoidsElement``).
    """
    findings: list[CheckFinding] = []
    fillers = list(model.by_type("IfcDoor")) + list(model.by_type("IfcWindow"))
    for element in fillers:
        hosted = False
        for fills_rel in _inverse(element, "FillsVoids"):
            opening = getattr(fills_rel, "RelatingOpeningElement", None)
            if opening is None or not opening.is_a("IfcOpeningElement"):
                continue
            for voids_rel in _inverse(opening, "VoidsElements"):
                if getattr(voids_rel, "RelatingBuildingElement", None) is not None:
                    hosted = True
                    break
            if hosted:
                break
        if not hosted:
            findings.append(
                _finding(
                    element,
                    f"{element.is_a()} is not hosted in a wall/element via an "
                    "opening (missing FillsVoids/VoidsElements chain)",
                )
            )
    return findings


# ── Registry ────────────────────────────────────────────────────────

CHECK_REGISTRY: tuple[QualityCheck, ...] = (
    QualityCheck(
        id="duplicate_globalids",
        title="Duplicate GlobalIds",
        severity="error",
        run=check_duplicate_globalids,
    ),
    QualityCheck(
        id="missing_globalid",
        title="Missing GlobalId",
        severity="error",
        run=check_missing_globalid,
    ),
    QualityCheck(
        id="unclassified_proxies",
        title="Unclassified proxies (IfcBuildingElementProxy)",
        severity="warning",
        run=check_unclassified_proxies,
    ),
    QualityCheck(
        id="generic_names",
        title="Generic or missing element names",
        severity="warning",
        run=check_generic_names,
    ),
    QualityCheck(
        id="no_material",
        title="No material assigned",
        severity="warning",
        run=check_no_material,
    ),
    QualityCheck(
        id="no_storey",
        title="No building storey containment",
        severity="warning",
        run=check_no_storey,
    ),
    QualityCheck(
        id="no_psets",
        title="No property sets",
        severity="info",
        run=check_no_psets,
    ),
    QualityCheck(
        id="unhosted_openings",
        title="Unhosted doors/windows",
        severity="warning",
        run=check_unhosted_openings,
    ),
)
