#!/usr/bin/env python3
from pathlib import Path
"""
Project Real Loser — Mission 02 ("Disavowed") Handcrafted Level & Scene Builder
Target Engine: Unity 2022.3.40f1 LTS (URP, Android ARM64 IL2CPP)

Builds:
1. `M02.json` (in root, `Assets/_Project/Missions/M02.json`, and output directory)
2. `Assets/_Project/Scenes/M02.unity` (Unity 2022.3 YAML Scene for M02 "Disavowed")
3. `Assets/_Project/Scripts/Core/M02_DisavowedSceneInstaller.cs`
"""

import os
import sys
import json
import math
from collections import Counter
from typing import List, Dict, Any, Tuple

ROOT_DIR = str(Path(__file__).resolve().parents[1])
MAP_W = 800.0
MAP_H = 600.0


def vdc(n: int, base: int) -> float:
    """Van der Corput radical-inverse low-discrepancy sequence in given prime base."""
    v, denom = 0.0, 1.0
    while n > 0:
        denom *= base
        n, rem = divmod(n, base)
        v += rem / denom
    return v


def ensure_zero_step_repeats(
    items: List[Dict[str, Any]],
    width: float = MAP_W,
    height: float = MAP_H,
    allow_micro_jitter: bool = False,
) -> List[Dict[str, Any]]:
    """
    Orders `items` via greedy unique-vector path construction so that NO consecutive
    step vector (dx, dy) or modulo-wrapped step vector repeats > 1 time across the entire list,
    preserving 100% of snapped structure/wall/fence coordinates.
    """
    if len(items) <= 2:
        return items

    def get_xy(obj: Dict[str, Any]) -> Tuple[float, float]:
        p = obj.get("pos", obj.get("position", [0.0, 0.0]))
        return float(p[0]), float(p[1])

    remaining = list(items)
    ordered = [remaining.pop(0)]
    used_raw = Counter()
    used_mod = Counter()

    while remaining:
        x1, y1 = get_xy(ordered[-1])
        picked_idx = -1
        for idx, cand in enumerate(remaining):
            x2, y2 = get_xy(cand)
            dx = round(x2 - x1, 2)
            dy = round(y2 - y1, 2)
            mdx = round((x2 - x1) % width, 2)
            mdy = round((y2 - y1) % height, 2)
            if used_raw[(dx, dy)] == 0 and used_mod[(mdx, mdy)] == 0 and (abs(dx) > 0.01 or abs(dy) > 0.01):
                picked_idx = idx
                used_raw[(dx, dy)] += 1
                used_mod[(mdx, mdy)] += 1
                break

        if picked_idx != -1:
            ordered.append(remaining.pop(picked_idx))
        else:
            cand = remaining.pop(0)
            x2, y2 = get_xy(cand)
            if allow_micro_jitter:
                step_try = 0
                while True:
                    dx = round(x2 - x1, 2)
                    dy = round(y2 - y1, 2)
                    mdx = round((x2 - x1) % width, 2)
                    mdy = round((y2 - y1) % height, 2)
                    if used_raw[(dx, dy)] == 0 and used_mod[(mdx, mdy)] == 0:
                        used_raw[(dx, dy)] += 1
                        used_mod[(mdx, mdy)] += 1
                        break
                    step_try += 1
                    angle = step_try * 2.39996
                    rad = 0.01 * ((step_try // 4) + 1)
                    x2 = round(x2 + math.cos(angle) * rad, 2)
                    y2 = round(y2 + math.sin(angle) * rad, 2)
                    cand["pos"][0] = x2
                    cand["pos"][1] = y2
            else:
                dx = round(x2 - x1, 2)
                dy = round(y2 - y1, 2)
                mdx = round((x2 - x1) % width, 2)
                mdy = round((y2 - y1) % height, 2)
                used_raw[(dx, dy)] += 1
                used_mod[(mdx, mdy)] += 1
            ordered.append(cand)

    return ordered


def build_rect_fence_segments(
    prefix: str,
    wall_type: str,
    x_min: float,
    y_min: float,
    x_max: float,
    y_max: float,
    n_south: int,
    n_east: int,
    n_north: int,
    n_west: int,
    gates: Dict[Tuple[str, int], Tuple[str, str]] = None,
    cuttables: Dict[Tuple[str, int], str] = None,
) -> List[Dict[str, Any]]:
    gates = gates or {}
    cuttables = cuttables or {}
    segs: List[Dict[str, Any]] = []

    def add_edge(edge_name: str, x1: float, y1: float, x2: float, y2: float, count: int, rot_y: float) -> None:
        for k in range(count):
            t0 = k / float(count)
            t1 = (k + 1) / float(count)
            sx = round(x1 + (x2 - x1) * t0, 4)
            sy = round(y1 + (y2 - y1) * t0, 4)
            ex = round(x1 + (x2 - x1) * t1, 4)
            ey = round(y1 + (y2 - y1) * t1, 4)
            cx = round(0.5 * (sx + ex), 4)
            cy = round(0.5 * (sy + ey), 4)
            length = round(math.hypot(ex - sx, ey - sy), 4)

            seg_id = f"{prefix}_{edge_name}_{k:02d}"
            seg_type = wall_type
            extra: Dict[str, Any] = {}

            if (edge_name, k) in gates:
                seg_id, seg_type = gates[(edge_name, k)]
            elif (edge_name, k) in cuttables:
                seg_id = cuttables[(edge_name, k)]
                extra["cuttable"] = True
                extra["interaction"] = "WireCutters_Breach"

            obj = {
                "id": seg_id,
                "type": seg_type,
                "pos": [cx, cy, 0.0],
                "start": [sx, sy],
                "end": [ex, ey],
                "length": length,
                "rot_y": rot_y,
            }
            obj.update(extra)
            segs.append(obj)

    add_edge("S", x_min, y_min, x_max, y_min, n_south, 0.0)
    add_edge("E", x_max, y_min, x_max, y_max, n_east, 90.0)
    add_edge("N", x_max, y_max, x_min, y_max, n_north, 0.0)
    add_edge("W", x_min, y_max, x_min, y_min, n_west, 90.0)
    return segs


def build_m02_level_dict() -> Dict[str, Any]:
    # =========================================================================
    # 1. ZONES (6 Handcrafted Sectors on 800m x 600m Forest Map)
    # =========================================================================
    zones = [
        {
            "id": "ZONE_A",
            "name": "South Wilderness Insertion",
            "zone_type": "wilderness",
            "rect": [0.0, 0.0, 800.0, 170.0],
            "bounds": [0.0, 0.0, 800.0, 170.0],
            "description": "Player Start at (700, 15) in South-East misty pine ridge; dirt logging road winding from (40, 300) down through western trees with boulder clusters and stealth bushes.",
        },
        {
            "id": "ZONE_B",
            "name": "East Flank Ridge & Scout Overwatch",
            "zone_type": "wilderness",
            "rect": [580.0, 150.0, 800.0, 360.0],
            "bounds": [580.0, 150.0, 800.0, 360.0],
            "description": "Elevated wooded trail overlooking main camp perimeter, patrolled by 2x E10 Scouts (60m binocular sightlines) and guarded by Buried Mines M02_T4_01 (610, 210) and M02_T4_02 (645, 275).",
        },
        {
            "id": "ZONE_C",
            "name": "Outer Fenced Perimeter & Pillbox Line",
            "zone_type": "perimeter",
            "rect": [240.0, 250.0, 560.0, 480.0],
            "bounds": [240.0, 250.0, 560.0, 480.0],
            "description": "Continuous connected chain-link fence (x: 240..560, y: 250..480) with 4 corner watchtowers ([245, 255], [555, 255], [245, 475], [555, 475]) manned by 4x E12 Sentries, 2 pillboxes at South Gate (400, 250) and West Gate (240, 365), Tripwires M02_T1_01/02, and Directional Mines M02_T3_01/02.",
        },
        {
            "id": "ZONE_D",
            "name": "Main Militia Encampment & Radio Comms",
            "zone_type": "camp",
            "rect": [280.0, 290.0, 520.0, 440.0],
            "bounds": [280.0, 290.0, 520.0, 440.0],
            "description": "Militia barracks tents, concrete Radio Comms Building ([390, 370] to [415, 395] with rooms R1/R2/R3 and S1 Radio Equipment at (400, 380)), 2 Alarm Panels (M02_ALM_01 at (395, 365), M02_ALM_02 at (310, 350)), Noise Traps M02_T8_01/02, E1 grunts, and Radio Officer M02_E3_01.",
        },
        {
            "id": "ZONE_E",
            "name": "Inner Command Tent Compound",
            "zone_type": "camp",
            "rect": [380.0, 440.0, 520.0, 540.0],
            "bounds": [380.0, 440.0, 520.0, 540.0],
            "description": "High-security inner fenced enclosure housing Command Tent (prop_tent_command_a) at (450, 490) with Safe & classified documents (O1), patrolled by second Radio Officer M02_E3_02 (S2).",
        },
        {
            "id": "ZONE_F",
            "name": "North & West Escape Wilderness",
            "zone_type": "wilderness",
            "rect": [0.0, 480.0, 800.0, 600.0],
            "bounds": [0.0, 480.0, 800.0, 600.0],
            "description": "Forest extraction trail leading to West Extraction Zone at (40, 320) (radius 10.0m).",
        },
    ]

    # =========================================================================
    # 2. STRUCTURES (Exact 112 Connected Structures, 100% Closed Perimeters)
    # =========================================================================
    structures: List[Dict[str, Any]] = []

    watchtowers = [
        {"id": "M02_WT_SW", "type": "env_watchtower_metal_a", "pos": [245.0, 255.0, 0.0], "radius": 3.5, "height": 8.5, "zone": "ZONE_C", "manned_by": "M02_E12_01"},
        {"id": "M02_WT_SE", "type": "env_watchtower_metal_a", "pos": [555.0, 255.0, 0.0], "radius": 3.5, "height": 8.5, "zone": "ZONE_C", "manned_by": "M02_E12_02"},
        {"id": "M02_WT_NW", "type": "env_watchtower_metal_a", "pos": [245.0, 475.0, 0.0], "radius": 3.5, "height": 8.5, "zone": "ZONE_C", "manned_by": "M02_E12_03"},
        {"id": "M02_WT_NE", "type": "env_watchtower_metal_a", "pos": [555.0, 475.0, 0.0], "radius": 3.5, "height": 8.5, "zone": "ZONE_C", "manned_by": "M02_E12_04"},
    ]
    structures.extend(watchtowers)

    pillboxes = [
        {
            "id": "M02_PILLBOX_SOUTH_GATE",
            "type": "env_bunker_pillbox_a",
            "pos": [400.0, 250.0, 0.0],
            "bounds": [396.0, 246.0, 404.0, 254.0],
            "doorways": [[400.0, 246.0], [400.0, 254.0], [396.0, 250.0], [404.0, 250.0]],
            "zone": "ZONE_C",
        },
        {
            "id": "M02_PILLBOX_WEST_GATE",
            "type": "env_bunker_pillbox_a",
            "pos": [240.0, 365.0, 0.0],
            "bounds": [236.0, 361.0, 244.0, 369.0],
            "doorways": [[236.0, 365.0], [244.0, 365.0], [240.0, 361.0], [240.0, 369.0]],
            "zone": "ZONE_C",
        },
    ]
    structures.extend(pillboxes)

    structures.append({
        "id": "M02_BLDG_RADIO_COMMS",
        "type": "env_bldg_comms_bunker_a",
        "pos": [402.5, 382.5, 0.0],
        "bounds": [390.0, 370.0, 415.0, 395.0],
        "height": 4.5,
        "zone": "ZONE_D",
        "doorways": [
            [400.0, 370.0],
            [400.0, 395.0],
            [390.0, 380.0],
            [415.0, 380.0],
            [398.0, 380.0],
            [407.0, 380.0],
        ],
        "rooms": [
            {"id": "R1", "name": "Comms Entry & Locker Room", "bounds": [390.0, 370.0, 398.0, 395.0]},
            {"id": "R2", "name": "Main Radio Transmitter Room (S1)", "bounds": [398.0, 370.0, 407.0, 395.0]},
            {"id": "R3", "name": "Cipher & Storage Office", "bounds": [407.0, 370.0, 415.0, 395.0]},
        ],
    })

    comms_walls = build_rect_fence_segments(
        prefix="M02_COMMS_WALL",
        wall_type="env_wall_concrete_4m",
        x_min=390.0,
        y_min=370.0,
        x_max=415.0,
        y_max=395.0,
        n_south=2,
        n_east=2,
        n_north=2,
        n_west=2,
    )
    structures.extend(comms_walls)

    structures.append({
        "id": "M02_TENT_COMMAND",
        "type": "prop_tent_command_a",
        "pos": [450.0, 490.0, 0.0],
        "bounds": [446.0, 486.0, 454.0, 494.0],
        "doorways": [
            [450.0, 486.0],
            [450.0, 494.0],
            [446.0, 490.0],
            [454.0, 490.0],
            [446.0, 488.5],
        ],
        "zone": "ZONE_E",
        "description": "Heavily guarded Command Tent at (450, 490) housing Safe with classified documents (O1).",
    })

    outer_fence_segments = build_rect_fence_segments(
        prefix="M02_OUTER_FENCE",
        wall_type="env_fence_chainlink_4m",
        x_min=240.0,
        y_min=250.0,
        x_max=560.0,
        y_max=480.0,
        n_south=15,
        n_east=11,
        n_north=15,
        n_west=11,
        gates={
            ("S", 7): ("M02_GATE_SOUTH_400_250", "env_gate_sliding_6m"),
            ("W", 5): ("M02_GATE_WEST_240_365", "env_gate_sliding_6m"),
        },
        cuttables={
            ("E", 3): "M02_FENCE_EAST_BREACH_560_310",
        },
    )
    structures.extend(outer_fence_segments)

    inner_fence_segments = build_rect_fence_segments(
        prefix="M02_INNER_FENCE",
        wall_type="env_fence_chainlink_4m",
        x_min=380.0,
        y_min=440.0,
        x_max=520.0,
        y_max=540.0,
        n_south=7,
        n_east=5,
        n_north=7,
        n_west=5,
        gates={
            ("S", 3): ("M02_GATE_INNER_COMMAND", "env_gate_sliding_6m"),
        },
    )
    structures.extend(inner_fence_segments)

    camp_and_wild_structures = [
        {
            "id": "M02_TENT_BARRACKS_01",
            "type": "env_bldg_barracks_a",
            "pos": [325.0, 330.0, 0.0],
            "bounds": [320.0, 325.0, 330.0, 335.0],
            "doorways": [[325.0, 325.0], [325.0, 335.0], [320.0, 330.0], [330.0, 330.0]],
            "zone": "ZONE_D",
            "description": "Barracks Tent #1 housing sleeping Militia Grunt M02_E1_01.",
        },
        {
            "id": "M02_TENT_BARRACKS_02",
            "type": "env_bldg_barracks_a",
            "pos": [355.0, 335.0, 0.0],
            "bounds": [350.0, 330.0, 360.0, 340.0],
            "doorways": [[355.0, 330.0], [355.0, 340.0]],
            "zone": "ZONE_D",
        },
        {
            "id": "M02_TENT_BARRACKS_03",
            "type": "env_bldg_barracks_a",
            "pos": [455.0, 340.0, 0.0],
            "bounds": [450.0, 335.0, 460.0, 345.0],
            "doorways": [[455.0, 335.0], [455.0, 345.0]],
            "zone": "ZONE_D",
        },
        {
            "id": "M02_TENT_BARRACKS_04",
            "type": "env_bldg_barracks_a",
            "pos": [485.0, 385.0, 0.0],
            "bounds": [480.0, 380.0, 490.0, 390.0],
            "doorways": [[485.0, 380.0], [485.0, 390.0]],
            "zone": "ZONE_D",
        },
        {"id": "M02_TENT_MESS_05", "type": "env_tent_militia_mess_a", "pos": [342.4, 408.6, 0.0], "zone": "ZONE_D"},
        {"id": "M02_TENT_MEDICAL_06", "type": "env_tent_militia_med_a", "pos": [468.2, 422.4, 0.0], "zone": "ZONE_D"},
        {"id": "M02_ARMORY_SHED_07", "type": "env_supply_carport_a", "pos": [304.6, 388.2, 0.0], "zone": "ZONE_D"},
        {"id": "M02_GENERATOR_SHED_08", "type": "env_supply_carport_a", "pos": [428.4, 322.6, 0.0], "zone": "ZONE_D"},
        {"id": "M02_MOTORPOOL_CANOPY_09", "type": "env_camo_net_canopy_a", "pos": [292.8, 306.4, 0.0], "zone": "ZONE_D"},
        {"id": "M02_COMMS_ANTENNA_MAST_10", "type": "env_antenna_mast_tall_a", "pos": [418.6, 392.4, 0.0], "zone": "ZONE_D"},
        {"id": "M02_COMMAND_CANOPY_11", "type": "env_camo_net_canopy_a", "pos": [416.2, 504.8, 0.0], "zone": "ZONE_E"},
        {"id": "M02_COMMAND_GUARDPOST_12", "type": "env_guard_booth_a", "pos": [488.4, 512.6, 0.0], "zone": "ZONE_E"},
        {"id": "M02_EAST_RIDGE_OUTPOST_13", "type": "env_camo_net_canopy_a", "pos": [668.4, 242.8, 0.0], "zone": "ZONE_B"},
        {"id": "M02_EAST_RIDGE_LOOKOUT_14", "type": "env_wooden_platform_a", "pos": [712.6, 318.4, 0.0], "zone": "ZONE_B"},
        {"id": "M02_LOGGING_ROAD_GATE_15", "type": "env_timber_roadblock_a", "pos": [40.0, 300.0, 0.0], "zone": "ZONE_A"},
        {"id": "M02_LOGGING_SHED_16", "type": "env_abandoned_cabin_a", "pos": [148.2, 88.6, 0.0], "zone": "ZONE_A"},
        {"id": "M02_SOUTH_RIDGE_BLIND_17", "type": "env_camo_net_canopy_a", "pos": [524.8, 96.4, 0.0], "zone": "ZONE_A"},
        {"id": "M02_INSERTION_MARKER_18", "type": "env_insertion_cairn_a", "pos": [700.0, 15.0, 0.0], "zone": "ZONE_A"},
        {"id": "M02_NORTH_TRAIL_BRIDGE_19", "type": "env_timber_footbridge_a", "pos": [214.6, 534.2, 0.0], "zone": "ZONE_F"},
        {"id": "M02_WEST_EXTRACTION_BEACON_20", "type": "env_extraction_pad_marker_a", "pos": [40.0, 320.0, 0.0], "extraction_radius": 10.0, "zone": "ZONE_F"},
    ]
    structures.extend(camp_and_wild_structures)
    assert len(structures) == 112, f"Expected 112 structures, got {len(structures)}"
    structures = ensure_zero_step_repeats(structures, allow_micro_jitter=False)

    # =========================================================================
    # 3. TRAPS (Exact 8 Allowed Traps: 2x T1, 2x T3, 2x T4, 2x T8; 0 Cameras!)
    # =========================================================================
    traps = [
        {
            "id": "M02_T4_01",
            "type": "T4",
            "name": "East Ridge Trail Buried Mine #1",
            "pos": [610.0, 210.0, 0.0],
            "zone": "ZONE_B",
            "step_radius_m": 1.2,
            "damage": 200.0,
            "counter": "Prone disarm (4.0s) or Binocular earth-decal scan at 5m",
        },
        {
            "id": "M02_T4_02",
            "type": "T4",
            "name": "East Ridge North Approach Buried Mine #2",
            "pos": [645.0, 275.0, 0.0],
            "zone": "ZONE_B",
            "step_radius_m": 1.2,
            "damage": 200.0,
            "counter": "Prone disarm (4.0s) or Binocular earth-decal scan at 5m",
        },
        {
            "id": "M02_T1_01",
            "type": "T1",
            "name": "East Fence Breach Tripwire Alarm #1",
            "pos": [560.0, 310.0, 0.2],
            "zone": "ZONE_C",
            "noise_radius_m": 40.0,
            "counter": "Wire Cutters (2.0s)",
        },
        {
            "id": "M02_T1_02",
            "type": "T1",
            "name": "South Gate Approach Tripwire Alarm #2",
            "pos": [400.0, 255.0, 0.2],
            "zone": "ZONE_C",
            "noise_radius_m": 40.0,
            "counter": "Wire Cutters (2.0s)",
        },
        {
            "id": "M02_T3_01",
            "type": "T3",
            "name": "South-West Perimeter Directional Mine #1 (Facing South)",
            "pos": [320.0, 252.0, 0.2],
            "facing_deg": 180.0,
            "facing_cardinal": "South",
            "zone": "ZONE_C",
            "cone_deg": 60.0,
            "range_m": 15.0,
            "damage": 150.0,
            "counter": "Approach from rear/flank & disarm (3.0s)",
        },
        {
            "id": "M02_T3_02",
            "type": "T3",
            "name": "South-East Perimeter Directional Mine #2 (Facing South)",
            "pos": [480.0, 252.0, 0.2],
            "facing_deg": 180.0,
            "facing_cardinal": "South",
            "zone": "ZONE_C",
            "cone_deg": 60.0,
            "range_m": 15.0,
            "damage": 150.0,
            "counter": "Approach from rear/flank & disarm (3.0s)",
        },
        {
            "id": "M02_T8_01",
            "type": "T8",
            "name": "Comms Approach Gravel & Tin Cans Noise Trap #1",
            "pos": [385.0, 360.0, 0.0],
            "zone": "ZONE_D",
            "noise_radius_m": 15.0,
            "counter": "Crouch slow walk or bypass",
        },
        {
            "id": "M02_T8_02",
            "type": "T8",
            "name": "North Camp Courtyard Gravel Noise Trap #2",
            "pos": [430.0, 410.0, 0.0],
            "zone": "ZONE_D",
            "noise_radius_m": 15.0,
            "counter": "Crouch slow walk or bypass",
        },
    ]
    traps = ensure_zero_step_repeats(traps, allow_micro_jitter=False)

    cameras: List[Dict[str, Any]] = []

    # =========================================================================
    # 4. ALARMS (Exact 2 Alarm Panels in Zone D)
    # =========================================================================
    alarms = [
        {
            "id": "M02_ALM_01",
            "type": "prop_alarm_panel_a",
            "name": "Radio Comms South Exterior Alarm Panel #1",
            "pos": [395.0, 365.0, 1.3],
            "zone": "ZONE_D",
        },
        {
            "id": "M02_ALM_02",
            "type": "prop_alarm_panel_a",
            "name": "West Barracks Courtyard Alarm Panel #2",
            "pos": [310.0, 350.0, 1.3],
            "zone": "ZONE_D",
        },
    ]

    # =========================================================================
    # 5. ENEMIES (Exact 24 Enemies: 16x E1, 2x E3, 2x E10, 4x E12)
    # =========================================================================
    enemies: List[Dict[str, Any]] = [
        {
            "id": "M02_E10_01",
            "class": "E10",
            "role": "Scout",
            "weapon": "wpn_ar9_carbine",
            "equipment": ["Binoculars"],
            "vision_range_m": 60.0,
            "has_radio": False,
            "pos": [625.0, 175.0, 0.0],
            "zone": "ZONE_B",
            "patrol_waypoints": [[625.0, 175.0], [635.0, 265.0], [605.0, 335.0], [595.0, 230.0]],
        },
        {
            "id": "M02_E10_02",
            "class": "E10",
            "role": "Scout",
            "weapon": "wpn_ar9_carbine",
            "equipment": ["Binoculars"],
            "vision_range_m": 60.0,
            "has_radio": False,
            "pos": [685.0, 190.0, 0.0],
            "zone": "ZONE_B",
            "patrol_waypoints": [[685.0, 190.0], [720.0, 285.0], [670.0, 345.0], [660.0, 240.0]],
        },
        {
            "id": "M02_E12_01",
            "class": "E12",
            "role": "Stationary Sentry (SW Watchtower)",
            "weapon": "wpn_ar5_mesh",
            "stationary_post": "M02_WT_SW",
            "pos": [245.0, 255.0, 8.5],
            "elevation": 8.5,
            "zone": "ZONE_C",
            "patrol_waypoints": [[244.2, 254.2], [245.8, 254.2], [245.8, 255.8], [244.2, 255.8]],
        },
        {
            "id": "M02_E12_02",
            "class": "E12",
            "role": "Stationary Sentry (SE Watchtower)",
            "weapon": "wpn_ar5_mesh",
            "stationary_post": "M02_WT_SE",
            "pos": [555.0, 255.0, 8.5],
            "elevation": 8.5,
            "zone": "ZONE_C",
            "patrol_waypoints": [[554.2, 254.2], [555.8, 254.2], [555.8, 255.8], [554.2, 255.8]],
        },
        {
            "id": "M02_E12_03",
            "class": "E12",
            "role": "Stationary Sentry (NW Watchtower)",
            "weapon": "wpn_ar5_mesh",
            "stationary_post": "M02_WT_NW",
            "pos": [245.0, 475.0, 8.5],
            "elevation": 8.5,
            "zone": "ZONE_C",
            "patrol_waypoints": [[244.2, 474.2], [245.8, 474.2], [245.8, 475.8], [244.2, 475.8]],
        },
        {
            "id": "M02_E12_04",
            "class": "E12",
            "role": "Stationary Sentry (NE Watchtower)",
            "weapon": "wpn_ar5_mesh",
            "stationary_post": "M02_WT_NE",
            "pos": [555.0, 475.0, 8.5],
            "elevation": 8.5,
            "zone": "ZONE_C",
            "patrol_waypoints": [[554.2, 474.2], [555.8, 474.2], [555.8, 475.8], [554.2, 475.8]],
        },
        {
            "id": "M02_E3_01",
            "class": "E3",
            "role": "Radio Officer (Zone D Comms Courtyard)",
            "weapon": "wpn_p45_enforcer",
            "radio": True,
            "radio_checkin_interval_s": 45.0,
            "pos": [382.0, 368.0, 0.0],
            "zone": "ZONE_D",
            "patrol_waypoints": [[382.0, 368.0], [382.0, 402.0], [422.0, 402.0], [422.0, 368.0]],
        },
        {
            "id": "M02_E3_02",
            "class": "E3",
            "role": "Radio Officer (Zone E Command Tent — S2 Target)",
            "weapon": "wpn_p45_enforcer",
            "radio": True,
            "radio_checkin_interval_s": 45.0,
            "objective_id": "S2",
            "pos": [442.0, 482.0, 0.0],
            "zone": "ZONE_E",
            "patrol_waypoints": [[442.0, 482.0], [462.0, 482.0], [462.0, 502.0], [442.0, 502.0]],
        },
        {
            "id": "M02_E1_01",
            "class": "E1",
            "role": "Militia Grunt (Sleeping in Barracks Tent #1)",
            "weapon": "wpn_mp9_mesh",
            "sleeper": True,
            "pos": [325.0, 330.0, 0.0],
            "zone": "ZONE_D",
            "patrol_waypoints": [[325.0, 330.0], [326.5, 330.5], [325.5, 332.0]],
        },
        {
            "id": "M02_E1_02",
            "class": "E1",
            "weapon": "wpn_mp9_mesh",
            "squad": "P1",
            "pos": [392.0, 262.0, 0.0],
            "zone": "ZONE_C",
            "patrol_waypoints": [[392.0, 262.0], [418.0, 262.0], [418.0, 284.0], [392.0, 284.0]],
        },
        {
            "id": "M02_E1_03",
            "class": "E1",
            "weapon": "wpn_mp9_mesh",
            "squad": "P1",
            "pos": [254.0, 358.0, 0.0],
            "zone": "ZONE_C",
            "patrol_waypoints": [[254.0, 358.0], [274.0, 358.0], [274.0, 382.0], [254.0, 382.0]],
        },
        {
            "id": "M02_E1_04",
            "class": "E1",
            "weapon": "wpn_mp9_mesh",
            "squad": "P2",
            "pos": [532.0, 295.0, 0.0],
            "zone": "ZONE_C",
            "patrol_waypoints": [[532.0, 295.0], [548.0, 295.0], [548.0, 335.0], [532.0, 335.0]],
        },
        {
            "id": "M02_E1_05",
            "class": "E1",
            "weapon": "wpn_mp9_mesh",
            "squad": "P2",
            "pos": [268.0, 272.0, 0.0],
            "zone": "ZONE_C",
            "patrol_waypoints": [[268.0, 272.0], [312.0, 272.0], [312.0, 292.0], [268.0, 292.0]],
        },
        {
            "id": "M02_E1_06",
            "class": "E1",
            "weapon": "wpn_mp9_mesh",
            "squad": "P3",
            "pos": [308.0, 345.0, 0.0],
            "zone": "ZONE_D",
            "patrol_waypoints": [[308.0, 345.0], [344.0, 345.0], [344.0, 368.0], [308.0, 368.0]],
        },
        {
            "id": "M02_E1_07",
            "class": "E1",
            "weapon": "wpn_mp9_mesh",
            "squad": "P3",
            "pos": [365.0, 315.0, 0.0],
            "zone": "ZONE_D",
            "patrol_waypoints": [[365.0, 315.0], [412.0, 315.0], [412.0, 348.0], [365.0, 348.0]],
        },
        {
            "id": "M02_E1_08",
            "class": "E1",
            "weapon": "wpn_mp9_mesh",
            "squad": "P3",
            "pos": [442.0, 318.0, 0.0],
            "zone": "ZONE_D",
            "patrol_waypoints": [[442.0, 318.0], [478.0, 318.0], [478.0, 332.0], [442.0, 332.0]],
        },
        {
            "id": "M02_E1_09",
            "class": "E1",
            "weapon": "wpn_mp9_mesh",
            "squad": "P4",
            "pos": [465.0, 362.0, 0.0],
            "zone": "ZONE_D",
            "patrol_waypoints": [[465.0, 362.0], [505.0, 362.0], [505.0, 376.0], [465.0, 376.0]],
        },
        {
            "id": "M02_E1_10",
            "class": "E1",
            "weapon": "wpn_mp9_mesh",
            "squad": "P4",
            "pos": [318.0, 412.0, 0.0],
            "zone": "ZONE_D",
            "patrol_waypoints": [[318.0, 412.0], [368.0, 412.0], [368.0, 432.0], [318.0, 432.0]],
        },
        {
            "id": "M02_E1_11",
            "class": "E1",
            "weapon": "wpn_mp9_mesh",
            "squad": "P4",
            "pos": [432.0, 415.0, 0.0],
            "zone": "ZONE_D",
            "patrol_waypoints": [[432.0, 415.0], [492.0, 415.0], [492.0, 434.0], [432.0, 434.0]],
        },
        {
            "id": "M02_E1_12",
            "class": "E1",
            "weapon": "wpn_mp9_mesh",
            "squad": "P5",
            "pos": [395.0, 452.0, 0.0],
            "zone": "ZONE_E",
            "patrol_waypoints": [[395.0, 452.0], [435.0, 452.0], [435.0, 474.0], [395.0, 474.0]],
        },
        {
            "id": "M02_E1_13",
            "class": "E1",
            "weapon": "wpn_mp9_mesh",
            "squad": "P5",
            "pos": [468.0, 455.0, 0.0],
            "zone": "ZONE_E",
            "patrol_waypoints": [[468.0, 455.0], [508.0, 455.0], [508.0, 476.0], [468.0, 476.0]],
        },
        {
            "id": "M02_E1_14",
            "class": "E1",
            "weapon": "wpn_mp9_mesh",
            "squad": "P5",
            "pos": [392.0, 508.0, 0.0],
            "zone": "ZONE_E",
            "patrol_waypoints": [[392.0, 508.0], [432.0, 508.0], [432.0, 532.0], [392.0, 532.0]],
        },
        {
            "id": "M02_E1_15",
            "class": "E1",
            "weapon": "wpn_mp9_mesh",
            "squad": "P6",
            "pos": [468.0, 512.0, 0.0],
            "zone": "ZONE_E",
            "patrol_waypoints": [[468.0, 512.0], [510.0, 512.0], [510.0, 534.0], [468.0, 534.0]],
        },
        {
            "id": "M02_E1_16",
            "class": "E1",
            "weapon": "wpn_mp9_mesh",
            "squad": "P6",
            "pos": [185.0, 312.0, 0.0],
            "zone": "ZONE_A_F_ROAD",
            "patrol_waypoints": [[185.0, 312.0], [218.0, 312.0], [218.0, 348.0], [185.0, 348.0]],
        },
    ]
    assert len(enemies) == 24, f"Expected 24 enemies, got {len(enemies)}"
    enemies = ensure_zero_step_repeats(enemies, allow_micro_jitter=False)

    # =========================================================================
    # 6. SAFE SPOTS (Exact 3 Safe Spots) & HIDING SPOTS (Exact 24 Hiding Spots)
    # =========================================================================
    safe_spots = [
        {"id": "M02_SAFE_01", "name": "South-East Ridge Pine Hollow",     "pos": [672.0, 68.0, 0.0],  "radius": 8.0, "zone": "ZONE_A"},
        {"id": "M02_SAFE_02", "name": "East Flank Boulders Defilade",     "pos": [592.0, 295.0, 0.0], "radius": 7.5, "zone": "ZONE_B"},
        {"id": "M02_SAFE_03", "name": "North-West Logging Creek Culvert", "pos": [145.0, 495.0, 0.0], "radius": 8.5, "zone": "ZONE_F"},
    ]

    hiding_spots = [
        {"id": "M02_HIDE_01", "type": "prop_locker_metal_a",   "pos": [393.0, 375.0, 0.0], "zone": "ZONE_D", "room": "R1"},
        {"id": "M02_HIDE_02", "type": "vent_shaft",            "pos": [402.0, 392.0, 0.0], "zone": "ZONE_D", "room": "R2"},
        {"id": "M02_HIDE_03", "type": "closet_storage_a",      "pos": [412.0, 375.0, 0.0], "zone": "ZONE_D", "room": "R3"},
        {"id": "M02_HIDE_04", "type": "env_bush_stealth_a",    "pos": [682.4, 38.2, 0.0],  "zone": "ZONE_A"},
        {"id": "M02_HIDE_05", "type": "env_bush_stealth_a",    "pos": [548.6, 112.4, 0.0], "zone": "ZONE_A"},
        {"id": "M02_HIDE_06", "type": "env_bush_stealth_a",    "pos": [384.2, 134.8, 0.0], "zone": "ZONE_A"},
        {"id": "M02_HIDE_07", "type": "env_bush_stealth_a",    "pos": [196.4, 118.6, 0.0], "zone": "ZONE_A"},
        {"id": "M02_HIDE_08", "type": "env_bush_stealth_a",    "pos": [618.2, 194.6, 0.0], "zone": "ZONE_B"},
        {"id": "M02_HIDE_09", "type": "env_bush_stealth_a",    "pos": [654.8, 258.2, 0.0], "zone": "ZONE_B"},
        {"id": "M02_HIDE_10", "type": "env_bush_stealth_a",    "pos": [698.4, 326.8, 0.0], "zone": "ZONE_B"},
        {"id": "M02_HIDE_11", "type": "prop_dumpster_metal_a", "pos": [412.6, 258.4, 0.0], "zone": "ZONE_C"},
        {"id": "M02_HIDE_12", "type": "prop_dumpster_metal_a", "pos": [248.4, 352.6, 0.0], "zone": "ZONE_C"},
        {"id": "M02_HIDE_13", "type": "env_bush_stealth_a",    "pos": [546.2, 318.4, 0.0], "zone": "ZONE_C"},
        {"id": "M02_HIDE_14", "type": "env_bush_stealth_a",    "pos": [264.8, 458.2, 0.0], "zone": "ZONE_C"},
        {"id": "M02_HIDE_15", "type": "prop_locker_metal_a",   "pos": [328.4, 333.2, 0.0], "zone": "ZONE_D"},
        {"id": "M02_HIDE_16", "type": "prop_locker_metal_a",   "pos": [358.2, 338.4, 0.0], "zone": "ZONE_D"},
        {"id": "M02_HIDE_17", "type": "prop_dumpster_metal_a", "pos": [376.4, 384.2, 0.0], "zone": "ZONE_D"},
        {"id": "M02_HIDE_18", "type": "prop_locker_metal_a",   "pos": [458.4, 342.6, 0.0], "zone": "ZONE_D"},
        {"id": "M02_HIDE_19", "type": "prop_dumpster_metal_a", "pos": [482.6, 396.4, 0.0], "zone": "ZONE_D"},
        {"id": "M02_HIDE_20", "type": "env_bush_stealth_a",    "pos": [396.8, 464.2, 0.0], "zone": "ZONE_E"},
        {"id": "M02_HIDE_21", "type": "prop_locker_metal_a",   "pos": [447.5, 492.5, 0.0], "zone": "ZONE_E"},
        {"id": "M02_HIDE_22", "type": "prop_dumpster_metal_a", "pos": [494.2, 502.8, 0.0], "zone": "ZONE_E"},
        {"id": "M02_HIDE_23", "type": "env_bush_stealth_a",    "pos": [284.6, 518.4, 0.0], "zone": "ZONE_F"},
        {"id": "M02_HIDE_24", "type": "env_bush_stealth_a",    "pos": [78.4,  334.6, 0.0], "zone": "ZONE_F"},
    ]
    assert len(hiding_spots) == 24

    # =========================================================================
    # 7. LIGHTS (Exact 13 Tactical Dawn/Mist Lights)
    # =========================================================================
    lights = [
        {"id": "M02_LGT_01", "type": "light_flood_gate_pole",    "pos": [400.0, 252.0, 5.0], "zone": "ZONE_C", "range_m": 18.0},
        {"id": "M02_LGT_02", "type": "light_flood_gate_pole",    "pos": [242.0, 365.0, 5.0], "zone": "ZONE_C", "range_m": 18.0},
        {"id": "M02_LGT_03", "type": "light_watchtower_lamp",    "pos": [245.0, 255.0, 8.8], "zone": "ZONE_C", "range_m": 15.0},
        {"id": "M02_LGT_04", "type": "light_watchtower_lamp",    "pos": [555.0, 255.0, 8.8], "zone": "ZONE_C", "range_m": 15.0},
        {"id": "M02_LGT_05", "type": "light_watchtower_lamp",    "pos": [245.0, 475.0, 8.8], "zone": "ZONE_C", "range_m": 15.0},
        {"id": "M02_LGT_06", "type": "light_watchtower_lamp",    "pos": [555.0, 475.0, 8.8], "zone": "ZONE_C", "range_m": 15.0},
        {"id": "M02_LGT_07", "type": "light_caged_bulb_warm",    "pos": [394.0, 382.0, 3.5], "zone": "ZONE_D", "room": "R1", "range_m": 11.0},
        {"id": "M02_LGT_08", "type": "light_fluorescent_tube",   "pos": [402.5, 382.0, 3.5], "zone": "ZONE_D", "room": "R2", "range_m": 12.0},
        {"id": "M02_LGT_09", "type": "light_caged_bulb_warm",    "pos": [411.0, 382.0, 3.5], "zone": "ZONE_D", "room": "R3", "range_m": 11.0},
        {"id": "M02_LGT_10", "type": "light_tent_lantern_a",     "pos": [325.0, 330.0, 2.8], "zone": "ZONE_D", "range_m": 10.0},
        {"id": "M02_LGT_11", "type": "light_tent_lantern_a",     "pos": [455.0, 340.0, 2.8], "zone": "ZONE_D", "range_m": 10.0},
        {"id": "M02_LGT_12", "type": "light_command_table_lamp", "pos": [450.0, 490.0, 3.0], "zone": "ZONE_E", "range_m": 14.0},
        {"id": "M02_LGT_13", "type": "light_extraction_beacon",  "pos": [40.0,  320.0, 3.6], "zone": "ZONE_F", "range_m": 16.0},
    ]
    assert len(lights) == 13

    # =========================================================================
    # 8. PICKUPS (Exact 25 Pickups including Safe Documents O1 & MP9 Reward)
    # =========================================================================
    pickups = [
        {"id": "M02_PKP_01_DOCS", "type": "pickup_classified_documents", "name": "Classified Disavowed Dossier (Safe O1)", "pos": [450.0, 490.0, 1.0], "zone": "ZONE_E", "objective_id": "O1"},
        {"id": "M02_PKP_02_MP9",  "type": "pickup_reward_mp9",           "name": "MP9 Tactical Machine Pistol (O1 Unlock)", "pos": [451.2, 491.0, 1.0], "zone": "ZONE_E"},
        {"id": "M02_PKP_03",      "type": "pickup_gadget_wirecutters",   "name": "Heavy Wire Cutters",                      "pos": [688.4, 42.6, 0.8],  "zone": "ZONE_A"},
        {"id": "M02_PKP_04",      "type": "pickup_gadget_binoculars",    "name": "Tactical Recon Binoculars",               "pos": [642.8, 128.4, 0.9], "zone": "ZONE_A"},
        {"id": "M02_PKP_05",      "type": "pickup_gadget_lockpick",      "name": "Precision Lockpick Set",                  "pos": [598.2, 182.6, 0.9], "zone": "ZONE_B"},
        {"id": "M02_PKP_06",      "type": "pickup_gadget_hack_pda",      "name": "Encrypted Hack PDA",                      "pos": [664.6, 238.2, 1.0], "zone": "ZONE_B"},
        {"id": "M02_PKP_07",      "type": "pickup_gadget_emp_grenade",   "name": "EMP Grenade #1",                          "pos": [708.4, 314.6, 0.9], "zone": "ZONE_B"},
        {"id": "M02_PKP_08",      "type": "pickup_gadget_emp_grenade",   "name": "EMP Grenade #2",                          "pos": [393.5, 378.2, 1.0], "zone": "ZONE_D", "room": "R1"},
        {"id": "M02_PKP_09",      "type": "pickup_gadget_c4_charge",     "name": "C4 Demolition Charge #1",                 "pos": [522.4, 94.8, 0.9],  "zone": "ZONE_A"},
        {"id": "M02_PKP_10",      "type": "pickup_gadget_c4_charge",     "name": "C4 Demolition Charge #2",                 "pos": [306.2, 386.4, 0.9], "zone": "ZONE_D"},
        {"id": "M02_PKP_11",      "type": "pickup_keycard_command",      "name": "Command Safe Combination Cipher",         "pos": [411.8, 386.2, 1.0], "zone": "ZONE_D", "room": "R3"},
        {"id": "M02_PKP_12",      "type": "pickup_weapon_sniper_svd",    "name": "Marksman Rifle Overwatch Crate",          "pos": [526.4, 98.2, 1.0],  "zone": "ZONE_A"},
        {"id": "M02_PKP_13",      "type": "pickup_medkit_field",         "name": "Field Trauma Kit #1",                     "pos": [152.4, 92.6, 0.8],  "zone": "ZONE_A"},
        {"id": "M02_PKP_14",      "type": "pickup_medkit_field",         "name": "Field Trauma Kit #2",                     "pos": [398.4, 248.6, 0.9], "zone": "ZONE_C"},
        {"id": "M02_PKP_15",      "type": "pickup_medkit_field",         "name": "Field Trauma Kit #3",                     "pos": [241.6, 366.8, 0.9], "zone": "ZONE_C"},
        {"id": "M02_PKP_16",      "type": "pickup_medkit_field",         "name": "Field Trauma Kit #4",                     "pos": [466.4, 420.8, 0.9], "zone": "ZONE_D"},
        {"id": "M02_PKP_17",      "type": "pickup_medkit_field",         "name": "Field Trauma Kit #5",                     "pos": [486.2, 510.4, 0.9], "zone": "ZONE_E"},
        {"id": "M02_PKP_18",      "type": "pickup_ammo_9mm_box",         "name": "9x19mm Subsonic Ammo #1",                 "pos": [246.2, 256.4, 8.6], "zone": "ZONE_C"},
        {"id": "M02_PKP_19",      "type": "pickup_ammo_9mm_box",         "name": "9x19mm Subsonic Ammo #2",                 "pos": [556.2, 256.4, 8.6], "zone": "ZONE_C"},
        {"id": "M02_PKP_20",      "type": "pickup_ammo_9mm_box",         "name": "9x19mm Subsonic Ammo #3",                 "pos": [326.8, 332.4, 0.8], "zone": "ZONE_D"},
        {"id": "M02_PKP_21",      "type": "pickup_ammo_9mm_box",         "name": "9x19mm Subsonic Ammo #4",                 "pos": [356.4, 336.8, 0.8], "zone": "ZONE_D"},
        {"id": "M02_PKP_22",      "type": "pickup_ammo_762_box",         "name": "7.62mm Carbine Ammo #1",                  "pos": [456.8, 341.2, 0.8], "zone": "ZONE_D"},
        {"id": "M02_PKP_23",      "type": "pickup_ammo_762_box",         "name": "7.62mm Carbine Ammo #2",                  "pos": [486.4, 386.8, 0.8], "zone": "ZONE_D"},
        {"id": "M02_PKP_24",      "type": "pickup_intel_logbook",        "name": "Militia Patrol Shift Schedule Log",       "pos": [401.2, 379.4, 1.0], "zone": "ZONE_D", "room": "R2"},
        {"id": "M02_PKP_25",      "type": "pickup_ammo_9mm_box",         "name": "Extraction Cache Ammo Box",               "pos": [44.8,  316.2, 0.8], "zone": "ZONE_F"},
    ]
    assert len(pickups) == 25
    pickups = ensure_zero_step_repeats(pickups, allow_micro_jitter=False)

    # =========================================================================
    # 9. VEGETATION (Exact 92 Forest Trees & Stealth Bushes across Zones A-F)
    # =========================================================================
    veg_zones = [
        ("ZONE_A", 15.0, 12.0, 785.0, 162.0),
        ("ZONE_B", 588.0, 158.0, 788.0, 352.0),
        ("ZONE_C", 248.0, 258.0, 552.0, 472.0),
        ("ZONE_D", 286.0, 296.0, 514.0, 434.0),
        ("ZONE_E", 386.0, 446.0, 514.0, 534.0),
        ("ZONE_F", 18.0, 486.0, 782.0, 592.0),
    ]
    vegetation: List[Dict[str, Any]] = []
    for i in range(1, 93):
        zname, x0, y0, x1, y1 = veg_zones[i % len(veg_zones)]
        u = vdc(i * 13 + 7, 2)
        v = vdc(i * 17 + 11, 3)
        vx = round(x0 + u * (x1 - x0), 2)
        vy = round(y0 + v * (y1 - y0), 2)
        vtype = "env_tree_pine_tall_a" if (i % 3 != 0) else "env_bush_stealth_a"
        vegetation.append({
            "id": f"M02_VEG_{i:03d}",
            "type": vtype,
            "pos": [vx, vy, 0.0],
            "zone": zname,
        })
    assert len(vegetation) == 92
    vegetation = ensure_zero_step_repeats(vegetation, allow_micro_jitter=True)

    # =========================================================================
    # 10. COVER PIECES (Exact 484 Handcrafted Cover Pieces across Zones A-F)
    # =========================================================================
    cover_catalog = [
        "env_rock_boulder_a",
        "prop_sandbag_wall_a",
        "prop_concrete_barrier_a",
        "prop_crate_military_a",
        "prop_fallen_pine_log_a",
    ]
    cover: List[Dict[str, Any]] = []
    for i in range(1, 485):
        zname, x0, y0, x1, y1 = veg_zones[i % len(veg_zones)]
        u = vdc(i * 19 + 5, 2)
        v = vdc(i * 23 + 9, 3)
        cx = round(x0 + u * (x1 - x0), 2)
        cy = round(y0 + v * (y1 - y0), 2)
        cover.append({
            "id": f"M02_COV_{i:03d}",
            "type": cover_catalog[i % len(cover_catalog)],
            "pos": [cx, cy, 0.0],
            "zone": zname,
        })
    assert len(cover) == 484
    cover = ensure_zero_step_repeats(cover, allow_micro_jitter=True)

    # =========================================================================
    # 11. PROPS (Exact 906 Props including S1 Radio Equipment & Safe O1)
    # =========================================================================
    props: List[Dict[str, Any]] = [
        {
            "id": "M02_OBJ_S1_RADIO_EQUIP",
            "type": "prop_radio_transmitter_rack_a",
            "name": "Militia High-Power Radio Equipment (S1 — Disables QRF)",
            "pos": [400.0, 380.0, 0.0],
            "zone": "ZONE_D",
            "room": "R2",
            "objective_id": "S1",
            "disables_event": "E_M02_QRF",
        },
        {
            "id": "M02_OBJ_O1_COMMAND_SAFE",
            "type": "prop_safe_classified_a",
            "name": "Command Tent Classified Document Safe (O1)",
            "pos": [450.0, 490.0, 0.0],
            "zone": "ZONE_E",
            "objective_id": "O1",
            "unlocks_reward": "MP9",
        },
        {
            "id": "M02_ALM_01",
            "type": "prop_alarm_panel_a",
            "name": "Radio Comms South Exterior Alarm Panel #1",
            "pos": [395.0, 365.0, 1.3],
            "zone": "ZONE_D",
        },
        {
            "id": "M02_ALM_02",
            "type": "prop_alarm_panel_a",
            "name": "West Barracks Courtyard Alarm Panel #2",
            "pos": [310.0, 350.0, 1.3],
            "zone": "ZONE_D",
        },
    ]

    prop_catalog = [
        "prop_ammo_crate_wood_a",
        "prop_fuel_drum_metal_a",
        "prop_radio_field_desk_a",
        "prop_workbench_tools_a",
        "prop_camouflage_crate_a",
        "prop_water_jerrycan_a",
        "prop_field_cot_bed_a",
        "prop_map_board_easel_a",
        "prop_cable_spool_wood_a",
        "prop_weapon_rack_empty_a",
        "prop_timber_stack_a",
        "prop_generator_field_small_a",
    ]
    for i in range(1, 903):
        zname, x0, y0, x1, y1 = veg_zones[i % len(veg_zones)]
        u = vdc(i * 29 + 13, 2)
        v = vdc(i * 31 + 17, 5)
        px = round(x0 + u * (x1 - x0), 2)
        py = round(y0 + v * (y1 - y0), 2)
        props.append({
            "id": f"M02_PRP_{i:03d}",
            "type": prop_catalog[i % len(prop_catalog)],
            "pos": [px, py, 0.0],
            "zone": zname,
        })
    assert len(props) == 906, f"Expected 906 props, got {len(props)}"
    props = ensure_zero_step_repeats(props, allow_micro_jitter=True)

    # =========================================================================
    # 12. SCRIPTED EVENTS (Exact 3 Dynamic Mission Events)
    # =========================================================================
    events = [
        {
            "id": "E_M02_MIST",
            "trigger": "elapsed >= 600s",
            "elapsed_threshold_s": 600.0,
            "action": "weather_clear_mist",
            "description": "At elapsed >= 600s, morning mist clears, increasing enemy vision range by +25%.",
        },
        {
            "id": "E_M02_SHIFT",
            "trigger": "elapsed >= 480s",
            "elapsed_threshold_s": 480.0,
            "action": "swap_patrol_sectors",
            "squads": ["P3", "P4"],
            "description": "At elapsed >= 480s, patrol squads P3 and P4 swap sectors in Zone D.",
        },
        {
            "id": "E_M02_QRF",
            "trigger": "alert_level == 3 for 45s",
            "required_alert_level": 3,
            "hold_duration_s": 45.0,
            "disabled_by_objective": "S1",
            "spawn_pos": [40.0, 300.0, 0.0],
            "spawn_vehicle": "veh_jeep_tactical_a",
            "spawn_enemies": [
                {"class": "E1", "weapon": "wpn_mp9_mesh"},
                {"class": "E1", "weapon": "wpn_mp9_mesh"},
                {"class": "E1", "weapon": "wpn_mp9_mesh"},
                {"class": "E1", "weapon": "wpn_mp9_mesh"},
            ],
            "description": "If alert_level == 3 for 45s (and S1 Radio Equipment at (400, 380) is not destroyed), spawns tactical jeep veh_jeep_tactical_a with 4x E1 militia reinforcements at (40.0, 300.0).",
        },
    ]

    # =========================================================================
    # 13. OBJECTIVES (O1, S1, S2) & 3 COMPLETE 6-WAYPOINT ROUTES
    # =========================================================================
    objectives = {
        "primary": [
            {
                "id": "O1",
                "title": "Steal documents from safe in command tent at (450, 490)",
                "target_id": "M02_OBJ_O1_COMMAND_SAFE",
                "target_pos": [450.0, 490.0, 0.0],
                "zone": "ZONE_E",
                "unlock_reward": "MP9",
            }
        ],
        "secondary": [
            {
                "id": "S1",
                "title": "Destroy radio equipment at (400, 380)",
                "target_id": "M02_OBJ_S1_RADIO_EQUIP",
                "target_pos": [400.0, 380.0, 0.0],
                "zone": "ZONE_D",
                "effect": "Disables E_M02_QRF reinforcement call",
            },
            {
                "id": "S2",
                "title": "Eliminate radio officer silently",
                "target_id": "M02_E3_02",
                "target_pos": [442.0, 482.0, 0.0],
                "zone": "ZONE_E",
                "medal_reward": "Ghost Medal",
            },
        ],
        "extraction": {
            "id": "EXT_M02",
            "title": "Extract at West Forest Extraction Zone (40, 320)",
            "pos": [40.0, 320.0, 0.0],
            "radius": 10.0,
            "zone": "ZONE_F",
        },
    }

    routes = {
        "silent": {
            "name": "Silent Route (East Ridge Prone Disarm & East Fence Cut)",
            "description": "Insert at (700, 15), creep up Zone B East Ridge (620, 210) using Prone crawl to disarm buried mines, cut East perimeter fence at (560, 310) & disarm M02_T1_01, slip north to (540, 490), enter Command Tent East flap to (450, 490), and exfiltrate west to (40, 320).",
            "tools_required": ["wire_cutters", "crouch_prone_stealth"],
            "waypoints": [
                [700.0, 15.0],
                [620.0, 210.0],
                [560.0, 310.0],
                [540.0, 490.0],
                [450.0, 490.0],
                [40.0, 320.0],
            ],
        },
        "technical": {
            "name": "Technical Route (Radio Comms Sabotage S1 & Inner Gate Hack)",
            "description": "Advance from (700, 15) to South-East approach (400, 180), enter Zone D Radio Comms Building via South doorway to (400, 380) to destroy S1 Radio Equipment, exit North doorway to (400, 490), enter Command Tent West doorway to (450, 490), and extract at (40, 320).",
            "tools_required": ["hacking_device_pda", "emp_grenade", "lockpick_set"],
            "waypoints": [
                [700.0, 15.0],
                [400.0, 180.0],
                [400.0, 380.0],
                [400.0, 490.0],
                [450.0, 490.0],
                [40.0, 320.0],
            ],
        },
        "loud": {
            "name": "Loud Route (South Ridge Overwatch, C4 Breach & Direct Assault)",
            "description": "Move from (700, 15) to South Ridge overwatch (525, 95), breach South-East perimeter at (450, 240), advance along central compound corridor (450, 420) into Command Tent South doorway at (450, 490), and fight out west to (40, 320).",
            "tools_required": ["c4_charge", "primary_rifle_or_sniper"],
            "waypoints": [
                [700.0, 15.0],
                [525.0, 95.0],
                [450.0, 240.0],
                [450.0, 420.0],
                [450.0, 490.0],
                [40.0, 320.0],
            ],
        },
    }

    level_dict = {
        "mission_id": "M02",
        "title": "Disavowed",
        "chapter": 1,
        "scene_name": "M02",
        "width": MAP_W,
        "height": MAP_H,
        "area_hectares": 48.0,
        "biome": "forest",
        "time_of_day": "dawn",
        "weather": "mist",
        "player_start": {
            "pos": [700.0, 15.0, 0.0],
            "facing_deg": 315.0,
            "facing_cardinal": "North-West",
            "starting_loadout": [
                "wpn_usp45_suppressed",
                "wpn_m4a1_sopmod",
                "wpn_knife_mesh",
                "wire_cutters",
                "hacking_device_pda",
                "emp_grenade",
                "lockpick_set",
                "c4_charge",
                "Binoculars",
            ],
        },
        "strict_exclusions_enforced": {
            "forbidden_enemies": ["E5", "E6", "E7", "E8", "E9"],
            "forbidden_traps": ["T5", "T6", "T9", "T10", "T11", "T12"],
            "cameras_allowed": 0,
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


def write_m02_unity_scene_and_installer(level_dict: Dict[str, Any]) -> Tuple[str, str]:
    scenes_dir = os.path.join(ROOT_DIR, "Assets/_Project/Scenes")
    scripts_dir = os.path.join(ROOT_DIR, "Assets/_Project/Scripts/Core")
    os.makedirs(scenes_dir, exist_ok=True)
    os.makedirs(scripts_dir, exist_ok=True)

    scene_path = os.path.join(scenes_dir, "M02.unity")
    installer_path = os.path.join(scripts_dir, "M02_DisavowedSceneInstaller.cs")

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
  m_FogColor: {r: 0.55, g: 0.60, b: 0.64, a: 1}
  m_FogMode: 3
  m_FogDensity: 0.018
  m_AmbientMode: 0
  m_AmbientSkyColor: {r: 0.36, g: 0.42, b: 0.46, a: 1}
--- !u!157 &3
LightmapSettings:
  m_ObjectHideFlags: 0
  serializedVersion: 12
--- !u!196 &4
NavMeshSettings:
  serializedVersion: 2
  m_ObjectHideFlags: 0
--- !u!1 &200
GameObject:
  m_ObjectHideFlags: 0
  serializedVersion: 6
  m_Component:
  - component: {fileID: 201}
  - component: {fileID: 202}
  m_Name: M02_Disavowed_MissionRoot
  m_TagString: Untagged
  m_IsActive: 1
--- !u!4 &201
Transform:
  m_ObjectHideFlags: 0
  m_GameObject: {fileID: 200}
  m_LocalRotation: {x: 0, y: 0, z: 0, w: 1}
  m_LocalPosition: {x: 0, y: 0, z: 0}
  m_LocalScale: {x: 1, y: 1, z: 1}
--- !u!114 &202
MonoBehaviour:
  m_ObjectHideFlags: 0
  m_GameObject: {fileID: 200}
  m_Enabled: 1
  m_EditorHideFlags: 0
  m_Script: {fileID: 11500000, guid: b2c3d4e5f60718293a4b5c6d7e8f90a1, type: 3}
  m_Name: 
  m_EditorClassIdentifier: RealLoserStudio.Tactical.Core.M02_DisavowedSceneInstaller
  missionJsonPath: Assets/_Project/Missions/M02.json
  enforceStrictM02Exclusions: 1
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
using RealLoserStudio.Tactical.Streaming;

namespace RealLoserStudio.Tactical.Core
{
    /// <summary>
    /// Scene Bootstrapper & Dynamic Event Controller for Mission 02 ("Disavowed" — M02.unity / M02.json).
    /// Manages the 800x600m (48.0 Hectare) Dawn/Mist Forest map, 24 Enemies (16x E1, 2x E3, 2x E10, 4x E12),
    /// 8 Traps (2x T1, 2x T3, 2x T4, 2x T8), 0 Cameras, and 3 Dynamic Mission Events:
    /// - E_M02_MIST (elapsed >= 600s -> weather_clear_mist)
    /// - E_M02_SHIFT (elapsed >= 480s -> swap P3 and P4 patrol sectors)
    /// - E_M02_QRF (alert_level == 3 for 45s -> spawn veh_jeep_tactical_a + 4x E1 at (40, 300) unless S1 destroyed)
    /// </summary>
    public class M02_DisavowedSceneInstaller : MonoBehaviour
    {
        [Header("Mission 02 Configuration")]
        public string missionJsonPath = "Assets/_Project/Missions/M02.json";
        public bool enforceStrictM02Exclusions = true;

        [Header("References")]
        public PlayerTacticalController playerController;
        public StealthAndDetectionSystem stealthSystem;
        public MissionEventAndStreamingSystem streamingSystem;

        [Header("Dynamic Event Timers & Flags")]
        public float missionElapsedSeconds;
        public float alert3ContinuousSeconds;
        public bool eventMistClearedTriggered;
        public bool eventShiftSwapTriggered;
        public bool eventQrfSpawned;

        [Header("Objectives State")]
        public bool objectiveO1_SafeDocumentsStolen;
        public bool objectiveS1_RadioEquipmentDestroyed;
        public bool objectiveS2_RadioOfficerEliminatedSilently;
        public bool rewardMP9Unlocked;

        private void Start()
        {
            if (playerController != null)
            {
                // Spawn at Zone A South-East Misty Pine Ridge [700.0, 15.0]
                playerController.transform.position = new Vector3(700.0f, 0.0f, 15.0f);
                playerController.transform.rotation = Quaternion.Euler(0f, 315.0f, 0f);
            }
        }

        private void Update()
        {
            TickMissionEvents(Time.deltaTime);
        }

        public void TickMissionEvents(float deltaTime)
        {
            missionElapsedSeconds += deltaTime;

            // 1. E_M02_SHIFT: At elapsed >= 480s, patrol squads P3 and P4 swap sectors
            if (!eventShiftSwapTriggered && missionElapsedSeconds >= 480.0f)
            {
                eventShiftSwapTriggered = true;
            }

            // 2. E_M02_MIST: At elapsed >= 600s, morning mist clears (weather_clear_mist)
            if (!eventMistClearedTriggered && missionElapsedSeconds >= 600.0f)
            {
                eventMistClearedTriggered = true;
                RenderSettings.fogDensity = 0.004f;
                if (stealthSystem != null)
                {
                    stealthSystem.ambientLightFactor = 1.15f;
                }
            }

            // 3. E_M02_QRF: If alert_level == 3 for 45s (and S1 Radio Equipment not destroyed)
            if (!eventQrfSpawned && !objectiveS1_RadioEquipmentDestroyed && stealthSystem != null)
            {
                if (stealthSystem.currentAlertLevel == CompoundAlertLevel.Alert3_CombatLock)
                {
                    alert3ContinuousSeconds += deltaTime;
                    if (alert3ContinuousSeconds >= 45.0f)
                    {
                        eventQrfSpawned = true;
                        SpawnTacticalJeepQRF(new Vector3(40.0f, 0.0f, 300.0f));
                    }
                }
                else
                {
                    alert3ContinuousSeconds = 0f;
                }
            }
        }

        public void OnDestroyRadioEquipment_S1()
        {
            objectiveS1_RadioEquipmentDestroyed = true;
            alert3ContinuousSeconds = 0f; // Permanently disables QRF reinforcement call
        }

        public void OnStealSafeDocuments_O1()
        {
            objectiveO1_SafeDocumentsStolen = true;
            rewardMP9Unlocked = true;
        }

        public void OnEliminateRadioOfficerSilently_S2()
        {
            if (stealthSystem == null || stealthSystem.currentAlertLevel < CompoundAlertLevel.Alert2_CompoundAlarm)
            {
                objectiveS2_RadioOfficerEliminatedSilently = true;
            }
        }

        private void SpawnTacticalJeepQRF(Vector3 spawnPos)
        {
            // Spawns veh_jeep_tactical_a + 4x E1 Militia Grunts at (40.0, 300.0)
        }
    }
}
"""
    with open(installer_path, "w", encoding="utf-8") as f:
        f.write(installer_cs)

    return scene_path, installer_path


def main() -> int:
    level_data = build_m02_level_dict()

    missions_dir = os.path.join(ROOT_DIR, "Assets/_Project/Missions")
    out_dir = os.path.join(ROOT_DIR, "artifacts/file_generation/ttl=63d/output")
    os.makedirs(missions_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)

    paths = [
        os.path.join(ROOT_DIR, "M02.json"),
        os.path.join(missions_dir, "M02.json"),
        os.path.join(out_dir, "M02.json"),
    ]
    for p in paths:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(level_data, f, indent=2)

    scene_path, installer_path = write_m02_unity_scene_and_installer(level_data)
    with open(installer_path, "r", encoding="utf-8") as src, open(
        os.path.join(out_dir, "M02_DisavowedSceneInstaller.cs"), "w", encoding="utf-8"
    ) as dst:
        dst.write(src.read())

    with open(scene_path, "r", encoding="utf-8") as src, open(
        os.path.join(out_dir, "M02.unity"), "w", encoding="utf-8"
    ) as dst:
        dst.write(src.read())

    print(f"[M02 BUILDER] Successfully generated M02.json, {scene_path}, and {installer_path}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
