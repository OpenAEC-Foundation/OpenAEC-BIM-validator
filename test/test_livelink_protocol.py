"""Unit tests for the Live Link feeder's pure protocol helpers.

Covers the content-hash function, geometry encoding, coordinate
conversion, material grouping and message building. No live WebSocket or
IFC file is required.

Run with:
    python -m pytest test/test_livelink_protocol.py -q -o addopts=""
"""

import base64
import re
import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.livelink.feeder import (  # noqa: E402
    APP_VERSION,
    PROTOCOL_VERSION,
    build_element_batches,
    build_element_update_deleted,
    build_element_update_modified,
    build_error,
    build_export_end,
    build_export_start,
    build_geometry_payload,
    build_health_payload,
    build_material_groups,
    build_model_end,
    build_model_start,
    build_pong,
    compute_content_hash,
    convert_zup_to_yup,
    diff_elements,
    encode_base64,
    is_origin_allowed,
    pack_float32,
    pack_uint32,
)

POSITIONS = pack_float32([0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0])
INDICES = pack_uint32([0, 1, 2])
NORMALS = pack_float32([0.0, 1.0, 0.0] * 3)


class TestPacking:
    def test_pack_float32_little_endian(self):
        assert pack_float32([1.0]) == struct.pack("<f", 1.0)

    def test_pack_uint32_little_endian(self):
        assert pack_uint32([7]) == struct.pack("<I", 7)

    def test_encode_base64_roundtrip(self):
        raw = pack_float32([1.5, -2.25, 3.0])
        assert base64.b64decode(encode_base64(raw)) == raw


class TestContentHash:
    def test_is_16_lowercase_hex_chars(self):
        result = compute_content_hash(POSITIONS, INDICES, NORMALS, {"a": 1})
        assert re.fullmatch(r"[0-9a-f]{16}", result)

    def test_deterministic(self):
        args = (POSITIONS, INDICES, NORMALS, {"Pset": {"FireRating": "REI60"}})
        assert compute_content_hash(*args) == compute_content_hash(*args)

    def test_changes_when_geometry_changes(self):
        base = compute_content_hash(POSITIONS, INDICES, NORMALS, {})
        moved = pack_float32([0.0, 0.0, 0.1, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0])
        assert compute_content_hash(moved, INDICES, NORMALS, {}) != base

    def test_changes_when_properties_change(self):
        props_a = {"Pset_WallCommon": {"FireRating": "REI60"}}
        props_b = {"Pset_WallCommon": {"FireRating": "REI90"}}
        hash_a = compute_content_hash(POSITIONS, INDICES, NORMALS, props_a)
        hash_b = compute_content_hash(POSITIONS, INDICES, NORMALS, props_b)
        assert hash_a != hash_b

    def test_property_key_order_is_irrelevant(self):
        props_a = {"B": 2, "A": 1}
        props_b = {"A": 1, "B": 2}
        hash_a = compute_content_hash(POSITIONS, INDICES, b"", props_a)
        hash_b = compute_content_hash(POSITIONS, INDICES, b"", props_b)
        assert hash_a == hash_b

    def test_empty_normals_and_none_properties(self):
        result = compute_content_hash(POSITIONS, INDICES)
        assert result == compute_content_hash(POSITIONS, INDICES, b"", {})


class TestCoordinateConversion:
    def test_zup_to_yup_mapping(self):
        # IFC (x=1, y=2, z=3) -> viewer (x=1, y=3, z=-2)
        assert convert_zup_to_yup([1.0, 2.0, 3.0]) == [1.0, 3.0, -2.0]

    def test_multiple_vertices(self):
        result = convert_zup_to_yup([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        assert result == [1.0, 3.0, -2.0, 4.0, 6.0, -5.0]

    def test_rejects_non_multiple_of_three(self):
        with pytest.raises(ValueError):
            convert_zup_to_yup([1.0, 2.0])


class TestMaterialGroups:
    FACES = [0, 1, 2, 3, 4, 5, 6, 7, 8]  # three triangles

    def test_no_material_ids_gives_flat_color(self):
        indices, groups, color = build_material_groups(self.FACES, [], [])
        assert indices == self.FACES
        assert groups is None
        assert color == [0.65, 0.65, 0.65, 1.0]

    def test_single_material_gives_flat_color(self):
        red = (1.0, 0.0, 0.0, 1.0)
        indices, groups, color = build_material_groups(
            self.FACES, [0, 0, 0], [red]
        )
        assert indices == self.FACES
        assert groups is None
        assert color == list(red)

    def test_multi_material_builds_contiguous_groups(self):
        opaque = (1.0, 0.0, 0.0, 1.0)
        glass = (0.6, 0.8, 1.0, 0.15)
        indices, groups, _ = build_material_groups(
            self.FACES, [1, 0, 1], [opaque, glass]
        )
        assert groups is not None
        assert len(groups) == 2
        # Opaque group first, then transparent.
        assert groups[0]["color"][3] == 1.0
        assert groups[1]["color"][3] < 1.0
        # Groups tile the index buffer contiguously.
        assert groups[0]["start"] == 0
        assert groups[1]["start"] == groups[0]["count"]
        assert groups[0]["count"] + groups[1]["count"] == len(self.FACES)
        # Triangle 1 (material 0 = opaque) is emitted first.
        assert indices == [3, 4, 5, 0, 1, 2, 6, 7, 8]

    def test_length_mismatch_raises(self):
        with pytest.raises(ValueError):
            build_material_groups(self.FACES, [0, 0], [])


class TestGeometryPayload:
    def test_payload_encodes_arrays(self):
        positions = [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0]
        indices = [0, 1, 2]
        normals = [0.0, 1.0, 0.0] * 3
        payload, pos_bytes, idx_bytes, nrm_bytes = build_geometry_payload(
            positions, indices, normals
        )
        assert base64.b64decode(payload["positions"]) == pack_float32(positions)
        assert base64.b64decode(payload["indices"]) == pack_uint32(indices)
        assert base64.b64decode(payload["normals"]) == pack_float32(normals)
        assert pos_bytes == pack_float32(positions)
        assert idx_bytes == pack_uint32(indices)
        assert nrm_bytes == pack_float32(normals)

    def test_normals_omitted_when_absent(self):
        payload, _, _, nrm_bytes = build_geometry_payload([0.0] * 9, [0, 1, 2])
        assert "normals" not in payload
        assert nrm_bytes == b""

    def test_groups_included_when_given(self):
        groups = [{"start": 0, "count": 3, "color": [1, 0, 0, 1]}]
        payload, _, _, _ = build_geometry_payload(
            [0.0] * 9, [0, 1, 2], groups=groups
        )
        assert payload["groups"] == groups


class TestMessageBuilders:
    def test_pong_carries_separate_protocol_and_app_versions(self):
        message = build_pong("model.ifc")
        assert message["type"] == "pong"
        assert message["version"] == PROTOCOL_VERSION
        assert message["feederVersion"] == APP_VERSION
        assert message["documentName"] == "model.ifc"
        # Protocol version is semver major.minor.
        assert re.fullmatch(r"\d+\.\d+", message["version"])

    def test_pong_without_document_name(self):
        assert "documentName" not in build_pong()

    def test_health_payload(self):
        payload = build_health_payload()
        assert payload["protocolVersion"] == PROTOCOL_VERSION
        assert payload["appVersion"] == APP_VERSION
        assert payload["name"]

    def test_export_start(self):
        message = build_export_start(1, 42)
        assert message == {
            "type": "export-start",
            "totalModels": 1,
            "totalElements": 42,
        }

    def test_model_start(self):
        message = build_model_start("model.ifc", 42)
        assert message == {
            "type": "model-start",
            "name": "model.ifc",
            "elementCount": 42,
        }

    def test_model_end_fields(self):
        message = build_model_end(
            storeys=["L1"],
            storey_data=[{"name": "L1", "elevation": 0.0}],
            element_hashes={"gid": "abc"},
            unchanged=["gid2"],
        )
        assert message["type"] == "model-end"
        assert message["storeys"] == ["L1"]
        assert message["elementHashes"] == {"gid": "abc"}
        assert message["unchanged"] == ["gid2"]

    def test_export_end(self):
        assert build_export_end() == {"type": "export-end"}

    def test_element_update_modified(self):
        elements = [{"globalId": "g1"}]
        message = build_element_update_modified(elements)
        assert message["type"] == "element-update"
        assert message["action"] == "modified"
        assert message["elements"] == elements

    def test_element_update_deleted(self):
        message = build_element_update_deleted(["g1", "g2"])
        assert message["action"] == "deleted"
        assert message["globalIds"] == ["g1", "g2"]

    def test_error(self):
        assert build_error("boom") == {"type": "error", "message": "boom"}


class TestElementBatching:
    def test_chunks_with_index_and_total(self):
        elements = [{"globalId": str(i)} for i in range(5)]
        batches = build_element_batches(elements, batch_size=2)
        assert len(batches) == 3
        assert [b["batchIndex"] for b in batches] == [0, 1, 2]
        assert all(b["totalBatches"] == 3 for b in batches)
        assert all(b["type"] == "element-batch" for b in batches)
        assert [len(b["elements"]) for b in batches] == [2, 2, 1]
        flattened = [e for b in batches for e in b["elements"]]
        assert flattened == elements

    def test_empty_input_gives_no_batches(self):
        assert build_element_batches([], batch_size=10) == []

    def test_invalid_batch_size(self):
        with pytest.raises(ValueError):
            build_element_batches([{"globalId": "g"}], batch_size=0)


class TestDiffElements:
    def test_full_diff(self):
        current = {"a": "h1", "b": "h2-new", "c": "h3"}
        known = {"a": "h1", "b": "h2-old", "d": "h4"}
        changed, unchanged, deleted = diff_elements(current, known)
        assert changed == ["b", "c"]
        assert unchanged == ["a"]
        assert deleted == ["d"]

    def test_empty_known_means_everything_changed(self):
        changed, unchanged, deleted = diff_elements({"a": "h1"}, {})
        assert changed == ["a"]
        assert unchanged == []
        assert deleted == []

    def test_identical_means_nothing_changed(self):
        hashes = {"a": "h1", "b": "h2"}
        changed, unchanged, deleted = diff_elements(hashes, dict(hashes))
        assert changed == []
        assert unchanged == ["a", "b"]
        assert deleted == []


class TestOriginAllowlist:
    def test_missing_origin_allowed(self):
        assert is_origin_allowed(None)

    def test_literal_null_allowed(self):
        assert is_origin_allowed("null")

    def test_loopback_origins_allowed_any_port(self):
        assert is_origin_allowed("http://localhost:5173")
        assert is_origin_allowed("http://127.0.0.1:8080")
        assert is_origin_allowed("http://[::1]:3000")

    def test_external_origin_denied(self):
        assert not is_origin_allowed("https://evil.example.com")
        assert not is_origin_allowed("http://192.168.1.10:5173")

    def test_extra_allowlist_exact_match(self):
        origin = "https://viewer.example.org"
        assert is_origin_allowed(origin, extra_allowed=(origin,))
        assert not is_origin_allowed("https://viewer.example.org.evil.com", (origin,))
