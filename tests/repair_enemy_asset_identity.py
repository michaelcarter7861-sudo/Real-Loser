#!/usr/bin/env python3
"""Repair and validate mission enemy class-to-GLB identity mappings."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MISSION_DIRS = [
    ROOT,
    ROOT / "Assets" / "_Project" / "Missions",
    ROOT / "Assets" / "StreamingAssets" / "Missions",
]
CHARACTER_DIR = ROOT / "Assets" / "_Project" / "Art" / "Characters"
CLASS_TO_ASSET = {
    "E1": "chr_enemy_e1_recruit",
    "E2": "chr_enemy_e2_rifleman",
    "E3": "chr_enemy_e3_officer",
    "E4": "chr_enemy_e4_shotgunner",
    "E5": "chr_enemy_e5_smg_runner",
    "E6": "chr_enemy_e6_sniper",
    "E7": "chr_enemy_e7_heavy_gunner",
    "E8": "chr_enemy_e8_shield_breacher",
    "E9": "chr_enemy_e9_technician",
    "E10": "chr_enemy_e10_dog_handler",
    "E11": "chr_enemy_e11_medic",
    "E12": "chr_enemy_e12_elite_commando",
    "E13": "chr_enemy_e13_ghillie_spotter",
    "E14": "chr_enemy_e14_juggernaut",
}
BOSS_ASSETS = {
    "chr_boss_captain_dar",
    "chr_boss_commander_rask",
    "chr_boss_viktor_hale",
}


def expected_asset(enemy: dict) -> str:
    enemy_class = enemy.get("class")
    if enemy_class not in CLASS_TO_ASSET:
        raise ValueError(f"{enemy.get('id')}: unknown/missing class {enemy_class!r}")
    current = enemy.get("asset_id")
    if enemy_class == "E14" and current in BOSS_ASSETS:
        return current
    return CLASS_TO_ASSET[enemy_class]


def encode(data: dict) -> bytes:
    return (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="write canonical asset_id values to all three mission copies")
    args = parser.parse_args()

    changed = 0
    filled = 0
    checked = 0
    for index in range(1, 11):
        name = f"M{index:02d}.json"
        source = MISSION_DIRS[0] / name
        data = json.loads(source.read_text(encoding="utf-8"))
        for enemy in data.get("enemies", []):
            expected = expected_asset(enemy)
            if enemy.get("asset_id") != expected:
                changed += 1
                if not enemy.get("asset_id"):
                    filled += 1
                enemy["asset_id"] = expected
            asset_path = CHARACTER_DIR / f"{expected}.glb"
            if not asset_path.is_file():
                raise FileNotFoundError(f"{name}/{enemy.get('id')}: missing GLB {asset_path}")

        expected_bytes = encode(data)
        for mission_dir in MISSION_DIRS:
            path = mission_dir / name
            if args.apply:
                path.write_bytes(expected_bytes)
            elif not path.is_file() or path.read_bytes() != expected_bytes:
                raise ValueError(f"{path} differs from canonical class-to-asset mapping; rerun with --apply")
            checked += 1

    print(f"Enemy identity: PASS; {checked} mission copies checked; {changed} asset_id values corrected; {filled} missing asset_id values filled.")
    print("Class map: E1-E14 map to same-class character GLBs; explicit E14 boss assets are preserved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
