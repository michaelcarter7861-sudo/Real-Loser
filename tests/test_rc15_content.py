#!/usr/bin/env python3
"""Regression checks for RC1.5 mission maps and the normalized barrier GLB."""
from __future__ import annotations

import hashlib
import json
import re
import struct
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def read_glb(path: Path) -> dict:
    data = path.read_bytes()
    assert len(data) >= 20 and data[:4] == b"glTF", f"not a GLB: {path}"
    magic, version, total = struct.unpack_from("<4sII", data, 0)
    assert version == 2 and total == len(data), f"invalid GLB header: {path}"
    offset = 12
    document = None
    while offset + 8 <= len(data):
        size, kind = struct.unpack_from("<II", data, offset)
        offset += 8
        payload = data[offset:offset + size]
        assert len(payload) == size, f"truncated chunk: {path}"
        offset += size
        if kind == 0x4E4F534A:
            document = json.loads(payload.decode("utf-8").rstrip(" \t\r\n\0"))
    assert document is not None, f"missing JSON chunk: {path}"
    return document


def close(a: float, b: float, eps: float = 0.002) -> bool:
    return abs(a - b) <= eps


def main() -> int:
    mission_files = [ROOT / f"M{i:02d}.json" for i in range(1, 11)]
    for mission in mission_files:
        data = json.loads(mission.read_text(encoding="utf-8"))
        assert data.get("mission_id") == mission.stem, f"mission ID mismatch: {mission.name}"
        texture = ROOT / "Assets" / "Resources" / "MissionMaps" / f"{mission.stem}.png"
        assert texture.is_file(), f"missing tactical map: {texture}"
        with Image.open(texture) as image:
            assert image.size == (1536, 1024), f"unexpected map size for {mission.stem}: {image.size}"
            assert image.getbbox() is not None, f"blank map texture: {texture}"

    asset = ROOT / "Assets" / "_Project" / "Art" / "Environment" / "prop_concrete_barrier_a.glb"
    mirror = ROOT / "Assets" / "StreamingAssets" / "Art" / "Environment" / asset.name
    document = read_glb(asset)
    assert mirror.is_file(), "missing StreamingAssets barrier copy"
    assert hashlib.sha256(asset.read_bytes()).digest() == hashlib.sha256(mirror.read_bytes()).digest(), "barrier mirrors differ"
    assert len(document.get("meshes", [])) == 1, "barrier should have one mesh"
    primitive = document["meshes"][0]["primitives"][0]
    assert "TEXCOORD_0" in primitive["attributes"], "barrier has no UV0"
    assert len(document.get("images", [])) >= 2, "expected embedded color/normal textures"
    material = document["materials"][primitive["material"]]
    pbr = material["pbrMetallicRoughness"]
    assert "baseColorTexture" in pbr, "missing base-color texture reference"
    assert "normalTexture" in material, "missing normal texture reference"
    position = document["accessors"][primitive["attributes"]["POSITION"]]
    mesh_dims = [position["max"][i] - position["min"][i] for i in range(3)]
    node = next(n for n in document["nodes"] if n.get("mesh") == 0)
    dimensions = [mesh_dims[i] * node["scale"][i] for i in range(3)]
    assert all(close(actual, expected) for actual, expected in zip(dimensions, (2.4, 1.05, 0.6))), f"bad barrier size: {dimensions}"
    ground = position["min"][1] * node["scale"][1] + node["translation"][1]
    assert close(ground, 0.0), f"barrier ground pivot is not zero: {ground}"
    triangles = document["accessors"][primitive["indices"]]["count"] // 3
    assert triangles <= 3500, f"barrier exceeds mobile triangle target: {triangles}"

    loader = (ROOT / "Assets/_Project/Scripts/Core/RuntimeGLBAndMeshLoader.cs").read_text(encoding="utf-8")
    hud = (ROOT / "Assets/_Project/Scripts/UI/MobileTouchHUDAndMEMap.cs").read_text(encoding="utf-8")
    spawner = (ROOT / "Assets/_Project/Scripts/Core/RuntimeMissionSpawner.cs").read_text(encoding="utf-8")
    motion = (ROOT / "Assets/_Project/Scripts/Core/ProceduralHumanoidMotion.cs").read_text(encoding="utf-8")
    assert "ImageConversion.LoadImage" in loader and "TEXCOORD_0" in loader and "normalTexture" in loader, "GLB PBR import wiring missing"
    assert "_prefabTemplateCache" in loader and "Object.Instantiate(template" in loader, "GLB instance cache wiring missing"
    assert "SkinnedMeshRenderer" in loader and "ReadMat4Accessor" in loader and "mesh.boneWeights" in loader, "GLB skinning import wiring missing"
    assert "legSwingDegrees" in motion and "GetComponentsInChildren<Transform>" in motion, "procedural humanoid motion wiring missing"
    assert "Resources.Load<Texture2D>(\"MissionMaps/\" + missionId)" in hud, "HUD map Resources load missing"
    assert "WorldToMapAnchor" in hud and "ConfigureMissionMapEnemies" in hud, "HUD dynamic map markers missing"
    assert "ConfigureMissionMapEnemies(_spawnedEnemies)" in spawner, "spawner does not connect enemy blips"

    build_settings = (ROOT / "ProjectSettings/EditorBuildSettings.asset").read_text(encoding="utf-8")
    scene_entries = re.findall(r"- enabled: 1\n\s+path: ([^\n]+)\n\s+guid: ([0-9a-f]{32})", build_settings)
    assert len(scene_entries) == 12, f"expected 12 enabled build scenes, found {len(scene_entries)}"
    known_guids = {}
    for meta_path in (ROOT / "Assets").rglob("*.meta"):
        match = re.search(r"^guid:\s*([0-9a-f]{32})\s*$", meta_path.read_text(encoding="utf-8", errors="replace"), re.M)
        if match:
            known_guids.setdefault(match.group(1), []).append(meta_path)
    assert all(len(paths) == 1 for paths in known_guids.values()), "duplicate Unity meta GUID"
    for scene_path, scene_guid in scene_entries:
        scene_meta = ROOT / (scene_path + ".meta")
        match = re.search(r"^guid:\s*([0-9a-f]{32})", scene_meta.read_text(encoding="utf-8"), re.M)
        assert match and match.group(1) == scene_guid, f"scene GUID/meta mismatch: {scene_path}"
    builtins = {"0000000000000000e000000000000000", "0000000000000000f000000000000000"}
    for scene in (ROOT / "Assets/_Project/Scenes").glob("*.unity"):
        refs = re.findall(r"guid:\s*([0-9a-f]{32})", scene.read_text(encoding="utf-8"))
        assert all(guid in known_guids or guid in builtins for guid in refs), f"unresolved custom script GUID in {scene.name}"

    character_path = ROOT / "Assets/_Project/Art/Characters/chr_enemy_e2_rifleman.glb"
    character = read_glb(character_path)
    character_primitive = character["meshes"][0]["primitives"][0]
    assert len(character.get("skins", [])[0]["joints"]) == 15, "expected 15-bone humanoid rig"
    assert "JOINTS_0" in character_primitive["attributes"] and "WEIGHTS_0" in character_primitive["attributes"], "character is not weighted to its rig"
    authored_clips = len(character.get("animations", []))
    weapon_files = sorted((ROOT / "Assets/_Project/Art/Weapons").glob("*.glb"))
    assert len(weapon_files) == 26, f"expected 26 weapon GLBs, found {len(weapon_files)}"
    for weapon_path in weapon_files:
        weapon = read_glb(weapon_path)
        assert len(weapon.get("meshes", [])) == 4, f"weapon should have four separate meshes: {weapon_path.name}"
        assert all(len(mesh.get("primitives", [])) == 1 for mesh in weapon["meshes"]), f"unexpected multi-primitive weapon mesh: {weapon_path.name}"
        assert all(primitive.get("material", 0) == 0 for mesh in weapon["meshes"] for primitive in mesh["primitives"]), f"unexpected weapon material index: {weapon_path.name}"
    print(f"PASS: {len(mission_files)} tactical maps and {len(scene_entries)} scene GUID/meta pairs checked; barrier {triangles} triangles, {dimensions[0]:.2f}×{dimensions[1]:.2f}×{dimensions[2]:.2f}m, ground pivot 0; HUD/GLB skinning/procedural motion wiring present; sample soldier has {len(character['skins'][0]['joints'])} weighted joints and {authored_clips} authored clips; all {len(weapon_files)} four-mesh weapon GLBs checked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
