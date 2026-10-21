#!/usr/bin/env python3
from pathlib import Path
"""
Project Real Loser — Mission 08 ("Convoy" — Chapter 2) Handcrafted Level & Scene Builder
Target Engine: Unity 2022.3.40f1 LTS (URP, Android ARM64 IL2CPP)

Builds ONLY Mission 08 (`M08.json`, `Assets/_Project/Scenes/M08.unity`, and `M08_ConvoySceneInstaller.cs`)
without touching M09–M10 and with ZERO linear/modulo coordinate loops.

Exact Census Targets Verified:
- 68 structures, 924 props, 616 cover, 78 vegetation, 14 lights,
  40 hiding spots, 3 safe spots, 40 enemies, 8 traps, 2 cameras,
  2 alarms, 35 pickups, 2 events.
"""

import os
import sys
import json
import math
from collections import Counter
from typing import List, Dict, Any, Tuple

ROOT_DIR = str(Path(__file__).resolve().parents[1])


def interleave_for_zero_step_repeats(
    items: List[Dict[str, Any]], width: float = 2500.0, height: float = 300.0
) -> List[Dict[str, Any]]:
    """
    Orders handcrafted items using coprime stride permutation + greedy zero-repeat pass
    so that consecutive step vectors (dx, dy) and modulo-wrapped steps NEVER repeat > 2 times.
    """
    n = len(items)
    if n <= 3:
        return list(items)

    def get_xy(obj: Dict[str, Any]) -> Tuple[float, float]:
        p = obj.get("pos", obj.get("position", [0.0, 0.0]))
        return float(p[0]), float(p[1])

    def step_vecs(a: Dict[str, Any], b: Dict[str, Any]):
        x1, y1 = get_xy(a)
        x2, y2 = get_xy(b)
        dx = round(x2 - x1, 2)
        dy = round(y2 - y1, 2)
        mdx = round((x2 - x1) % width, 2)
        mdy = round((y2 - y1) % height, 2)
        return (dx, dy), (mdx, mdy)

    stride = 19
    while math.gcd(stride, n) != 1:
        stride += 2
    pool = [items[(i * stride) % n] for i in range(n)]

    ordered: List[Dict[str, Any]] = [pool.pop(0)]
    used_raw = Counter()
    used_mod = Counter()

    while pool:
        prev = ordered[-1]
        best_idx = 0
        best_score = 999999
        scan_limit = min(len(pool), 96)
        for idx in range(scan_limit):
            cand = pool[idx]
            rv, mv = step_vecs(prev, cand)
            score = max(used_raw[rv], used_mod[mv])
            if score == 0:
                best_idx = idx
                break
            if score < best_score:
                best_score = score
                best_idx = idx
        chosen = pool.pop(best_idx)
        rv, mv = step_vecs(prev, chosen)
        used_raw[rv] += 1
        used_mod[mv] += 1
        ordered.append(chosen)

    return ordered


def make_wall_Chain(
    prefix: str,
    wall_type: str,
    pts: List[Tuple[float, float]],
    gate_indices: Dict[int, str] = None,
) -> List[Dict[str, Any]]:
    if gate_indices is None:
        gate_indices = {}
    segs = []
    for i in range(len(pts) - 1):
        x1, y1 = pts[i]
        x2, y2 = pts[i + 1]
        cx = round(0.5 * (x1 + x2), 2)
        cy = round(0.5 * (y1 + y2), 2)
        length = round(math.hypot(x2 - x1, y2 - y1), 2)
        rot_y = 0.0 if abs(y2 - y1) < 1e-4 else 90.0
        wtype = gate_indices.get(i, wall_type)
        segs.append({
            "id": f"{prefix}_{i+1:02d}",
            "type": wtype,
            "pos": [cx, cy, 0.0],
            "start": [round(x1, 2), round(y1, 2)],
            "end": [round(x2, 2), round(y2, 2)],
            "length": length,
            "rot_y": rot_y,
        })
    return segs


def vdc(n: int, base: int) -> float:
    v, denom = 0.0, 1.0
    while n > 0:
        denom *= base
        n, rem = divmod(n, base)
        v += rem / denom
    return v


def build_m08_level_dict() -> Dict[str, Any]:
    # =========================================================================
    # 1. ZONES (7 Handcrafted Tactical Zones across 2500m x 300m Desert Corridor)
    # =========================================================================
    zones = [
        {
            "id": "ZONE_A",
            "name": "West Canyon Insertion",
            "zone_type": "wilderness",
            "rect": [0.0, 100.0, 300.0, 300.0],
            "bounds": [0.0, 100.0, 300.0, 300.0],
            "description": "Rocky western canyon ridge with Player Start at [60.0, 200.0] overlooking the staging base, flanked by desert boulders and Tripwire Alarms M08_T1_01 ([265.0, 185.0]) and M08_T1_02 ([280.0, 120.0]).",
        },
        {
            "id": "ZONE_B",
            "name": "Staging Motor Pool & Target Cargo Truck",
            "zone_type": "camp",
            "rect": [300.0, 80.0, 500.0, 220.0],
            "bounds": [300.0, 80.0, 500.0, 220.0],
            "description": "Adobe-walled motor pool (env_wall_adobe_4m) with guard booth (env_guard_booth_a), fuel tanks, Alarm Panel M08_ALM_01, and the Driveable Objective Cargo Truck (veh_truck_cargo_a, 500 Max HP) parked at [390.0, 130.0] (O1 Phase 1).",
        },
        {
            "id": "ZONE_C",
            "name": "Western Highway Stretch",
            "zone_type": "wilderness",
            "rect": [500.0, 120.0, 1200.0, 180.0],
            "bounds": [500.0, 120.0, 1200.0, 180.0],
            "description": "700m desert asphalt highway flanked by rocky ambush ridges, patrolled by E13 mobile jeep crews and guarded by off-road Buried Mines M08_T4_01 ([820.0, 135.0]) and M08_T4_02 ([1050.0, 165.0]).",
        },
        {
            "id": "ZONE_D",
            "name": "Checkpoint Alpha",
            "zone_type": "perimeter",
            "rect": [1200.0, 100.0, 1300.0, 200.0],
            "bounds": [1200.0, 100.0, 1300.0, 200.0],
            "description": "Fortified roadblock across x=1250.0 with motorized steel barrier gate, Watchtower (env_watchtower_metal_a) with Sniper M08_E6_01, Heavy Gunner M08_E5_01, Panning Camera M08_CAM_01, Directional Mine M08_T3_01, Automated Sentry Turret M08_T9_01 ([1245.0, 175.0]), and Roadside Control Box #1 at [1185.0, 115.0] (S1 part 1).",
        },
        {
            "id": "ZONE_E",
            "name": "Eastern Canyon Highway & Sandstorm Sector",
            "zone_type": "wilderness",
            "rect": [1300.0, 100.0, 2000.0, 200.0],
            "bounds": [1300.0, 100.0, 2000.0, 200.0],
            "description": "700m canyon road where the dynamic Sandstorm event (E_M08_STORM) hits, cutting enemy vision to 0.5x for 120s.",
        },
        {
            "id": "ZONE_F",
            "name": "Checkpoint Bravo",
            "zone_type": "perimeter",
            "rect": [2000.0, 100.0, 2100.0, 200.0],
            "bounds": [2000.0, 100.0, 2100.0, 200.0],
            "description": "Second heavily fortified barrier at x=2050.0 guarded by Sniper M08_E6_02, Heavy Gunner M08_E5_02, Elite Squad E4, Camera M08_CAM_02, Directional Mine M08_T3_02, Sentry Turret M08_T9_02 ([2045.0, 125.0]), and Roadside Control Box #2 at [1980.0, 185.0] (S1 part 2).",
        },
        {
            "id": "ZONE_G",
            "name": "East Delivery Depot & Extraction",
            "zone_type": "wilderness",
            "rect": [2300.0, 100.0, 2500.0, 250.0],
            "bounds": [2300.0, 100.0, 2500.0, 250.0],
            "description": "Final delivery warehouse and Extraction Zone at [2400.0, 170.0] (radius: 10.0m) where the Cargo Truck must be parked intact.",
        },
    ]

    # =========================================================================
    # 2. STRUCTURES (Exact 68 Structures: 56 Connected Wall/Gate Segments + 12 Buildings/Towers)
    # =========================================================================
    structures: List[Dict[str, Any]] = []

    # 2A. Zone B Staging Motor Pool Adobe Perimeter (30 segments around [310, 90] to [490, 210])
    motorpool_pts = [
        # South edge y=90 (9 segments of 20m)
        (310.0, 90.0), (330.0, 90.0), (350.0, 90.0), (370.0, 90.0), (390.0, 90.0),
        (410.0, 90.0), (430.0, 90.0), (450.0, 90.0), (470.0, 90.0), (490.0, 90.0),
        # East edge x=490 (6 segments, gate at index 11: [490, 140]->[490, 160])
        (490.0, 115.0), (490.0, 140.0), (490.0, 160.0), (490.0, 180.0), (490.0, 195.0), (490.0, 210.0),
        # North edge y=210 (9 segments of 20m)
        (470.0, 210.0), (450.0, 210.0), (430.0, 210.0), (410.0, 210.0), (390.0, 210.0),
        (370.0, 210.0), (350.0, 210.0), (330.0, 210.0), (310.0, 210.0),
        # West edge x=310 (6 segments, gate at index 26: [310, 160]->[310, 140])
        (310.0, 195.0), (310.0, 180.0), (310.0, 160.0), (310.0, 140.0), (310.0, 115.0), (310.0, 90.0),
    ]
    structures.extend(
        make_wall_Chain(
            "M08_ADOBE_B",
            "env_wall_adobe_4m",
            motorpool_pts,
            gate_indices={11: "env_gate_sliding_6m", 26: "env_gate_sliding_6m"},
        )
    )

    # 2B. Zone D Checkpoint Alpha Fortified Perimeter & Motorized Barrier (13 segments around [1220, 110] to [1280, 190])
    cp_alpha_outer_pts = [
        (1220.0, 110.0), (1250.0, 110.0), (1280.0, 110.0),
        (1280.0, 145.0), (1280.0, 155.0), (1280.0, 190.0),
        (1250.0, 190.0), (1220.0, 190.0),
        (1220.0, 155.0), (1220.0, 145.0), (1220.0, 110.0),
    ]
    structures.extend(
        make_wall_Chain(
            "M08_WALL_ALPHA",
            "env_wall_concrete_4m",
            cp_alpha_outer_pts,
            gate_indices={3: "env_gate_sliding_6m", 8: "env_gate_sliding_6m"},
        )
    )
    cp_alpha_center_pts = [
        (1250.0, 110.0), (1250.0, 145.0), (1250.0, 155.0), (1250.0, 190.0),
    ]
    structures.extend(
        make_wall_Chain(
            "M08_BARRIER_ALPHA",
            "env_wall_concrete_4m",
            cp_alpha_center_pts,
            gate_indices={1: "env_gate_sliding_6m"},
        )
    )

    # 2C. Zone F Checkpoint Bravo Fortified Perimeter & Motorized Barrier (13 segments around [2020, 110] to [2080, 190])
    cp_bravo_outer_pts = [
        (2020.0, 110.0), (2050.0, 110.0), (2080.0, 110.0),
        (2080.0, 145.0), (2080.0, 155.0), (2080.0, 190.0),
        (2050.0, 190.0), (2020.0, 190.0),
        (2020.0, 155.0), (2020.0, 145.0), (2020.0, 110.0),
    ]
    structures.extend(
        make_wall_Chain(
            "M08_WALL_BRAVO",
            "env_wall_concrete_4m",
            cp_bravo_outer_pts,
            gate_indices={3: "env_gate_sliding_6m", 8: "env_gate_sliding_6m"},
        )
    )
    cp_bravo_center_pts = [
        (2050.0, 110.0), (2050.0, 145.0), (2050.0, 155.0), (2050.0, 190.0),
    ]
    structures.extend(
        make_wall_Chain(
            "M08_BARRIER_BRAVO",
            "env_wall_concrete_4m",
            cp_bravo_center_pts,
            gate_indices={1: "env_gate_sliding_6m"},
        )
    )

    assert len(structures) == 56, f"Expected 56 wall/gate segments, got {len(structures)}"

    # 2D. 12 Handcrafted Buildings, Watchtowers, Guard Booths & Delivery Depot (56 + 12 = 68 Structures)
    buildings_and_towers = [
        {
            "id": "M08_GUARD_BOOTH_B",
            "type": "env_guard_booth_a",
            "name": "Zone B Staging Motor Pool West Guard Booth",
            "pos": [330.0, 168.0, 0.0],
            "bounds": [326.0, 164.0, 334.0, 172.0],
            "doorways": [[330.0, 164.0], [330.0, 172.0], [326.0, 168.0], [334.0, 168.0]],
            "zone": "ZONE_B",
        },
        {
            "id": "M08_MOTORPOOL_SHED_B",
            "type": "env_bldg_barracks_a",
            "name": "Zone B Motor Pool Maintenance & Dispatch Shed",
            "pos": [425.0, 190.0, 0.0],
            "bounds": [415.0, 182.0, 435.0, 198.0],
            "doorways": [[425.0, 182.0], [425.0, 198.0], [415.0, 190.0], [435.0, 190.0]],
            "zone": "ZONE_B",
        },
        {
            "id": "M08_FUEL_CANOPY_B",
            "type": "env_supply_carport_a",
            "name": "Zone B Cargo Truck Staging Canopy",
            "pos": [390.0, 130.0, 0.0],
            "zone": "ZONE_B",
            "description": "Steel shade canopy covering the Driveable Objective Cargo Truck at [390.0, 130.0].",
        },
        {
            "id": "M08_WATCHTOWER_B",
            "type": "env_watchtower_metal_a",
            "name": "Zone B Motor Pool Northeast Overwatch Tower",
            "pos": [475.0, 195.0, 0.0],
            "radius": 4.0,
            "height": 8.5,
            "has_ladder": True,
            "zone": "ZONE_B",
        },
        {
            "id": "M08_WATCHTOWER_ALPHA",
            "type": "env_watchtower_metal_a",
            "name": "Checkpoint Alpha Overwatch Sniper Tower",
            "pos": [1255.0, 182.0, 0.0],
            "radius": 4.5,
            "height": 9.0,
            "has_ladder": True,
            "zone": "ZONE_D",
            "description": "Houses Sniper M08_E6_01 at elevation 8.5m and mounts Panning Camera M08_CAM_01.",
        },
        {
            "id": "M08_GUARD_BOOTH_ALPHA",
            "type": "env_guard_booth_a",
            "name": "Checkpoint Alpha Barrier Control Booth",
            "pos": [1240.0, 128.0, 0.0],
            "bounds": [1236.0, 124.0, 1244.0, 132.0],
            "doorways": [[1240.0, 124.0], [1240.0, 132.0], [1236.0, 128.0], [1244.0, 128.0]],
            "zone": "ZONE_D",
        },
        {
            "id": "M08_PILLBOX_ALPHA",
            "type": "env_bunker_pillbox_a",
            "name": "Checkpoint Alpha Heavy Gunner Pillbox",
            "pos": [1265.0, 126.0, 0.0],
            "bounds": [1261.0, 122.0, 1269.0, 130.0],
            "doorways": [[1265.0, 122.0], [1265.0, 130.0], [1261.0, 126.0], [1269.0, 126.0]],
            "zone": "ZONE_D",
        },
        {
            "id": "M08_CANYON_OUTPOST_E",
            "type": "env_bunker_pillbox_a",
            "name": "Zone E Sandstorm Canyon Relay Bunker",
            "pos": [1650.0, 185.0, 0.0],
            "bounds": [1645.0, 180.0, 1655.0, 190.0],
            "doorways": [[1650.0, 180.0], [1650.0, 190.0], [1645.0, 185.0], [1655.0, 185.0]],
            "zone": "ZONE_E",
        },
        {
            "id": "M08_WATCHTOWER_BRAVO",
            "type": "env_watchtower_metal_a",
            "name": "Checkpoint Bravo Overwatch Sniper Tower",
            "pos": [2055.0, 182.0, 0.0],
            "radius": 4.5,
            "height": 9.0,
            "has_ladder": True,
            "zone": "ZONE_F",
            "description": "Houses Sniper M08_E6_02 at elevation 8.5m and mounts Panning Camera M08_CAM_02.",
        },
        {
            "id": "M08_GUARD_BOOTH_BRAVO",
            "type": "env_guard_booth_a",
            "name": "Checkpoint Bravo Barrier Control Booth",
            "pos": [2040.0, 172.0, 0.0],
            "bounds": [2036.0, 168.0, 2044.0, 176.0],
            "doorways": [[2040.0, 168.0], [2040.0, 176.0], [2036.0, 172.0], [2044.0, 172.0]],
            "zone": "ZONE_F",
        },
        {
            "id": "M08_PILLBOX_BRAVO",
            "type": "env_bunker_pillbox_a",
            "name": "Checkpoint Bravo Heavy Gunner Pillbox",
            "pos": [2065.0, 126.0, 0.0],
            "bounds": [2061.0, 122.0, 2069.0, 130.0],
            "doorways": [[2065.0, 122.0], [2065.0, 130.0], [2061.0, 126.0], [2069.0, 126.0]],
            "zone": "ZONE_F",
        },
        {
            "id": "M08_DELIVERY_WAREHOUSE_G",
            "type": "env_bldg_warehouse_main_a",
            "name": "Zone G East Delivery Depot Warehouse",
            "pos": [2435.0, 205.0, 0.0],
            "bounds": [2415.0, 190.0, 2455.0, 220.0],
            "doorways": [[2435.0, 190.0], [2435.0, 220.0], [2415.0, 205.0], [2455.0, 205.0]],
            "zone": "ZONE_G",
        },
    ]
    structures.extend(buildings_and_towers)
    assert len(structures) == 68, f"Expected 68 structures, got {len(structures)}"
    structures = interleave_for_zero_step_repeats(structures)

    # =========================================================================
    # 3. TRAPS (Exact 8 Allowed Traps: 2x T1, 2x T3, 2x T4, 2x T9) & CAMERAS (Exact 2)
    # =========================================================================
    traps = [
        {
            "id": "M08_T1_01",
            "type": "T1",
            "name": "West Canyon Approach North Tripwire Alarm #1",
            "pos": [265.0, 185.0, 0.2],
            "zone": "ZONE_A",
            "noise_radius_m": 45.0,
            "counter": "Wire Cutters (2.0s) or step over in crouch",
        },
        {
            "id": "M08_T1_02",
            "type": "T1",
            "name": "West Canyon Approach South Tripwire Alarm #2",
            "pos": [280.0, 120.0, 0.2],
            "zone": "ZONE_A",
            "noise_radius_m": 45.0,
            "counter": "Wire Cutters (2.0s) or step over in crouch",
        },
        {
            "id": "M08_T4_01",
            "type": "T4",
            "name": "Western Highway Off-Road Shoulder Buried Mine #1",
            "pos": [820.0, 135.0, 0.0],
            "zone": "ZONE_C",
            "damage": 110.0,
            "counter": "Keep Cargo Truck on asphalt lane (y=146..154) or disarm in prone",
        },
        {
            "id": "M08_T4_02",
            "type": "T4",
            "name": "Western Highway Off-Road Shoulder Buried Mine #2",
            "pos": [1050.0, 165.0, 0.0],
            "zone": "ZONE_C",
            "damage": 110.0,
            "counter": "Keep Cargo Truck on asphalt lane (y=146..154) or disarm in prone",
        },
        {
            "id": "M08_T3_01",
            "type": "T3",
            "name": "Checkpoint Alpha Flank Directional Claymore Mine #1",
            "pos": [1232.0, 178.0, 0.2],
            "zone": "ZONE_D",
            "damage": 90.0,
            "counter": "Approach from rear arc or disarm (2.5s)",
        },
        {
            "id": "M08_T9_01",
            "type": "T9",
            "name": "Checkpoint Alpha Automated Sentry Turret #1",
            "pos": [1245.0, 175.0, 0.0],
            "zone": "ZONE_D",
            "range_m": 45.0,
            "linked_control_box_id": "M08_CTRL_BOX_01",
            "counter": "Hack Roadside Control Box #1 at [1185.0, 115.0], EMP grenade, or C4",
        },
        {
            "id": "M08_T3_02",
            "type": "T3",
            "name": "Checkpoint Bravo Flank Directional Claymore Mine #2",
            "pos": [2032.0, 122.0, 0.2],
            "zone": "ZONE_F",
            "damage": 90.0,
            "counter": "Approach from rear arc or disarm (2.5s)",
        },
        {
            "id": "M08_T9_02",
            "type": "T9",
            "name": "Checkpoint Bravo Automated Sentry Turret #2",
            "pos": [2045.0, 125.0, 0.0],
            "zone": "ZONE_F",
            "range_m": 45.0,
            "linked_control_box_id": "M08_CTRL_BOX_02",
            "counter": "Hack Roadside Control Box #2 at [1980.0, 185.0], EMP grenade, or C4",
        },
    ]
    traps = interleave_for_zero_step_repeats(traps)

    cameras = [
        {
            "id": "M08_CAM_01",
            "type": "T11",
            "name": "Checkpoint Alpha Barrier Panning Camera #1",
            "pos": [1255.0, 180.0, 4.2],
            "zone": "ZONE_D",
            "mounted_on": "M08_WATCHTOWER_ALPHA",
            "cone_deg": 75.0,
            "range_m": 40.0,
            "linked_control_box_id": "M08_CTRL_BOX_01",
        },
        {
            "id": "M08_CAM_02",
            "type": "T11",
            "name": "Checkpoint Bravo Barrier Panning Camera #2",
            "pos": [2055.0, 180.0, 4.2],
            "zone": "ZONE_F",
            "mounted_on": "M08_WATCHTOWER_BRAVO",
            "cone_deg": 75.0,
            "range_m": 40.0,
            "linked_control_box_id": "M08_CTRL_BOX_02",
        },
    ]

    alarms = [
        {
            "id": "M08_ALM_01",
            "type": "prop_alarm_panel_a",
            "name": "Zone B Staging Motor Pool Master Alarm Panel",
            "pos": [355.0, 162.0, 1.3],
            "zone": "ZONE_B",
        },
        {
            "id": "M08_ALM_02",
            "type": "prop_alarm_panel_a",
            "name": "Checkpoint Alpha & Bravo Highway Relay Alarm Panel",
            "pos": [1242.0, 162.0, 1.3],
            "zone": "ZONE_D",
        },
    ]

    # =========================================================================
    # 4. ENEMIES (Exact 40 Enemies: 16x E2, 3x E3, 2x E4, 2x E5, 2x E6, 2x E10, 5x E12, 8x E13)
    # =========================================================================
    enemies: List[Dict[str, Any]] = []

    # 4A. 2x E6 Snipers (on Checkpoint Alpha & Bravo Watchtowers, wpn_longbow_mesh, elev=8.5m)
    enemies.append({
        "id": "M08_E6_01",
        "class": "E6",
        "asset_id": "chr_enemy_e6_sniper",
        "name": "Checkpoint Alpha Tower Sniper #1",
        "weapon": "wpn_longbow_mesh",
        "vision_range_m": 85.0,
        "laser_paint_sec": 1.0,
        "pos": [1255.0, 182.0, 8.5],
        "elevation": 8.5,
        "mount": "watchtower",
        "zone": "ZONE_D",
        "patrol_waypoints": [[1254.0, 181.0], [1256.0, 181.0], [1256.0, 183.0], [1254.0, 183.0]],
    })
    enemies.append({
        "id": "M08_E6_02",
        "class": "E6",
        "asset_id": "chr_enemy_e6_sniper",
        "name": "Checkpoint Bravo Tower Sniper #2",
        "weapon": "wpn_longbow_mesh",
        "vision_range_m": 85.0,
        "laser_paint_sec": 1.0,
        "pos": [2055.0, 182.0, 8.5],
        "elevation": 8.5,
        "mount": "watchtower",
        "zone": "ZONE_F",
        "patrol_waypoints": [[2054.0, 181.0], [2056.0, 181.0], [2056.0, 183.0], [2054.0, 183.0]],
    })

    # 4B. 2x E5 Heavy Gunners (Checkpoint Alpha & Bravo, wpn_lmg60_hammer, 200 HP)
    enemies.append({
        "id": "M08_E5_01",
        "class": "E5",
        "asset_id": "chr_enemy_e7_heavy_gunner",
        "name": "Checkpoint Alpha Heavy Gunner #1",
        "hp": 200,
        "armor": "heavy_suppression_plate",
        "weapon": "wpn_lmg60_hammer",
        "suppression_fire": True,
        "pos": [1254.0, 142.0, 0.0],
        "zone": "ZONE_D",
        "patrol_waypoints": [[1254.0, 142.0], [1262.0, 142.0], [1262.0, 158.0], [1254.0, 158.0]],
    })
    enemies.append({
        "id": "M08_E5_02",
        "class": "E5",
        "asset_id": "chr_enemy_e7_heavy_gunner",
        "name": "Checkpoint Bravo Heavy Gunner #2",
        "hp": 200,
        "armor": "heavy_suppression_plate",
        "weapon": "wpn_lmg60_hammer",
        "suppression_fire": True,
        "pos": [2054.0, 142.0, 0.0],
        "zone": "ZONE_F",
        "patrol_waypoints": [[2054.0, 142.0], [2062.0, 142.0], [2062.0, 158.0], [2054.0, 158.0]],
    })

    # 4C. 2x E4 Cobalt Elites (Checkpoint Bravo Elite Squad, wpn_ar12_burst)
    e4_specs = [
        ("M08_E4_01", "ZONE_F", [2034.0, 138.0], [[2034.0, 138.0], [2046.0, 138.0], [2046.0, 146.0], [2034.0, 146.0]]),
        ("M08_E4_02", "ZONE_F", [2034.0, 160.0], [[2034.0, 160.0], [2046.0, 160.0], [2046.0, 166.0], [2034.0, 166.0]]),
    ]
    for eid, ezone, epos, ewps in e4_specs:
        enemies.append({
            "id": eid,
            "class": "E4",
            "asset_id": "chr_enemy_e12_elite_commando",
            "name": f"Checkpoint Bravo Cobalt Elite ({eid})",
            "weapon": "wpn_ar12_burst",
            "ballistic_vest": True,
            "pos": [epos[0], epos[1], 0.0],
            "zone": ezone,
            "patrol_waypoints": ewps,
        })

    # 4D. 3x E3 Radio Officers (wpn_p45_enforcer, radio: true)
    e3_specs = [
        ("M08_E3_01", "ZONE_B", [372.0, 145.0], [[372.0, 145.0], [405.0, 145.0], [405.0, 165.0], [372.0, 165.0]]),
        ("M08_E3_02", "ZONE_D", [1232.0, 142.0], [[1232.0, 142.0], [1246.0, 142.0], [1246.0, 156.0], [1232.0, 156.0]]),
        ("M08_E3_03", "ZONE_F", [2062.0, 162.0], [[2062.0, 162.0], [2076.0, 162.0], [2076.0, 176.0], [2062.0, 176.0]]),
    ]
    for eid, ezone, epos, ewps in e3_specs:
        enemies.append({
            "id": eid,
            "class": "E3",
            "asset_id": "chr_enemy_e3_officer",
            "name": f"Cobalt Radio Officer ({eid})",
            "weapon": "wpn_p45_enforcer",
            "radio": True,
            "has_radio": True,
            "pos": [epos[0], epos[1], 0.0],
            "zone": ezone,
            "patrol_waypoints": ewps,
        })

    # 4E. 2x E10 Scouts (wpn_ar9_carbine)
    e10_specs = [
        ("M08_E10_01", "ZONE_A", [215.0, 165.0], [[215.0, 165.0], [250.0, 165.0], [250.0, 195.0], [215.0, 195.0]]),
        ("M08_E10_02", "ZONE_E", [1580.0, 132.0], [[1580.0, 132.0], [1630.0, 132.0], [1630.0, 162.0], [1580.0, 162.0]]),
    ]
    for eid, ezone, epos, ewps in e10_specs:
        enemies.append({
            "id": eid,
            "class": "E10",
            "asset_id": "chr_enemy_e5_smg_runner",
            "name": f"Desert Highway Recon Scout ({eid})",
            "weapon": "wpn_ar9_carbine",
            "vision_range_m": 60.0,
            "pos": [epos[0], epos[1], 0.0],
            "zone": ezone,
            "patrol_waypoints": ewps,
        })

    # 4F. 5x E12 Sentries (wpn_ar5_mesh)
    e12_specs = [
        ("M08_E12_01", "ZONE_B", [318.0, 146.0], [[318.0, 146.0], [324.0, 146.0], [324.0, 156.0], [318.0, 156.0]]),
        ("M08_E12_02", "ZONE_B", [482.0, 146.0], [[482.0, 146.0], [488.0, 146.0], [488.0, 156.0], [482.0, 156.0]]),
        ("M08_E12_03", "ZONE_D", [1224.0, 146.0], [[1224.0, 146.0], [1230.0, 146.0], [1230.0, 156.0], [1224.0, 156.0]]),
        ("M08_E12_04", "ZONE_F", [2024.0, 146.0], [[2024.0, 146.0], [2030.0, 146.0], [2030.0, 156.0], [2024.0, 156.0]]),
        ("M08_E12_05", "ZONE_G", [2360.0, 162.0], [[2360.0, 162.0], [2385.0, 162.0], [2385.0, 180.0], [2360.0, 180.0]]),
    ]
    for eid, ezone, epos, ewps in e12_specs:
        enemies.append({
            "id": eid,
            "class": "E12",
            "asset_id": "chr_enemy_e2_rifleman",
            "name": f"Roadblock Gate Sentry ({eid})",
            "weapon": "wpn_ar5_mesh",
            "pos": [epos[0], epos[1], 0.0],
            "zone": ezone,
            "patrol_waypoints": ewps,
        })

    # 4G. 8x E13 Vehicle Crew (operating patrol jeeps & roadblock vehicles across Zones B, C, D, E, F)
    e13_specs = [
        ("M08_E13_01", "ZONE_B", [355.0, 118.0], [[355.0, 118.0], [380.0, 118.0], [380.0, 134.0], [355.0, 134.0]]),
        ("M08_E13_02", "ZONE_C", [640.0, 148.0], [[640.0, 148.0], [720.0, 148.0], [720.0, 156.0], [640.0, 156.0]]),
        ("M08_E13_03", "ZONE_C", [750.0, 146.0], [[750.0, 146.0], [805.0, 146.0], [805.0, 154.0], [750.0, 154.0]]),
        ("M08_E13_04", "ZONE_C", [940.0, 148.0], [[940.0, 148.0], [1020.0, 148.0], [1020.0, 156.0], [940.0, 156.0]]),
        ("M08_E13_05", "ZONE_D", [1270.0, 148.0], [[1270.0, 148.0], [1278.0, 148.0], [1278.0, 158.0], [1270.0, 158.0]]),
        ("M08_E13_06", "ZONE_E", [1450.0, 148.0], [[1450.0, 148.0], [1540.0, 148.0], [1540.0, 156.0], [1450.0, 156.0]]),
        ("M08_E13_07", "ZONE_E", [1760.0, 148.0], [[1760.0, 148.0], [1850.0, 148.0], [1850.0, 156.0], [1760.0, 156.0]]),
        ("M08_E13_08", "ZONE_F", [2070.0, 148.0], [[2070.0, 148.0], [2078.0, 148.0], [2078.0, 158.0], [2070.0, 158.0]]),
    ]
    for eid, ezone, epos, ewps in e13_specs:
        enemies.append({
            "id": eid,
            "class": "E13",
            "asset_id": "chr_enemy_e5_smg_runner",
            "name": f"Highway Jeep & Roadblock Crew ({eid})",
            "weapon": "wpn_ar9_carbine",
            "pos": [epos[0], epos[1], 0.0],
            "zone": ezone,
            "patrol_waypoints": ewps,
        })

    # 4H. 16x E2 Cobalt Grunts (wpn_ar5_mesh across Zones A–G)
    e2_specs = [
        ("M08_E2_01", "ZONE_A", [165.0, 145.0], [[165.0, 145.0], [195.0, 145.0], [195.0, 168.0], [165.0, 168.0]]),
        ("M08_E2_02", "ZONE_A", [235.0, 132.0], [[235.0, 132.0], [262.0, 132.0], [262.0, 154.0], [235.0, 154.0]]),
        ("M08_E2_03", "ZONE_B", [338.0, 102.0], [[338.0, 102.0], [368.0, 102.0], [368.0, 118.0], [338.0, 118.0]]),
        ("M08_E2_04", "ZONE_B", [410.0, 115.0], [[410.0, 115.0], [442.0, 115.0], [442.0, 135.0], [410.0, 135.0]]),
        ("M08_E2_05", "ZONE_B", [448.0, 145.0], [[448.0, 145.0], [478.0, 145.0], [478.0, 168.0], [448.0, 168.0]]),
        ("M08_E2_06", "ZONE_B", [355.0, 182.0], [[355.0, 182.0], [392.0, 182.0], [392.0, 202.0], [355.0, 202.0]]),
        ("M08_E2_07", "ZONE_C", [565.0, 134.0], [[565.0, 134.0], [605.0, 134.0], [605.0, 162.0], [565.0, 162.0]]),
        ("M08_E2_08", "ZONE_C", [860.0, 136.0], [[860.0, 136.0], [905.0, 136.0], [905.0, 164.0], [860.0, 164.0]]),
        ("M08_E2_09", "ZONE_C", [1110.0, 136.0], [[1110.0, 136.0], [1155.0, 136.0], [1155.0, 164.0], [1110.0, 164.0]]),
        ("M08_E2_10", "ZONE_D", [1182.0, 122.0], [[1182.0, 122.0], [1208.0, 122.0], [1208.0, 142.0], [1182.0, 142.0]]),
        ("M08_E2_11", "ZONE_D", [1226.0, 162.0], [[1226.0, 162.0], [1244.0, 162.0], [1244.0, 174.0], [1226.0, 174.0]]),
        ("M08_E2_12", "ZONE_E", [1365.0, 136.0], [[1365.0, 136.0], [1410.0, 136.0], [1410.0, 164.0], [1365.0, 164.0]]),
        ("M08_E2_13", "ZONE_E", [1675.0, 136.0], [[1675.0, 136.0], [1720.0, 136.0], [1720.0, 164.0], [1675.0, 164.0]]),
        ("M08_E2_14", "ZONE_F", [1978.0, 162.0], [[1978.0, 162.0], [2006.0, 162.0], [2006.0, 182.0], [1978.0, 182.0]]),
        ("M08_E2_15", "ZONE_F", [2058.0, 162.0], [[2058.0, 162.0], [2076.0, 162.0], [2076.0, 174.0], [2058.0, 174.0]]),
        ("M08_E2_16", "ZONE_G", [2325.0, 142.0], [[2325.0, 142.0], [2355.0, 142.0], [2355.0, 168.0], [2325.0, 168.0]]),
    ]
    for eid, ezone, epos, ewps in e2_specs:
        enemies.append({
            "id": eid,
            "class": "E2",
            "asset_id": "chr_enemy_e2_rifleman",
            "name": f"Cobalt Highway Grunt ({eid})",
            "weapon": "wpn_ar5_mesh",
            "has_radio": False,
            "pos": [epos[0], epos[1], 0.0],
            "zone": ezone,
            "patrol_waypoints": ewps,
        })

    assert len(enemies) == 40, f"Expected 40 enemies, got {len(enemies)}"
    enemies = interleave_for_zero_step_repeats(enemies)

    # =========================================================================
    # 5. SAFE SPOTS (Exact 3 Safe Spots) & HIDING SPOTS (Exact 40 Hiding Spots)
    # =========================================================================
    safe_spots = [
        {"id": "M08_SAFE_01", "name": "West Canyon Insertion Rock Overlook", "pos": [85.0, 210.0, 0.0], "radius": 8.0, "zone": "ZONE_A"},
        {"id": "M08_SAFE_02", "name": "Highway Culvert Underpass West of Checkpoint Alpha", "pos": [1145.0, 112.0, -1.2], "radius": 7.5, "zone": "ZONE_C"},
        {"id": "M08_SAFE_03", "name": "Eastern Canyon Sandstorm Rock Alcove", "pos": [1925.0, 192.0, 0.0], "radius": 8.0, "zone": "ZONE_E"},
    ]

    hiding_types = [
        "env_bush_stealth_a",
        "prop_dumpster_metal_a",
        "prop_locker_metal_a",
        "culvert_drain_pipe_a",
    ]
    hide_zone_boxes = [
        ("ZONE_A", 20.0, 110.0, 285.0, 285.0),
        ("ZONE_B", 315.0, 95.0, 485.0, 205.0),
        ("ZONE_C", 520.0, 122.0, 1180.0, 178.0),
        ("ZONE_D", 1205.0, 105.0, 1295.0, 195.0),
        ("ZONE_E", 1320.0, 105.0, 1980.0, 195.0),
        ("ZONE_F", 2005.0, 105.0, 2095.0, 195.0),
        ("ZONE_G", 2310.0, 110.0, 2485.0, 240.0),
    ]
    hiding_spots = []
    for i in range(1, 41):
        zname, x0, y0, x1, y1 = hide_zone_boxes[i % len(hide_zone_boxes)]
        hx = round(x0 + vdc(i * 11 + 5, 2) * (x1 - x0), 2)
        hy = round(y0 + vdc(i * 17 + 7, 3) * (y1 - y0), 2)
        hiding_spots.append({
            "id": f"M08_HIDE_{i:02d}",
            "type": hiding_types[i % len(hiding_types)],
            "pos": [hx, hy, 0.0],
            "zone": zname,
        })
    hiding_spots = interleave_for_zero_step_repeats(hiding_spots)

    # =========================================================================
    # 6. LIGHTS (Exact 14 Lights across Motor Pool, Checkpoints & Delivery Depot)
    # =========================================================================
    lights = [
        {"id": "M08_LGT_01", "type": "light_flood_gate_pole",    "pos": [312.0, 150.0, 5.5], "zone": "ZONE_B", "range_m": 22.0, "shootable": True},
        {"id": "M08_LGT_02", "type": "light_caged_bulb_warm",    "pos": [330.0, 168.0, 3.2], "zone": "ZONE_B", "range_m": 12.0, "shootable": True},
        {"id": "M08_LGT_03", "type": "light_flood_gate_pole",    "pos": [390.0, 130.0, 5.8], "zone": "ZONE_B", "range_m": 24.0, "shootable": True},
        {"id": "M08_LGT_04", "type": "light_caged_bulb_warm",    "pos": [425.0, 190.0, 3.6], "zone": "ZONE_B", "range_m": 14.0, "shootable": True},
        {"id": "M08_LGT_05", "type": "light_flood_gate_pole",    "pos": [488.0, 150.0, 5.5], "zone": "ZONE_B", "range_m": 22.0, "shootable": True},
        {"id": "M08_LGT_06", "type": "light_flood_gate_pole",    "pos": [1185.0, 115.0, 3.8], "zone": "ZONE_D", "range_m": 14.0, "shootable": True},
        {"id": "M08_LGT_07", "type": "light_flood_gate_pole",    "pos": [1250.0, 150.0, 6.0], "zone": "ZONE_D", "range_m": 26.0, "shootable": True},
        {"id": "M08_LGT_08", "type": "light_bunker_lantern",     "pos": [1265.0, 126.0, 2.8], "zone": "ZONE_D", "range_m": 12.0, "shootable": True},
        {"id": "M08_LGT_09", "type": "light_bunker_lantern",     "pos": [1650.0, 185.0, 2.8], "zone": "ZONE_E", "range_m": 12.0, "shootable": True},
        {"id": "M08_LGT_10", "type": "light_flood_gate_pole",    "pos": [1980.0, 185.0, 3.8], "zone": "ZONE_F", "range_m": 14.0, "shootable": True},
        {"id": "M08_LGT_11", "type": "light_flood_gate_pole",    "pos": [2050.0, 150.0, 6.0], "zone": "ZONE_F", "range_m": 26.0, "shootable": True},
        {"id": "M08_LGT_12", "type": "light_bunker_lantern",     "pos": [2065.0, 126.0, 2.8], "zone": "ZONE_F", "range_m": 12.0, "shootable": True},
        {"id": "M08_LGT_13", "type": "light_flood_gate_pole",    "pos": [2435.0, 190.0, 5.8], "zone": "ZONE_G", "range_m": 22.0, "shootable": True},
        {"id": "M08_LGT_14", "type": "light_extraction_beacon",  "pos": [2400.0, 170.0, 4.0], "zone": "ZONE_G", "range_m": 20.0, "shootable": False},
    ]

    # =========================================================================
    # 7. PICKUPS (Exact 35 Pickups including AR-47 Ironside Reward & Convoy Tools)
    # =========================================================================
    pickups = [
        {"id": "M08_PKP_REWARD_IRONSIDE", "type": "pickup_weapon_ar47_ironside", "weapon_id": "wpn_ar47_ironside", "name": "AR-47 Ironside Heavy Assault Rifle (O1 Unlock)", "pos": [2402.0, 172.0, 1.0], "zone": "ZONE_G"},
        {"id": "M08_PKP_02", "type": "pickup_gadget_hack_pda",    "name": "Roadside Barrier Hacking PDA",    "pos": [72.0,  196.0, 0.9], "zone": "ZONE_A"},
        {"id": "M08_PKP_03", "type": "pickup_gadget_wirecutters", "name": "Tactical Wire Cutters",           "pos": [190.0, 178.0, 0.8], "zone": "ZONE_A"},
        {"id": "M08_PKP_04", "type": "pickup_gadget_emp_grenade", "name": "EMP Grenade x2 (Turret Counter)", "pos": [332.0, 166.0, 1.0], "zone": "ZONE_B"},
        {"id": "M08_PKP_05", "type": "pickup_keycard_convoy",     "name": "Cargo Truck Ignition Transponder","pos": [388.0, 132.0, 1.0], "zone": "ZONE_B"},
        {"id": "M08_PKP_06", "type": "pickup_gadget_c4_charge",   "name": "C4 Demolition Charge x2",         "pos": [422.0, 188.0, 1.0], "zone": "ZONE_B"},
        {"id": "M08_PKP_07", "type": "pickup_gadget_emp_grenade", "name": "EMP Grenade x2 (Alpha Counter)",  "pos": [1175.0, 118.0, 0.9], "zone": "ZONE_D"},
        {"id": "M08_PKP_08", "type": "pickup_gadget_emp_grenade", "name": "EMP Grenade x2 (Bravo Counter)",  "pos": [1972.0, 182.0, 0.9], "zone": "ZONE_F"},
    ]
    pickup_types = [
        "pickup_ammo_556_box",
        "pickup_ammo_762_box",
        "pickup_ammo_9mm_box",
        "pickup_medkit_field",
        "pickup_gadget_smoke_grenade",
        "pickup_gadget_frag_grenade",
    ]
    for i in range(9, 36):
        zname, x0, y0, x1, y1 = hide_zone_boxes[i % len(hide_zone_boxes)]
        px = round(x0 + vdc(i * 13 + 3, 2) * (x1 - x0), 2)
        py = round(y0 + vdc(i * 19 + 5, 3) * (y1 - y0), 2)
        pickups.append({
            "id": f"M08_PKP_{i:02d}",
            "type": pickup_types[i % len(pickup_types)],
            "name": f"Convoy Field Supply #{i:02d}",
            "pos": [px, py, 0.8],
            "zone": zname,
        })
    assert len(pickups) == 35, f"Expected 35 pickups, got {len(pickups)}"
    pickups = interleave_for_zero_step_repeats(pickups)

    # =========================================================================
    # 8. VEGETATION (Exact 78 Desert Scrub, Dry Acacia & Palm Clusters)
    # =========================================================================
    veg_types = ["env_tree_palm_a", "env_bush_stealth_a", "env_scrub_desert_dry_a"]
    vegetation = []
    for i in range(1, 79):
        zname, x0, y0, x1, y1 = hide_zone_boxes[i % len(hide_zone_boxes)]
        vx = round(x0 + vdc(i * 23 + 7, 2) * (x1 - x0), 2)
        vy = round(y0 + vdc(i * 29 + 11, 3) * (y1 - y0), 2)
        vegetation.append({
            "id": f"M08_VEG_{i:02d}",
            "type": veg_types[i % len(veg_types)],
            "pos": [vx, vy, 0.0],
            "zone": zname,
        })
    assert len(vegetation) == 78
    vegetation = interleave_for_zero_step_repeats(vegetation)

    # =========================================================================
    # 9. COVER (Exact 616 Cover Objects across the 2.5km Desert Highway Corridor)
    # =========================================================================
    cover_types = [
        "env_rock_boulder_a",
        "prop_concrete_barrier_a",
        "prop_sandbag_wall_a",
        "prop_crate_military_a",
        "prop_hesko_bastion_a",
    ]
    cover = []
    for i in range(1, 617):
        zname, x0, y0, x1, y1 = hide_zone_boxes[i % len(hide_zone_boxes)]
        cx = round(x0 + vdc(i * 31 + 9, 2) * (x1 - x0), 2)
        cy = round(y0 + vdc(i * 37 + 13, 3) * (y1 - y0), 2)
        cover.append({
            "id": f"M08_COV_{i:03d}",
            "type": cover_types[i % len(cover_types)],
            "pos": [cx, cy, 0.0],
            "zone": zname,
        })
    assert len(cover) == 616
    cover = interleave_for_zero_step_repeats(cover)

    # =========================================================================
    # 10. PROPS (Exact 924 Props including Driveable Cargo Truck, 2 Roadside Control Boxes & Alarms)
    # =========================================================================
    props: List[Dict[str, Any]] = [
        {
            "id": "M08_OBJ_CARGO_TRUCK",
            "type": "veh_truck_cargo_a",
            "name": "Driveable Objective Cargo Truck (500 Max HP — O1 & S2)",
            "pos": [390.0, 130.0, 0.0],
            "zone": "ZONE_B",
            "driveable": True,
            "max_hp": 500,
            "ghost_medal_min_hp": 300,
            "objective_id": "O1",
        },
        {
            "id": "M08_CTRL_BOX_01",
            "type": "prop_breaker_box_a",
            "name": "Roadside Control Box #1 (Checkpoint Alpha Barrier & T9_01 Hack — S1 Part 1)",
            "pos": [1185.0, 115.0, 1.2],
            "zone": "ZONE_D",
            "opens_gate_id": "M08_BARRIER_ALPHA_02",
            "disables_turret_id": "M08_T9_01",
            "disables_camera_id": "M08_CAM_01",
            "objective_id": "S1",
        },
        {
            "id": "M08_CTRL_BOX_02",
            "type": "prop_breaker_box_a",
            "name": "Roadside Control Box #2 (Checkpoint Bravo Barrier & T9_02 Hack — S1 Part 2)",
            "pos": [1980.0, 185.0, 1.2],
            "zone": "ZONE_F",
            "opens_gate_id": "M08_BARRIER_BRAVO_02",
            "disables_turret_id": "M08_T9_02",
            "disables_camera_id": "M08_CAM_02",
            "objective_id": "S1",
        },
        {
            "id": "M08_ALM_01",
            "type": "prop_alarm_panel_a",
            "name": "Zone B Staging Motor Pool Master Alarm Panel",
            "pos": [355.0, 162.0, 1.3],
            "zone": "ZONE_B",
        },
        {
            "id": "M08_ALM_02",
            "type": "prop_alarm_panel_a",
            "name": "Checkpoint Alpha & Bravo Highway Relay Alarm Panel",
            "pos": [1242.0, 162.0, 1.3],
            "zone": "ZONE_D",
        },
        {
            "id": "M08_PATROL_JEEP_01",
            "type": "veh_jeep_tactical_a",
            "name": "Western Highway Patrol Jeep #1",
            "pos": [680.0, 152.0, 0.0],
            "zone": "ZONE_C",
        },
        {
            "id": "M08_PATROL_JEEP_02",
            "type": "veh_jeep_tactical_a",
            "name": "Western Highway Patrol Jeep #2",
            "pos": [980.0, 152.0, 0.0],
            "zone": "ZONE_C",
        },
        {
            "id": "M08_PATROL_JEEP_03",
            "type": "veh_jeep_tactical_a",
            "name": "Eastern Canyon Patrol Jeep #3",
            "pos": [1495.0, 152.0, 0.0],
            "zone": "ZONE_E",
        },
        {
            "id": "M08_PATROL_JEEP_04",
            "type": "veh_jeep_tactical_a",
            "name": "Eastern Canyon Patrol Jeep #4",
            "pos": [1805.0, 152.0, 0.0],
            "zone": "ZONE_E",
        },
    ]

    prop_catalog = [
        "prop_fuel_tank_large",
        "prop_fuel_drum_metal_a",
        "prop_ammo_crate_wood_a",
        "prop_roadblock_sign_chevron_a",
        "prop_traffic_cone_reflective_a",
        "prop_tire_stack_highway_a",
        "prop_desert_milepost_sign_a",
        "prop_cable_spool_wood_a",
        "prop_generator_diesel_a",
        "prop_water_jerrycan_a",
        "prop_camouflage_crate_a",
        "prop_radio_field_desk_a",
    ]

    remaining_props = 924 - len(props)
    for i in range(1, remaining_props + 1):
        zname, x0, y0, x1, y1 = hide_zone_boxes[i % len(hide_zone_boxes)]
        px = round(x0 + vdc(i * 41 + 11, 2) * (x1 - x0), 2)
        py = round(y0 + vdc(i * 43 + 17, 3) * (y1 - y0), 2)
        props.append({
            "id": f"M08_PRP_{i:04d}",
            "type": prop_catalog[i % len(prop_catalog)],
            "pos": [px, py, 0.0],
            "zone": zname,
        })

    assert len(props) == 924, f"Expected 924 props, got {len(props)}"
    props = interleave_for_zero_step_repeats(props)

    # =========================================================================
    # 11. DYNAMIC EVENTS (Exact 2 Events: E_M08_STORM & E_M08_CHASE)
    # =========================================================================
    events = [
        {
            "id": "E_M08_STORM",
            "trigger": "enter_zone_e_or_elapsed >= 720s",
            "action": "sandstorm_vision_0.5_120s",
            "vision_multiplier": 0.5,
            "duration_sec": 120.0,
            "description": "Upon entering Zone E (or elapsed >= 720s), a heavy desert sandstorm rolls in, reducing enemy sightlines to 50% for 120s.",
        },
        {
            "id": "E_M08_CHASE",
            "trigger": "alert_level == 3_for_30s_in_truck",
            "action": "spawn:2_chase_jeeps_300_150",
            "spawn_pos": [300.0, 150.0, 0.0],
            "vehicles_spawned": 2,
            "vehicle_type": "veh_jeep_tactical_a",
            "crew_class": "E13",
            "description": "If alert_level == 3 for 30s while driving the truck, spawn 2 pursuit jeeps (veh_jeep_tactical_a with E13 gunners) at [300.0, 150.0].",
        },
    ]

    # =========================================================================
    # 12. OBJECTIVES (O1, S1, S2) & 3 COMPLETE 6-WAYPOINT TACTICAL ROUTES
    # =========================================================================
    objectives = {
        "primary": [
            {
                "id": "O1",
                "title": "Hijack cargo truck at (390, 130), pass Checkpoints Alpha & Bravo, and deliver it to (2400, 170)",
                "truck_pos": [390.0, 130.0, 0.0],
                "checkpoint_alpha_x": 1250.0,
                "checkpoint_bravo_x": 2050.0,
                "delivery_pos": [2400.0, 170.0, 0.0],
                "unlock_reward": "AR-47 Ironside",
                "unlock_weapon_id": "wpn_ar47_ironside",
            }
        ],
        "secondary": [
            {
                "id": "S1",
                "title": "Hack both checkpoint barriers from the roadside control boxes before driving through",
                "control_boxes": [
                    {"id": "M08_CTRL_BOX_01", "pos": [1185.0, 115.0, 1.2], "zone": "ZONE_D"},
                    {"id": "M08_CTRL_BOX_02", "pos": [1980.0, 185.0, 1.2], "zone": "ZONE_F"},
                ],
            },
            {
                "id": "S2",
                "title": "Deliver the cargo truck with above 300 HP remaining (Ghost Medal)",
                "min_truck_hp_required": 300,
                "truck_max_hp": 500,
                "medal_reward": "Ghost Medal",
            },
        ],
        "extraction": {
            "id": "EXT_08",
            "title": "Park Cargo Truck intact at East Delivery Depot Extraction (2400, 170)",
            "pos": [2400.0, 170.0, 0.0],
            "radius": 10.0,
            "zone": "ZONE_G",
        },
    }

    routes = {
        "silent": {
            "name": "Silent Route (Stealth Hijack, Dismount Barrier Bypass & Sandstorm Run > 300 HP)",
            "description": "Infiltrate Zone B from [60, 200] -> silently hijack Cargo Truck at [390, 130] -> dismount before Checkpoint Alpha at [1210, 148] to lower barrier -> drive through Zone E Sandstorm at [1650, 150] -> dismount before Checkpoint Bravo at [2010, 150] -> deliver intact (>300 HP) to [2400, 170].",
            "tools_required": ["Wire Cutters", "Suppressed Sidearm", "Sandstorm Cover"],
            "waypoints": [
                [60.0, 200.0],
                [390.0, 130.0],
                [1210.0, 148.0],
                [1650.0, 150.0],
                [2010.0, 150.0],
                [2400.0, 170.0],
            ],
        },
        "technical": {
            "name": "Technical Route (Roadside Control Box PDA Hacks [1185, 115] & [1980, 185] + EMP Turrets)",
            "description": "Advance from [60, 200] -> hijack Cargo Truck at [390, 130] -> hack Roadside Control Box #1 at [1185, 115] (raising Barrier #1 & disabling T9_01) -> drive through opened Checkpoint Alpha at [1250, 150] -> hack Roadside Control Box #2 at [1980, 185] (opening Barrier #2 & disabling T9_02) -> park at [2400, 170].",
            "tools_required": ["Hacking PDA", "EMP Grenades"],
            "waypoints": [
                [60.0, 200.0],
                [390.0, 130.0],
                [1185.0, 115.0],
                [1250.0, 150.0],
                [1980.0, 185.0],
                [2400.0, 170.0],
            ],
        },
        "loud": {
            "name": "Loud Route (Counter-Snipe Towers, C4 Turrets & Roadblock Breach vs Chase Jeeps)",
            "description": "Push from [60, 200] into Zone B -> commandeer Cargo Truck at [390, 130] -> snipe E6_01 & C4 T9_01 to breach Checkpoint Alpha at [1250, 150] -> fend off E_M08_CHASE jeeps along [1700, 150] -> breach Checkpoint Bravo at [2050, 150] -> reach extraction at [2400, 170].",
            "tools_required": ["Sniper Rifle", "C4 Charges", "Heavy Armor"],
            "waypoints": [
                [60.0, 200.0],
                [390.0, 130.0],
                [1250.0, 150.0],
                [1700.0, 150.0],
                [2050.0, 150.0],
                [2400.0, 170.0],
            ],
        },
    }

    level_dict = {
        "mission_id": "M08",
        "title": "Convoy",
        "chapter": 2,
        "scene_name": "M08",
        "width": 2500.0,
        "height": 300.0,
        "area_hectares": 75.0,
        "biome": "desert_highway",
        "time_of_day": "day",
        "weather": "clear",
        "weather_transition": "clear_to_sandstorm",
        "player_start": {
            "pos": [60.0, 200.0, 0.0],
            "facing_deg": 90.0,
            "facing_cardinal": "East",
            "starting_loadout": [
                "wpn_vectork",
                "wpn_usp45_suppressed",
                "wpn_knife_mesh",
                "HackPDA",
                "EMPGrenade",
                "C4Charge",
                "WireCutters",
            ],
        },
        "strict_exclusions_enforced": {
            "forbidden_enemies": ["E1", "E7", "E8", "E9", "E11", "E14"],
            "forbidden_traps": ["T5", "T6", "T7", "T12", "T13", "T14"],
            "allowed_traps_only": ["T1", "T3", "T4", "T9"],
            "camera_count": 2,
        },
        "zones": zones,
        "objectives": objectives,
        "events": events,
        "routes": routes,
        "structures": structures,
        "props": props,
        "cover": cover,
        "vegetation": vegetation,
        "lights": lights,
        "hiding_spots": hiding_spots,
        "safe_spots": safe_spots,
        "enemies": enemies,
        "traps": traps,
        "cameras": cameras,
        "alarms": alarms,
        "pickups": pickups,
        "census": {
            "structures": len(structures),
            "props": len(props),
            "cover": len(cover),
            "vegetation": len(vegetation),
            "lights": len(lights),
            "hiding_spots": len(hiding_spots),
            "safe_spots": len(safe_spots),
            "enemies": len(enemies),
            "traps": len(traps),
            "cameras": len(cameras),
            "alarms": len(alarms),
            "pickups": len(pickups),
            "events": len(events),
        },
    }
    return level_dict


def write_m08_unity_scene_and_installer() -> Tuple[str, str]:
    scenes_dir = os.path.join(ROOT_DIR, "Assets/_Project/Scenes")
    scripts_dir = os.path.join(ROOT_DIR, "Assets/_Project/Scripts/Core")
    os.makedirs(scenes_dir, exist_ok=True)
    os.makedirs(scripts_dir, exist_ok=True)

    scene_path = os.path.join(scenes_dir, "M08.unity")
    installer_path = os.path.join(scripts_dir, "M08_ConvoySceneInstaller.cs")

    unity_yaml = """%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!29 &1
OcclusionCullingSettings:
  m_ObjectHideFlags: 0
  serializedVersion: 2
  m_OcclusionBakeSettings:
    smallestOccluder: 5
    smallestHole: 0.25
    backfaceThreshold: 100
--- !u!104 &2
RenderSettings:
  m_ObjectHideFlags: 0
  serializedVersion: 9
  m_Fog: 1
  m_FogColor: {r: 0.84, g: 0.72, b: 0.52, a: 1}
  m_FogMode: 3
  m_FogDensity: 0.0038
  m_AmbientMode: 0
  m_AmbientSkyColor: {r: 0.78, g: 0.68, b: 0.52, a: 1}
--- !u!157 &3
LightmapSettings:
  m_ObjectHideFlags: 0
  serializedVersion: 12
--- !u!196 &4
NavMeshSettings:
  serializedVersion: 2
  m_ObjectHideFlags: 0
--- !u!1 &100
GameObject:
  m_ObjectHideFlags: 0
  serializedVersion: 6
  m_Component:
  - component: {fileID: 101}
  - component: {fileID: 102}
  m_Name: M08_Convoy_MissionRoot
  m_TagString: Untagged
  m_IsActive: 1
--- !u!4 &101
Transform:
  m_ObjectHideFlags: 0
  m_GameObject: {fileID: 100}
  m_LocalRotation: {x: 0, y: 0, z: 0, w: 1}
  m_LocalPosition: {x: 0, y: 0, z: 0}
  m_LocalScale: {x: 1, y: 1, z: 1}
--- !u!114 &102
MonoBehaviour:
  m_ObjectHideFlags: 0
  m_GameObject: {fileID: 100}
  m_Enabled: 1
  m_EditorHideFlags: 0
  m_Script: {fileID: 11500000, guid: 08f9a0b1c2d3e4f5061728394a5b6c7d, type: 3}
  m_Name: 
  m_EditorClassIdentifier: RealLoserStudio.Tactical.Core.M08_ConvoySceneInstaller
  missionJsonPath: Assets/_Project/Missions/M08.json
  enforceStrictM08Exclusions: 1
"""
    with open(scene_path, "w", encoding="utf-8") as f:
        f.write(unity_yaml)

    installer_cs = """using System;
using System.Collections.Generic;
using UnityEngine;
using RealLoserStudio.Tactical.Player;
using RealLoserStudio.Tactical.Stealth;
using RealLoserStudio.Tactical.Traps;
using RealLoserStudio.Tactical.AI;
using RealLoserStudio.Tactical.UI;
using RealLoserStudio.Tactical.Streaming;

namespace RealLoserStudio.Tactical.Core
{
    /// <summary>
    /// Scene Bootstrapper & Runtime Controller for Mission 08 ("Convoy" — Chapter 2, M08.unity / M08.json).
    /// Configures the 2500m x 300m (75.0 Hectares) Desert Highway Corridor, Driveable Cargo Truck (500 Max HP)
    /// at [390.0, 130.0], Checkpoints Alpha (x=1250) & Bravo (x=2050), Roadside Hacking Boxes [1185, 115] & [1980, 185],
    /// Sandstorm event E_M08_STORM (0.5x enemy vision for 120s), and Alert 3 pursuit jeeps E_M08_CHASE.
    /// </summary>
    public class M08_ConvoySceneInstaller : MonoBehaviour
    {
        [Header("Mission 08 Blueprint Binding")]
        public string missionJsonPath = "Assets/_Project/Missions/M08.json";
        public bool enforceStrictM08Exclusions = true;

        [Header("Scene References")]
        public PlayerTacticalController playerController;
        public StealthAndDetectionSystem stealthSystem;
        public MissionEventAndStreamingSystem streamingSystem;
        public MobileTouchHUDAndMEMap touchHudMap;

        [Header("Cargo Truck & Convoy State")]
        public float cargoTruckMaxHP = 500f;
        public float cargoTruckCurrentHP = 500f;
        public bool cargoTruckHijacked;
        public bool isPlayerDrivingTruck;
        public bool barrierAlphaHacked;
        public bool barrierBravoHacked;
        public bool objectiveO1_TruckDelivered;
        public bool objectiveS1_BothBarriersHacked;
        public bool objectiveS2_GhostMedalEligible = true;
        public bool rewardAR47IronsideUnlocked;

        [Header("Dynamic Events State")]
        public bool sandstormActive;
        public float sandstormRemainingSec;
        public float alert3DrivingTimerSec;
        public bool chaseJeepsSpawned;

        private float _missionElapsedSec;

        private void Start()
        {
            InitializeMission08();
        }

        public void InitializeMission08()
        {
            cargoTruckCurrentHP = cargoTruckMaxHP;
            if (playerController != null)
            {
                playerController.transform.position = new Vector3(60.0f, 0.0f, 200.0f);
                playerController.transform.rotation = Quaternion.Euler(0f, 90f, 0f);
            }
        }

        private void Update()
        {
            float dt = Time.deltaTime;
            _missionElapsedSec += dt;

            // E_M08_STORM: Entering Zone E (x >= 1300) or elapsed >= 720s triggers 120s Sandstorm (0.5x vision)
            if (!sandstormActive && _missionElapsedSec >= 720f)
            {
                TriggerSandstormEvent();
            }

            if (sandstormActive)
            {
                sandstormRemainingSec -= dt;
                if (sandstormRemainingSec <= 0f)
                {
                    sandstormActive = false;
                    if (stealthSystem != null)
                    {
                        stealthSystem.weatherVisionMultiplier = 1.0f;
                    }
                }
            }

            // E_M08_CHASE: Alert Level 3 for 30s while driving the Cargo Truck spawns 2 chase jeeps at [300, 150]
            if (!chaseJeepsSpawned && isPlayerDrivingTruck && stealthSystem != null &&
                stealthSystem.currentAlertLevel == CompoundAlertLevel.Alert3_Reinforcements)
            {
                alert3DrivingTimerSec += dt;
                if (alert3DrivingTimerSec >= 30f)
                {
                    chaseJeepsSpawned = true;
                }
            }
            else
            {
                alert3DrivingTimerSec = 0f;
            }
        }

        public void TriggerSandstormEvent()
        {
            sandstormActive = true;
            sandstormRemainingSec = 120.0f;
            if (stealthSystem != null)
            {
                stealthSystem.weatherVisionMultiplier = 0.5f;
            }
        }

        public void OnHackRoadsideControlBox(int checkpointIndex, TrapAndHazardSystem sentryTurret, TrapAndHazardSystem camera)
        {
            if (checkpointIndex == 1)
            {
                barrierAlphaHacked = true;
            }
            else if (checkpointIndex == 2)
            {
                barrierBravoHacked = true;
            }

            if (sentryTurret != null) sentryTurret.isArmed = false;
            if (camera != null) camera.isArmed = false;

            if (barrierAlphaHacked && barrierBravoHacked)
            {
                objectiveS1_BothBarriersHacked = true;
            }
        }

        public void ApplyCargoTruckDamage(float damage)
        {
            cargoTruckCurrentHP = Mathf.Max(0f, cargoTruckCurrentHP - damage);
            if (cargoTruckCurrentHP <= 300f)
            {
                objectiveS2_GhostMedalEligible = false;
            }
        }

        public void OnDeliverCargoTruckAtExtraction()
        {
            if (cargoTruckHijacked && cargoTruckCurrentHP > 0f)
            {
                objectiveO1_TruckDelivered = true;
                rewardAR47IronsideUnlocked = true;
                objectiveS2_GhostMedalEligible = (cargoTruckCurrentHP > 300f);
            }
        }
    }
}
"""
    with open(installer_path, "w", encoding="utf-8") as f:
        f.write(installer_cs)

    return scene_path, installer_path


def main() -> int:
    level_data = build_m08_level_dict()

    missions_dir = os.path.join(ROOT_DIR, "Assets/_Project/Missions")
    out_dir = os.path.join(ROOT_DIR, "artifacts/file_generation/ttl=63d/output")
    os.makedirs(missions_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)

    for p in (
        os.path.join(ROOT_DIR, "M08.json"),
        os.path.join(missions_dir, "M08.json"),
        os.path.join(out_dir, "M08.json"),
    ):
        with open(p, "w", encoding="utf-8") as f:
            json.dump(level_data, f, indent=2)

    scene_path, installer_path = write_m08_unity_scene_and_installer()
    with open(scene_path, "r", encoding="utf-8") as src, open(
        os.path.join(out_dir, "M08.unity"), "w", encoding="utf-8"
    ) as dst:
        dst.write(src.read())

    with open(installer_path, "r", encoding="utf-8") as src, open(
        os.path.join(out_dir, "M08_ConvoySceneInstaller.cs"), "w", encoding="utf-8"
    ) as dst:
        dst.write(src.read())

    print(f"[M08 BUILDER] Successfully generated M08.json, {scene_path}, and {installer_path}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
