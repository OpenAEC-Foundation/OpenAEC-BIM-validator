"""HTML output formatter for IFC validation results.

This module provides HTML-formatted output for validation results,
preferring IfcTester's built-in ifctester.reporter.Html when available.
Falls back to a minimal HTML template when using ValidationResult dataclass.

Usage:
    from ifc_validator.formatters.html import (
        format_html_from_ids,
        format_html,
        format_html_to_file,
    )

    # Preferred: Using IDS file directly (uses ifctester.reporter.Html)
    html_content = format_html_from_ids(ids_file)

    # Fallback: Using ValidationResult
    from ifc_validator.models import ValidationResult
    result: ValidationResult = validate(ifc_path, ids_path)
    html_content = format_html(result)
"""

from pathlib import Path
from typing import Optional, Union

from ifc_validator.models import ValidationResult


def format_html_from_ids(
    ids_file,
    hide_skipped: bool = False,
) -> str:
    """Format validation results as HTML using IfcTester's reporter.

    This is the preferred method as it uses IfcTester's built-in HTML
    reporter which provides comprehensive formatting of validation results.

    Args:
        ids_file: IDS file object after validation (ids_file.validate() called)
        hide_skipped: Whether to hide skipped specifications

    Returns:
        HTML string with formatted validation results

    Example:
        from ifctester import ids
        import ifcopenshell

        ifc_model = ifcopenshell.open("model.ifc")
        ids_file = ids.open("rules.ids")
        ids_file.validate(ifc_model)

        html = format_html_from_ids(ids_file)
    """
    from ifctester import reporter

    html_reporter = reporter.Html(ids_file, hide_skipped=hide_skipped)
    return html_reporter.to_string()


def format_html_from_ids_to_file(
    ids_file,
    output_path: Union[str, Path],
    hide_skipped: bool = False,
) -> Path:
    """Write validation results to an HTML file using IfcTester's reporter.

    This is the preferred method as it uses IfcTester's built-in HTML
    reporter which provides comprehensive formatting of validation results.

    Args:
        ids_file: IDS file object after validation (ids_file.validate() called)
        output_path: Path to the output HTML file
        hide_skipped: Whether to hide skipped specifications

    Returns:
        Path to the written file

    Raises:
        OSError: If the file cannot be written
    """
    from ifctester import reporter

    path = Path(output_path)

    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    html_reporter = reporter.Html(ids_file, hide_skipped=hide_skipped)
    html_reporter.to_file(str(path))

    return path


def _escape_html(text: Optional[str]) -> str:
    """Escape HTML special characters.

    Args:
        text: Text to escape (may be None)

    Returns:
        Escaped text or empty string if None
    """
    if text is None:
        return ""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def _get_status_class(passed: bool) -> str:
    """Get CSS class for pass/fail status.

    Args:
        passed: Whether the check passed

    Returns:
        CSS class name
    """
    return "pass" if passed else "fail"


def _get_status_text(passed: bool) -> str:
    """Get status text for pass/fail.

    Args:
        passed: Whether the check passed

    Returns:
        Status text string
    """
    return "✓ PASS" if passed else "✗ FAIL"


def _generate_html_template(result: ValidationResult) -> str:
    """Generate HTML content from ValidationResult.

    This is a fallback method when the IDS file object is not available.
    Generates a clean, readable HTML report with embedded CSS styling.

    Args:
        result: ValidationResult from IFC-IDS validation

    Returns:
        HTML string with formatted validation results
    """
    overall_status_class = _get_status_class(result.overall_pass)
    overall_status_text = _get_status_text(result.overall_pass)

    # Build specifications rows
    spec_rows = []
    for i, spec in enumerate(result.specifications, 1):
        status_class = _get_status_class(spec.passed)
        status_text = _get_status_text(spec.passed)
        description = _escape_html(spec.description) if spec.description else ""

        spec_rows.append(f"""
            <tr class="{status_class}">
                <td>{i}</td>
                <td class="status">{status_text}</td>
                <td>
                    <strong>{_escape_html(spec.name)}</strong>
                    {f'<br><small class="description">{description}</small>' if description else ''}
                </td>
                <td class="count">{spec.applicable_count}</td>
                <td class="count passed-count">{spec.passed_count}</td>
                <td class="count failed-count">{spec.failed_count}</td>
            </tr>""")

    spec_rows_html = "\n".join(spec_rows)

    # Build failure details
    failure_sections = []
    for spec in result.specifications:
        if not spec.passed and spec.failures:
            failure_rows = []
            for failure in spec.failures[:50]:  # Limit to 50 per spec
                name = _escape_html(failure.entity_name) if failure.entity_name else "—"
                global_id = _escape_html(failure.global_id) if failure.global_id else "—"
                failure_rows.append(f"""
                    <tr>
                        <td>#{failure.entity_id}</td>
                        <td>{_escape_html(failure.entity_type)}</td>
                        <td>{name}</td>
                        <td class="global-id">{global_id}</td>
                    </tr>""")

            remaining = len(spec.failures) - 50
            if remaining > 0:
                failure_rows.append(f"""
                    <tr>
                        <td colspan="4" class="more-items">... and {remaining} more failures</td>
                    </tr>""")

            failure_rows_html = "\n".join(failure_rows)

            failure_sections.append(f"""
            <div class="failure-section">
                <h3 class="failure-title">Failed Entities: {_escape_html(spec.name)}</h3>
                <p class="failure-count">{spec.failed_count} failures</p>
                <table class="failure-table">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Type</th>
                            <th>Name</th>
                            <th>GlobalId</th>
                        </tr>
                    </thead>
                    <tbody>
                        {failure_rows_html}
                    </tbody>
                </table>
            </div>""")

    failure_details_html = "\n".join(failure_sections) if failure_sections else ""

    # IDS title section
    ids_title_html = f"<p><strong>Title:</strong> {_escape_html(result.ids_title)}</p>" if result.ids_title else ""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IFC-IDS Validation Report</title>
    <style>
        :root {{
            --pass-color: #28a745;
            --fail-color: #dc3545;
            --border-color: #dee2e6;
            --bg-light: #f8f9fa;
            --text-muted: #6c757d;
        }}

        * {{
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #fff;
            color: #333;
        }}

        h1, h2, h3 {{
            margin-top: 0;
        }}

        .summary-panel {{
            border: 3px solid var(--{overall_status_class}-color);
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 30px;
            background-color: var(--bg-light);
        }}

        .summary-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid var(--border-color);
        }}

        .overall-status {{
            font-size: 1.5em;
            font-weight: bold;
        }}

        .overall-status.pass {{
            color: var(--pass-color);
        }}

        .overall-status.fail {{
            color: var(--fail-color);
        }}

        .info-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
        }}

        .info-section {{
            background: #fff;
            padding: 15px;
            border-radius: 4px;
            border: 1px solid var(--border-color);
        }}

        .info-section h4 {{
            margin: 0 0 10px 0;
            color: #495057;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .info-section p {{
            margin: 5px 0;
        }}

        .stat {{
            font-size: 1.2em;
            font-weight: bold;
        }}

        .stat.pass {{
            color: var(--pass-color);
        }}

        .stat.fail {{
            color: var(--fail-color);
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }}

        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }}

        th {{
            background-color: var(--bg-light);
            font-weight: 600;
        }}

        .spec-table tr.pass td:first-child {{
            border-left: 4px solid var(--pass-color);
        }}

        .spec-table tr.fail td:first-child {{
            border-left: 4px solid var(--fail-color);
        }}

        .status {{
            font-weight: bold;
        }}

        .pass .status {{
            color: var(--pass-color);
        }}

        .fail .status {{
            color: var(--fail-color);
        }}

        .count {{
            text-align: right;
        }}

        .passed-count {{
            color: var(--pass-color);
        }}

        .failed-count {{
            color: var(--fail-color);
        }}

        .description {{
            color: var(--text-muted);
        }}

        .failure-section {{
            border: 2px solid var(--fail-color);
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
        }}

        .failure-title {{
            color: var(--fail-color);
            margin-bottom: 5px;
        }}

        .failure-count {{
            color: var(--text-muted);
            margin-top: 0;
            margin-bottom: 15px;
        }}

        .failure-table {{
            margin-bottom: 0;
        }}

        .global-id {{
            font-family: monospace;
            font-size: 0.9em;
            color: var(--text-muted);
        }}

        .more-items {{
            text-align: center;
            color: var(--text-muted);
            font-style: italic;
        }}

        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid var(--border-color);
            color: var(--text-muted);
            font-size: 0.9em;
        }}

        @media (max-width: 768px) {{
            .info-grid {{
                grid-template-columns: 1fr;
            }}

            table {{
                font-size: 0.9em;
            }}

            th, td {{
                padding: 8px;
            }}
        }}
    </style>
</head>
<body>
    <h1>IFC-IDS Validation Report</h1>

    <div class="summary-panel">
        <div class="summary-header">
            <h2>Validation Summary</h2>
            <span class="overall-status {overall_status_class}">{overall_status_text}</span>
        </div>

        <div class="info-grid">
            <div class="info-section">
                <h4>IFC Model</h4>
                <p><strong>File:</strong> {_escape_html(result.ifc_file)}</p>
                <p><strong>Schema:</strong> {_escape_html(result.ifc_schema)}</p>
                <p><strong>Entities:</strong> {result.ifc_entity_count:,}</p>
            </div>

            <div class="info-section">
                <h4>IDS Specification</h4>
                <p><strong>File:</strong> {_escape_html(result.ids_file)}</p>
                {ids_title_html}
            </div>

            <div class="info-section">
                <h4>Validation Results</h4>
                <p><strong>Time:</strong> {result.validation_time_seconds:.3f} seconds</p>
                <p><strong>Total Specifications:</strong> {result.total_specifications}</p>
                <p><strong>Passed:</strong> <span class="stat pass">{result.passed_specifications}</span></p>
                <p><strong>Failed:</strong> <span class="stat fail">{result.failed_specifications}</span></p>
                <p><strong>Pass Rate:</strong> <span class="stat {overall_status_class}">{result.pass_rate_percent:.1f}%</span></p>
            </div>
        </div>
    </div>

    <h2>Specification Results</h2>
    <table class="spec-table">
        <thead>
            <tr>
                <th>#</th>
                <th>Status</th>
                <th>Specification</th>
                <th class="count">Applicable</th>
                <th class="count">Passed</th>
                <th class="count">Failed</th>
            </tr>
        </thead>
        <tbody>
            {spec_rows_html}
        </tbody>
    </table>

    {f'<h2>Failed Entities Detail</h2>' + failure_details_html if failure_details_html else ''}

    <div class="footer">
        <p>Generated: {_escape_html(result.timestamp)}</p>
        <p>Report generated by ifc-validate CLI tool</p>
    </div>
</body>
</html>"""

    return html


def format_html(result: ValidationResult) -> str:
    """Format validation results as HTML string.

    This is a fallback method that generates HTML from ValidationResult.
    For best results, use format_html_from_ids() with the IDS file object.

    Args:
        result: ValidationResult from IFC-IDS validation

    Returns:
        HTML string with formatted validation results
    """
    return _generate_html_template(result)


def format_html_to_file(
    result: ValidationResult,
    output_path: Union[str, Path],
) -> Path:
    """Write validation results to an HTML file.

    This is a fallback method that generates HTML from ValidationResult.
    For best results, use format_html_from_ids_to_file() with the IDS file object.

    Args:
        result: ValidationResult from IFC-IDS validation
        output_path: Path to the output HTML file

    Returns:
        Path to the written file

    Raises:
        OSError: If the file cannot be written
    """
    path = Path(output_path)
    html_content = format_html(result)

    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(html_content, encoding="utf-8")
    return path


def print_html(result: ValidationResult) -> None:
    """Print validation results as HTML to stdout.

    Convenience function for CLI output.

    Args:
        result: ValidationResult from IFC-IDS validation
    """
    print(format_html(result))
