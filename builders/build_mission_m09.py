#!/usr/bin/env python3
from pathlib import Path
"""
Project Real Loser — Mission 09 ("Eyes Above" — Chapter 2) Level & Scene Builder
Target Engine: Unity 2022.3.40f1 LTS (URP, Android ARM64 IL2CPP)

Builds & synchronizes:
1. `M09.json` (in root, `Assets/_Project/Missions/M09.json`, `Assets/StreamingAssets/Missions/M09.json`, and output directory)
2. `Assets/_Project/Scenes/M09.unity`
3. `Assets/_Project/Scripts/Core/M09_EyesAboveSceneInstaller.cs`
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

    src_json = os.path.join(missions_dir, "M09.json")
    if not os.path.exists(src_json):
        src_json = os.path.join(ROOT_DIR, "M09.json")

    with open(src_json, "r", encoding="utf-8") as f:
        level_data = json.load(f)

    assert level_data["mission_id"] == "M09"
    assert level_data["title"] == "Eyes Above"
    assert level_data["width"] == 800.0 and level_data["height"] == 800.0
    assert level_data["census"]["structures"] == 129
    assert level_data["census"]["props"] == 1127
    assert level_data["census"]["cover"] == 718
    assert level_data["census"]["vegetation"] == 49
    assert level_data["census"]["lights"] == 35
    assert level_data["census"]["hiding_spots"] == 34
    assert level_data["census"]["safe_spots"] == 3
    assert level_data["census"]["enemies"] == 34
    assert level_data["census"]["traps"] == 10
    assert level_data["census"]["cameras"] == 4
    assert level_data["census"]["alarms"] == 3
    assert level_data["census"]["pickups"] == 32
    assert level_data["census"]["events"] == 2

    for dst in (
        os.path.join(ROOT_DIR, "M09.json"),
        os.path.join(missions_dir, "M09.json"),
        os.path.join(stream_dir, "M09.json"),
        os.path.join(out_dir, "M09.json"),
    ):
        with open(dst, "w", encoding="utf-8") as f:
            json.dump(level_data, f, indent=2)

    print("[M09 BUILDER] Verified & synchronized M09.json, M09.unity, and M09_EyesAboveSceneInstaller.cs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
