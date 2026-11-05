"""Optimizer pass implementations.

Each graph pass takes an ``ifcopenshell.file`` and mutates it in place,
returning a PassResult describing exactly what changed. The ``compact``
pass is special: it produces a *new* file object (ifcpatch Optimise
recipe) and therefore returns the new model alongside its result.
"""

from typing import Any

import ifcopenshell
import ifcopenshell.guid

from ifc_validator.optimizer.models import PassResult

# Relationship attributes that must reference at least one object for the
# relationship to be meaningful
_RELATED_ATTRS = ("RelatedObjects", "RelatedElements")


def fix_duplicate_globalids(model: ifcopenshell.file) -> PassResult:
    """Give duplicate GlobalIds a fresh GUID (first occurrence wins).

    Args:
        model: The IFC model to fix in place.

    Returns:
        PassResult with old → new GUID mapping per re-identified entity.
    """
    seen: set[str] = set()
    details: list[dict[str, Any]] = []

    for entity in model.by_type("IfcRoot"):
        guid = entity.GlobalId
        if guid and guid not in seen:
            seen.add(guid)
            continue
        new_guid = ifcopenshell.guid.new()
        details.append(
            {
                "entity_type": entity.is_a(),
                "entity_name": getattr(entity, "Name", None),
                "old": guid,
                "new": new_guid,
            }
        )
        entity.GlobalId = new_guid
        seen.add(new_guid)

    return PassResult(
        name="fix_duplicate_globalids", changed=len(details), details=details
    ).cap_details()


def remove_broken_relationships(model: ifcopenshell.file) -> PassResult:
    """Remove relationship entities that relate to nothing.

    A relationship whose RelatedObjects/RelatedElements attribute exists
    but is empty or None carries no information and only bloats the file.

    Args:
        model: The IFC model to clean in place.

    Returns:
        PassResult listing the removed relationships.
    """
    details: list[dict[str, Any]] = []

    for rel in list(model.by_type("IfcRelationship")):
        for attr in _RELATED_ATTRS:
            try:
                value = getattr(rel, attr)
            except AttributeError:
                continue
            if value is None or len(value) == 0:
                details.append(
                    {
                        "entity_type": rel.is_a(),
                        "global_id": getattr(rel, "GlobalId", None),
                        "reason": f"{attr} is empty",
                    }
                )
                model.remove(rel)
                break

    return PassResult(
        name="remove_broken_relationships",
        changed=len(details),
        details=details,
    ).cap_details()


def remove_unused_psets(model: ifcopenshell.file) -> PassResult:
    """Remove property sets and quantities that nothing references.

    Args:
        model: The IFC model to clean in place.

    Returns:
        PassResult listing the removed property sets.
    """
    details: list[dict[str, Any]] = []

    candidates = list(model.by_type("IfcPropertySet")) + list(
        model.by_type("IfcElementQuantity")
    )
    for pset in candidates:
        if model.get_inverse(pset):
            continue
        details.append(
            {
                "entity_type": pset.is_a(),
                "entity_name": getattr(pset, "Name", None),
                "global_id": getattr(pset, "GlobalId", None),
            }
        )
        model.remove(pset)

    return PassResult(
        name="remove_unused_psets", changed=len(details), details=details
    ).cap_details()


def compact(
    model: ifcopenshell.file,
) -> tuple[ifcopenshell.file, PassResult]:
    """Deduplicate identical instances and rewrite compactly.

    Delegates to the ifcpatch ``Optimise`` recipe, which merges
    byte-identical instances and renumbers the file densely.

    Args:
        model: The IFC model to compact.

    Returns:
        Tuple of (new compacted model, PassResult with the entity delta).
    """
    import ifcpatch

    before = sum(1 for _ in model)
    optimized = ifcpatch.execute(
        {"input": "", "file": model, "recipe": "Optimise", "arguments": []}
    )
    after = sum(1 for _ in optimized)

    result = PassResult(
        name="compact",
        changed=max(before - after, 0),
        details=[{"entities_before": before, "entities_after": after}],
    )
    return optimized, result
