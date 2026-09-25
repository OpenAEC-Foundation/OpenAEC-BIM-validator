"""Rich-based console output formatter for IFC validation results.

This module provides formatted console output using Rich tables and panels
to display validation summaries, specification details, and failed entities
with color-coded pass/fail status.

Usage:
    from ifc_validator.formatters.console import format_console
    from ifc_validator.validator import ValidationResult

    result: ValidationResult = validate(ifc_path, ids_path)
    format_console(result)
"""

from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ifc_validator.models import SpecificationResult, ValidationResult


# Console instance for output
console = Console()

# Style constants
PASS_STYLE = "bold green"
FAIL_STYLE = "bold red"
HEADER_STYLE = "bold cyan"
DIM_STYLE = "dim"


def _get_status_text(passed: bool) -> Text:
    """Get styled status text for pass/fail.

    Args:
        passed: Whether the check passed

    Returns:
        Rich Text object with appropriate styling
    """
    if passed:
        return Text("✓ PASS", style=PASS_STYLE)
    else:
        return Text("✗ FAIL", style=FAIL_STYLE)


def _get_status_badge(passed: bool) -> str:
    """Get a styled status badge string.

    Args:
        passed: Whether the check passed

    Returns:
        Status badge string with Rich markup
    """
    if passed:
        return "[bold green]✓ PASS[/bold green]"
    else:
        return "[bold red]✗ FAIL[/bold red]"


def _truncate(text: Optional[str], max_length: int = 60) -> str:
    """Truncate text to maximum length with ellipsis.

    Args:
        text: Text to truncate (may be None)
        max_length: Maximum length before truncation

    Returns:
        Truncated text or empty string if None
    """
    if text is None:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def _create_summary_panel(result: ValidationResult) -> Panel:
    """Create a summary panel with validation overview.

    Args:
        result: ValidationResult containing validation data

    Returns:
        Rich Panel with formatted summary
    """
    # Build summary content
    lines = []

    # Overall status
    status_text = _get_status_badge(result.overall_pass)
    lines.append(f"Overall Status: {status_text}")
    lines.append("")

    # IFC Model info
    lines.append(f"[{HEADER_STYLE}]IFC Model[/{HEADER_STYLE}]")
    lines.append(f"  File: {result.ifc_file}")
    lines.append(f"  Schema: {result.ifc_schema}")
    lines.append(f"  Entities: {result.ifc_entity_count:,}")
    lines.append("")

    # IDS Specification info
    lines.append(f"[{HEADER_STYLE}]IDS Specification[/{HEADER_STYLE}]")
    lines.append(f"  File: {result.ids_file}")
    if result.ids_title:
        lines.append(f"  Title: {result.ids_title}")
    lines.append("")

    # Validation Statistics
    lines.append(f"[{HEADER_STYLE}]Validation Results[/{HEADER_STYLE}]")
    lines.append(f"  Time: {result.validation_time_seconds:.3f} seconds")
    lines.append(f"  Total Specifications: {result.total_specifications}")

    # Passed count with color
    passed_color = "green" if result.passed_specifications > 0 else "dim"
    lines.append(f"  Passed: [{passed_color}]{result.passed_specifications}[/{passed_color}]")

    # Failed count with color
    failed_color = "red" if result.failed_specifications > 0 else "dim"
    lines.append(f"  Failed: [{failed_color}]{result.failed_specifications}[/{failed_color}]")

    # Not-checkable count (honesty rule: never hide unevaluated specs)
    if result.not_checkable_specifications > 0:
        lines.append(
            f"  Not checkable: [yellow]{result.not_checkable_specifications}[/yellow]"
        )

    # Pass rate with color based on value
    rate = result.pass_rate_percent
    if rate == 100.0:
        rate_color = "bold green"
    elif rate >= 75.0:
        rate_color = "yellow"
    else:
        rate_color = "red"
    lines.append(f"  Pass Rate: [{rate_color}]{rate:.1f}%[/{rate_color}]")

    content = "\n".join(lines)

    # Determine border style based on overall pass/fail
    border_style = "green" if result.overall_pass else "red"

    return Panel(
        content,
        title="[bold]IFC-IDS Validation Summary[/bold]",
        border_style=border_style,
        padding=(1, 2),
    )


def _create_specifications_table(result: ValidationResult) -> Table:
    """Create a table with specification results.

    Args:
        result: ValidationResult containing specification data

    Returns:
        Rich Table with specification results
    """
    table = Table(
        title="Specification Results",
        show_header=True,
        header_style="bold",
        show_lines=True,
    )

    # Define columns
    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("Status", width=13, justify="center")
    table.add_column("Specification", min_width=30)
    table.add_column("Applicable", justify="right", width=10)
    table.add_column("Passed", justify="right", width=10)
    table.add_column("Failed", justify="right", width=10)

    # Add rows for each specification
    for i, spec in enumerate(result.specifications, 1):
        if spec.status == "not_checkable":
            status = Text("? NOT CHECKED", style="yellow")
        else:
            status = _get_status_text(spec.passed)

        # Format name with description if available
        name = spec.name
        if spec.description:
            desc = _truncate(spec.description, 50)
            name = f"{name}\n[dim]{desc}[/dim]"
        if spec.status == "not_checkable" and spec.not_checkable_reason:
            reason = _truncate(spec.not_checkable_reason, 60)
            name = f"{name}\n[yellow]{reason}[/yellow]"

        # Format counts with colors
        applicable = str(spec.applicable_count)
        passed = f"[green]{spec.passed_count}[/green]" if spec.passed_count > 0 else str(spec.passed_count)
        failed = f"[red]{spec.failed_count}[/red]" if spec.failed_count > 0 else str(spec.failed_count)

        table.add_row(
            str(i),
            status,
            name,
            applicable,
            passed,
            failed,
        )

    return table


def _create_failures_panel(spec: SpecificationResult, spec_index: int) -> Optional[Panel]:
    """Create a panel showing failed entities for a specification.

    Args:
        spec: SpecificationResult with failures
        spec_index: Index number of the specification (1-based)

    Returns:
        Rich Panel with failure details, or None if no failures
    """
    if not spec.failures:
        return None

    # Create table for failures
    table = Table(
        show_header=True,
        header_style="bold",
        box=None,
        padding=(0, 1),
    )

    table.add_column("ID", style="dim", width=8)
    table.add_column("Type", width=20)
    table.add_column("Name", min_width=30)
    table.add_column("GlobalId", style="dim", width=24)

    # Limit displayed failures to prevent overwhelming output
    max_failures_to_show = 10
    failures_to_show = spec.failures[:max_failures_to_show]

    for failure in failures_to_show:
        name = failure.entity_name if failure.entity_name else "[dim]—[/dim]"
        global_id = failure.global_id if failure.global_id else "[dim]—[/dim]"

        table.add_row(
            f"#{failure.entity_id}",
            failure.entity_type,
            name,
            global_id,
        )

    # Show count of remaining failures
    remaining = len(spec.failures) - max_failures_to_show
    if remaining > 0:
        table.add_row(
            "",
            f"[dim]... and {remaining} more[/dim]",
            "",
            "",
        )

    return Panel(
        table,
        title=f"[bold red]Failed Entities: {spec.name}[/bold red]",
        subtitle=f"[dim]{spec.failed_count} failures[/dim]",
        border_style="red",
        padding=(0, 1),
    )


def format_console(
    result: ValidationResult,
    show_failures: bool = True,
    verbose: bool = False,
) -> None:
    """Format and display validation results to console using Rich.

    This function outputs:
    1. A summary panel with overall validation status
    2. A table showing all specification results
    3. Detailed failure panels for failed specifications (if show_failures=True)

    Args:
        result: ValidationResult from IFC-IDS validation
        show_failures: Whether to show detailed failure information (default True)
        verbose: Whether to show all failures (default False shows max 10 per spec)
    """
    console.print()

    # Print summary panel
    summary_panel = _create_summary_panel(result)
    console.print(summary_panel)
    console.print()

    # Print specifications table
    if result.specifications:
        specs_table = _create_specifications_table(result)
        console.print(specs_table)
        console.print()

        # Print failure details for failed specifications
        if show_failures:
            failed_specs = [
                (i, spec)
                for i, spec in enumerate(result.specifications, 1)
                if not spec.passed and spec.failures
            ]

            if failed_specs:
                console.print("[bold red]Failed Entities Detail[/bold red]")
                console.print()

                for spec_index, spec in failed_specs:
                    failure_panel = _create_failures_panel(spec, spec_index)
                    if failure_panel:
                        console.print(failure_panel)
                        console.print()
    else:
        console.print("[dim]No specifications found in IDS file.[/dim]")
        console.print()

    # Final status line
    if result.overall_pass:
        console.print("[bold green]✓ All specifications passed![/bold green]")
    else:
        console.print(
            f"[bold red]✗ {result.failed_specifications} specification(s) failed.[/bold red]"
        )
    console.print()


def format_console_to_string(
    result: ValidationResult,
    show_failures: bool = True,
    verbose: bool = False,
) -> str:
    """Format validation results and return as string.

    Same as format_console but captures output to a string instead of
    printing directly. Useful for testing and capturing output.

    Args:
        result: ValidationResult from IFC-IDS validation
        show_failures: Whether to show detailed failure information
        verbose: Whether to show all failures

    Returns:
        Formatted string with validation results
    """
    # Create a console that captures output
    string_console = Console(force_terminal=True, record=True)

    # Temporarily replace the module console
    global console
    original_console = console
    console = string_console

    try:
        format_console(result, show_failures=show_failures, verbose=verbose)
        return string_console.export_text()
    finally:
        # Restore original console
        console = original_console
