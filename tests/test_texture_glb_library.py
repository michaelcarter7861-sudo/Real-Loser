#!/usr/bin/env python3
"""Validate the original textured art and additive RC1.6 mission environment catalog."""
from __future__ import annotations
import hashlib
import io
import json
import shutil
import sys
import tempfile
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import texture_glb_library as pipeline  # noqa: E402
from integrate_rc16_assets import parse_glb as parse_integrated_glb  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_base_tree(root: Path, manifest: dict, temp_root: Path, label: str, errors: list[str]):
    stage = temp_root / label
    for relative in manifest["files"]:
        src = root / relative
        if not src.is_file():
            errors.append(f"{label}: missing baseline asset {relative}")
            continue
        dst = stage / relative
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    ok, found, _ = pipeline.validate_tree(stage, manifest)
    if not ok:
        errors.extend(f"{label}: {error}" for error in found)


def main() -> int:
    manifest_path = ROOT / "tools" / "texture_glb_baseline.json"
    manifest = pipeline.load_manifest(manifest_path)
    streaming = ROOT / "Assets" / "StreamingAssets" / "Art"
    project = ROOT / "Assets" / "_Project" / "Art"
    errors: list[str] = []
    manifest_names = set(manifest["files"])

    with tempfile.TemporaryDirectory(prefix="prl_rc16_base_art_") as temp:
        temp_root = Path(temp)
        validate_base_tree(project, manifest, temp_root, "project_baseline", errors)
        validate_base_tree(streaming, manifest, temp_root, "streaming_baseline", errors)

    barrier_rel = next(k for k in manifest_names if k.endswith(pipeline.BARRIER_NAME))
    expected_barrier = manifest["barrier_sha256"]
    for label, root in (("project", project), ("streaming", streaming)):
        barrier = root / barrier_rel
        if not barrier.is_file() or sha256(barrier) != expected_barrier:
            errors.append(f"{label}: protected barrier hash changed")

    project_files = {p.relative_to(project).as_posix(): p for p in pipeline.all_glbs(project)}
    stream_files = {p.relative_to(streaming).as_posix(): p for p in pipeline.all_glbs(streaming)}
    if set(project_files) != set(stream_files):
        errors.append("project and streaming GLB inventories differ")
    if len(project_files) != len(manifest_names) + 104:
        errors.append(f"expected 185 total GLBs (81 baseline + 104 RC1.6 environment), found {len(project_files)}")
    for relative in sorted(set(project_files) | set(stream_files)):
        a, b = project_files.get(relative), stream_files.get(relative)
        if a is None or b is None:
            errors.append(f"missing project/stream mirror: {relative}")
        elif sha256(a) != sha256(b):
            errors.append(f"mirror hash mismatch: {relative}")

    extra = set(project_files) - manifest_names
    expected_generated = {"Environment/" + p for p in (
        "env_tower_radio_relay_steel_a.glb", "veh_truck_cargo_a.glb")}
    if len(extra) != 104:
        errors.append(f"expected 104 additive environment assets, found {len(extra)}")
    if not expected_generated.issubset(extra):
        errors.append("generated relay mast or armored truck missing")
    generated_procedural = 0
    for relative in sorted(extra):
        path = project_files[relative]
        try:
            doc, _, bin_payload = parse_integrated_glb(path)
            if not doc.get("meshes") or not doc.get("materials"):
                errors.append(f"{relative}: mesh/material missing")
            for mesh in doc.get("meshes", []):
                for prim in mesh.get("primitives", []):
                    attrs = prim.get("attributes", {})
                    if not all(k in attrs for k in ("POSITION", "NORMAL", "TEXCOORD_0")):
                        errors.append(f"{relative}: required vertex attributes missing")
                        continue
                    accessors = doc.get("accessors", [])
                    pacc, uacc = accessors[attrs["POSITION"]], accessors[attrs["TEXCOORD_0"]]
                    if pacc.get("count") != uacc.get("count"):
                        errors.append(f"{relative}: UV vertex count mismatch")
            for image in doc.get("images", []):
                view = doc["bufferViews"][image["bufferView"]]
                start, size = int(view.get("byteOffset", 0)), int(view["byteLength"])
                payload = bin_payload[start:start + size]
                if len(payload) != size:
                    errors.append(f"{relative}: embedded image range invalid")
                    continue
                try:
                    with Image.open(io.BytesIO(payload)) as im:
                        im.verify()
                except Exception as exc:
                    errors.append(f"{relative}: invalid embedded image ({exc})")
            if relative in expected_generated:
                node = doc["nodes"][0]
                extras = node.get("extras", {})
                expected_dims = [2.2, 7.5, 2.2] if "relay" in relative else [5.8, 2.7, 2.5]
                if extras.get("prl_normalized_dimensions_m") != expected_dims:
                    errors.append(f"{relative}: normalized world dimensions are wrong")
                if len(doc.get("images", [])) < 3 or not doc.get("textures"):
                    errors.append(f"{relative}: expected generated PBR image set missing")
            elif isinstance(doc.get("extras"), dict) and doc["extras"].get(pipeline.MARKER_KEY):
                generated_procedural += 1
                if len(doc.get("images", [])) < 2 or len(doc.get("textures", [])) < 2:
                    errors.append(f"{relative}: embedded PBR pair missing")
            else:
                errors.append(f"{relative}: unrecognized additive GLB provenance")
        except Exception as exc:
            errors.append(f"{relative}: GLB parse/validation failed ({exc})")
    if generated_procedural != 102:
        errors.append(f"expected 102 textured procedural environment models, found {generated_procedural}")

    if errors:
        print("FAIL")
        print("\n".join("  " + error for error in errors))
        return 1
    print("PASS: baseline 81 GLBs validated against pre-texture manifest; 104 added mission environment models validated (102 procedural textured + 2 generated PBR); all 185 Art/StreamingAssets mirrors match; barrier hash preserved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
