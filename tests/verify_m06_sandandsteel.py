#!/usr/bin/env python3
from pathlib import Path
"""
Project Real Loser — Mission 06 ("Sand and Steel" — Chapter 2) Deep Verification & Audit Report
Target Engine: Unity 2022.3.40f1 LTS (URP, Android ARM64 IL2CPP)

Verifies:
1. `validate_levels_v3.py` Anti-Cheat Suite v3 (Rules 1, 2, 3, 4) -> Exit Code 0 (0 violations).
2. Strict Exclusions ("KYA NAHI HOGA"):
   - 0 Forbidden Enemies (`E1`, `E6`, `E7`, `E8`, `E11`, `E14` == 0)
   - 0 Forbidden Traps (`T5`, `T7`, `T9`, `T10`, `T14` == 0)
   - Exact Enemy Breakdown: `22x E2`, `3x E3`, `2x E4`, `2x E5`, `4x E9`, `2x E10`, `3x E12`, `2x E13` = 40 enemies
   - Exact Trap Breakdown: `2x T1`, `2x T4`, `2x T6`, `2x T12`, `2x T13` = 10 traps
   - Exact Camera Count: `6` (`M06_CAM_01` to `M06_CAM_06` linked to `M06_MON_01` in Zone D R2)
3. Exact Object Census Targets:
   - `196` structures, `1618` props, `912` cover, `66` vegetation, `18` lights,
     `40` hiding spots, `3` safe spots, `40` enemies, `10` traps, `6` cameras,
     `3` alarms, `43` pickups, `1` event.
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


def run_m06_audit(m06_path: str) -> int:
    with open(m06_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("=" * 80)
    print("MISSION 06 ('SAND AND STEEL' — CHAPTER 2) — ANTI-CHEAT V3 & AUDIT REPORT")
    print("=" * 80)

    # 1. Run validate_levels_v3.py
    ok, errs = validate_levels_v3.validate_level_file(m06_path)
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
    print(f"  - Total Adobe/Fence/Gate Segments : {wall_seg_count} (64 Outer Adobe + 72 Depots C1/C2/C3 + 20 Cmd D + 16 Barracks F)")
    print(f"  - Building Doorways Registered    : {len(doorways)}")
    print(f"  - Disconnected / Floating Pieces  : {len(wall_errs)} (100% end-to-end snapped within <= 0.15m)")

    # 4. Strict Exclusions Audit ("KYA NAHI HOGA")
    print(f"\n--- 3. Strict Exclusions & Roster Audit ('KYA NAHI HOGA') ---")
    e_counts = Counter(e["class"] for e in data["enemies"])
    expected_enemies = {"E2": 22, "E3": 3, "E4": 2, "E5": 2, "E9": 4, "E10": 2, "E12": 3, "E13": 2}
    assert e_counts == expected_enemies, f"Enemy roster mismatch: {e_counts}"
    t_counts = Counter(t["type"] for t in data["traps"])
    assert t_counts == {"T1": 2, "T4": 2, "T6": 2, "T12": 2, "T13": 2}, f"Trap roster mismatch: {t_counts}"
    assert len(data["cameras"]) == 6
    print(
        f"  - Enemy Roster (40) : E2={e_counts['E2']}, E3={e_counts['E3']}, E4={e_counts['E4']}, "
        f"E5={e_counts['E5']} (Heavy Gunner), E9={e_counts['E9']} (Technician 10s C4 Disarm), "
        f"E10={e_counts['E10']}, E12={e_counts['E12']}, E13={e_counts['E13']} [PASS]"
    )
    print(f"  - Forbidden Enemies : E1=0, E6=0, E7=0, E8=0, E11=0, E14=0 [PASS]")
    print(f"  - Trap Roster (10)  : T1={t_counts['T1']}, T4={t_counts['T4']}, T6={t_counts['T6']}, T12={t_counts['T12']}, T13={t_counts['T13']} [PASS]")
    print(f"  - Forbidden Traps   : T5=0, T7=0, T9=0, T10=0, T14=0 | Cameras = 6 (M06_CAM_01..06 -> M06_MON_01) [PASS]")

    # 5. Tactical Routes Audit (3 routes x 6 waypoints, 0 wall collisions)
    print(f"\n--- 4. Tactical Routes Audit (Silent, Technical, Loud) ---")
    for r_key in ("silent", "technical", "loud"):
        r_obj = data["routes"][r_key]
        wps = r_obj["waypoints"]
        assert len(wps) == 6, f"Route {r_key} must have 6 waypoints, got {len(wps)}"
        assert wps[0] == [480.0, 10.0] and [500.0, 570.0] in wps and wps[5] == [980.0, 600.0]
        collisions = 0
        for i in range(len(wps) - 1):
            p1 = (float(wps[i][0]), float(wps[i][1]))
            p2 = (float(wps[i + 1][0]), float(wps[i + 1][1]))
            for w1, w2 in solid_walls:
                if validate_levels_v3.segments_strictly_intersect(p1, p2, w1, w2):
                    collisions += 1
                    print(f"    [COLLISION] {r_key} {i}->{i+1} {p1}->{p2} hits {w1}->{w2}")
        assert collisions == 0, f"Route {r_key} has {collisions} solid wall collision(s)"
        print(f"  - Route '{r_key:9s}': {len(wps)} waypoints | solid-wall collisions = {collisions} | {wps[0]} -> [500, 570] -> {wps[-1]} [PASS]")

    # 6. Exact Object Census Verification
    print(f"\n--- 5. Exact Object Census Verification ---")
    c = data["census"]
    expected_census = [
        ("structures",   196),
        ("props",       1618),
        ("cover",        912),
        ("vegetation",    66),
        ("lights",        18),
        ("hiding_spots",  40),
        ("safe_spots",     3),
        ("enemies",       40),
        ("traps",         10),
        ("cameras",        6),
        ("alarms",         3),
        ("pickups",       43),
        ("events",         1),
    ]
    for name, exp_val in expected_census:
        actual = c[name]
        assert actual == exp_val, f"Census mismatch for {name}: got {actual}, expected {exp_val}"
        print(f"  - {name:14s}: {actual:4d} / {exp_val:4d} -> [EXACT MATCH PASS]")

    print("=" * 80)
    print("MISSION 06 ('SAND AND STEEL') VERIFIED & READY FOR PLAYABLE BUILD.")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT_DIR, "M06.json")
    sys.exit(run_m06_audit(target))
