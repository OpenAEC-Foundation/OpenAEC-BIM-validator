"""Live Link reference feeder.

Streams the contents of an IFC file to the viewer over the Live Link
WebSocket protocol (see ``docs/LIVE_LINK_PROTOCOL.md``). The feeder:

* loads an IFC file with ifcopenshell + ifcopenshell.geom (world
  coordinates, triangulated meshes),
* serves the protocol on a localhost-only WebSocket (127.0.0.1 and [::1],
  port 19790 by default) with an HTTP health probe on the same port,
* watches the file on disk (mtime polling every 2 s) and re-streams only
  the elements whose content hash changed (``element-update`` messages).

Usage::

    python tools/livelink/feeder.py path/to/model.ifc [--port 19790]

Requires the ``websockets`` package for serving (``pip install websockets``)
and ``ifcopenshell`` for IFC loading. The pure protocol helpers in this
module (hashing, encoding, message building) have no third-party
dependencies so they can be unit-tested standalone.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import logging
import os
import struct
import sys
from http import HTTPStatus
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urlsplit

PROTOCOL_VERSION = "1.0"
APP_VERSION = "0.1.0"
FEEDER_NAME = "openaec-livelink-feeder"

DEFAULT_PORT = 19790
DEFAULT_BATCH_SIZE = 100
DEFAULT_POLL_INTERVAL = 2.0
DEFAULT_COLOR = (0.65, 0.65, 0.65, 1.0)

LOOPBACK_HOSTNAMES = {"localhost", "127.0.0.1", "::1", "[::1]"}

logger = logging.getLogger("livelink.feeder")


# ---------------------------------------------------------------------------
# Pure helpers: encoding, hashing, geometry conversion, message building.
# These functions have no side effects and no third-party dependencies.
# ---------------------------------------------------------------------------


def pack_float32(values: Sequence[float]) -> bytes:
    """Pack a flat sequence of floats as little-endian Float32 bytes."""
    return struct.pack(f"<{len(values)}f", *values)


def pack_uint32(values: Sequence[int]) -> bytes:
    """Pack a flat sequence of ints as little-endian Uint32 bytes."""
    return struct.pack(f"<{len(values)}I", *values)


def encode_base64(raw: bytes) -> str:
    """Encode raw bytes as an ASCII base64 string for JSON transport."""
    return base64.b64encode(raw).decode("ascii")


def canonical_json(data: Any) -> str:
    """Serialize data as canonical JSON: sorted keys, no whitespace."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def compute_content_hash(
    positions: bytes,
    indices: bytes,
    normals: bytes = b"",
    properties: Optional[Dict[str, Any]] = None,
) -> str:
    """Compute the per-element content hash defined by the protocol.

    The hash is SHA-256 over the raw little-endian geometry bytes
    (positions, indices, normals) concatenated with the canonical JSON of
    the element properties, truncated to the first 8 bytes and rendered as
    16 lowercase hex characters.

    Args:
        positions: Raw Float32 position bytes.
        indices: Raw Uint32 index bytes.
        normals: Raw Float32 normal bytes (empty if not sent).
        properties: Element property sets (``parameters`` on the wire).

    Returns:
        A 16-character lowercase hex string.
    """
    digest = hashlib.sha256()
    digest.update(positions)
    digest.update(indices)
    digest.update(normals)
    digest.update(canonical_json(properties or {}).encode("utf-8"))
    return digest.hexdigest()[:16]


def convert_zup_to_yup(vertices: Sequence[float]) -> List[float]:
    """Convert a flat XYZ vertex list from IFC Z-up to viewer Y-up.

    Applies the proper rotation ``(x, y, z) -> (x, z, -y)`` per vertex,
    which preserves triangle winding order.
    """
    if len(vertices) % 3 != 0:
        raise ValueError("vertex list length must be a multiple of 3")
    out: List[float] = [0.0] * len(vertices)
    for i in range(0, len(vertices), 3):
        out[i] = vertices[i]
        out[i + 1] = vertices[i + 2]
        out[i + 2] = -vertices[i + 1]
    return out


def build_material_groups(
    faces: Sequence[int],
    material_ids: Sequence[int],
    colors: Sequence[Tuple[float, float, float, float]],
    default_color: Tuple[float, float, float, float] = DEFAULT_COLOR,
) -> Tuple[List[int], Optional[List[Dict[str, Any]]], List[float]]:
    """Reorder triangles by material and build per-material draw groups.

    Triangles are regrouped so each material occupies one contiguous index
    range; opaque groups are emitted before transparent ones so the viewer
    renders transparency correctly.

    Args:
        faces: Flat triangle index list (3 indices per triangle).
        material_ids: One material index per triangle (-1 = no material).
        colors: RGBA color per material index, values in 0-1.
        default_color: Color used for triangles without a material.

    Returns:
        Tuple of (reordered flat index list, draw groups or None if a
        single material suffices, flat element color).
    """
    triangle_count = len(faces) // 3
    if len(material_ids) not in (0, triangle_count):
        raise ValueError("material_ids length must match triangle count")

    def color_for(mat_id: int) -> Tuple[float, float, float, float]:
        if 0 <= mat_id < len(colors):
            return tuple(colors[mat_id])  # type: ignore[return-value]
        return default_color

    if not material_ids:
        return list(faces), None, list(default_color)

    used = sorted(set(material_ids))
    if len(used) <= 1:
        return list(faces), None, list(color_for(used[0]))

    # Sort material ids: opaque (alpha == 1) first, then transparent.
    ordered = sorted(used, key=lambda m: (color_for(m)[3] < 1.0, m))

    reordered: List[int] = []
    groups: List[Dict[str, Any]] = []
    for mat_id in ordered:
        start = len(reordered)
        for tri in range(triangle_count):
            if material_ids[tri] == mat_id:
                reordered.extend(faces[tri * 3 : tri * 3 + 3])
        count = len(reordered) - start
        if count:
            groups.append(
                {"start": start, "count": count, "color": list(color_for(mat_id))}
            )
    return reordered, groups, list(color_for(ordered[0]))


def build_geometry_payload(
    positions: Sequence[float],
    indices: Sequence[int],
    normals: Sequence[float] = (),
    color: Sequence[float] = DEFAULT_COLOR,
    groups: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[Dict[str, Any], bytes, bytes, bytes]:
    """Build the wire ``geometry`` object plus the raw bytes for hashing.

    Returns:
        Tuple of (geometry dict, position bytes, index bytes, normal bytes).
    """
    pos_bytes = pack_float32(positions)
    idx_bytes = pack_uint32(indices)
    nrm_bytes = pack_float32(normals) if normals else b""
    geometry: Dict[str, Any] = {
        "positions": encode_base64(pos_bytes),
        "indices": encode_base64(idx_bytes),
        "color": list(color),
    }
    if nrm_bytes:
        geometry["normals"] = encode_base64(nrm_bytes)
    if groups:
        geometry["groups"] = groups
    return geometry, pos_bytes, idx_bytes, nrm_bytes


# --- Message builders -------------------------------------------------------


def build_pong(document_name: Optional[str] = None) -> Dict[str, Any]:
    """Build the ``pong`` handshake reply."""
    message: Dict[str, Any] = {
        "type": "pong",
        "version": PROTOCOL_VERSION,
        "feederVersion": APP_VERSION,
    }
    if document_name:
        message["documentName"] = document_name
    return message


def build_health_payload() -> Dict[str, Any]:
    """Build the JSON body for the HTTP health probe."""
    return {
        "name": FEEDER_NAME,
        "protocolVersion": PROTOCOL_VERSION,
        "appVersion": APP_VERSION,
    }


def build_export_start(total_models: int, total_elements: int) -> Dict[str, Any]:
    """Build the ``export-start`` message."""
    return {
        "type": "export-start",
        "totalModels": total_models,
        "totalElements": total_elements,
    }


def build_model_start(name: str, element_count: int) -> Dict[str, Any]:
    """Build the ``model-start`` message."""
    return {"type": "model-start", "name": name, "elementCount": element_count}


def build_element_batches(
    elements: Sequence[Dict[str, Any]], batch_size: int = DEFAULT_BATCH_SIZE
) -> List[Dict[str, Any]]:
    """Chunk elements into ``element-batch`` messages.

    Args:
        elements: Wire-format element dicts.
        batch_size: Maximum number of elements per batch (must be >= 1).

    Returns:
        A list of ``element-batch`` messages with ``batchIndex`` and
        ``totalBatches`` set. Empty input yields an empty list.
    """
    if batch_size < 1:
        raise ValueError("batch_size must be >= 1")
    chunks = [
        list(elements[i : i + batch_size]) for i in range(0, len(elements), batch_size)
    ]
    total = len(chunks)
    return [
        {
            "type": "element-batch",
            "batchIndex": index,
            "totalBatches": total,
            "elements": chunk,
        }
        for index, chunk in enumerate(chunks)
    ]


def build_model_end(
    storeys: Optional[List[str]] = None,
    storey_data: Optional[List[Dict[str, Any]]] = None,
    element_hashes: Optional[Dict[str, str]] = None,
    unchanged: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Build the ``model-end`` message."""
    message: Dict[str, Any] = {"type": "model-end"}
    if storeys:
        message["storeys"] = storeys
    if storey_data:
        message["storeyData"] = storey_data
    if element_hashes is not None:
        message["elementHashes"] = element_hashes
    if unchanged is not None:
        message["unchanged"] = unchanged
    return message


def build_export_end() -> Dict[str, Any]:
    """Build the ``export-end`` message."""
    return {"type": "export-end"}


def build_element_update_modified(
    elements: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build an ``element-update`` message with action ``modified``."""
    return {"type": "element-update", "action": "modified", "elements": list(elements)}


def build_element_update_deleted(global_ids: Sequence[str]) -> Dict[str, Any]:
    """Build an ``element-update`` message with action ``deleted``."""
    return {
        "type": "element-update",
        "action": "deleted",
        "globalIds": list(global_ids),
    }


def build_error(message: str) -> Dict[str, Any]:
    """Build a generic ``error`` message."""
    return {"type": "error", "message": message}


def diff_elements(
    current_hashes: Dict[str, str], known_hashes: Dict[str, str]
) -> Tuple[List[str], List[str], List[str]]:
    """Diff the current element hashes against a client's known hashes.

    Args:
        current_hashes: ``globalId -> contentHash`` for the current model.
        known_hashes: ``globalId -> contentHash`` the client already has.

    Returns:
        Tuple of (changed_or_new ids, unchanged ids, deleted ids), each
        sorted for deterministic output.
    """
    changed = [
        gid
        for gid, h in current_hashes.items()
        if known_hashes.get(gid) != h
    ]
    unchanged = [
        gid for gid, h in current_hashes.items() if known_hashes.get(gid) == h
    ]
    deleted = [gid for gid in known_hashes if gid not in current_hashes]
    return sorted(changed), sorted(unchanged), sorted(deleted)


def is_origin_allowed(
    origin: Optional[str], extra_allowed: Iterable[str] = ()
) -> bool:
    """Check a WebSocket ``Origin`` header against the allowlist.

    Allowed: no header (non-browser clients), the literal ``"null"``
    (pages opened from ``file://``), any loopback origin regardless of
    port, and any origin listed in ``extra_allowed`` (exact match).
    """
    if origin is None or origin == "null":
        return True
    if origin in extra_allowed:
        return True
    try:
        hostname = urlsplit(origin).hostname
    except ValueError:
        return False
    return hostname is not None and hostname.lower() in LOOPBACK_HOSTNAMES


# ---------------------------------------------------------------------------
# IFC extraction (requires ifcopenshell).
# ---------------------------------------------------------------------------

#: IFC classes that are never shown in 3D and must not be streamed.
SKIP_IFC_CLASSES = (
    "IfcSpace",
    "IfcOpeningElement",
    "IfcGrid",
    "IfcAnnotation",
    "IfcVirtualElement",
)


def _material_color(material: Any) -> Tuple[float, float, float, float]:
    """Extract an RGBA color from an ifcopenshell style, with fallback."""
    try:
        diffuse = material.diffuse
        rgb = (float(diffuse[0]), float(diffuse[1]), float(diffuse[2]))
        transparency = getattr(material, "transparency", 0.0) or 0.0
        if transparency != transparency:  # NaN guard
            transparency = 0.0
        alpha = max(0.0, min(1.0, 1.0 - float(transparency)))
        return (rgb[0], rgb[1], rgb[2], alpha)
    except (AttributeError, IndexError, TypeError, ValueError):
        return DEFAULT_COLOR


def extract_elements(ifc_path: str) -> Dict[str, Any]:
    """Load an IFC file and build wire-format elements plus content hashes.

    Uses ifcopenshell.geom with world coordinates and triangulation, and
    converts Z-up meters to the protocol's Y-up meters.

    Args:
        ifc_path: Path to the IFC file on disk.

    Returns:
        Dict with keys:
            ``elements``: ``globalId -> wire element dict``.
            ``hashes``: ``globalId -> content hash``.
            ``storeys``: ordered storey names.
            ``storey_data``: ``[{name, elevation}]`` (elevation in meters).
            ``document_name``: file name of the model.
    """
    try:
        import ifcopenshell
        import ifcopenshell.geom
        import ifcopenshell.util.element
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise SystemExit(
            "The 'ifcopenshell' package is required to load IFC files.\n"
            "Install it with:  pip install ifcopenshell"
        ) from exc

    model = ifcopenshell.open(ifc_path)

    settings = ifcopenshell.geom.settings()
    try:  # ifcopenshell >= 0.8 string-based settings
        settings.set("use-world-coords", True)
        settings.set("weld-vertices", True)
    except Exception:  # pragma: no cover - legacy API fallback
        settings.set(settings.USE_WORLD_COORDS, True)
        settings.set(settings.WELD_VERTICES, True)

    # Length-unit scale: ifcopenshell.geom outputs meters by default, but
    # storey elevations from attributes are in project units.
    try:
        import ifcopenshell.util.unit

        unit_scale = float(ifcopenshell.util.unit.calculate_unit_scale(model))
    except Exception:
        unit_scale = 1.0

    elements: Dict[str, Dict[str, Any]] = {}
    hashes: Dict[str, str] = {}

    products = [
        product
        for product in model.by_type("IfcProduct")
        if product.Representation is not None
        and not product.is_a("IfcSpatialStructureElement")
        and not any(product.is_a(cls) for cls in SKIP_IFC_CLASSES)
    ]

    for product in products:
        global_id = getattr(product, "GlobalId", None)
        if not global_id:
            continue
        try:
            shape = ifcopenshell.geom.create_shape(settings, product)
        except Exception as exc:
            logger.warning("Geometry failed for %s: %s", global_id, exc)
            continue

        geometry = shape.geometry
        verts = list(geometry.verts)
        faces = list(geometry.faces)
        if not verts or not faces:
            continue

        positions = convert_zup_to_yup(verts)
        raw_normals = list(getattr(geometry, "normals", ()) or ())
        normals = convert_zup_to_yup(raw_normals) if raw_normals else []

        material_ids = list(getattr(geometry, "material_ids", ()) or ())
        colors = [_material_color(m) for m in getattr(geometry, "materials", ())]
        indices, groups, flat_color = build_material_groups(
            faces, material_ids, colors
        )

        # Properties and quantities.
        try:
            psets = ifcopenshell.util.element.get_psets(product, psets_only=True)
        except Exception:
            psets = {}
        try:
            qsets = ifcopenshell.util.element.get_psets(product, qtos_only=True)
        except Exception:
            qsets = {}
        quantities: Dict[str, float] = {}
        for qset in qsets.values():
            for key in ("Length", "Area", "Volume", "Width", "Height", "Thickness"):
                for qname, qvalue in qset.items():
                    if key.lower() in qname.lower() and isinstance(
                        qvalue, (int, float)
                    ):
                        quantities.setdefault(key, float(qvalue))

        # Containing storey.
        level = None
        try:
            container = ifcopenshell.util.element.get_container(product)
            if container is not None:
                level = getattr(container, "Name", None)
        except Exception:
            pass

        # Materials by name.
        material_names: List[str] = []
        try:
            material = ifcopenshell.util.element.get_material(product)
            if material is not None:
                name = getattr(material, "Name", None)
                if name:
                    material_names.append(name)
        except Exception:
            pass

        geometry_payload, pos_bytes, idx_bytes, nrm_bytes = build_geometry_payload(
            positions, indices, normals, flat_color, groups
        )
        content_hash = compute_content_hash(pos_bytes, idx_bytes, nrm_bytes, psets)

        element: Dict[str, Any] = {
            "globalId": global_id,
            "name": getattr(product, "Name", None) or "",
            "category": product.is_a(),
            "geometry": geometry_payload,
        }
        object_type = getattr(product, "ObjectType", None)
        if object_type:
            element["type"] = object_type
        if level:
            element["level"] = level
        if material_names:
            element["materials"] = material_names
        if psets:
            element["parameters"] = psets
        if quantities:
            element["quantities"] = quantities

        elements[global_id] = element
        hashes[global_id] = content_hash

    # Storeys, ordered by elevation.
    storey_data: List[Dict[str, Any]] = []
    for storey in model.by_type("IfcBuildingStorey"):
        elevation = getattr(storey, "Elevation", None)
        storey_data.append(
            {
                "name": getattr(storey, "Name", None) or "",
                "elevation": float(elevation) * unit_scale
                if elevation is not None
                else 0.0,
            }
        )
    storey_data.sort(key=lambda s: s["elevation"])

    return {
        "elements": elements,
        "hashes": hashes,
        "storeys": [s["name"] for s in storey_data],
        "storey_data": storey_data,
        "document_name": os.path.basename(ifc_path),
    }


# ---------------------------------------------------------------------------
# WebSocket server.
# ---------------------------------------------------------------------------


class FeederState:
    """Mutable server state: current model snapshot and connected clients."""

    def __init__(self, ifc_path: str, batch_size: int, extra_origins: Tuple[str, ...]):
        self.ifc_path = ifc_path
        self.batch_size = batch_size
        self.extra_origins = extra_origins
        self.snapshot: Dict[str, Any] = {
            "elements": {},
            "hashes": {},
            "storeys": [],
            "storey_data": [],
            "document_name": os.path.basename(ifc_path),
        }
        self.mtime: Optional[float] = None
        self.clients: set = set()

    def reload(self) -> None:
        """(Re)load the IFC file into the snapshot. Blocking; run off-loop."""
        self.snapshot = extract_elements(self.ifc_path)


async def _send(websocket: Any, message: Dict[str, Any]) -> None:
    await websocket.send(json.dumps(message))


async def stream_export(
    websocket: Any, state: FeederState, known_elements: Dict[str, str]
) -> None:
    """Stream a full or delta export sequence to one client."""
    snapshot = state.snapshot
    hashes: Dict[str, str] = snapshot["hashes"]
    changed, unchanged, _deleted = diff_elements(hashes, known_elements)

    await _send(websocket, build_export_start(1, len(hashes)))
    await _send(
        websocket,
        build_model_start(snapshot["document_name"], len(hashes)),
    )
    elements = [snapshot["elements"][gid] for gid in changed]
    for batch in build_element_batches(elements, state.batch_size):
        await _send(websocket, batch)
    await _send(
        websocket,
        build_model_end(
            storeys=snapshot["storeys"],
            storey_data=snapshot["storey_data"],
            element_hashes=hashes,
            unchanged=unchanged,
        ),
    )
    await _send(websocket, build_export_end())


async def handle_client(websocket: Any, state: FeederState) -> None:
    """Handle one viewer connection: ping/pong handshake and export requests."""
    state.clients.add(websocket)
    export_task: Optional[asyncio.Task] = None
    try:
        async for raw in websocket:
            try:
                message = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                await _send(websocket, build_error("Invalid JSON message"))
                continue
            msg_type = message.get("type")
            if msg_type == "ping":
                await _send(
                    websocket, build_pong(state.snapshot["document_name"])
                )
            elif msg_type == "export":
                known = message.get("knownElements") or {}
                if export_task and not export_task.done():
                    export_task.cancel()
                export_task = asyncio.ensure_future(
                    stream_export(websocket, state, known)
                )
            elif msg_type == "cancel-export":
                if export_task and not export_task.done():
                    export_task.cancel()
            else:
                logger.debug("Ignoring unknown message type: %r", msg_type)
    finally:
        if export_task and not export_task.done():
            export_task.cancel()
        state.clients.discard(websocket)


async def broadcast(state: FeederState, message: Dict[str, Any]) -> None:
    """Send a message to all connected clients, dropping dead sockets."""
    payload = json.dumps(message)
    for websocket in list(state.clients):
        try:
            await websocket.send(payload)
        except Exception:
            state.clients.discard(websocket)


async def watch_file(state: FeederState, poll_interval: float) -> None:
    """Poll the IFC file's mtime and broadcast deltas when it changes."""
    while True:
        await asyncio.sleep(poll_interval)
        try:
            mtime = os.path.getmtime(state.ifc_path)
        except OSError:
            continue  # File temporarily missing (e.g. mid-save).
        if state.mtime is not None and mtime == state.mtime:
            continue
        previous_hashes = dict(state.snapshot["hashes"])
        first_load = state.mtime is None
        state.mtime = mtime
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, state.reload)
        except SystemExit:
            raise
        except Exception as exc:
            logger.warning("Reload failed (file mid-write?): %s", exc)
            state.mtime = None  # Force retry on the next poll.
            continue
        if first_load:
            logger.info(
                "Loaded %s: %d elements",
                state.snapshot["document_name"],
                len(state.snapshot["hashes"]),
            )
            continue
        changed, _unchanged, deleted = diff_elements(
            state.snapshot["hashes"], previous_hashes
        )
        logger.info(
            "File changed: %d modified/new, %d deleted", len(changed), len(deleted)
        )
        if changed:
            elements = [state.snapshot["elements"][gid] for gid in changed]
            for chunk_start in range(0, len(elements), state.batch_size):
                await broadcast(
                    state,
                    build_element_update_modified(
                        elements[chunk_start : chunk_start + state.batch_size]
                    ),
                )
        if deleted:
            await broadcast(state, build_element_update_deleted(deleted))


def _import_websockets() -> Any:
    """Import the websockets server API with a helpful error message."""
    try:
        from websockets.asyncio.server import serve
    except ImportError as exc:
        raise SystemExit(
            "The 'websockets' package is required to run the Live Link "
            "feeder.\nInstall it with:  pip install websockets"
        ) from exc
    return serve


async def run_server(
    ifc_path: str,
    port: int = DEFAULT_PORT,
    batch_size: int = DEFAULT_BATCH_SIZE,
    poll_interval: float = DEFAULT_POLL_INTERVAL,
    extra_origins: Tuple[str, ...] = (),
) -> None:
    """Run the Live Link feeder server until cancelled."""
    serve = _import_websockets()
    state = FeederState(ifc_path, batch_size, extra_origins)

    logger.info("Loading %s ...", ifc_path)
    state.mtime = os.path.getmtime(ifc_path)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, state.reload)
    logger.info(
        "Loaded %s: %d elements",
        state.snapshot["document_name"],
        len(state.snapshot["hashes"]),
    )

    def process_request(connection: Any, request: Any) -> Any:
        upgrade = request.headers.get("Upgrade", "")
        if upgrade.lower() != "websocket":
            # HTTP health probe: 200 + version JSON on any plain GET.
            response = connection.respond(
                HTTPStatus.OK, json.dumps(build_health_payload())
            )
            response.headers["Content-Type"] = "application/json"
            return response
        origin = request.headers.get("Origin")
        if not is_origin_allowed(origin, state.extra_origins):
            logger.warning("Rejected connection from origin %r", origin)
            return connection.respond(HTTPStatus.FORBIDDEN, "Forbidden origin\n")
        return None  # Continue with the WebSocket upgrade.

    async def handler(websocket: Any) -> None:
        await handle_client(websocket, state)

    hosts = ["127.0.0.1", "::1"]
    try:
        server = await serve(
            handler, hosts, port, process_request=process_request, max_size=None
        )
    except OSError:
        logger.warning("Dual-loopback bind failed; falling back to 127.0.0.1 only")
        server = await serve(
            handler,
            "127.0.0.1",
            port,
            process_request=process_request,
            max_size=None,
        )

    logger.info(
        "Live Link feeder listening on ws://127.0.0.1:%d and ws://[::1]:%d "
        "(protocol %s, app %s)",
        port,
        port,
        PROTOCOL_VERSION,
        APP_VERSION,
    )
    watcher = asyncio.ensure_future(watch_file(state, poll_interval))
    try:
        await asyncio.Future()  # Run forever.
    finally:
        watcher.cancel()
        server.close()
        await server.wait_closed()


def main(argv: Optional[Sequence[str]] = None) -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Live Link reference feeder: stream an IFC file to the "
        "viewer over the Live Link WebSocket protocol."
    )
    parser.add_argument("ifc_path", help="Path to the IFC file to stream")
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT, help="Port (default 19790)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Elements per element-batch message (default 100)",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=DEFAULT_POLL_INTERVAL,
        help="File mtime poll interval in seconds (default 2)",
    )
    parser.add_argument(
        "--allow-origin",
        action="append",
        default=[],
        metavar="ORIGIN",
        help="Extra allowed Origin (repeatable); loopback origins, 'null' "
        "and non-browser clients are always allowed",
    )
    parser.add_argument("--verbose", action="store_true", help="Debug logging")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if not os.path.isfile(args.ifc_path):
        raise SystemExit(f"IFC file not found: {args.ifc_path}")

    try:
        asyncio.run(
            run_server(
                args.ifc_path,
                port=args.port,
                batch_size=args.batch_size,
                poll_interval=args.poll_interval,
                extra_origins=tuple(args.allow_origin),
            )
        )
    except KeyboardInterrupt:
        logger.info("Stopped.")


if __name__ == "__main__":
    main()
