"""BCF 2.1 export module for IDS validation results.

Generates a BCF 2.1 .bcfzip from validation results. Each failed element
becomes one BCF topic with severity-mapped priority. The output is directly
importable in BIMcollab, Solibri, Navisworks, etc.

Only uses stdlib (zipfile + xml.etree.ElementTree) — no external dependencies.
"""

import io
import uuid
import zipfile
from datetime import datetime, timezone
from typing import Any
from xml.etree.ElementTree import Element, SubElement, tostring

# BCF 2.1 XML namespace
BCF_NS = "http://www.buildingsmart-tech.org/bcf/markup/3"
BCF_VERSION_NS = "http://www.buildingsmart-tech.org/bcf/version/2.1"

# Severity → BCF priority mapping
SEVERITY_TO_PRIORITY = {
    "error": "Critical",
    "warning": "Normal",
    "info": "Minor",
}

# BCF extension values
TOPIC_TYPES = ["IDS Validation"]
TOPIC_STATUSES = ["Open", "Closed"]
PRIORITIES = ["Critical", "Normal", "Minor"]


def _build_version_xml() -> bytes:
    """Build bcf.version XML content for BCF 2.1."""
    root = Element("Version", xmlns=BCF_VERSION_NS, VersionId="2.1")
    return b'<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(
        root, encoding="unicode"
    ).encode("utf-8")


def _build_extensions_xml() -> bytes:
    """Build extensions.xml with allowed values."""
    root = Element("Extensions", xmlns=BCF_NS)

    topic_types = SubElement(root, "TopicTypes")
    for tt in TOPIC_TYPES:
        SubElement(topic_types, "TopicType").text = tt

    topic_statuses = SubElement(root, "TopicStatuses")
    for ts in TOPIC_STATUSES:
        SubElement(topic_statuses, "TopicStatus").text = ts

    priorities_el = SubElement(root, "Priorities")
    for p in PRIORITIES:
        SubElement(priorities_el, "Priority").text = p

    return b'<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(
        root, encoding="unicode"
    ).encode("utf-8")


def _build_markup_xml(
    topic_guid: str,
    title: str,
    description: str,
    priority: str,
    labels: list[str],
    author: str,
    creation_date: str,
    comment_text: str,
) -> bytes:
    """Build markup.bcf XML for a single topic."""
    root = Element("Markup", xmlns=BCF_NS)

    # Topic element
    topic = SubElement(root, "Topic", Guid=topic_guid, TopicType="IDS Validation")
    SubElement(topic, "Title").text = title
    SubElement(topic, "Priority").text = priority
    SubElement(topic, "CreationDate").text = creation_date
    SubElement(topic, "CreationAuthor").text = author
    SubElement(topic, "Description").text = description
    SubElement(topic, "TopicStatus").text = "Open"

    for label in labels:
        SubElement(topic, "Labels").text = label

    # Comment
    comment = SubElement(root, "Comment", Guid=str(uuid.uuid4()))
    SubElement(comment, "Date").text = creation_date
    SubElement(comment, "Author").text = author
    SubElement(comment, "Comment").text = comment_text

    return b'<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(
        root, encoding="unicode"
    ).encode("utf-8")


def _truncate(text: str, max_length: int = 256) -> str:
    """Truncate text to max_length, adding ellipsis if needed."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def generate_bcf_zip(
    validation_result: dict[str, Any],
    author: str = "OpenAEC Validator",
) -> bytes:
    """Generate a BCF 2.1 .bcfzip from validation results.

    Iterates through specifications → requirements → elements and creates
    one BCF topic per failed element with severity-mapped priority.

    Args:
        validation_result: Dict with keys: specifications, ifc_file_name,
            ids_file_name, etc. (as returned by the validation endpoint).
        author: Author name for BCF topics.

    Returns:
        Bytes of the generated .bcfzip file.
    """
    creation_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ifc_name = validation_result.get("ifc_file_name", "unknown.ifc")
    ids_name = validation_result.get("ids_file_name", "unknown.ids")

    buf = io.BytesIO()

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # BCF version file
        zf.writestr("bcf.version", _build_version_xml())

        # Extensions
        zf.writestr("extensions.xml", _build_extensions_xml())

        # Create topics for each failed element
        specifications = validation_result.get("specifications", [])

        for spec in specifications:
            spec_name = spec.get("specification_name", "Unknown Specification")
            severity = spec.get("severity", "error")
            priority = SEVERITY_TO_PRIORITY.get(severity, "Normal")
            requirements = spec.get("requirements", [])

            for req in requirements:
                req_desc = req.get(
                    "requirement_description", "Requirement"
                )
                elements = req.get("elements", [])

                for element in elements:
                    if element.get("status") != "fail":
                        continue

                    el_type = element.get("element_type", "Unknown")
                    el_name = element.get("element_name") or "Unnamed"
                    global_id = element.get("global_id", "")

                    # Build topic content
                    topic_guid = str(uuid.uuid4())

                    title = _truncate(
                        f"{el_type}: {el_name} — {spec_name}"
                    )

                    description_parts = [
                        f"Requirement: {req_desc}",
                        f"IFC: {ifc_name}",
                        f"IDS: {ids_name}",
                    ]
                    if global_id:
                        description_parts.append(f"GlobalId: {global_id}")
                    description = "\n".join(description_parts)

                    # Comment with failure details
                    messages = element.get("messages", [])
                    comment_parts = [
                        f"Element '{el_name}' ({el_type}) failed "
                        f"requirement: {req_desc}",
                    ]
                    if global_id:
                        comment_parts.append(f"GlobalId: {global_id}")
                    if messages:
                        comment_parts.append(
                            "Details: " + "; ".join(messages)
                        )
                    comment_text = "\n".join(comment_parts)

                    markup = _build_markup_xml(
                        topic_guid=topic_guid,
                        title=title,
                        description=description,
                        priority=priority,
                        labels=[spec_name],
                        author=author,
                        creation_date=creation_date,
                        comment_text=comment_text,
                    )

                    zf.writestr(f"{topic_guid}/markup.bcf", markup)

    return buf.getvalue()
