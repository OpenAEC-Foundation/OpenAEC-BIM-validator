"""CLI entry point for IFC validation using Typer.

This module provides the command-line interface for the ifc-validate tool.
It defines the validate command with IFC file positional argument,
required --ids option, and --output option (console|json|html).

Usage:
    ifc-validate path/to/model.ifc --ids path/to/rules.ids
    ifc-validate path/to/model.ifc --ids path/to/rules.ids --output json
    ifc-validate path/to/model.ifc --ids path/to/rules.ids --output html

Dutch BIM Standards Shortcuts:
    ifc-validate path/to/model.ifc --ids nl-bim    # NL_BIM Basis ILS v2
    ifc-validate path/to/model.ifc --ids rvb       # RVB BIM Norm v1.1

CRITICAL: This module uses typer.Exit(code=X) for exit codes, never sys.exit().
"""

from enum import Enum
from pathlib import Path
from typing import Optional

import click
import typer
from rich.console import Console

# Create the Typer app instance
# Entry point is ifc_validator.cli:app
app = typer.Typer(
    name="ifc-validate",
    help="Validate IFC building models against IDS specification rules.",
    add_completion=False,
)


class OutputFormat(str, Enum):
    """Output format options for validation results."""

    console = "console"
    json = "json"
    html = "html"


# Rich console for error output
err_console = Console(stderr=True)


def version_callback(value: bool) -> None:
    """Handle --version flag."""
    if value:
        from ifc_validator import __version__

        err_console.print(f"ifc-validate version {__version__}")
        raise typer.Exit(code=0)


@app.command()
def validate(
    ifc_file: str = typer.Argument(
        ...,
        help="Path to the IFC file to validate (.ifc, .ifcxml, .ifczip)",
        metavar="IFC_FILE",
    ),
    ids: str = typer.Option(
        ...,
        "--ids",
        "-i",
        help="Path to IDS rules file (.ids) or shortcut (nl-bim, rvb) - REQUIRED",
        metavar="IDS_FILE",
    ),
    output: OutputFormat = typer.Option(
        OutputFormat.console,
        "--output",
        "-o",
        help="Output format: console (default), json, or html",
        case_sensitive=False,
    ),
    html_output_file: Optional[str] = typer.Option(
        None,
        "--html-output",
        help="Output file path for HTML report (only used with --output html). "
        "If not specified, writes to <ifc_file>_report.html",
        metavar="FILE",
    ),
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """Validate an IFC model against IDS (Information Delivery Specification) rules.

    Validates the specified IFC building model file against the IDS rules file
    and outputs the results in the requested format.

    \b
    Dutch BIM Standards Shortcuts:
        nl-bim - NL_BIM Basis ILS v2 (Dutch baseline BIM standard)
        rvb    - RVB BIM Norm v1.1 (Dutch Government Real Estate norm)

    \b
    Exit codes:
        0 - All specifications passed validation
        1 - One or more specifications failed validation, or an error occurred

    \b
    Examples:
        ifc-validate model.ifc --ids rules.ids
        ifc-validate model.ifc --ids nl-bim
        ifc-validate model.ifc --ids rvb
        ifc-validate model.ifc --ids rules.ids --output json
        ifc-validate model.ifc --ids rules.ids --output html
    """
    from ifc_validator.formatters import (
        format_console,
        format_html_to_file,
        print_json,
    )
    from ifc_validator.standards import get_bundled_ids, is_shortcut
    from ifc_validator.validator import (
        validate as run_validation,
    )

    try:
        # Resolve IDS shortcut to bundled file path if applicable
        # Shortcuts (nl-bim, rvb) are resolved to bundled IDS files
        # File paths are passed through unchanged for backward compatibility
        if is_shortcut(ids):
            ids_path = str(get_bundled_ids(ids))
        else:
            ids_path = ids

        # Run validation (handles file validation, memory checks, and parsing)
        result = run_validation(ifc_file, ids_path)

        # Output results based on format
        if output == OutputFormat.console:
            format_console(result)

        elif output == OutputFormat.json:
            print_json(result)

        elif output == OutputFormat.html:
            # Determine output file path
            if html_output_file:
                output_path = Path(html_output_file)
            else:
                # Default: <ifc_file>_report.html in current directory
                ifc_path = Path(ifc_file)
                output_path = Path(f"{ifc_path.stem}_report.html")

            # Generate HTML report
            written_path = format_html_to_file(result, output_path)
            err_console.print(
                f"[green]HTML report written to:[/green] {written_path}",
            )

        # Exit based on validation result
        # Exit code 0 = all passed, exit code 1 = any failed
        if result.overall_pass:
            raise typer.Exit(code=0)
        else:
            raise typer.Exit(code=1)

    except FileNotFoundError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)

    except ValueError as e:
        err_console.print(f"[red]Validation Error:[/red] {e}")
        raise typer.Exit(code=1)

    except MemoryError as e:
        err_console.print(f"[red]Memory Error:[/red] {e}")
        raise typer.Exit(code=1)

    except click.exceptions.Exit:
        # Re-raise typer.Exit/click.Exit - don't catch these
        # (they inherit from RuntimeError but should propagate)
        raise

    except RuntimeError as e:
        err_console.print(f"[red]Runtime Error:[/red] {e}")
        raise typer.Exit(code=1)

    except Exception as e:
        err_console.print(f"[red]Unexpected Error:[/red] {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
