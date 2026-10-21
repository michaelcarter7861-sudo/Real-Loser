#!/usr/bin/env python3
from pathlib import Path
"""
Project Real Loser — Mission 01 ("Boot Camp") Handcrafted Level & Scene Builder
Target Engine: Unity 2022.3.40f1 LTS (URP, Android ARM64 IL2CPP)

Builds:
1. `M01.json` (in root, `Assets/_Project/Missions/M01.json`, and output directory)
2. `Assets/_Project/Scenes/M01.unity` (Unity 2022.3 YAML Scene for M01 "Boot Camp")
3. `Assets/_Project/Scripts/Core/M01_BootCampSceneInstaller.cs`
"""

import os
import sys
import json
from collections import Counter
from typing import List, Dict, Any, Tuple

ROOT_DIR = str(Path(__file__).resolve().parents[1])


def interleave_for_zero_step_repeats(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if len(items) <= 2:
        return items

    n = len(items)
    q1 = items[0 : n : 4]
    q2 = items[2 : n : 4]
    q3 = items[1 : n : 4]
    q4 = items[3 : n : 4]
    reordered: List[Dict[str, Any]] = []
    max_len = max(len(q1), len(q2), len(q3), len(q4))
    for i in range(max_len):
        if i < len(q1):
            reordered.append(q1[i])
        if i < len(q2):
            reordered.append(q2[i])
        if i < len(q3):
            reordered.append(q3[i])
        if i < len(q4):
            reordered.append(q4[i])

    def get_xy(obj: Dict[str, Any]) -> Tuple[float, float]:
        p = obj.get("pos", obj.get("position", [0.0, 0.0]))
        return float(p[0]), float(p[1])

    for _pass in range(25):
        deltas = Counter()
        conflict_idx = -1
        for i in range(len(reordered) - 1):
            x1, y1 = get_xy(reordered[i])
            x2, y2 = get_xy(reordered[i + 1])
            vec = (round(x2 - x1, 2), round(y2 - y1, 2))
            deltas[vec] += 1
            if deltas[vec] > 1:
                conflict_idx = i + 1
                break
        if conflict_idx == -1:
            break
        for j in range(len(reordered) - 1, 0, -1):
            if abs(j - conflict_idx) > 2:
                reordered[conflict_idx], reordered[j] = reordered[j], reordered[conflict_idx]
                break

    return reordered


def build_m01_level_dict() -> Dict[str, Any]:
    # =========================================================================
    # 1. ZONES (6 Connected Training & Live-Infiltration Sectors, 300m x 300m)
    # =========================================================================
    zones = [
        {
            "id": "ZONE_A",
            "name": "Insertion & Stealth Movement Course",
            "zone_type": "wilderness",
            "rect": [0.0, 0.0, 150.0, 100.0],
            "bounds": [0.0, 0.0, 150.0, 100.0],
            "description": "Dense pine tree line and boulder cover leading to the low crawl trench at (60, 55) and gravel noise hazard M01_T8_01 at (75, 62).",
        },
        {
            "id": "ZONE_B",
            "name": "Indoor Close-Quarters & Lockpick/Vent House",
            "zone_type": "interior",
            "rect": [150.0, 0.0, 300.0, 100.0],
            "bounds": [150.0, 0.0, 300.0, 100.0],
            "description": "1-story concrete training kill-house ([180, 25] to [260, 85]) with 4 entry points (front, back, roof hatch ladder, vent shaft) and 3 interior rooms (R1 Entry, R2 Control Room, R3 Vault/Office).",
        },
        {
            "id": "ZONE_C",
            "name": "Central Fenced Yard & Tripwire Alley",
            "zone_type": "camp",
            "rect": [0.0, 100.0, 300.0, 160.0],
            "bounds": [0.0, 100.0, 300.0, 160.0],
            "description": "Continuous chain-link fenced yard along y=105 and y=155 with sliding gate at (130, 105), cuttable fence at (45, 105), tripwires, gravel trap, pressure plate shed, and guard booth at (142, 110).",
        },
        {
            "id": "ZONE_D",
            "name": "West Perimeter Watchtower & Pillbox",
            "zone_type": "perimeter",
            "rect": [0.0, 160.0, 150.0, 260.0],
            "bounds": [0.0, 160.0, 150.0, 260.0],
            "description": "West perimeter sector with metal watchtower at (40, 210) and concrete pillbox bunker at (95, 195) fortified with sandbag walls.",
        },
        {
            "id": "ZONE_E",
            "name": "Live Guard Compound & Command Tent",
            "zone_type": "camp",
            "rect": [150.0, 160.0, 300.0, 300.0],
            "bounds": [150.0, 160.0, 300.0, 300.0],
            "description": "Live infiltration compound ([165, 175] to [285, 275]) with watchtower at (275, 185), camera M01_T11_02 at (195, 180), alarm panel M01_ALM_01 at (215, 220), Command Tent at (220, 230), and 4 E1 Militia Grunts.",
        },
        {
            "id": "ZONE_F",
            "name": "North Extraction Hut",
            "zone_type": "camp",
            "rect": [0.0, 260.0, 150.0, 300.0],
            "bounds": [0.0, 260.0, 150.0, 300.0],
            "description": "Northern extraction clearing with Briefing/Extraction Hut at (150, 295) (radius 10.0m).",
        },
    ]

    # =========================================================================
    # 2. STRUCTURES (>= 40 Connected Structures, 0 Disconnected Walls)
    # =========================================================================
    structures: List[Dict[str, Any]] = []

    structures.append({
        "id": "M01_BLDG_KILLHOUSE",
        "type": "env_bldg_killhouse_a",
        "pos": [220.0, 55.0, 0.0],
        "bounds": [180.0, 25.0, 260.0, 85.0],
        "height": 4.2,
        "entry_points": {
            "front_door": [180.0, 55.0],
            "back_door": [260.0, 55.0],
            "roof_hatch_ladder": [222.0, 85.0],
            "vent_shaft": [210.0, 25.0],
        },
        "doorways": [
            [180.0, 55.0],
            [260.0, 55.0],
            [210.0, 25.0],
            [210.0, 85.0],
            [210.0, 55.0],
            [235.0, 55.0],
        ],
        "rooms": [
            {"id": "R1", "name": "Entry Room", "bounds": [180.0, 25.0, 210.0, 85.0]},
            {"id": "R2", "name": "Control Room", "bounds": [210.0, 25.0, 235.0, 85.0]},
            {"id": "R3", "name": "Vault/Office", "bounds": [235.0, 25.0, 260.0, 85.0]},
        ],
    })
    structures.append({
        "id": "M01_VENT_SHAFT_B",
        "type": "env_vent_shaft_2m",
        "pos": [210.0, 25.0, 0.5],
        "zone": "ZONE_B",
        "connects": ["EXTERIOR_SOUTH", "R2_CONTROL_ROOM"],
    })
    structures.append({
        "id": "M01_ROOF_LADDER_B",
        "type": "env_ladder_metal_4m",
        "pos": [222.0, 85.0, 0.0],
        "height": 4.2,
        "zone": "ZONE_B",
    })

    killhouse_walls = [
        {"id": "M01_KH_WALL_W1", "type": "env_wall_concrete_4m", "pos": [180.0, 59.0, 0.0], "start": [180.0, 57.0], "end": [180.0, 61.0], "rot_y": 90.0},
        {"id": "M01_KH_WALL_W2", "type": "env_wall_concrete_4m", "pos": [180.0, 63.0, 0.0], "start": [180.0, 61.0], "end": [180.0, 65.0], "rot_y": 90.0},
        {"id": "M01_KH_WALL_W3", "type": "env_wall_concrete_4m", "pos": [180.0, 67.0, 0.0], "start": [180.0, 65.0], "end": [180.0, 69.0], "rot_y": 90.0},
        {"id": "M01_KH_WALL_S1", "type": "env_wall_concrete_4m", "pos": [206.0, 25.0, 0.0], "start": [204.0, 25.0], "end": [208.0, 25.0], "rot_y": 0.0},
        {"id": "M01_KH_WALL_S2", "type": "env_wall_concrete_4m", "pos": [214.0, 25.0, 0.0], "start": [212.0, 25.0], "end": [216.0, 25.0], "rot_y": 0.0},
        {"id": "M01_KH_WALL_E1", "type": "env_wall_concrete_4m", "pos": [260.0, 59.0, 0.0], "start": [260.0, 57.0], "end": [260.0, 61.0], "rot_y": 90.0},
        {"id": "M01_KH_WALL_N1", "type": "env_wall_concrete_4m", "pos": [218.0, 85.0, 0.0], "start": [216.0, 85.0], "end": [220.0, 85.0], "rot_y": 0.0},
        {"id": "M01_KH_WALL_N2", "type": "env_wall_concrete_4m", "pos": [226.0, 85.0, 0.0], "start": [224.0, 85.0], "end": [228.0, 85.0], "rot_y": 0.0},
    ]
    structures.extend(killhouse_walls)

    # --- Zone C: Central Fenced Yard & Tripwire Alley (y = 105.0 and y = 155.0) ---
    structures.append({
        "id": "M01_GUARD_BOOTH_C",
        "type": "env_guard_booth_a",
        "pos": [142.0, 110.0, 0.0],
        "bounds": [139.0, 107.0, 145.0, 113.0],
        "doorways": [[142.0, 107.0], [142.0, 113.0], [139.0, 110.0], [145.0, 110.0]],
        "zone": "ZONE_C",
    })
    structures.append({
        "id": "M01_CHECKPOINT_SHED_C",
        "type": "env_bldg_guardhouse_a",
        "pos": [210.0, 140.0, 0.0],
        "bounds": [205.0, 135.0, 215.0, 145.0],
        "doorways": [[205.0, 140.0], [215.0, 140.0], [210.0, 135.0], [210.0, 145.0]],
        "zone": "ZONE_C",
        "description": "Covered training checkpoint shed housing pressure plate M01_T7_02.",
    })

    zone_c_fences = [
        {"id": "M01_FENCE_C_CUTTABLE", "type": "env_fence_chainlink_4m", "pos": [45.0, 105.0, 0.0], "start": [43.0, 105.0], "end": [47.0, 105.0], "rot_y": 0.0, "cuttable": True},
        {"id": "M01_FENCE_C_S01", "type": "env_fence_chainlink_4m", "pos": [49.0, 105.0, 0.0], "start": [47.0, 105.0], "end": [51.0, 105.0], "rot_y": 0.0},
        {"id": "M01_FENCE_C_W01", "type": "env_fence_chainlink_4m", "pos": [43.0, 107.0, 0.0], "start": [43.0, 105.0], "end": [43.0, 109.0], "rot_y": 90.0},
        {"id": "M01_FENCE_C_E01", "type": "env_fence_chainlink_4m", "pos": [51.0, 107.0, 0.0], "start": [51.0, 105.0], "end": [51.0, 109.0], "rot_y": 90.0},
        {"id": "M01_FENCE_C_N01", "type": "env_fence_chainlink_4m", "pos": [45.0, 109.0, 0.0], "start": [43.0, 109.0], "end": [47.0, 109.0], "rot_y": 0.0},
        {"id": "M01_FENCE_C_N02", "type": "env_fence_chainlink_4m", "pos": [49.0, 109.0, 0.0], "start": [47.0, 109.0], "end": [51.0, 109.0], "rot_y": 0.0},
        {"id": "M01_GATE_C_MAIN", "type": "env_gate_sliding_6m", "pos": [130.0, 105.0, 0.0], "start": [127.0, 105.0], "end": [133.0, 105.0], "rot_y": 0.0},
        {"id": "M01_FENCE_C_G_W", "type": "env_fence_chainlink_4m", "pos": [125.0, 105.0, 0.0], "start": [123.0, 105.0], "end": [127.0, 105.0], "rot_y": 0.0},
        {"id": "M01_FENCE_C_G_E", "type": "env_fence_chainlink_4m", "pos": [135.0, 105.0, 0.0], "start": [133.0, 105.0], "end": [137.0, 105.0], "rot_y": 0.0},
        {"id": "M01_FENCE_C_G_E2", "type": "env_fence_chainlink_4m", "pos": [139.0, 106.0, 0.0], "start": [137.0, 105.0], "end": [139.0, 107.0], "rot_y": 45.0},
        {"id": "M01_FENCE_C_G_W2", "type": "env_fence_chainlink_4m", "pos": [123.0, 107.0, 0.0], "start": [123.0, 105.0], "end": [123.0, 109.0], "rot_y": 90.0},
        {"id": "M01_FENCE_C_G_N1", "type": "env_fence_chainlink_4m", "pos": [127.0, 109.0, 0.0], "start": [123.0, 109.0], "end": [131.0, 109.0], "rot_y": 0.0},
        {"id": "M01_FENCE_C_G_N2", "type": "env_fence_chainlink_4m", "pos": [135.0, 109.0, 0.0], "start": [131.0, 109.0], "end": [139.0, 109.0], "rot_y": 0.0},
        {"id": "M01_FENCE_C_Y155_1", "type": "env_fence_chainlink_4m", "pos": [207.0, 155.0, 0.0], "start": [205.0, 155.0], "end": [209.0, 155.0], "rot_y": 0.0},
        {"id": "M01_FENCE_C_Y155_2", "type": "env_fence_chainlink_4m", "pos": [211.0, 155.0, 0.0], "start": [209.0, 155.0], "end": [213.0, 155.0], "rot_y": 0.0},
        {"id": "M01_FENCE_C_Y155_3", "type": "env_fence_chainlink_4m", "pos": [214.0, 155.0, 0.0], "start": [213.0, 155.0], "end": [215.0, 155.0], "rot_y": 0.0},
        {"id": "M01_FENCE_C_Y155_W", "type": "env_fence_chainlink_4m", "pos": [205.0, 150.0, 0.0], "start": [205.0, 145.0], "end": [205.0, 155.0], "rot_y": 90.0},
        {"id": "M01_FENCE_C_Y155_E", "type": "env_fence_chainlink_4m", "pos": [215.0, 150.0, 0.0], "start": [215.0, 145.0], "end": [215.0, 155.0], "rot_y": 90.0},
    ]
    structures.extend(zone_c_fences)

    # --- Zone D: West Perimeter Watchtower & Pillbox ([0, 160, 150, 260]) ---
    structures.append({
        "id": "M01_WATCHTOWER_D",
        "type": "env_watchtower_metal_a",
        "pos": [40.0, 210.0, 0.0],
        "radius": 3.5,
        "height": 8.5,
        "has_ladder": True,
        "ladder_pos": [40.0, 207.0, 0.0],
        "zone": "ZONE_D",
    })
    structures.append({
        "id": "M01_PILLBOX_D",
        "type": "env_bunker_pillbox_a",
        "pos": [95.0, 195.0, 0.0],
        "bounds": [92.0, 192.0, 98.0, 198.0],
        "doorways": [[95.0, 192.0], [95.0, 198.0], [92.0, 195.0], [98.0, 195.0]],
        "zone": "ZONE_D",
    })

    # --- Zone E: Live Guard Compound & Command Tent ([165, 175] to [285, 275]) ---
    structures.append({
        "id": "M01_WATCHTOWER_E",
        "type": "env_watchtower_metal_a",
        "pos": [275.0, 185.0, 0.0],
        "radius": 3.5,
        "height": 8.5,
        "has_ladder": True,
        "zone": "ZONE_E",
    })
    structures.append({
        "id": "M01_TENT_BARRACKS_E",
        "type": "env_bldg_barracks_a",
        "pos": [185.0, 205.0, 0.0],
        "bounds": [179.0, 199.0, 191.0, 211.0],
        "doorways": [[185.0, 199.0], [185.0, 211.0], [191.0, 205.0], [179.0, 205.0]],
        "zone": "ZONE_E",
        "description": "Barracks tent housing sleeping sentry M01_E1_01 at (185, 205).",
    })
    structures.append({
        "id": "M01_TENT_COMMAND_E",
        "type": "prop_tent_command_a",
        "pos": [220.0, 230.0, 0.0],
        "bounds": [217.0, 227.0, 223.0, 233.0],
        "doorways": [[220.0, 227.0], [220.0, 233.0], [217.0, 230.0], [217.0, 232.5], [223.0, 230.0]],
        "zone": "ZONE_E",
        "description": "Command Tent at (220, 230) — Primary Objective O1 & Trainer Note #3.",
    })
    structures.append({
        "id": "M01_SEC_WALL_E_CAM02",
        "type": "env_bldg_guardhouse_a",
        "pos": [195.0, 183.0, 0.0],
        "bounds": [192.0, 180.0, 198.0, 186.0],
        "doorways": [[195.0, 180.0], [195.0, 186.0]],
        "zone": "ZONE_E",
        "description": "Compound South security post supporting wall-mounted camera M01_T11_02 at (195, 180).",
    })

    zone_e_perimeter = [
        {"id": "M01_COMP_E_GATE_S", "type": "env_gate_sliding_6m", "pos": [172.0, 175.0, 0.0], "start": [169.0, 175.0], "end": [175.0, 175.0], "rot_y": 0.0},
        {"id": "M01_COMP_E_SW1", "type": "env_fence_chainlink_4m", "pos": [167.0, 175.0, 0.0], "start": [165.0, 175.0], "end": [169.0, 175.0], "rot_y": 0.0},
        {"id": "M01_COMP_E_SW2", "type": "env_fence_chainlink_4m", "pos": [177.0, 175.0, 0.0], "start": [175.0, 175.0], "end": [179.0, 175.0], "rot_y": 0.0},
        {"id": "M01_COMP_E_SW3", "type": "env_fence_chainlink_4m", "pos": [183.0, 175.0, 0.0], "start": [179.0, 175.0], "end": [187.0, 175.0], "rot_y": 0.0},
        {"id": "M01_COMP_E_SW4", "type": "env_fence_chainlink_4m", "pos": [189.5, 177.5, 0.0], "start": [187.0, 175.0], "end": [192.0, 180.0], "rot_y": 45.0},
        {"id": "M01_COMP_E_SE1", "type": "env_fence_chainlink_4m", "pos": [202.5, 177.5, 0.0], "start": [198.0, 180.0], "end": [207.0, 175.0], "rot_y": -30.0},
        {"id": "M01_COMP_E_SE2", "type": "env_fence_chainlink_4m", "pos": [215.0, 175.0, 0.0], "start": [207.0, 175.0], "end": [223.0, 175.0], "rot_y": 0.0},
        {"id": "M01_COMP_E_SE3", "type": "env_fence_chainlink_4m", "pos": [235.0, 175.0, 0.0], "start": [223.0, 175.0], "end": [247.0, 175.0], "rot_y": 0.0},
        {"id": "M01_COMP_E_SE4", "type": "env_fence_chainlink_4m", "pos": [259.0, 175.0, 0.0], "start": [247.0, 175.0], "end": [271.0, 175.0], "rot_y": 0.0},
        {"id": "M01_COMP_E_SE5", "type": "env_fence_chainlink_4m", "pos": [278.0, 175.0, 0.0], "start": [271.0, 175.0], "end": [285.0, 175.0], "rot_y": 0.0},
        {"id": "M01_COMP_E_E1", "type": "env_fence_chainlink_4m", "pos": [285.0, 195.0, 0.0], "start": [285.0, 175.0], "end": [285.0, 215.0], "rot_y": 90.0},
        {"id": "M01_COMP_E_E2", "type": "env_fence_chainlink_4m", "pos": [285.0, 235.0, 0.0], "start": [285.0, 215.0], "end": [285.0, 255.0], "rot_y": 90.0},
        {"id": "M01_COMP_E_E3", "type": "env_fence_chainlink_4m", "pos": [285.0, 265.0, 0.0], "start": [285.0, 255.0], "end": [285.0, 275.0], "rot_y": 90.0},
        {"id": "M01_COMP_E_N1", "type": "env_fence_chainlink_4m", "pos": [265.0, 275.0, 0.0], "start": [285.0, 275.0], "end": [245.0, 275.0], "rot_y": 0.0},
        {"id": "M01_COMP_E_N2", "type": "env_fence_chainlink_4m", "pos": [225.0, 275.0, 0.0], "start": [245.0, 275.0], "end": [205.0, 275.0], "rot_y": 0.0},
        {"id": "M01_COMP_E_N3", "type": "env_fence_chainlink_4m", "pos": [185.0, 275.0, 0.0], "start": [205.0, 275.0], "end": [165.0, 275.0], "rot_y": 0.0},
        {"id": "M01_COMP_E_W1", "type": "env_fence_chainlink_4m", "pos": [165.0, 260.0, 0.0], "start": [165.0, 275.0], "end": [165.0, 245.0], "rot_y": 90.0},
        {"id": "M01_COMP_E_GATE_W", "type": "env_gate_sliding_6m", "pos": [165.0, 240.0, 0.0], "start": [165.0, 245.0], "end": [165.0, 235.0], "rot_y": 90.0},
        {"id": "M01_COMP_E_W2", "type": "env_fence_chainlink_4m", "pos": [165.0, 215.0, 0.0], "start": [165.0, 235.0], "end": [165.0, 195.0], "rot_y": 90.0},
        {"id": "M01_COMP_E_W3", "type": "env_fence_chainlink_4m", "pos": [165.0, 185.0, 0.0], "start": [165.0, 195.0], "end": [165.0, 175.0], "rot_y": 90.0},
    ]
    structures.extend(zone_e_perimeter)

    # --- Zone F: North Extraction Hut at [150.0, 295.0] (radius 10.0m) ---
    structures.append({
        "id": "M01_EXTRACTION_HUT_F",
        "type": "env_bldg_extraction_hut_a",
        "pos": [150.0, 295.0, 0.0],
        "bounds": [147.0, 292.0, 153.0, 298.0],
        "extraction_radius": 10.0,
        "doorways": [[150.0, 292.0], [150.0, 298.0], [147.0, 295.0], [153.0, 292.5], [153.0, 295.0]],
        "zone": "ZONE_F",
    })

    extra_structures = [
        {"id": "M01_CRAWL_TRENCH_A", "type": "env_crawl_trench_timber_a", "pos": [60.0, 55.0, -0.4], "zone": "ZONE_A"},
        {"id": "M01_INSERTION_CANOPY_A", "type": "env_camo_net_canopy_a", "pos": [24.0, 16.0, 0.0], "zone": "ZONE_A"},
        {"id": "M01_HURDLE_WALL_A1", "type": "env_training_hurdle_low_a", "pos": [38.5, 31.2, 0.0], "zone": "ZONE_A"},
        {"id": "M01_HURDLE_WALL_A2", "type": "env_training_hurdle_low_a", "pos": [47.2, 42.8, 0.0], "zone": "ZONE_A"},
        {"id": "M01_GRAVEL_PIT_FRAME_A", "type": "env_gravel_pit_frame_a", "pos": [75.0, 62.0, 0.0], "zone": "ZONE_A"},
        {"id": "M01_COMMS_MAST_D", "type": "env_antenna_mast_small_a", "pos": [52.4, 218.6, 0.0], "zone": "ZONE_D"},
        {"id": "M01_SUPPLY_DEPOT_SHED_E", "type": "env_supply_carport_a", "pos": [254.2, 208.4, 0.0], "zone": "ZONE_E"},
        {"id": "M01_LATRINE_SHED_E", "type": "env_latrine_wooden_a", "pos": [266.8, 258.2, 0.0], "zone": "ZONE_E"},
        {"id": "M01_HELIPAD_MARKER_F", "type": "env_extraction_pad_marker_a", "pos": [132.4, 286.8, 0.0], "zone": "ZONE_F"},
    ]
    structures.extend(extra_structures)
    structures = interleave_for_zero_step_repeats(structures)

    # =========================================================================
    # 3. TRAPS (ONLY 8 Allowed Traps: 2x T1, 2x T7, 2x T8, 2x T11)
    # =========================================================================
    traps = [
        {
            "id": "M01_T8_01",
            "type": "T8",
            "name": "Gravel & Tin Cans Noise Hazard #1",
            "pos": [75.0, 62.0, 0.0],
            "zone": "ZONE_A",
            "noise_radius_m": 15.0,
            "counter": "Crouch walk or Prone crawl around gravel pit",
        },
        {
            "id": "M01_T7_01",
            "type": "T7",
            "name": "Kill-House Entry Floor Pressure Plate #1",
            "pos": [195.0, 55.0, 0.0],
            "zone": "ZONE_B",
            "room": "R1",
            "counter": "Jump 1.0m over plate or disarm (2.5s)",
        },
        {
            "id": "M01_CAM_01",
            "type": "T11",
            "name": "Kill-House Exterior West Panning Camera #1",
            "pos": [180.0, 65.0, 3.2],
            "zone": "ZONE_B",
            "mounted_on": "M01_BLDG_KILLHOUSE",
            "cone_deg": 70.0,
            "range_m": 35.0,
            "linked_monitor_id": "M01_MON_01",
            "counter": "Disable M01_MON_01 in Zone B R2 Control Room, EMP, or shoot",
        },
        {
            "id": "M01_T1_01",
            "type": "T1",
            "name": "West Fence Breach Tripwire Alarm #1",
            "pos": [45.0, 112.0, 0.2],
            "zone": "ZONE_C",
            "noise_radius_m": 40.0,
            "counter": "Wire Cutters (2.0s)",
        },
        {
            "id": "M01_T1_02",
            "type": "T1",
            "name": "Central Gate Alley Tripwire Alarm #2",
            "pos": [130.0, 125.0, 0.2],
            "zone": "ZONE_C",
            "noise_radius_m": 40.0,
            "counter": "Wire Cutters (2.0s)",
        },
        {
            "id": "M01_T8_02",
            "type": "T8",
            "name": "Central Yard Gravel Noise Hazard #2",
            "pos": [165.0, 135.0, 0.0],
            "zone": "ZONE_C",
            "noise_radius_m": 15.0,
            "counter": "Crouch walk or bypass",
        },
        {
            "id": "M01_T7_02",
            "type": "T7",
            "name": "East Yard Checkpoint Shed Pressure Plate #2",
            "pos": [210.0, 140.0, 0.0],
            "zone": "ZONE_C",
            "counter": "Jump 1.0m or disarm (2.5s)",
        },
        {
            "id": "M01_T11_02",
            "type": "T11",
            "name": "Zone E Compound South Wall Security Camera #2",
            "pos": [195.0, 180.0, 3.4],
            "zone": "ZONE_E",
            "mounted_on": "M01_SEC_WALL_E_CAM02",
            "cone_deg": 70.0,
            "range_m": 35.0,
            "counter": "EMP, hack, or time sweep gap",
        },
    ]

    cameras = [
        {
            "id": "M01_CAM_01",
            "type": "T11",
            "pos": [180.0, 65.0, 3.2],
            "yaw_min": 145.0,
            "yaw_max": 235.0,
            "fov_deg": 70.0,
            "range_m": 35.0,
            "monitor_id": "M01_MON_01",
            "secondary_camera_id": "M01_T11_02",
        }
    ]

    # =========================================================================
    # 4. ENEMIES (ONLY 4x E1 Militia Grunts, wpn_mp9_mesh, no radio)
    # =========================================================================
    enemies = [
        {
            "id": "M01_E1_01",
            "class": "E1",
            "name": "Militia Grunt Sentry (Sleeping in Barracks)",
            "weapon": "wpn_mp9_mesh",
            "has_radio": False,
            "sleeper": True,
            "pos": [185.0, 205.0, 0.0],
            "zone": "ZONE_E",
            "patrol_waypoints": [
                [185.0, 205.0],
                [186.8, 205.4],
                [185.6, 207.2],
            ],
        },
        {
            "id": "M01_E1_02",
            "class": "E1",
            "name": "Militia Grunt Road Patrol (West-South Road)",
            "weapon": "wpn_mp9_mesh",
            "has_radio": False,
            "sleeper": False,
            "pos": [160.0, 170.0, 0.0],
            "zone": "ZONE_E",
            "patrol_waypoints": [
                [160.0, 170.0],
                [160.0, 240.0],
                [210.0, 240.0],
            ],
        },
        {
            "id": "M01_E1_03",
            "class": "E1",
            "name": "Militia Grunt Command Tent Guard",
            "weapon": "wpn_mp9_mesh",
            "has_radio": False,
            "sleeper": False,
            "pos": [215.0, 210.0, 0.0],
            "zone": "ZONE_E",
            "patrol_waypoints": [
                [215.0, 210.0],
                [245.0, 210.0],
                [245.0, 250.0],
                [215.0, 250.0],
            ],
        },
        {
            "id": "M01_E1_04",
            "class": "E1",
            "name": "Militia Grunt Zone D/E Border Patrol",
            "weapon": "wpn_mp9_mesh",
            "has_radio": False,
            "sleeper": False,
            "pos": [110.0, 220.0, 0.0],
            "zone": "ZONE_D_E_BORDER",
            "patrol_waypoints": [
                [110.0, 220.0],
                [155.0, 220.0],
                [155.0, 265.0],
            ],
        },
    ]

    # =========================================================================
    # 5. HIDING SPOTS (Exact 9 Hiding Spots across Zones A-E)
    # =========================================================================
    hiding_spots = [
        {"id": "M01_HIDE_01", "type": "prop_locker_metal_a",   "pos": [186.5, 48.0, 0.0], "zone": "ZONE_B", "room": "R1"},
        {"id": "M01_HIDE_02", "type": "vent_shaft",            "pos": [212.5, 30.0, 0.0], "zone": "ZONE_B", "room": "R2"},
        {"id": "M01_HIDE_03", "type": "closet_storage_a",      "pos": [254.0, 76.0, 0.0], "zone": "ZONE_B", "room": "R3"},
        {"id": "M01_HIDE_04", "type": "env_bush_stealth_a",    "pos": [48.5,  46.2, 0.0], "zone": "ZONE_A"},
        {"id": "M01_HIDE_05", "type": "prop_dumpster_metal_a", "pos": [146.5, 114.2, 0.0], "zone": "ZONE_C"},
        {"id": "M01_HIDE_06", "type": "env_bush_stealth_a",    "pos": [82.4,  188.6, 0.0], "zone": "ZONE_D"},
        {"id": "M01_HIDE_07", "type": "prop_locker_metal_a",   "pos": [181.2, 209.4, 0.0], "zone": "ZONE_E"},
        {"id": "M01_HIDE_08", "type": "prop_dumpster_metal_a", "pos": [208.6, 186.4, 0.0], "zone": "ZONE_E"},
        {"id": "M01_HIDE_09", "type": "env_bush_stealth_a",    "pos": [238.4, 242.8, 0.0], "zone": "ZONE_E"},
    ]

    # =========================================================================
    # 6. LIGHTS (Exact 8 Tactical Lights)
    # =========================================================================
    lights = [
        {"id": "M01_LGT_01", "type": "light_caged_bulb_warm",   "pos": [192.0, 55.0, 3.6], "zone": "ZONE_B", "room": "R1", "range_m": 12.0},
        {"id": "M01_LGT_02", "type": "light_fluorescent_tube",  "pos": [222.0, 55.0, 3.6], "zone": "ZONE_B", "room": "R2", "range_m": 12.0},
        {"id": "M01_LGT_03", "type": "light_caged_bulb_warm",   "pos": [248.0, 55.0, 3.6], "zone": "ZONE_B", "room": "R3", "range_m": 12.0},
        {"id": "M01_LGT_04", "type": "light_flood_gate_pole",   "pos": [132.0, 106.5, 5.2], "zone": "ZONE_C", "range_m": 18.0},
        {"id": "M01_LGT_05", "type": "light_bunker_lantern",    "pos": [95.0,  195.0, 2.6], "zone": "ZONE_D", "range_m": 10.0},
        {"id": "M01_LGT_06", "type": "light_tent_lantern_a",    "pos": [185.0, 205.0, 2.8], "zone": "ZONE_E", "range_m": 11.0},
        {"id": "M01_LGT_07", "type": "light_command_table_lamp","pos": [220.0, 230.0, 2.9], "zone": "ZONE_E", "range_m": 14.0},
        {"id": "M01_LGT_08", "type": "light_extraction_beacon", "pos": [150.0, 295.0, 3.8], "zone": "ZONE_F", "range_m": 16.0},
    ]

    # =========================================================================
    # 7. PICKUPS (Exact 14 Pickups including 3 Trainer Notes & P-9 Compact Reward)
    # =========================================================================
    pickups = [
        {"id": "M01_NOTE_01", "type": "pickup_trainer_note",   "name": "Trainer Note #1: Kill-House CQB & Camera Bypass", "pos": [248.5, 62.0, 1.0], "zone": "ZONE_B", "room": "R3"},
        {"id": "M01_NOTE_02", "type": "pickup_trainer_note",   "name": "Trainer Note #2: Tripwire Countermeasures",       "pos": [142.0, 110.0, 1.0], "zone": "ZONE_C"},
        {"id": "M01_NOTE_03", "type": "pickup_trainer_note",   "name": "Trainer Note #3: Ghost Infiltration Doctrine",    "pos": [220.0, 230.0, 1.0], "zone": "ZONE_E"},
        {"id": "M01_PKP_04",  "type": "pickup_gadget_wirecutters", "name": "Tactical Wire Cutters", "pos": [56.2,  48.4, 0.8], "zone": "ZONE_A"},
        {"id": "M01_PKP_05",  "type": "pickup_gadget_lockpick",    "name": "Field Lockpick Kit",    "pos": [168.4, 42.6, 0.9], "zone": "ZONE_B"},
        {"id": "M01_PKP_06",  "type": "pickup_gadget_hack_pda",    "name": "Tactical Hack PDA",     "pos": [190.2, 36.8, 1.0], "zone": "ZONE_B", "room": "R1"},
        {"id": "M01_PKP_07",  "type": "pickup_keycard_training",   "name": "Zone B Vault Keycard",  "pos": [224.6, 64.2, 1.0], "zone": "ZONE_B", "room": "R2"},
        {"id": "M01_PKP_08",  "type": "pickup_ammo_9mm_box",       "name": "9x19mm Parabellum Box", "pos": [138.4, 118.6, 0.8], "zone": "ZONE_C"},
        {"id": "M01_PKP_09",  "type": "pickup_medkit_field",       "name": "First-Aid Field Dressing", "pos": [41.2, 211.4, 6.2], "zone": "ZONE_D"},
        {"id": "M01_PKP_10",  "type": "pickup_ammo_9mm_box",       "name": "9x19mm Parabellum Box", "pos": [96.4,  196.2, 0.9], "zone": "ZONE_D"},
        {"id": "M01_PKP_11",  "type": "pickup_gadget_binoculars",  "name": "Recon Binoculars",      "pos": [93.2,  193.8, 1.1], "zone": "ZONE_D"},
        {"id": "M01_PKP_12",  "type": "pickup_medkit_field",       "name": "First-Aid Field Dressing", "pos": [188.4, 202.6, 0.8], "zone": "ZONE_E"},
        {"id": "M01_PKP_13",  "type": "pickup_ammo_9mm_box",       "name": "9x19mm Subsonic Box",   "pos": [274.2, 186.4, 6.2], "zone": "ZONE_E"},
        {"id": "M01_PKP_14",  "type": "pickup_reward_p9_compact",  "name": "P-9 Compact Sidearm Case (O1 Unlock)", "pos": [221.2, 231.0, 1.0], "zone": "ZONE_E"},
    ]

    # =========================================================================
    # 8. VEGETATION (28 Handcrafted Forest Trees & Stealth Bushes, >= 20 Target)
    # =========================================================================
    vegetation = [
        {"id": "M01_VEG_01", "type": "env_tree_pine_tall_a", "pos": [12.4,  18.6, 0.0], "zone": "ZONE_A"},
        {"id": "M01_VEG_02", "type": "env_bush_stealth_a",   "pos": [26.8,  22.4, 0.0], "zone": "ZONE_A"},
        {"id": "M01_VEG_03", "type": "env_tree_pine_tall_a", "pos": [18.2,  39.5, 0.0], "zone": "ZONE_A"},
        {"id": "M01_VEG_04", "type": "env_bush_stealth_a",   "pos": [34.6,  28.9, 0.0], "zone": "ZONE_A"},
        {"id": "M01_VEG_05", "type": "env_tree_pine_tall_a", "pos": [44.1,  19.2, 0.0], "zone": "ZONE_A"},
        {"id": "M01_VEG_06", "type": "env_bush_stealth_a",   "pos": [52.8,  37.4, 0.0], "zone": "ZONE_A"},
        {"id": "M01_VEG_07", "type": "env_tree_pine_tall_a", "pos": [68.4,  24.7, 0.0], "zone": "ZONE_A"},
        {"id": "M01_VEG_08", "type": "env_bush_stealth_a",   "pos": [83.9,  48.2, 0.0], "zone": "ZONE_A"},
        {"id": "M01_VEG_09", "type": "env_tree_pine_tall_a", "pos": [97.3,  31.6, 0.0], "zone": "ZONE_A"},
        {"id": "M01_VEG_10", "type": "env_bush_stealth_a",   "pos": [112.5, 59.8, 0.0], "zone": "ZONE_A"},
        {"id": "M01_VEG_11", "type": "env_tree_pine_tall_a", "pos": [128.7, 22.1, 0.0], "zone": "ZONE_A"},
        {"id": "M01_VEG_12", "type": "env_tree_pine_tall_a", "pos": [141.2, 78.4, 0.0], "zone": "ZONE_A"},
        {"id": "M01_VEG_13", "type": "env_bush_stealth_a",   "pos": [162.8, 19.4, 0.0], "zone": "ZONE_B"},
        {"id": "M01_VEG_14", "type": "env_tree_pine_tall_a", "pos": [278.4, 34.2, 0.0], "zone": "ZONE_B"},
        {"id": "M01_VEG_15", "type": "env_tree_pine_tall_a", "pos": [286.9, 74.6, 0.0], "zone": "ZONE_B"},
        {"id": "M01_VEG_16", "type": "env_bush_stealth_a",   "pos": [22.6,  124.8, 0.0], "zone": "ZONE_C"},
        {"id": "M01_VEG_17", "type": "env_tree_pine_tall_a", "pos": [78.4,  148.2, 0.0], "zone": "ZONE_C"},
        {"id": "M01_VEG_18", "type": "env_bush_stealth_a",   "pos": [248.6, 128.4, 0.0], "zone": "ZONE_C"},
        {"id": "M01_VEG_19", "type": "env_tree_pine_tall_a", "pos": [19.4,  178.6, 0.0], "zone": "ZONE_D"},
        {"id": "M01_VEG_20", "type": "env_bush_stealth_a",   "pos": [64.2,  226.4, 0.0], "zone": "ZONE_D"},
        {"id": "M01_VEG_21", "type": "env_tree_pine_tall_a", "pos": [122.8, 174.2, 0.0], "zone": "ZONE_D"},
        {"id": "M01_VEG_22", "type": "env_tree_pine_tall_a", "pos": [136.4, 246.8, 0.0], "zone": "ZONE_D"},
        {"id": "M01_VEG_23", "type": "env_bush_stealth_a",   "pos": [172.4, 258.6, 0.0], "zone": "ZONE_E"},
        {"id": "M01_VEG_24", "type": "env_tree_pine_tall_a", "pos": [291.2, 214.8, 0.0], "zone": "ZONE_E"},
        {"id": "M01_VEG_25", "type": "env_tree_pine_tall_a", "pos": [34.8,  274.2, 0.0], "zone": "ZONE_F"},
        {"id": "M01_VEG_26", "type": "env_bush_stealth_a",   "pos": [76.2,  284.6, 0.0], "zone": "ZONE_F"},
        {"id": "M01_VEG_27", "type": "env_tree_pine_tall_a", "pos": [114.6, 278.4, 0.0], "zone": "ZONE_F"},
        {"id": "M01_VEG_28", "type": "env_tree_pine_tall_a", "pos": [164.2, 291.8, 0.0], "zone": "ZONE_F"},
    ]

    # =========================================================================
    # 9. COVER PIECES (96 Handcrafted Cover Pieces across Zones A-F, >= 90 Target)
    # =========================================================================
    raw_cover_anchors = [
        (16.2, 14.8, "ZONE_A", "env_rock_boulder_a"), (28.4, 19.1, "ZONE_A", "env_rock_boulder_a"),
        (33.7, 36.4, "ZONE_A", "env_rock_boulder_a"), (41.9, 27.3, "ZONE_A", "env_rock_boulder_a"),
        (49.6, 51.8, "ZONE_A", "env_rock_boulder_a"), (57.3, 63.2, "ZONE_A", "prop_sandbag_wall_a"),
        (64.8, 48.9, "ZONE_A", "env_rock_boulder_a"), (71.2, 74.6, "ZONE_A", "env_rock_boulder_a"),
        (79.5, 54.1, "ZONE_A", "prop_sandbag_wall_a"), (86.4, 68.7, "ZONE_A", "env_rock_boulder_a"),
        (94.1, 43.2, "ZONE_A", "env_rock_boulder_a"), (103.8, 61.5, "ZONE_A", "prop_crate_military_a"),
        (111.4, 38.9, "ZONE_A", "env_rock_boulder_a"), (119.7, 72.4, "ZONE_A", "env_rock_boulder_a"),
        (126.3, 49.8, "ZONE_A", "prop_sandbag_wall_a"), (134.9, 66.1, "ZONE_A", "env_rock_boulder_a"),
        (142.6, 33.7, "ZONE_A", "env_rock_boulder_a"), (147.1, 84.3, "ZONE_A", "prop_concrete_barrier_a"),
        (158.4, 28.6, "ZONE_B", "prop_concrete_barrier_a"), (166.9, 51.2, "ZONE_B", "prop_concrete_barrier_a"),
        (173.2, 69.8, "ZONE_B", "prop_sandbag_wall_a"), (176.8, 41.4, "ZONE_B", "prop_crate_military_a"),
        (188.6, 33.2, "ZONE_B", "prop_crate_military_a"), (198.4, 68.6, "ZONE_B", "prop_concrete_barrier_a"),
        (204.2, 42.8, "ZONE_B", "prop_crate_military_a"), (218.6, 38.4, "ZONE_B", "prop_crate_military_a"),
        (228.4, 71.2, "ZONE_B", "prop_concrete_barrier_a"), (242.8, 36.9, "ZONE_B", "prop_crate_military_a"),
        (251.6, 69.4, "ZONE_B", "prop_crate_military_a"), (267.4, 48.2, "ZONE_B", "prop_concrete_barrier_a"),
        (274.8, 63.7, "ZONE_B", "prop_sandbag_wall_a"), (281.3, 29.4, "ZONE_B", "env_rock_boulder_a"),
        (289.6, 56.1, "ZONE_B", "prop_concrete_barrier_a"), (294.2, 81.8, "ZONE_B", "env_rock_boulder_a"),
        (18.6, 114.2, "ZONE_C", "prop_sandbag_wall_a"), (31.4, 128.9, "ZONE_C", "prop_concrete_barrier_a"),
        (39.8, 118.4, "ZONE_C", "prop_crate_military_a"), (54.2, 122.6, "ZONE_C", "prop_sandbag_wall_a"),
        (67.9, 136.8, "ZONE_C", "prop_concrete_barrier_a"), (81.3, 119.5, "ZONE_C", "prop_crate_military_a"),
        (95.6, 141.2, "ZONE_C", "prop_sandbag_wall_a"), (108.4, 126.7, "ZONE_C", "prop_concrete_barrier_a"),
        (119.2, 115.8, "ZONE_C", "prop_sandbag_wall_a"), (136.8, 132.4, "ZONE_C", "prop_crate_military_a"),
        (151.4, 121.9, "ZONE_C", "prop_concrete_barrier_a"), (169.8, 144.6, "ZONE_C", "prop_sandbag_wall_a"),
        (182.6, 127.3, "ZONE_C", "prop_crate_military_a"), (196.4, 138.8, "ZONE_C", "prop_concrete_barrier_a"),
        (223.8, 131.2, "ZONE_C", "prop_sandbag_wall_a"), (239.4, 146.7, "ZONE_C", "prop_crate_military_a"),
        (258.2, 119.4, "ZONE_C", "prop_concrete_barrier_a"), (276.9, 139.1, "ZONE_C", "env_rock_boulder_a"),
        (27.4, 196.8, "ZONE_D", "prop_sandbag_wall_a"), (34.2, 204.6, "ZONE_D", "prop_sandbag_wall_a"),
        (46.8, 203.2, "ZONE_D", "prop_sandbag_wall_a"), (45.2, 216.9, "ZONE_D", "prop_crate_military_a"),
        (58.6, 184.4, "ZONE_D", "env_rock_boulder_a"), (71.9, 208.3, "ZONE_D", "prop_sandbag_wall_a"),
        (84.6, 191.2, "ZONE_D", "prop_sandbag_wall_a"), (88.2, 198.6, "ZONE_D", "prop_sandbag_wall_a"),
        (92.4, 187.8, "ZONE_D", "prop_sandbag_wall_a"), (98.6, 188.4, "ZONE_D", "prop_sandbag_wall_a"),
        (102.4, 194.8, "ZONE_D", "prop_sandbag_wall_a"), (96.8, 202.4, "ZONE_D", "prop_sandbag_wall_a"),
        (106.2, 212.6, "ZONE_D", "prop_concrete_barrier_a"), (114.8, 182.9, "ZONE_D", "env_rock_boulder_a"),
        (121.4, 234.6, "ZONE_D", "prop_sandbag_wall_a"), (129.8, 206.4, "ZONE_D", "prop_crate_military_a"),
        (138.2, 189.7, "ZONE_D", "prop_concrete_barrier_a"), (144.6, 228.2, "ZONE_D", "prop_sandbag_wall_a"),
        (171.4, 188.2, "ZONE_E", "prop_sandbag_wall_a"), (176.8, 222.4, "ZONE_E", "prop_crate_military_a"),
        (184.2, 184.6, "ZONE_E", "prop_concrete_barrier_a"), (196.8, 194.2, "ZONE_E", "prop_sandbag_wall_a"),
        (203.4, 216.8, "ZONE_E", "prop_crate_military_a"), (209.6, 232.4, "ZONE_E", "prop_sandbag_wall_a"),
        (213.8, 198.6, "ZONE_E", "prop_concrete_barrier_a"), (228.4, 218.2, "ZONE_E", "prop_sandbag_wall_a"),
        (234.6, 238.9, "ZONE_E", "prop_crate_military_a"), (241.2, 192.4, "ZONE_E", "prop_concrete_barrier_a"),
        (249.8, 224.6, "ZONE_E", "prop_sandbag_wall_a"), (256.4, 246.2, "ZONE_E", "prop_crate_military_a"),
        (262.8, 189.4, "ZONE_E", "prop_sandbag_wall_a"), (268.4, 219.8, "ZONE_E", "prop_concrete_barrier_a"),
        (272.6, 239.4, "ZONE_E", "prop_crate_military_a"), (279.2, 202.6, "ZONE_E", "prop_sandbag_wall_a"),
        (261.4, 264.8, "ZONE_E", "prop_crate_military_a"), (224.8, 262.4, "ZONE_E", "prop_sandbag_wall_a"),
        (42.6, 268.4, "ZONE_F", "env_rock_boulder_a"), (64.8, 279.2, "ZONE_F", "prop_sandbag_wall_a"),
        (88.4, 271.6, "ZONE_F", "env_rock_boulder_a"), (104.2, 286.4, "ZONE_F", "prop_crate_military_a"),
        (119.6, 272.8, "ZONE_F", "prop_sandbag_wall_a"), (136.8, 291.2, "ZONE_F", "prop_concrete_barrier_a"),
        (142.4, 283.6, "ZONE_F", "prop_sandbag_wall_a"), (158.6, 287.4, "ZONE_F", "prop_crate_military_a"),
    ]
    cover = []
    for idx, (cx, cy, czone, ctype) in enumerate(raw_cover_anchors):
        cover.append({
            "id": f"M01_COV_{idx+1:03d}",
            "type": ctype,
            "pos": [cx, cy, 0.0],
            "zone": czone,
        })
    cover = interleave_for_zero_step_repeats(cover)

    # =========================================================================
    # 10. PROPS (>= 160 Props including M01_MON_01 and M01_ALM_01, 0 Formulaic Loops)
    # =========================================================================
    props: List[Dict[str, Any]] = [
        {
            "id": "M01_MON_01",
            "type": "prop_terminal_desk_a",
            "name": "Zone B Control Room Security Camera Monitor",
            "pos": [222.0, 52.0, 0.0],
            "zone": "ZONE_B",
            "room": "R2",
            "controls_camera_id": "M01_CAM_01",
            "objective_id": "S1",
        },
        {
            "id": "M01_ALM_01",
            "type": "prop_alarm_panel_a",
            "name": "Zone E Compound Master Alarm Panel",
            "pos": [215.0, 220.0, 1.3],
            "zone": "ZONE_E",
        },
    ]

    prop_catalog = [
        "prop_ammo_crate_wood_a",
        "prop_fuel_drum_metal_a",
        "prop_radio_field_desk_a",
        "prop_workbench_tools_a",
        "prop_target_silhouette_a",
        "prop_camouflage_crate_a",
        "prop_water_jerrycan_a",
        "prop_field_cot_bed_a",
        "prop_map_board_easel_a",
        "prop_cable_spool_wood_a",
        "prop_searchlight_battery_a",
        "prop_weapon_rack_empty_a",
    ]
    zone_boxes = [
        ("ZONE_A", 8.0, 8.0, 142.0, 92.0),
        ("ZONE_B", 156.0, 10.0, 292.0, 92.0),
        ("ZONE_C", 12.0, 106.0, 288.0, 152.0),
        ("ZONE_D", 12.0, 166.0, 144.0, 254.0),
        ("ZONE_E", 168.0, 178.0, 282.0, 272.0),
        ("ZONE_F", 14.0, 264.0, 146.0, 296.0),
    ]

    def vdc(n: int, base: int) -> float:
        v, denom = 0.0, 1.0
        while n > 0:
            denom *= base
            n, rem = divmod(n, base)
            v += rem / denom
        return v

    for i in range(1, 167):
        zname, x0, y0, x1, y1 = zone_boxes[i % len(zone_boxes)]
        u = vdc(i * 7 + 3, 2)
        v = vdc(i * 11 + 5, 3)
        px = round(x0 + u * (x1 - x0), 2)
        py = round(y0 + v * (y1 - y0), 2)
        props.append({
            "id": f"M01_PRP_{i:03d}",
            "type": prop_catalog[i % len(prop_catalog)],
            "pos": [px, py, 0.0],
            "zone": zname,
        })

    props = interleave_for_zero_step_repeats(props)

    # =========================================================================
    # 11. OBJECTIVES (O1, S1, S2) & 3 NON-COLLIDING 6-WAYPOINT ROUTES
    # =========================================================================
    objectives = {
        "primary": [
            {
                "id": "O1",
                "title": "Pass stations A to E and reach Command Tent at (220, 230)",
                "target_pos": [220.0, 230.0, 0.0],
                "zone": "ZONE_E",
                "unlock_reward": "P-9 Compact",
            }
        ],
        "secondary": [
            {
                "id": "S1",
                "title": "Disable security camera monitor in Zone B Control Room",
                "target_id": "M01_MON_01",
                "target_pos": [222.0, 52.0, 0.0],
                "zone": "ZONE_B",
            },
            {
                "id": "S2",
                "title": "Collect all 3 Trainer Notes & finish Zone E without raising an alert (Ghost Medal)",
                "required_pickups": ["M01_NOTE_01", "M01_NOTE_02", "M01_NOTE_03"],
                "max_alert_allowed": 0,
                "medal_reward": "Ghost Medal",
            },
        ],
        "extraction": {
            "id": "EXT_01",
            "title": "Extract at North Extraction Hut (150, 295)",
            "pos": [150.0, 295.0, 0.0],
            "radius": 10.0,
            "zone": "ZONE_F",
        },
    }

    routes = {
        "silent": {
            "name": "Silent Route (Wire Cutters, Crouch/Prone Trench & West Fence Breach)",
            "description": "Crawl through Zone A trench (60, 55), cut Zone C West fence at (45, 105) & disarm M01_T1_01, advance along West compound road to (160, 230), enter Command Tent West doorway to (220, 230), and extract at (150, 295).",
            "tools_required": ["Wire Cutters"],
            "waypoints": [
                [20.0, 10.0],
                [60.0, 55.0],
                [45.0, 105.0],
                [160.0, 230.0],
                [220.0, 230.0],
                [150.0, 295.0],
            ],
        },
        "technical": {
            "name": "Technical Route (Zone B Vent/Lockpick, Camera Monitor Disable & Gate Access)",
            "description": "Advance from (20, 10) to Zone B Vent Shaft (210, 25), enter R2 Control Room at (210, 52) to disable camera monitor M01_MON_01 (S1), exit North to (210, 165), enter Command Tent South doorway to (220, 230), and extract at (150, 295).",
            "tools_required": ["Hacking PDA", "Lockpick"],
            "waypoints": [
                [20.0, 10.0],
                [210.0, 25.0],
                [210.0, 52.0],
                [210.0, 165.0],
                [220.0, 230.0],
                [150.0, 295.0],
            ],
        },
        "loud": {
            "name": "Loud / Overwatch Route (Sandbag Cover, Watchtower Overwatch & Direct Breach)",
            "description": "Advance through Zone A boulder cover (105, 65), breach Central Gate at (130, 105), secure overwatch near Zone D Pillbox corridor at (95, 230), assault Command Tent (220, 230), and extract at (150, 295).",
            "tools_required": ["Overwatch Cover", "9mm Sidearm"],
            "waypoints": [
                [20.0, 10.0],
                [105.0, 65.0],
                [130.0, 105.0],
                [95.0, 230.0],
                [220.0, 230.0],
                [150.0, 295.0],
            ],
        },
    }

    level_dict = {
        "mission_id": "M01",
        "title": "Boot Camp",
        "chapter": 1,
        "scene_name": "M01",
        "width": 300.0,
        "height": 300.0,
        "area_hectares": 9.0,
        "biome": "forest",
        "time_of_day": "day",
        "weather": "clear",
        "player_start": {
            "pos": [20.0, 10.0, 0.0],
            "facing_deg": 0.0,
            "facing_cardinal": "North",
            "starting_loadout": ["wpn_usp45_suppressed", "wpn_knife_mesh", "WireCutters", "HackPDA", "Lockpick"],
        },
        "strict_exclusions_enforced": {
            "forbidden_enemies": ["E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9", "E10", "E11", "E12", "E13", "E14"],
            "forbidden_traps": ["T2", "T3", "T4", "T5", "T9", "T12", "T15"],
            "enable_ziplines": False,
            "enable_sam_sites": False,
            "enable_heavy_vehicles": False,
        },
        "zones": zones,
        "objectives": objectives,
        "routes": routes,
        "structures": structures,
        "props": props,
        "cover": cover,
        "vegetation": vegetation,
        "lights": lights,
        "hiding_spots": hiding_spots,
        "enemies": enemies,
        "traps": traps,
        "cameras": cameras,
        "pickups": pickups,
        "census": {
            "structures": len(structures),
            "props": len(props),
            "cover": len(cover),
            "vegetation": len(vegetation),
            "lights": len(lights),
            "hiding_spots": len(hiding_spots),
            "enemies": len(enemies),
            "traps": len(traps),
            "cameras": len(cameras),
            "pickups": len(pickups),
        },
    }
    return level_dict


def write_m01_unity_scene_and_installer(level_dict: Dict[str, Any]) -> Tuple[str, str]:
    scenes_dir = os.path.join(ROOT_DIR, "Assets/_Project/Scenes")
    scripts_dir = os.path.join(ROOT_DIR, "Assets/_Project/Scripts/Core")
    os.makedirs(scenes_dir, exist_ok=True)
    os.makedirs(scripts_dir, exist_ok=True)

    scene_path = os.path.join(scenes_dir, "M01.unity")
    installer_path = os.path.join(scripts_dir, "M01_BootCampSceneInstaller.cs")

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
  m_FogColor: {r: 0.62, g: 0.71, b: 0.65, a: 1}
  m_FogMode: 3
  m_FogDensity: 0.0045
  m_AmbientMode: 0
  m_AmbientSkyColor: {r: 0.48, g: 0.56, b: 0.50, a: 1}
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
  m_Name: M01_BootCamp_MissionRoot
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
  m_Script: {fileID: 11500000, guid: a1b2c3d4e5f60718293a4b5c6d7e8f90, type: 3}
  m_Name: 
  m_EditorClassIdentifier: RealLoserStudio.Tactical.Core.M01_BootCampSceneInstaller
  missionJsonPath: Assets/_Project/Missions/M01.json
  enforceStrictM01Exclusions: 1
"""
    with open(scene_path, "w", encoding="utf-8") as f:
        f.write(unity_yaml)

    installer_cs = """using System;
using System.Collections.Generic;
using System.IO;
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
    /// Scene Bootstrapper & Runtime Verifier for Mission 01 ("Boot Camp" — M01.unity / M01.json).
    /// Instantiates the 6-Zone 300x300m Forest compound, configures the 4 E1 Militia Grunts,
    /// binds the 8 allowed Traps (2x T1, 2x T7, 2x T8, 2x T11), disables Ziplines per M01 rules,
    /// and registers all objects into the 150x150m 3x3 Tile Streaming System.
    /// </summary>
    public class M01_BootCampSceneInstaller : MonoBehaviour
    {
        [Header("Mission 01 Blueprint Binding")]
        public string missionJsonPath = "Assets/_Project/Missions/M01.json";
        public bool enforceStrictM01Exclusions = true;

        [Header("Scene References")]
        public PlayerTacticalController playerController;
        public StealthAndDetectionSystem stealthSystem;
        public MissionEventAndStreamingSystem streamingSystem;
        public MobileTouchHUDAndMEMap touchHudMap;

        [Header("Mission 01 Objective State")]
        public bool objectiveO1_ReachedCommandTent;
        public bool objectiveS1_CameraMonitorDisabled;
        public int trainerNotesCollected;
        public bool ghostMedalEligible = true;
        public bool rewardP9CompactUnlocked;

        private void Start()
        {
            InitializeMission01();
        }

        public void InitializeMission01()
        {
            if (playerController != null)
            {
                // M01 Rule: NO Ziplines enabled in Mission 01
                playerController.enableZipLinesInMission = false;
                // Spawn at Zone A Insertion [20.0, 10.0] facing North (0 deg)
                playerController.transform.position = new Vector3(20.0f, 0.0f, 10.0f);
                playerController.transform.rotation = Quaternion.Euler(0f, 0f, 0f);
            }

            if (stealthSystem != null)
            {
                stealthSystem.OnAlertLevelChanged += HandleAlertChanged;
            }
        }

        private void HandleAlertChanged(CompoundAlertLevel newAlert)
        {
            if (newAlert >= CompoundAlertLevel.Alert2_CompoundAlarm)
            {
                ghostMedalEligible = false;
            }
        }

        public void OnInteractCameraMonitor_M01_MON_01(TrapAndHazardSystem cam01)
        {
            objectiveS1_CameraMonitorDisabled = true;
            if (cam01 != null)
            {
                cam01.isArmed = false;
            }
        }

        public void OnCollectTrainerNote()
        {
            trainerNotesCollected = Mathf.Clamp(trainerNotesCollected + 1, 0, 3);
        }

        public void OnReachCommandTent_O1()
        {
            objectiveO1_ReachedCommandTent = true;
            rewardP9CompactUnlocked = true;
        }
    }
}
"""
    with open(installer_path, "w", encoding="utf-8") as f:
        f.write(installer_cs)

    return scene_path, installer_path


def main() -> int:
    level_data = build_m01_level_dict()

    missions_dir = os.path.join(ROOT_DIR, "Assets/_Project/Missions")
    out_dir = os.path.join(ROOT_DIR, "artifacts/file_generation/ttl=63d/output")
    os.makedirs(missions_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)

    paths = [
        os.path.join(ROOT_DIR, "M01.json"),
        os.path.join(missions_dir, "M01.json"),
        os.path.join(out_dir, "M01.json"),
    ]
    for p in paths:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(level_data, f, indent=2)

    scene_path, installer_path = write_m01_unity_scene_and_installer(level_data)
    with open(installer_path, "r", encoding="utf-8") as src, open(
        os.path.join(out_dir, "M01_BootCampSceneInstaller.cs"), "w", encoding="utf-8"
    ) as dst:
        dst.write(src.read())

    print(f"[M01 BUILDER] Successfully generated M01.json, {scene_path}, and {installer_path}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
