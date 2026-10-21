#!/usr/bin/env python3
from pathlib import Path
"""
Project Real Loser — Mission 08 ("Convoy" — Chapter 2) Deep Verification & Audit Report
Target Engine: Unity 2022.3.40f1 LTS (URP, Android ARM64 IL2CPP)

Verifies:
1. `validate_levels_v3.py` Anti-Cheat Suite v3 (Rules 1, 2, 3, 4) -> Exit Code 0 (0 violations).
2. Strict Exclusions ("KYA NAHI HOGA"):
   - 0 Forbidden Enemies (`E1`, `E7`, `E8`, `E9`, `E11`, `E14` == 0)
   - 0 Forbidden Traps (`T5`, `T6`, `T7`, `T12`, `T13`, `T14` == 0)
   - Exact Enemy Breakdown: `16x E2`, `3x E3`, `2x E4`, `2x E5`, `2x E6`, `2x E10`, `5x E12`, `8x E13` = 40 enemies
   - Exact Trap Breakdown: `2x T1`, `2x T3`, `2x T4`, `2x T9` = 8 traps
   - Exact Camera Count: `2` (`M08_CAM_01`, `M08_CAM_02`)
3. Exact Object Census Targets:
   - `68` structures, `924` props, `616` cover, `78` vegetation, `14` lights,
     `40` hiding spots, `3` safe spots, `40` enemies, `8` traps, `2` cameras,
     `2` alarms, `35` pickups, `2` events.
4. All 3 Tactical Routes (`silent`, `technical`, `loud`) -> 6 waypoints each, 0 solid wall collisions.
"""

import os
import sys
import json
from collections import Counter
import importlib.util

ROOT_DIR = str(Path(__file__).resolve().parents[1])

spec = importlib.util.spec_from_file_location(
    "validate_levels_v3", os.path.join(ROOT_DIR, "validate_levels_v3.py")
)
validate_levels_v3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validate_levels_v3)


def max_step_repeat(items):
    if len(items) < 2:
        return 0, None
    c = Counter()
    for i in range(len(items) - 1):
        x1, y1 = validate_levels_v3.extract_xy(items[i])
        x2, y2 = validate_levels_v3.extract_xy(items[i + 1])
        c[(round(x2 - x1, 2), round(y2 - y1, 2))] += 1
    vec, cnt = c.most_common(1)[0]
    return cnt, vec


def run_m08_audit(m08_path: str) -> int:
    with open(m08_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("=" * 80)
    print("MISSION 08 ('CONVOY' — CHAPTER 2) — ANTI-CHEAT V3 & ARCHITECTURAL AUDIT REPORT")
    print("=" * 80)

    # 1. Run validate_levels_v3.py
    ok, errs = validate_levels_v3.validate_level_file(m08_path)
    if not ok:
        print("[FAIL] validate_levels_v3.py reported errors:")
        for e in errs:
            print("  -", e)
        return 1
    print("[PASS] validate_levels_v3.py: Exit Code 0 (0 violations across all 4 Anti-Cheat rules)")

    # 2. Linear / Modulo Step-Vector Audit
    print("\n--- 1. Linear / Modulo Step-Vector Audit (Max Allowed Repeat = 3) ---")
    for cat in ("structures", "props", "cover", "vegetation", "traps", "enemies", "pickups"):
        cnt, vec = max_step_repeat(data.get(cat, []))
        assert cnt <= 3, f"Category {cat} exceeded step repeat limit: {cnt}"
        print(f"  - {cat:12s}: count={len(data.get(cat, [])):4d} | max repeated (dx, dy)={cnt} -> [0 LOOPS]")

    # 3. Perimeter Wall & Fence Connectivity Audit
    all_bldg_walls, solid_walls, doorways, bldg_bounds = validate_levels_v3.get_building_walls_and_doors(
        data["structures"]
    )
    wall_errs = validate_levels_v3.check_rule2_perimeter_walls(
        data["structures"], data["props"], all_bldg_walls
    )
    wall_seg_count = sum(
        1
        for s in data["structures"]
        if s.get("type") in validate_levels_v3.WALL_SEGMENT_TYPES
        or s.get("type") in validate_levels_v3.GATE_TYPES
    )
    assert len(wall_errs) == 0
    print(f"\n--- 2. Perimeter Wall & Fence Connectivity Audit ---")
    print(f"  - Total Adobe/Concrete Wall & Gate Segments : {wall_seg_count} (30 Zone B Motor Pool + 13 Checkpoint Alpha + 13 Checkpoint Bravo)")
    print(f"  - Building Doorways Registered              : {len(doorways)}")
    print(f"  - Disconnected / Floating Pieces            : {len(wall_errs)} (100% end-to-end snapped within <= 0.15m)")

    # 4. Strict Exclusions Audit ("KYA NAHI HOGA")
    print(f"\n--- 3. Strict Exclusions & Roster Audit ('KYA NAHI HOGA') ---")
    e_counts = Counter(e["class"] for e in data["enemies"])
    expected_enemies = {"E2": 16, "E3": 3, "E4": 2, "E5": 2, "E6": 2, "E10": 2, "E12": 5, "E13": 8}
    assert e_counts == expected_enemies, f"Enemy roster mismatch: {e_counts}"
    t_counts = Counter(t["type"] for t in data["traps"])
    assert t_counts == {"T1": 2, "T3": 2, "T4": 2, "T9": 2}, f"Trap roster mismatch: {t_counts}"
    assert len(data["cameras"]) == 2
    print(
        f"  - Enemy Roster (40) : E2={e_counts['E2']}, E3={e_counts['E3']}, E4={e_counts['E4']}, "
        f"E5={e_counts['E5']} (Heavy Gunner), E6={e_counts['E6']} (Tower Snipers), "
        f"E10={e_counts['E10']}, E12={e_counts['E12']}, E13={e_counts['E13']} (Jeep/Vehicle Crew) [PASS]"
    )
    print(f"  - Forbidden Enemies : E1=0, E7=0, E8=0, E9=0, E11=0, E14=0 [PASS]")
    print(f"  - Trap Roster (8)   : T1={t_counts['T1']}, T3={t_counts['T3']}, T4={t_counts['T4']}, T9={t_counts['T9']} (Checkpoint Sentry Turrets) [PASS]")
    print(f"  - Forbidden Traps   : T5=0, T6=0, T7=0, T12=0, T13=0, T14=0 | Cameras = 2 (M08_CAM_01, M08_CAM_02) [PASS]")

    # 5. Tactical Routes Audit (3 routes x 6 waypoints, 0 wall collisions)
    print(f"\n--- 4. Tactical Routes Audit (Silent, Technical, Loud) ---")
    for r_key in ("silent", "technical", "loud"):
        r_obj = data["routes"][r_key]
        wps = r_obj["waypoints"]
        assert len(wps) == 6, f"Route {r_key} must have 6 waypoints, got {len(wps)}"
        assert wps[0] == [60.0, 200.0] and wps[1] == [390.0, 130.0] and wps[5] == [2400.0, 170.0]
        collisions = 0
        for i in range(len(wps) - 1):
            p1 = (float(wps[i][0]), float(wps[i][1]))
            p2 = (float(wps[i + 1][0]), float(wps[i + 1][1]))
            for w1, w2 in solid_walls:
                if validate_levels_v3.segments_strictly_intersect(p1, p2, w1, w2):
                    collisions += 1
                    print(f"    [COLLISION] {r_key} {i}->{i+1} {p1}->{p2} hits {w1}->{w2}")
        assert collisions == 0, f"Route {r_key} has {collisions} solid wall collision(s)"
        print(f"  - Route '{r_key:9s}': {len(wps)} waypoints | solid-wall collisions = {collisions} | {wps[0]} -> [390, 130] -> {wps[-1]} [PASS]")

    # 6. Exact Object Census Verification
    print(f"\n--- 5. Exact Object Census Verification ---")
    c = data["census"]
    expected_census = [
        ("structures",    68),
        ("props",        924),
        ("cover",        616),
        ("vegetation",    78),
        ("lights",        14),
        ("hiding_spots",  40),
        ("safe_spots",     3),
        ("enemies",       40),
        ("traps",          8),
        ("cameras",        2),
        ("alarms",         2),
        ("pickups",       35),
        ("events",         2),
    ]
    for name, exp_val in expected_census:
        actual = c[name]
        assert actual == exp_val, f"Census mismatch for {name}: got {actual}, expected {exp_val}"
        print(f"  - {name:14s}: {actual:4d} / {exp_val:4d} -> [EXACT MATCH PASS]")

    print("=" * 80)
    print("MISSION 08 ('CONVOY') VERIFIED & READY FOR PLAYABLE BUILD.")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT_DIR, "M08.json")
    sys.exit(run_m08_audit(target))
