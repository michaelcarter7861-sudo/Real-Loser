#!/usr/bin/env python3
"""Texture the shipped GLB library without changing its render geometry or rig schema.

This tool is deliberately stdlib/Pillow-only and treats GLB JSON/BIN as data.  It
never imports or executes project code.  The safe workflow is:

  baseline  --source-root Assets/_Project/Art --manifest tools/texture_glb_baseline.json
  transform --source-root Assets/_Project/Art --output-root /tmp/prl-textured/Art
  validate  --root /tmp/prl-textured/Art --manifest tools/texture_glb_baseline.json
  sync      --working-root /tmp/prl-textured/Art --project-root Assets/_Project/Art \
            --streaming-root Assets/StreamingAssets/Art --manifest tools/texture_glb_baseline.json

Texture bytes are generated from stable SHA-256-derived phases and periodic (tileable)
functions.  A marker in root extras makes reruns no-ops rather than appending duplicate
accessors/images.  Existing geometry, nodes, skins, animations, accessors and chunks are
copied verbatim; only appended UV/image payloads and material texture references are added.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import math
import shutil
import struct
import sys
from pathlib import Path
from typing import Any, Iterable

from PIL import Image

MAGIC = b"glTF"
VERSION = 2
JSON_CHUNK = 0x4E4F534A
BIN_CHUNK = 0x004E4942
FLOAT = 5126
VEC2 = "VEC2"
MARKER_KEY = "prl_texture_pipeline"
PIPELINE_VERSION = 1
BARRIER_NAME = "prop_concrete_barrier_a.glb"
EXPECTED_TOTAL = 81
EXPECTED_MODIFIED = 80
CATEGORY_COUNTS = {"Characters": 24, "Weapons": 26, "Traps": 16, "Environment": 15}


def align4(n: int) -> int:
    return (n + 3) & ~3


def parse_glb(path: Path) -> tuple[dict[str, Any], list[tuple[int, bytes]], bytes]:
    """Read a GLB as bytes/JSON; do not interpret anything as executable content."""
    data = path.read_bytes()
    if len(data) < 20:
        raise ValueError(f"{path}: file is shorter than a GLB header")
    magic, version, total = struct.unpack_from("<4sII", data, 0)
    if magic != MAGIC or version != VERSION or total != len(data):
        raise ValueError(f"{path}: invalid GLB header/version/length")
    off = 12
    chunks: list[tuple[int, bytes]] = []
    document: dict[str, Any] | None = None
    bin_payload: bytes | None = None
    while off < len(data):
        if off + 8 > len(data):
            raise ValueError(f"{path}: truncated chunk header")
        length, kind = struct.unpack_from("<II", data, off)
        off += 8
        end = off + length
        if end > len(data):
            raise ValueError(f"{path}: truncated chunk payload")
        payload = data[off:end]
        off = end
        chunks.append((kind, payload))
        if kind == JSON_CHUNK:
            if document is not None:
                raise ValueError(f"{path}: multiple JSON chunks")
            try:
                document = json.loads(payload.decode("utf-8").rstrip(" \t\r\n\x00"))
            except Exception as exc:
                raise ValueError(f"{path}: invalid JSON chunk: {exc}") from exc
        elif kind == BIN_CHUNK:
            if bin_payload is not None:
                raise ValueError(f"{path}: multiple BIN chunks are not supported safely")
            bin_payload = payload
    if document is None or bin_payload is None:
        raise ValueError(f"{path}: GLB must contain one JSON and one BIN chunk")
    if not isinstance(document, dict):
        raise ValueError(f"{path}: glTF root is not an object")
    return document, chunks, bin_payload


def pack_glb(document: dict[str, Any], chunks: list[tuple[int, bytes]], bin_payload: bytes) -> bytes:
    raw_json = json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    raw_json += b" " * ((4 - len(raw_json) % 4) % 4)
    rebuilt: list[tuple[int, bytes]] = []
    json_done = bin_done = False
    for kind, payload in chunks:
        if kind == JSON_CHUNK and not json_done:
            rebuilt.append((kind, raw_json)); json_done = True
        elif kind == BIN_CHUNK and not bin_done:
            rebuilt.append((kind, bin_payload)); bin_done = True
        else:
            rebuilt.append((kind, payload))
    if not json_done or not bin_done:
        raise ValueError("GLB chunks lost JSON or BIN")
    body = b"".join(struct.pack("<II", len(p), k) + p for k, p in rebuilt)
    return struct.pack("<4sII", MAGIC, VERSION, 12 + len(body)) + body


def gltf_array(doc: dict[str, Any], key: str) -> list[Any]:
    value = doc.get(key)
    if value is None:
        value = []
        doc[key] = value
    if not isinstance(value, list):
        raise ValueError(f"glTF {key} must be an array")
    return value


def validate_index(index: Any, length: int, label: str) -> int:
    if not isinstance(index, int) or index < 0 or index >= length:
        raise ValueError(f"invalid {label} index {index!r}")
    return index


def accessor_payload(doc: dict[str, Any], bin_payload: bytes, accessor_index: int) -> tuple[dict[str, Any], bytes, int, int]:
    accessors = gltf_array(doc, "accessors")
    views = gltf_array(doc, "bufferViews")
    acc = accessors[validate_index(accessor_index, len(accessors), "accessor")]
    if acc.get("sparse"):
        raise ValueError("sparse accessors are not safely editable")
    view_index = validate_index(acc.get("bufferView"), len(views), "bufferView")
    view = views[view_index]
    if view.get("buffer", 0) != 0:
        raise ValueError("only buffer 0 in a GLB is supported")
    component_size = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}.get(acc.get("componentType"))
    components = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT2": 4, "MAT3": 9, "MAT4": 16}.get(acc.get("type"))
    count = acc.get("count")
    if component_size is None or components is None or not isinstance(count, int) or count < 0:
        raise ValueError("malformed accessor")
    element_size = component_size * components
    stride = int(view.get("byteStride", 0) or 0) or element_size
    if stride < element_size:
        raise ValueError("accessor byteStride is smaller than its element")
    start = int(view.get("byteOffset", 0) or 0) + int(acc.get("byteOffset", 0) or 0)
    needed = 0 if count == 0 else (count - 1) * stride + element_size
    if start < 0 or start + needed > len(bin_payload):
        raise ValueError("accessor exceeds BIN payload")
    return acc, bin_payload, start, stride


def read_positions(doc: dict[str, Any], bin_payload: bytes, accessor_index: int) -> list[tuple[float, float, float]]:
    acc, raw, start, stride = accessor_payload(doc, bin_payload, accessor_index)
    if acc.get("componentType") != FLOAT or acc.get("type") != "VEC3":
        raise ValueError("POSITION must be float VEC3")
    out = []
    for i in range(acc["count"]):
        out.append(struct.unpack_from("<3f", raw, start + i * stride))
    return out


def image_png(rgb: Any) -> bytes:
    # Pillow encodes RGB PNG deterministically with this fixed encoder configuration.
    im = Image.fromarray(rgb, mode="RGB")
    buf = io.BytesIO()
    im.save(buf, format="PNG", optimize=False, compress_level=9)
    return buf.getvalue()


def stable_phase(stem: str, category: str) -> tuple[float, float, float]:
    digest = hashlib.sha256((category + "/" + stem).encode("utf-8")).digest()
    return tuple((int.from_bytes(digest[i:i + 2], "little") / 65535.0) * math.tau for i in (0, 2, 4))


def palette(stem: str, category: str) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    s = stem.lower()
    if category == "Characters":
        if "civ_" in s or "npc_" in s:
            base = (0.38, 0.40, 0.34) if "technician" not in s else (0.27, 0.33, 0.31)
            accent = (0.52, 0.48, 0.36)
        elif "boss" in s:
            base, accent = (0.20, 0.24, 0.22), (0.33, 0.12, 0.10)
        else:
            base, accent = (0.22, 0.28, 0.20), (0.36, 0.34, 0.24)
    elif category == "Weapons":
        base, accent = ((0.18, 0.20, 0.18), (0.34, 0.28, 0.18)) if "knife" not in s and "garrote" not in s else ((0.28, 0.29, 0.27), (0.40, 0.36, 0.28))
    elif category == "Traps":
        base, accent = (0.19, 0.22, 0.20), (0.55, 0.28, 0.07)
        if any(k in s for k in ("laser", "alarm", "sensor", "camera")):
            accent = (0.62, 0.18, 0.06)
    else:
        if "brick" in s:
            base, accent = (0.32, 0.22, 0.17), (0.48, 0.33, 0.23)
        elif "adobe" in s or "wall_" in s:
            base, accent = (0.43, 0.37, 0.26), (0.60, 0.50, 0.34)
        elif "chainlink" in s or "metal" in s or "gate" in s or "locker" in s or "dumpster" in s:
            base, accent = (0.25, 0.28, 0.25), (0.42, 0.36, 0.23)
        else:
            base, accent = (0.34, 0.35, 0.31), (0.47, 0.42, 0.32)
    return base, accent


def make_textures(stem: str, category: str, size: int = 128) -> tuple[bytes, bytes]:
    """Create low-frequency, seamless RGB albedo and tangent normal PNGs."""
    import numpy as np
    phase = stable_phase(stem, category)
    base, accent = palette(stem, category)
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    u, v = x / size, y / size
    f = (
        0.52 * np.sin(math.tau * (u + phase[0] / math.tau) * 2.0) * np.cos(math.tau * (v + phase[1] / math.tau) * 2.0)
        + 0.30 * np.sin(math.tau * (u * 4.0 + v * 3.0 + phase[2] / math.tau))
        + 0.18 * np.cos(math.tau * (u * 7.0 - v * 5.0 + phase[0] / math.tau))
    )
    f = (f + 1.0) * 0.5
    # Broad mottling keeps generated surfaces readable without baked shadows.
    blend = np.clip(0.12 + 0.20 * f, 0.0, 1.0)[..., None]
    rgb = np.asarray(base, dtype=np.float32) * (1.0 - blend) + np.asarray(accent, dtype=np.float32) * blend
    grime = 0.88 + 0.16 * (0.5 + 0.5 * np.sin(math.tau * (u * 3.0 + v * 2.0 + phase[1] / math.tau)))
    rgb *= grime[..., None]
    if category == "Traps":
        stripe = ((np.sin(math.tau * (u * 10.0 + v * 10.0 + phase[0] / math.tau)) > 0.82) * 0.10)[..., None]
        rgb += stripe * np.asarray((0.75, 0.25, 0.03), dtype=np.float32)
    rgb8 = np.clip(rgb * 255.0, 0, 255).astype(np.uint8)

    # Height has matching periodic boundaries, so finite differences also tile.
    height = 0.5 + 0.15 * f + 0.04 * np.sin(math.tau * (u * 5.0 - v * 4.0 + phase[2] / math.tau))
    dx = np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)
    dy = np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0)
    nx, ny = -dx * 2.0, -dy * 2.0
    nz = np.ones_like(nx)
    norm = np.sqrt(nx * nx + ny * ny + nz * nz)
    normal8 = np.stack(((nx / norm + 1.0) * 127.5, (ny / norm + 1.0) * 127.5, (nz / norm + 1.0) * 127.5), axis=-1)
    return image_png(rgb8), image_png(np.clip(normal8, 0, 255).astype(np.uint8))


def category_for(path: Path) -> str:
    if path.parent.name not in CATEGORY_COUNTS:
        raise ValueError(f"unexpected GLB category directory: {path}")
    return path.parent.name


def all_glbs(root: Path) -> list[Path]:
    return sorted(root.glob("**/*.glb"))


def position_bounds(doc: dict[str, Any], bin_payload: bytes) -> tuple[list[float], list[float]]:
    lows = [float("inf")] * 3; highs = [float("-inf")] * 3
    for mesh in gltf_array(doc, "meshes"):
        for prim in mesh.get("primitives", []):
            attrs = prim.get("attributes", {})
            if "POSITION" not in attrs:
                raise ValueError("primitive lacks POSITION")
            for pos in read_positions(doc, bin_payload, attrs["POSITION"]):
                for i in range(3):
                    lows[i] = min(lows[i], pos[i]); highs[i] = max(highs[i], pos[i])
    if not all(math.isfinite(v) for v in lows + highs):
        raise ValueError("empty/non-finite POSITION bounds")
    return lows, highs


def uv_bytes(doc: dict[str, Any], bin_payload: bytes) -> dict[int, bytes]:
    lows, highs = position_bounds(doc, bin_payload)
    spans = [max(highs[i] - lows[i], 1e-6) for i in range(3)]
    axes = sorted(range(3), key=lambda i: spans[i], reverse=True)[:2]
    # The two widest local axes make UVs useful for boxes, character bodies, and weapons.
    result: dict[int, bytes] = {}
    for mesh in gltf_array(doc, "meshes"):
        for prim in mesh.get("primitives", []):
            attrs = prim.get("attributes", {})
            positions = read_positions(doc, bin_payload, attrs["POSITION"])
            packed = bytearray()
            for p in positions:
                uu = ((p[axes[0]] - lows[axes[0]]) / spans[axes[0]] * 2.0) % 1.0
                vv = ((p[axes[1]] - lows[axes[1]]) / spans[axes[1]] * 2.0) % 1.0
                packed += struct.pack("<2f", uu, vv)
            result[id(prim)] = bytes(packed)
    return result


def append_buffer_view(doc: dict[str, Any], bin_buf: bytearray, payload: bytes) -> int:
    pad = align4(len(bin_buf)) - len(bin_buf)
    if pad: bin_buf.extend(b"\0" * pad)
    offset = len(bin_buf); bin_buf.extend(payload)
    views = gltf_array(doc, "bufferViews")
    views.append({"buffer": 0, "byteOffset": offset, "byteLength": len(payload), "target": 34962})
    return len(views) - 1


def transform_one(source: Path, output: Path) -> bool:
    doc, chunks, original_bin = parse_glb(source)
    if source.name == BARRIER_NAME:
        output.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(source, output)
        return False
    category = category_for(source)
    marker = doc.get("extras", {}).get(MARKER_KEY) if isinstance(doc.get("extras"), dict) else None
    if isinstance(marker, dict) and marker.get("version") == PIPELINE_VERSION:
        output.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(source, output)
        return False
    if doc.get("images") or doc.get("textures"):
        raise ValueError(f"{source}: pre-existing images/textures without pipeline marker; refusing to risk them")
    uv_payloads = uv_bytes(doc, original_bin)
    bin_buf = bytearray(original_bin)
    accessors = gltf_array(doc, "accessors")
    for mesh in gltf_array(doc, "meshes"):
        for prim in mesh.get("primitives", []):
            attrs = prim.setdefault("attributes", {})
            if "TEXCOORD_0" in attrs:
                raise ValueError(f"{source}: primitive unexpectedly already has UV0")
            payload = uv_payloads[id(prim)]
            view_index = append_buffer_view(doc, bin_buf, payload)
            acc_index = len(accessors)
            count = len(payload) // 8
            accessors.append({"bufferView": view_index, "byteOffset": 0, "componentType": FLOAT, "count": count, "type": VEC2, "min": [0.0, 0.0], "max": [1.0, 1.0]})
            attrs["TEXCOORD_0"] = acc_index
    base_png, normal_png = make_textures(source.stem, category)
    images = gltf_array(doc, "images"); textures = gltf_array(doc, "textures")
    base_view = append_buffer_view(doc, bin_buf, base_png)
    base_image = len(images); images.append({"mimeType": "image/png", "bufferView": base_view, "name": source.stem + "_albedo"})
    base_texture = len(textures); textures.append({"source": base_image, "name": source.stem + "_albedo"})
    normal_view = append_buffer_view(doc, bin_buf, normal_png)
    normal_image = len(images); images.append({"mimeType": "image/png", "bufferView": normal_view, "name": source.stem + "_normal"})
    normal_texture = len(textures); textures.append({"source": normal_image, "name": source.stem + "_normal"})
    for material in gltf_array(doc, "materials"):
        pbr = material.setdefault("pbrMetallicRoughness", {})
        pbr["baseColorTexture"] = {"index": base_texture, "texCoord": 0}
        material["normalTexture"] = {"index": normal_texture, "texCoord": 0, "scale": 0.55}
    extras = doc.setdefault("extras", {})
    if not isinstance(extras, dict): raise ValueError(f"{source}: root extras is not an object")
    extras[MARKER_KEY] = {"version": PIPELINE_VERSION, "category": category, "albedo": "embedded_png", "normal": "embedded_png", "uv": "TEXCOORD_0"}
    buffers = gltf_array(doc, "buffers")
    if len(buffers) != 1: raise ValueError(f"{source}: expected exactly one GLB buffer")
    buffers[0]["byteLength"] = len(bin_buf)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(pack_glb(doc, chunks, bytes(bin_buf)))
    return True


def semantic_signature(doc: dict[str, Any], bin_payload: bytes, baseline: dict[str, Any] | None = None) -> dict[str, Any]:
    """Hash all original schema/data while excluding only this pipeline's additions."""
    clean = copy.deepcopy(doc)
    clean.pop("images", None); clean.pop("textures", None)
    if isinstance(clean.get("extras"), dict):
        clean["extras"].pop(MARKER_KEY, None)
        if not clean["extras"]: clean.pop("extras", None)
    for mat in clean.get("materials", []):
        pbr = mat.get("pbrMetallicRoughness", {})
        if isinstance(pbr, dict): pbr.pop("baseColorTexture", None)
        mat.pop("normalTexture", None)
    for mesh in clean.get("meshes", []):
        for prim in mesh.get("primitives", []):
            prim.get("attributes", {}).pop("TEXCOORD_0", None)
    original_bin_length = len(bin_payload)
    if baseline:
        original_bin_length = int(baseline["bin_length"])
        clean["accessors"] = clean.get("accessors", [])[:int(baseline["accessor_count"])]
        clean["bufferViews"] = clean.get("bufferViews", [])[:int(baseline["buffer_view_count"])]
        if clean.get("buffers"): clean["buffers"][0]["byteLength"] = original_bin_length
    canonical = json.dumps(clean, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return {"json_sha256": hashlib.sha256(canonical).hexdigest(), "bin_prefix_sha256": hashlib.sha256(bin_payload[:original_bin_length]).hexdigest(), "bin_length": original_bin_length, "mesh_count": len(clean.get("meshes", [])), "primitive_count": sum(len(m.get("primitives", [])) for m in clean.get("meshes", [])), "material_count": len(clean.get("materials", [])), "accessor_count": len(clean.get("accessors", [])), "buffer_view_count": len(clean.get("bufferViews", [])), "node_count": len(clean.get("nodes", [])), "skin_count": len(clean.get("skins", [])), "animation_count": len(clean.get("animations", []))}


def make_baseline(source_root: Path, manifest_path: Path) -> dict[str, Any]:
    files = all_glbs(source_root)
    if len(files) != EXPECTED_TOTAL: raise ValueError(f"expected {EXPECTED_TOTAL} source GLBs, found {len(files)}")
    records = {}
    for p in files:
        doc, _, bin_payload = parse_glb(p)
        records[str(p.relative_to(source_root))] = {"source_sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "semantic": semantic_signature(doc, bin_payload), "barrier": p.name == BARRIER_NAME}
    manifest = {"pipeline_version": PIPELINE_VERSION, "expected_total": EXPECTED_TOTAL, "expected_modified": EXPECTED_MODIFIED, "category_counts": CATEGORY_COUNTS, "barrier_sha256": records[next(k for k in records if k.endswith(BARRIER_NAME))]["source_sha256"], "files": records}
    manifest_path.parent.mkdir(parents=True, exist_ok=True); manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_tree(root: Path, manifest: dict[str, Any]) -> tuple[bool, list[str], dict[str, int]]:
    errors: list[str] = []; counts = {k: 0 for k in CATEGORY_COUNTS}; files = all_glbs(root)
    if len(files) != EXPECTED_TOTAL: errors.append(f"{root}: expected {EXPECTED_TOTAL} GLBs, found {len(files)}")
    for p in files:
        rel = str(p.relative_to(root)); rec = manifest.get("files", {}).get(rel)
        try:
            doc, chunks, bin_payload = parse_glb(p)
            if rec is None: errors.append(f"unexpected GLB {rel}"); continue
            if p.name != BARRIER_NAME:
                counts[p.parent.name] = counts.get(p.parent.name, 0) + 1
                if not (isinstance(doc.get("extras"), dict) and doc["extras"].get(MARKER_KEY, {}).get("version") == PIPELINE_VERSION): errors.append(f"{rel}: missing pipeline marker")
                images, textures = gltf_array(doc, "images"), gltf_array(doc, "textures")
                if len(images) < 2 or len(textures) < 2: errors.append(f"{rel}: missing embedded image/texture entries")
                for i, image in enumerate(images[-2:]):
                    vi = image.get("bufferView"); views = gltf_array(doc, "bufferViews")
                    if not isinstance(vi, int) or vi >= len(views): errors.append(f"{rel}: image {i} invalid bufferView")
                    else:
                        v = views[vi]; start = int(v.get("byteOffset", 0)); payload = bin_payload[start:start + int(v.get("byteLength", 0))]
                        try: Image.open(io.BytesIO(payload)).verify()
                        except Exception as exc: errors.append(f"{rel}: image {i} invalid PNG ({exc})")
                for mesh in gltf_array(doc, "meshes"):
                    for prim in mesh.get("primitives", []):
                        attrs = prim.get("attributes", {}); uv_i = attrs.get("TEXCOORD_0")
                        if not isinstance(uv_i, int): errors.append(f"{rel}: primitive missing TEXCOORD_0")
                        else:
                            ua = gltf_array(doc, "accessors")[uv_i]; pa = gltf_array(doc, "accessors")[attrs["POSITION"]]
                            if ua.get("componentType") != FLOAT or ua.get("type") != VEC2 or ua.get("count") != pa.get("count"): errors.append(f"{rel}: UV accessor schema/count mismatch")
                            if ua.get("bufferView") is None: errors.append(f"{rel}: UV accessor missing bufferView")
                            else:
                                try:
                                    _, _, uv_start, uv_stride = accessor_payload(doc, bin_payload, uv_i)
                                    uv_view = gltf_array(doc, "bufferViews")[ua["bufferView"]]
                                    expected_bytes = int(ua["count"]) * 8
                                    if uv_stride != 8 or int(uv_view.get("byteLength", 0)) != expected_bytes or uv_start + expected_bytes > len(bin_payload):
                                        errors.append(f"{rel}: UV accessor byte range/size mismatch")
                                except Exception as exc:
                                    errors.append(f"{rel}: invalid UV accessor payload ({exc})")
                for mat in gltf_array(doc, "materials"):
                    pbr = mat.get("pbrMetallicRoughness", {})
                    if not isinstance(pbr.get("baseColorTexture", {}).get("index"), int) or not isinstance(mat.get("normalTexture", {}).get("index"), int): errors.append(f"{rel}: material missing PBR texture references")
            else:
                if hashlib.sha256(p.read_bytes()).hexdigest() != manifest.get("barrier_sha256"): errors.append(f"{rel}: barrier hash changed")
            sig = semantic_signature(doc, bin_payload, rec["semantic"])
            if sig != {**rec["semantic"], "bin_prefix_sha256": rec["semantic"]["bin_prefix_sha256"]}:
                errors.append(f"{rel}: original schema/geometry/accessor signature changed")
        except Exception as exc:
            errors.append(f"{rel}: {exc}")
    for category, expected in CATEGORY_COUNTS.items():
        got = sum(1 for p in files if p.parent.name == category and p.name != BARRIER_NAME)
        if category == "Environment": got += 1  # category count includes the untouched barrier
        if got != expected: errors.append(f"{root}: {category} count {got} != {expected}")
    return not errors, errors, counts


def transform_tree(source_root: Path, output_root: Path) -> int:
    files = all_glbs(source_root)
    if len(files) != EXPECTED_TOTAL: raise ValueError(f"expected {EXPECTED_TOTAL} source GLBs, found {len(files)}")
    changed = 0
    for src in files:
        out = output_root / src.relative_to(source_root)
        changed += int(transform_one(src, out))
    return changed


def sync_tree(working_root: Path, project_root: Path, streaming_root: Path, manifest: dict[str, Any]) -> None:
    ok, errors, _ = validate_tree(working_root, manifest)
    if not ok: raise ValueError("refusing sync because working tree failed validation:\n" + "\n".join(errors))
    for src in all_glbs(working_root):
        rel = src.relative_to(working_root)
        for dst_root in (project_root, streaming_root):
            dst = dst_root / rel; dst.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(src, dst)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    bp = sub.add_parser("baseline"); bp.add_argument("--source-root", type=Path, required=True); bp.add_argument("--manifest", type=Path, required=True)
    tp = sub.add_parser("transform"); tp.add_argument("--source-root", type=Path, required=True); tp.add_argument("--output-root", type=Path, required=True)
    vp = sub.add_parser("validate"); vp.add_argument("--root", type=Path, required=True); vp.add_argument("--manifest", type=Path, required=True)
    sp = sub.add_parser("sync"); sp.add_argument("--working-root", type=Path, required=True); sp.add_argument("--project-root", type=Path, required=True); sp.add_argument("--streaming-root", type=Path, required=True); sp.add_argument("--manifest", type=Path, required=True)
    args = ap.parse_args(argv)
    if args.command == "baseline":
        m = make_baseline(args.source_root, args.manifest); print(f"baseline: {len(m['files'])} GLBs -> {args.manifest}")
    elif args.command == "transform":
        print(f"transform: {transform_tree(args.source_root, args.output_root)} modified GLBs -> {args.output_root}")
    elif args.command == "validate":
        ok, errors, counts = validate_tree(args.root, load_manifest(args.manifest)); print(f"validate: {'PASS' if ok else 'FAIL'}; modified category counts={counts}")
        if errors:
            print("\n".join("  " + e for e in errors)); return 1
    elif args.command == "sync":
        sync_tree(args.working_root, args.project_root, args.streaming_root, load_manifest(args.manifest)); print(f"sync: copied {EXPECTED_TOTAL} GLBs to both mirrors")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
