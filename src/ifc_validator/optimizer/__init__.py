"""IFC optimizer: selectable cleanup passes with a full change report.

The optimizer never touches the input file — it loads the model, runs
the selected passes in a fixed order and writes a new file, returning
an OptimizeReport that states exactly what changed.

Usage:
    from ifc_validator.optimizer import optimize

    report = optimize("model.ifc", "model.optimized.ifc")
    report = optimize("model.ifc", out, passes=["fix_duplicate_globalids"])
"""

from pathlib import Path
from typing import Optional, Union

import ifcopenshell

from ifc_validator.optimizer.models import OptimizeReport, PassResult
from ifc_validator.optimizer.passes import (
    compact,
    fix_duplicate_globalids,
    remove_broken_relationships,
    remove_unused_psets,
)

# Fixed execution order; the selection only decides which ones take part.
# compact runs last because it renumbers the whole file.
PASS_ORDER = (
    "fix_duplicate_globalids",
    "remove_broken_relationships",
    "remove_unused_psets",
    "compact",
)

_GRAPH_PASSES = {
    "fix_duplicate_globalids": fix_duplicate_globalids,
    "remove_broken_relationships": remove_broken_relationships,
    "remove_unused_psets": remove_unused_psets,
}

_PASS_INFO = {
    "fix_duplicate_globalids": {
        "title": "Dubbele GlobalIds herstellen",
        "description": "Entiteiten met een al gebruikt GlobalId krijgen een "
        "nieuwe GUID; het eerste exemplaar behoudt het origineel.",
    },
    "remove_broken_relationships": {
        "title": "Kapotte relaties verwijderen",
        "description": "Relatie-entiteiten zonder gerelateerde objecten "
        "worden verwijderd.",
    },
    "remove_unused_psets": {
        "title": "Ongebruikte property sets verwijderen",
        "description": "Property sets en quantities waar niets naar "
        "verwijst worden verwijderd.",
    },
    "compact": {
        "title": "Compact herschrijven",
        "description": "Identieke instanties worden gededupliceerd en het "
        "bestand wordt compact hernummerd (ifcpatch Optimise).",
    },
}


def list_passes() -> list[dict[str, str]]:
    """Describe the available passes, in execution order (for UIs)."""
    return [
        {"name": name, **_PASS_INFO[name]}
        for name in PASS_ORDER
    ]


def optimize(
    input_path: Union[str, Path],
    output_path: Union[str, Path],
    passes: Optional[list[str]] = None,
) -> OptimizeReport:
    """Optimize an IFC file into a new file, running the selected passes.

    Args:
        input_path: Path to the input IFC file (never modified).
        output_path: Path to write the optimized IFC file to.
        passes: Pass names to run; None runs all passes. Order of the
            list is irrelevant — execution order is fixed (PASS_ORDER).

    Returns:
        OptimizeReport with size delta and per-pass changes.

    Raises:
        ValueError: If an unknown pass name is given.
        FileNotFoundError: If the input file does not exist.
    """
    input_path = Path(input_path)
    output_path = Path(output_path)

    selected = list(PASS_ORDER) if passes is None else list(passes)
    unknown = [p for p in selected if p not in PASS_ORDER]
    if unknown:
        valid = ", ".join(PASS_ORDER)
        raise ValueError(
            f"Unknown optimizer pass(es): {', '.join(unknown)}. "
            f"Valid passes are: {valid}"
        )
    if not input_path.exists():
        raise FileNotFoundError(f"IFC file not found: {input_path}")

    size_before = input_path.stat().st_size
    model = ifcopenshell.open(str(input_path))
    ifc_schema = model.schema

    results: list[PassResult] = []
    for name in PASS_ORDER:
        if name not in selected:
            continue
        if name == "compact":
            model, result = compact(model)
        else:
            result = _GRAPH_PASSES[name](model)
        results.append(result)

    model.write(str(output_path))
    size_after = output_path.stat().st_size

    return OptimizeReport(
        input_file=input_path.name,
        output_file=output_path.name,
        ifc_schema=ifc_schema,
        size_before=size_before,
        size_after=size_after,
        passes=results,
    )


__all__ = [
    "PASS_ORDER",
    "OptimizeReport",
    "PassResult",
    "list_passes",
    "optimize",
]
