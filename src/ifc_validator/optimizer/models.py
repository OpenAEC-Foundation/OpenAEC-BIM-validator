"""Pydantic result models for the IFC optimizer.

Follows the same honesty principle as the validation reporting: every
pass reports exactly what it changed, details are capped with an
explicit omitted counter, and nothing is silently dropped.
"""

from typing import Any

from pydantic import BaseModel, Field

MAX_DETAILS = 50


class PassResult(BaseModel):
    """Result of a single optimizer pass.

    Attributes:
        name: Registry name of the pass.
        changed: Number of entities changed/removed by the pass.
        details: Per-change details (entity types, old/new GlobalIds),
            capped at MAX_DETAILS entries.
        details_omitted: Number of detail entries dropped by the cap.
    """

    name: str
    changed: int
    details: list[dict[str, Any]] = Field(default_factory=list)
    details_omitted: int = 0

    def cap_details(self) -> "PassResult":
        """Apply the detail cap, recording how many entries were dropped."""
        if len(self.details) > MAX_DETAILS:
            self.details_omitted = len(self.details) - MAX_DETAILS
            self.details = self.details[:MAX_DETAILS]
        return self


class OptimizeReport(BaseModel):
    """Complete report of an optimize run.

    Attributes:
        input_file: Name of the input IFC file.
        output_file: Name of the written output file.
        ifc_schema: Schema of the model (e.g. "IFC4").
        size_before: Input file size in bytes.
        size_after: Output file size in bytes.
        passes: Results of the executed passes, in execution order.
    """

    input_file: str
    output_file: str
    ifc_schema: str
    size_before: int
    size_after: int
    passes: list[PassResult] = Field(default_factory=list)
