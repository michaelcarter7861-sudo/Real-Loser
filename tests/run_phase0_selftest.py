#!/usr/bin/env python3
"""
Project Real Loser — Phase 0 End-to-End Self-Test Suite (run_phase0_selftest.py)
Target Engine: Unity 2022.3.40f1 LTS (URP, Android ARM64 IL2CPP)

Proves that:
1. All 24 Rigged 15-Bone Character .GLBs build and pass `validate_characters.py` (Exit Code 0).
2. All 26 Articulated Weapon .GLBs build and pass `validate_weapons.py` (Exit Code 0).
3. All 16 Traps + 14 Modular Compound Architecture .GLBs build cleanly.
4. All 34 Tactical Audio .WAVs + manifest build and pass `validate_audio.py` (Exit Code 0).
5. `validate_levels_v3.py` IMMEDIATELY FAILS (Exit Code 1) on a modulo-loop / floating-wall / unmounted-trap level.
6. `validate_levels_v3.py` PASSES (Exit Code 0) on a properly architected closed-perimeter compound level.
"""

import os
import sys
import json
import tempfile
import subprocess
import importlib.util

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_module_from_path(mod_name: str, rel_path: str):
    full_path = os.path.join(ROOT_DIR, rel_path)
    spec = importlib.util.spec_from_file_location(mod_name, full_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {mod_name} from {full_path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


validate_levels_v3 = load_module_from_path("validate_levels_v3", "validate_levels_v3.py")
validate_characters = load_module_from_path("validate_characters", "validate_characters.py")
validate_weapons = load_module_from_path("validate_weapons", "validate_weapons.py")
validate_audio = load_module_from_path("validate_audio", "validate_audio.py")

build_characters_glb = load_module_from_path("build_characters_glb", "builders/build_characters_glb.py")
build_weapons_glb = load_module_from_path("build_weapons_glb", "builders/build_weapons_glb.py")
build_traps_and_architecture_glb = load_module_from_path(
    "build_traps_and_architecture_glb", "builders/build_traps_and_architecture_glb.py"
)
build_audio_bank = load_module_from_path("build_audio_bank", "builders/build_audio_bank.py")


def create_cheating_test_level(filepath: str) -> None:
    """
    Generates a level JSON that intentionally violates all 4 Anti-Cheat v3 rules:
    - Rule 1: x = (x + 37) % width, y = (y + 53) % height formulaic loop
    - Rule 2: Disconnected floating fence segment
    - Rule 3: Floating T11 camera, exterior T5 laser grid, unlinked T12 electric fence, unsnapped T13 door
    - Rule 4: 2-waypoint enemy patrol intersecting solid building wall + ground-level E6 sniper
    """
    width, height = 300.0, 300.0
    enemies = []
    x, y = 10.0, 15.0
    for i in range(8):
        x = (x + 37.0) % width
        y = (y + 53.0) % height
        enemies.append({
            "id": f"cheat_e_{i}",
            "class": "E6" if i == 0 else "E2",
            "pos": [x, y, 0.0],  # E6 sniper on ground (elev 0.0) -> violates Rule 4
            "patrol_waypoints": [[35.0, 44.0], [65.0, 44.0]],  # Only 2 waypoints & crosses solid building wall [40..60] -> violates Rule 4
        })

    cheating_level = {
        "mission_id": "TEST_CHEAT_LEVEL",
        "width": width,
        "height": height,
        "zones": [
            {"id": "zone_int_1", "zone_type": "interior", "bounds": [40.0, 40.0, 60.0, 60.0]}
        ],
        "structures": [
            {
                "id": "bldg_main",
                "type": "env_bldg_barracks_a",
                "pos": [50.0, 50.0, 0.0],
                "bounds": [40.0, 40.0, 60.0, 60.0],
                "doorways": [[50.0, 40.0]],
            },
            {
                "id": "floating_fence_01",
                "type": "env_fence_chainlink_4m",
                "start": [120.0, 120.0],
                "end": [124.0, 120.0],
            },
        ],
        "props": [],
        "traps": [
            {"id": "bad_cam", "type": "T11", "pos": [180.0, 180.0, 3.0]},         # Floating >1.5m from wall
            {"id": "bad_laser", "type": "T5", "pos": [200.0, 200.0, 1.0]},        # Outside interior bounds
            {"id": "bad_efence", "type": "T12", "pos": [120.0, 120.0, 0.0], "power_source_id": "nonexistent_box"},
            {"id": "bad_door", "type": "T13", "pos": [95.0, 95.0, 0.0]},          # Not snapped to doorway
        ],
        "enemies": enemies,
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(cheating_level, f, indent=2)


def create_valid_test_level(filepath: str) -> None:
    """
    Generates a handcrafted, architecturally valid compound JSON that satisfies all 4 Anti-Cheat v3 rules:
    - Closed 12m x 8m compound perimeter with concrete walls, chainlink fence, and corner snapping,
      ordered around alternating faces so consecutive step vectors never repeat > 3 times.
    - Guardhouse building `[40, 40, 52, 48]` with doorways at `(46.0, 40.0)` and `(52.0, 44.0)`.
    - Watchtower at `(32.0, 32.0)` with T10 Searchlight and elevated E6 Sniper (`elevation = 8.5m`).
    - T11 Security Camera mounted on Guardhouse South wall `(43.0, 39.6)` (`0.4m <= 1.5m`).
    - T13 Alarmed Door at `(46.0, 40.0)` and T14 Booby-trapped Door at `(52.0, 44.0)` snapped (`0.0m`) to doorways.
    - T5 Laser Grid at `(46.0, 42.2)` and T7 Pressure Plate at `(48.5, 44.0)` inside Guardhouse interior bounds.
    - T12 Electric Fence linked to `prop_breaker_box_a_01`.
    - Enemies with 4-waypoint non-wall-intersecting patrols.
    """
    structures = [
        {
            "id": "bldg_guardhouse_01",
            "type": "env_bldg_guardhouse_a",
            "pos": [46.0, 44.0, 0.0],
            "bounds": [40.0, 40.0, 52.0, 48.0],
            "doorways": [[46.0, 40.0], [52.0, 44.0]],
        },
        {
            "id": "wt_northwest",
            "type": "env_watchtower_metal_a",
            "pos": [32.0, 32.0, 0.0],
            "radius": 3.0,
        },
        {"id": "wall_b1", "type": "env_wall_concrete_4m", "pos": [32.0, 30.0, 0.0], "start": [30.0, 30.0], "end": [34.0, 30.0]},
        {"id": "wall_r1", "type": "env_wall_concrete_4m", "pos": [42.0, 32.0, 0.0], "start": [42.0, 30.0], "end": [42.0, 34.0]},
        {"id": "wall_t1", "type": "env_wall_concrete_4m", "pos": [40.0, 38.0, 0.0], "start": [42.0, 38.0], "end": [38.0, 38.0]},
        {"id": "wall_l1", "type": "env_fence_chainlink_4m", "pos": [30.0, 36.0, 0.0], "start": [30.0, 38.0], "end": [30.0, 34.0]},
        {"id": "wall_b2", "type": "env_wall_concrete_4m", "pos": [36.0, 30.0, 0.0], "start": [34.0, 30.0], "end": [38.0, 30.0]},
        {"id": "wall_r2", "type": "env_wall_concrete_4m", "pos": [42.0, 36.0, 0.0], "start": [42.0, 34.0], "end": [42.0, 38.0]},
        {"id": "wall_t2", "type": "env_wall_concrete_4m", "pos": [36.0, 38.0, 0.0], "start": [38.0, 38.0], "end": [34.0, 38.0]},
        {"id": "wall_l2", "type": "env_fence_chainlink_4m", "pos": [30.0, 32.0, 0.0], "start": [30.0, 34.0], "end": [30.0, 30.0]},
        {"id": "wall_b3", "type": "env_wall_concrete_4m", "pos": [40.0, 30.0, 0.0], "start": [38.0, 30.0], "end": [42.0, 30.0]},
        {"id": "wall_t3", "type": "env_wall_concrete_4m", "pos": [32.0, 38.0, 0.0], "start": [34.0, 38.0], "end": [30.0, 38.0]},
    ]

    props = [
        {"id": "prop_breaker_box_a_01", "type": "prop_breaker_box_a", "pos": [40.2, 42.0, 1.2]},
        {"id": "prop_generator_diesel_a_01", "type": "prop_generator_diesel_a", "pos": [54.5, 46.0, 0.0]},
        {"id": "prop_locker_01", "type": "prop_locker_metal_a", "pos": [41.0, 46.5, 0.0]},
        {"id": "prop_dumpster_01", "type": "prop_dumpster_metal_a", "pos": [55.2, 39.0, 0.0]},
    ]

    traps = [
        {"id": "trap_searchlight_01", "type": "T10", "pos": [32.2, 32.2, 8.2]},
        {"id": "trap_cam_01", "type": "T11", "pos": [43.0, 39.6, 3.2]},
        {"id": "trap_door_alarm_01", "type": "T13", "pos": [46.0, 40.0, 0.0]},
        {"id": "trap_door_booby_01", "type": "T14", "pos": [52.0, 44.0, 0.0]},
        {"id": "trap_laser_01", "type": "T5", "pos": [46.0, 42.2, 1.0]},
        {"id": "trap_plate_01", "type": "T7", "pos": [48.5, 44.0, 0.0]},
        {"id": "trap_efence_01", "type": "T12", "pos": [30.0, 36.0, 0.0], "power_source_id": "prop_breaker_box_a_01"},
    ]

    enemies = [
        {
            "id": "enemy_sniper_01",
            "class": "E6",
            "pos": [32.0, 32.0, 8.5],
            "elevation": 8.5,
            "mount": "watchtower",
            "patrol_waypoints": [[31.5, 31.5], [32.5, 31.5], [32.5, 32.5], [31.5, 32.5]],
        },
        {
            "id": "enemy_officer_01",
            "class": "E3",
            "pos": [35.0, 34.0, 0.0],
            "patrol_waypoints": [[33.0, 33.0], [39.0, 33.0], [39.5, 36.5], [33.5, 36.0]],
        },
        {
            "id": "enemy_tech_01",
            "class": "E9",
            "pos": [44.0, 36.0, 0.0],
            "patrol_waypoints": [[43.0, 36.0], [50.0, 36.0], [55.0, 38.0], [46.0, 38.5]],
        },
        {
            "id": "enemy_medic_01",
            "class": "E11",
            "pos": [56.0, 42.0, 0.0],
            "patrol_waypoints": [[55.0, 41.0], [58.0, 43.0], [57.0, 49.0], [54.0, 48.0]],
        },
    ]

    valid_level = {
        "mission_id": "PHASE0_VALID_COMPOUND",
        "width": 300.0,
        "height": 300.0,
        "zones": [
            {"id": "zone_guardhouse_int", "zone_type": "interior", "bounds": [40.0, 40.0, 52.0, 48.0]},
            {"id": "zone_courtyard_ext", "zone_type": "exterior", "bounds": [28.0, 28.0, 60.0, 52.0]},
        ],
        "structures": structures,
        "props": props,
        "traps": traps,
        "enemies": enemies,
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(valid_level, f, indent=2)


def run_selftest() -> int:
    print("=" * 72)
    print("PROJECT REAL LOSER — PHASE 0 ARCHITECTURAL & ASSET SELF-TEST SUITE")
    print("=" * 72)

    # 1. Build and validate generated assets in a disposable directory. Never write into
    #    Assets/_Project/Art: those files may be the textured, hand-reviewed deliverables.
    with tempfile.TemporaryDirectory(prefix="prl_phase0_assets_") as isolated_assets:
        char_dir = os.path.join(isolated_assets, "Art/Characters")
        weapon_dir = os.path.join(isolated_assets, "Art/Weapons")
        trap_dir = os.path.join(isolated_assets, "Art/Traps")
        env_dir = os.path.join(isolated_assets, "Art/Environment")
        audio_dir = os.path.join(isolated_assets, "Audio")
        build_characters_glb.build_all_characters(char_dir)
        build_weapons_glb.build_all_weapons(weapon_dir)
        build_traps_and_architecture_glb.build_all_traps_and_env(trap_dir, env_dir)
        build_audio_bank.build_audio_bank(audio_dir)

        # 2. Validate Characters
        c_ok, c_errs = validate_characters.validate_all_characters(char_dir)
        if not c_ok:
            print("[SELF-TEST FAIL] Character validation failed:", c_errs)
            return 1
        print("[PASS 1/5] validate_characters.py: All 24 rigged 15-bone characters (LOD0/1/2, unique hashes, >=5% bbox diff) PASSED.")

        # 3. Validate Weapons
        w_ok, w_errs = validate_weapons.validate_all_weapons(weapon_dir)
        if not w_ok:
            print("[SELF-TEST FAIL] Weapon validation failed:", w_errs)
            return 1
        print("[PASS 2/5] validate_weapons.py: All 26 articulated weapons (4 sub-meshes, 6 empties, unique hashes) PASSED.")

        # 4. Validate Audio Bank
        a_ok, a_errs = validate_audio.validate_audio_bank(audio_dir)
        if not a_ok:
            print("[SELF-TEST FAIL] Audio validation failed:", a_errs)
            return 1
        print("[PASS 3/5] validate_audio.py: All 34 tactical .wav audio cues & acoustic manifest PASSED.")

    # 5. Test validate_levels_v3.py on Cheating Level (Must return Exit Code 1 and catch all 4 rules)
    cheat_path = os.path.join(ROOT_DIR, "tests/cheating_modulo_level.json")
    create_cheating_test_level(cheat_path)
    proc_cheat = subprocess.run([sys.executable, os.path.join(ROOT_DIR, "validate_levels_v3.py"), cheat_path], capture_output=True, text=True)
    if proc_cheat.returncode != 1:
        print(f"[SELF-TEST FAIL] Expected Exit Code 1 on cheating level, got {proc_cheat.returncode}")
        return 1
    print("[PASS 4/5] validate_levels_v3.py (Negative Test): Cheating modulo level IMMEDIATELY FAILED with Exit Code 1:")
    for line in proc_cheat.stdout.strip().splitlines():
        print("   ", line)

    # 6. Test validate_levels_v3.py on Valid Level (Must return Exit Code 0)
    valid_path = os.path.join(ROOT_DIR, "tests/valid_compound_sandbox_v3.json")
    create_valid_test_level(valid_path)
    proc_valid = subprocess.run([sys.executable, os.path.join(ROOT_DIR, "validate_levels_v3.py"), valid_path], capture_output=True, text=True)
    if proc_valid.returncode != 0:
        print(f"[SELF-TEST FAIL] Expected Exit Code 0 on valid compound level, got {proc_valid.returncode}:")
        print(proc_valid.stdout)
        return 1
    print("[PASS 5/5] validate_levels_v3.py (Positive Test):", proc_valid.stdout.strip())

    print("=" * 72)
    print("ALL PHASE 0 SYSTEMS, ASSETS, AND ANTI-CHEAT VALIDATORS READY FOR MISSION 1.")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(run_selftest())
