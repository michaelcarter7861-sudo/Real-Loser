#!/usr/bin/env python3
"""Normalize a generated one-mesh GLB to explicit game dimensions and ground pivot."""
from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

MAGIC = b"glTF"
JSON_CHUNK = 0x4E4F534A


def read_glb(path: Path):
    data = path.read_bytes()
    if len(data) < 20:
        raise ValueError("File is too short to be a GLB")
    magic, version, total_length = struct.unpack_from("<4sII", data, 0)
    if magic != MAGIC or version != 2 or total_length != len(data):
        raise ValueError("Invalid GLB 2.0 header/length")
    chunks = []
    offset = 12
    document = None
    while offset + 8 <= len(data):
        length, kind = struct.unpack_from("<II", data, offset)
        offset += 8
        payload = data[offset:offset + length]
        if len(payload) != length:
            raise ValueError("Truncated GLB chunk")
        offset += length
        chunks.append((kind, payload))
        if kind == JSON_CHUNK:
            document = json.loads(payload.decode("utf-8").rstrip(" \t\r\n\0"))
    if document is None:
        raise ValueError("Missing GLB JSON chunk")
    return document, chunks


def write_glb(path: Path, document: dict, chunks: list[tuple[int, bytes]]) -> None:
    json_raw = json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    json_raw += b" " * ((4 - len(json_raw) % 4) % 4)
    rebuilt = []
    replaced = False
    for kind, payload in chunks:
        if kind == JSON_CHUNK and not replaced:
            rebuilt.append((kind, json_raw))
            replaced = True
        else:
            rebuilt.append((kind, payload))
    if not replaced:
        raise ValueError("Could not replace GLB JSON chunk")
    body = b"".join(struct.pack("<II", len(payload), kind) + payload for kind, payload in rebuilt)
    total = 12 + len(body)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(struct.pack("<4sII", MAGIC, 2, total) + body)


def normalize(source: Path, output: Path, target: tuple[float, float, float]) -> None:
    doc, chunks = read_glb(source)
    meshes = doc.get("meshes", [])
    nodes = doc.get("nodes", [])
    if len(meshes) != 1 or not nodes:
        raise ValueError("Expected a single-mesh GLB with at least one node")
    primitives = meshes[0].get("primitives", [])
    if len(primitives) != 1:
        raise ValueError("Expected exactly one render primitive")
    position_index = primitives[0].get("attributes", {}).get("POSITION")
    accessors = doc.get("accessors", [])
    if position_index is None or position_index >= len(accessors):
        raise ValueError("Missing POSITION accessor")
    accessor = accessors[position_index]
    lower, upper = accessor.get("min"), accessor.get("max")
    if not lower or not upper or len(lower) < 3 or len(upper) < 3:
        raise ValueError("POSITION accessor must have min/max bounds")
    dimensions = [float(upper[i]) - float(lower[i]) for i in range(3)]
    if any(v <= 0 for v in dimensions):
        raise ValueError(f"Invalid mesh dimensions: {dimensions}")
    sx, sy, sz = (target[i] / dimensions[i] for i in range(3))
    center_x = (float(lower[0]) + float(upper[0])) * 0.5
    center_z = (float(lower[2]) + float(upper[2])) * 0.5
    node = next((n for n in nodes if "mesh" in n), nodes[0])
    node["rotation"] = [0.0, 0.0, 0.0, 1.0]
    node["scale"] = [sx, sy, sz]
    node["translation"] = [-center_x * sx, -float(lower[1]) * sy, -center_z * sz]

    for material in doc.get("materials", []):
        pbr = material.get("pbrMetallicRoughness", {})
        pbr["metallicFactor"] = 0.0
        pbr["roughnessFactor"] = 0.92
        material["pbrMetallicRoughness"] = pbr

    write_glb(output, doc, chunks)
    print(f"Normalized {source} -> {output}")
    print(f"Source bounds size={dimensions}; target={target}; node scale={[sx, sy, sz]}; ground y offset={node['translation'][1]:.6f}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--length", type=float, default=2.4)
    parser.add_argument("--height", type=float, default=1.05)
    parser.add_argument("--depth", type=float, default=0.6)
    args = parser.parse_args()
    normalize(args.input, args.output, (args.length, args.height, args.depth))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
