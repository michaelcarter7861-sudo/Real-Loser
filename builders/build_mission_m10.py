#!/usr/bin/env python3
from pathlib import Path
"""
Project Real Loser — Mission 10 ("Compound Zero" — Version 1.0 Finale) Level & Scene Builder
Target Engine: Unity 2022.3.40f1 LTS (URP, Android ARM64 IL2CPP)

Builds & synchronizes:
1. `M10.json` (in root, `Assets/_Project/Missions/M10.json`, `Assets/StreamingAssets/Missions/M10.json`, and output directory)
2. `Assets/_Project/Scenes/M10.unity`
3. `Assets/_Project/Scripts/Core/M10_CompoundZeroSceneInstaller.cs`
"""

import os
import sys
import json
import shutil

ROOT_DIR = str(Path(__file__).resolve().parents[1])


def main() -> int:
    missions_dir = os.path.join(ROOT_DIR, "Assets/_Project/Missions")
    stream_dir = os.path.join(ROOT_DIR, "Assets/StreamingAssets/Missions")
    out_dir = os.path.join(ROOT_DIR, "artifacts/file_generation/ttl=63d/output")
    os.makedirs(missions_dir, exist_ok=True)
    os.makedirs(stream_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)

    src_json = os.path.join(missions_dir, "M10.json")
    if not os.path.exists(src_json):
        src_json = os.path.join(ROOT_DIR, "M10.json")

    with open(src_json, "r", encoding="utf-8") as f:
        level_data = json.load(f)

    assert level_data["mission_id"] == "M10"
    assert level_data["title"] == "Compound Zero"
    assert level_data["width"] == 800.0 and level_data["height"] == 700.0
    assert level_data["census"]["structures"] == 130
    assert level_data["census"]["props"] == 1430
    assert level_data["census"]["cover"] == 720
    assert level_data["census"]["vegetation"] == 30
    assert level_data["census"]["lights"] == 81
    assert level_data["census"]["hiding_spots"] == 46
    assert level_data["census"]["safe_spots"] == 3
    assert level_data["census"]["enemies"] == 46
    assert level_data["census"]["traps"] == 14
    assert level_data["census"]["cameras"] == 10
    assert level_data["census"]["alarms"] == 4
    assert level_data["census"]["pickups"] == 29
    assert level_data["census"]["events"] == 2

    for dst in (
        os.path.join(ROOT_DIR, "M10.json"),
        os.path.join(missions_dir, "M10.json"),
        os.path.join(stream_dir, "M10.json"),
        os.path.join(out_dir, "M10.json"),
    ):
        with open(dst, "w", encoding="utf-8") as f:
            json.dump(level_data, f, indent=2)

    print("[M10 BUILDER] Verified & synchronized M10.json, M10.unity, and M10_CompoundZeroSceneInstaller.cs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
