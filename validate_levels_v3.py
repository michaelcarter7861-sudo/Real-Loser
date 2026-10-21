#!/usr/bin/env python3
"""
Project Real Loser — Anti-Cheat Level Validator v3 (validate_levels_v3.py)
Target Engine: Unity 2022.3.40f1 LTS (URP, Android ARM64 IL2CPP)

Strictly enforces Phase 0 Anti-Cheat Rules on Mission Level JSON files:
1. Linear/Modulo Coordinate Detection:
   Computes first-order differences (dx, dy) (and modulo-wrapped steps) between
   consecutive objects in `structures`, `props`, `traps`, and `enemies`.
   If more than 3 pairs share the exact same (dx, dy) step vector (or modulo wrap),
   IMMEDIATELY FAILS with Exit Code 1 ("Formulaic Loop Detected").
2. Disconnected Wall/Fence Check:
   Every wall/fence segment (`env_fence_chainlink_4m`, `env_wall_concrete_4m`,
   `env_wall_brick_4m`, `env_wall_adobe_4m`) MUST snap end-to-end (within 0.15m
   tolerance) to another wall segment, corner post, gate (`env_gate_sliding_6m`),
   or building wall to form a closed perimeter. Any floating/isolated or dead-end
   fence piece FAILS validation.
3. Contextual Trap & Camera Mounting:
   - `T11` (Security Camera) and `T10` (Searchlight) MUST be within 1.5m of a
     structure wall or `env_watchtower_metal_a`.
   - `T13` (Alarmed Door) and `T14` (Booby-trapped Door) MUST snap to a building
     doorway coordinate (within 0.5m).
   - `T5` (Laser Grid) and `T7` (Pressure Plate) MUST lie inside an `interior`
     zone or building room bounds.
   - `T12` (Electric Fence) MUST be linked to a valid `prop_breaker_box_a` or
     `prop_generator_diesel_a` ID.
4. Guard Patrol & Sightline Coherence:
   - Every enemy (`E1`–`E14`) must have a multi-waypoint patrol path (`>= 3`
     waypoints) that does not intersect solid building walls.
   - Snipers (`E6`) must be positioned on high points (`env_watchtower_metal_a`,
     building roofs, or cliff ridges).
"""

import sys
import os
import json
import math
from collections import Counter
from typing import List, Tuple, Dict, Any

WALL_SEGMENT_TYPES = {
    "env_fence_chainlink_4m": 4.0,
    "env_wall_concrete_4m": 4.0,
    "env_wall_brick_4m": 4.0,
    "env_wall_adobe_4m": 4.0,
}

GATE_TYPES = {
    "env_gate_sliding_6m": 6.0,
}

CORNER_POST_TYPES = {
    "env_corner_post_a",
    "prop_corner_post_a",
    "corner_post",
}

POWER_SOURCE_TYPES = {
    "prop_breaker_box_a",
    "prop_generator_diesel_a",
}

ENEMY_CLASSES = {f"E{i}" for i in range(1, 15)}

SNAP_TOLERANCE = 0.15
CAMERA_MOUNT_TOLERANCE = 1.5
DOOR_SNAP_TOLERANCE = 0.5


def extract_xy(obj: Dict[str, Any]) -> Tuple[float, float]:
    if "pos" in obj:
        p = obj["pos"]
        if isinstance(p, (list, tuple)):
            if len(p) == 2:
                return float(p[0]), float(p[1])
            elif len(p) >= 3:
                if obj.get("coord_space") == "unity_xyz":
                    return float(p[0]), float(p[2])
                return float(p[0]), float(p[1])
        elif isinstance(p, dict):
            return float(p.get("x", 0.0)), float(p.get("y", p.get("z", 0.0)))
    if "position" in obj:
        p = obj["position"]
        if isinstance(p, (list, tuple)):
            return float(p[0]), float(p[1])
        elif isinstance(p, dict):
            return float(p.get("x", 0.0)), float(p.get("y", p.get("z", 0.0)))
    return float(obj.get("x", 0.0)), float(obj.get("y", obj.get("z", 0.0)))


def extract_elevation(obj: Dict[str, Any]) -> float:
    if "elevation" in obj:
        return float(obj["elevation"])
    if "height" in obj:
        return float(obj["height"])
    if "z" in obj and "y" in obj:
        return float(obj["z"])
    if "pos" in obj and isinstance(obj["pos"], (list, tuple)) and len(obj["pos"]) >= 3:
        return float(obj["pos"][2])
    if "position" in obj and isinstance(obj["position"], dict):
        return float(obj["position"].get("z", 0.0))
    return 0.0


def dist2d(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def point_to_segment_dist(
    p: Tuple[float, float], a: Tuple[float, float], b: Tuple[float, float]
) -> float:
    px, py = p
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    len_sq = dx * dx + dy * dy
    if len_sq < 1e-12:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / len_sq))
    proj_x = ax + t * dx
    proj_y = ay + t * dy
    return math.hypot(px - proj_x, py - proj_y)


def segments_strictly_intersect(
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    q1: Tuple[float, float],
    q2: Tuple[float, float],
) -> bool:
    def ccw(A: Tuple[float, float], B: Tuple[float, float], C: Tuple[float, float]) -> float:
        return (C[1] - A[1]) * (B[0] - A[0]) - (B[1] - A[1]) * (C[0] - A[0])

    d1 = ccw(q1, q2, p1)
    d2 = ccw(q1, q2, p2)
    d3 = ccw(p1, p2, q1)
    d4 = ccw(p1, p2, q2)

    if ((d1 > 1e-7 and d2 < -1e-7) or (d1 < -1e-7 and d2 > 1e-7)) and (
        (d3 > 1e-7 and d4 < -1e-7) or (d3 < -1e-7 and d4 > 1e-7)
    ):
        return True
    return False


def get_wall_segment_endpoints(obj: Dict[str, Any], default_len: float) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    if "start" in obj and "end" in obj:
        s = obj["start"]
        e = obj["end"]
        return (float(s[0]), float(s[1])), (float(e[0]), float(e[1]))
    cx, cy = extract_xy(obj)
    length = float(obj.get("length", default_len))
    yaw_deg = float(obj.get("rot_y", obj.get("rotation", obj.get("yaw", 0.0))))
    yaw_rad = math.radians(yaw_deg)
    half = 0.5 * length
    dx = math.cos(yaw_rad) * half
    dy = math.sin(yaw_rad) * half
    return (cx - dx, cy - dy), (cx + dx, cy + dy)


def get_building_walls_and_doors(
    structures: List[Dict[str, Any]]
) -> Tuple[
    List[Tuple[Tuple[float, float], Tuple[float, float]]],
    List[Tuple[Tuple[float, float], Tuple[float, float]]],
    List[Tuple[float, float]],
    List[Tuple[float, float, float, float]],
]:
    all_building_walls = []
    solid_wall_segments = []
    doorways = []
    building_bounds = []

    for s in structures:
        stype = s.get("type", s.get("asset_id", ""))
        if stype in WALL_SEGMENT_TYPES or stype in GATE_TYPES or stype in CORNER_POST_TYPES:
            continue
        if stype == "env_watchtower_metal_a":
            continue

        cx, cy = extract_xy(s)
        w = float(s.get("width", s.get("size_x", 0.0)))
        d = float(s.get("depth", s.get("height_2d", s.get("size_y", 0.0))))
        if "bounds" in s and isinstance(s["bounds"], (list, tuple)) and len(s["bounds"]) == 4:
            min_x, min_y, max_x, max_y = [float(v) for v in s["bounds"]]
        elif w > 0.0 and d > 0.0:
            min_x, min_y, max_x, max_y = cx - w / 2.0, cy - d / 2.0, cx + w / 2.0, cy + d / 2.0
        else:
            continue

        building_bounds.append((min_x, min_y, max_x, max_y))

        b_doors = []
        for door in s.get("doorways", s.get("doors", [])):
            if isinstance(door, (list, tuple)) and len(door) >= 2:
                dp = (float(door[0]), float(door[1]))
            elif isinstance(door, dict):
                dp = extract_xy(door)
            else:
                continue
            doorways.append(dp)
            b_doors.append(dp)

        corners = [
            (min_x, min_y),
            (max_x, min_y),
            (max_x, max_y),
            (min_x, max_y),
        ]
        edges = [
            (corners[0], corners[1]),
            (corners[1], corners[2]),
            (corners[2], corners[3]),
            (corners[3], corners[0]),
        ]
        for e_start, e_end in edges:
            all_building_walls.append((e_start, e_end))
            edge_len = dist2d(e_start, e_end)
            if edge_len < 1e-6:
                continue
            ux = (e_end[0] - e_start[0]) / edge_len
            uy = (e_end[1] - e_start[1]) / edge_len
            door_intervals = []
            for dp in b_doors:
                if point_to_segment_dist(dp, e_start, e_end) <= DOOR_SNAP_TOLERANCE:
                    t_center = (dp[0] - e_start[0]) * ux + (dp[1] - e_start[1]) * uy
                    door_intervals.append((max(0.0, t_center - 1.0), min(edge_len, t_center + 1.0)))
            if not door_intervals:
                solid_wall_segments.append((e_start, e_end))
            else:
                door_intervals.sort()
                curr_t = 0.0
                for d_start, d_end in door_intervals:
                    if d_start > curr_t + 0.1:
                        p_a = (e_start[0] + ux * curr_t, e_start[1] + uy * curr_t)
                        p_b = (e_start[0] + ux * d_start, e_start[1] + uy * d_start)
                        solid_wall_segments.append((p_a, p_b))
                    curr_t = max(curr_t, d_end)
                if curr_t < edge_len - 0.1:
                    p_a = (e_start[0] + ux * curr_t, e_start[1] + uy * curr_t)
                    solid_wall_segments.append((p_a, e_end))

    return all_building_walls, solid_wall_segments, doorways, building_bounds


def check_rule1_linear_modulo(level_data: Dict[str, Any]) -> List[str]:
    errors = []
    width = float(level_data.get("width", level_data.get("map_width", 1000.0)))
    height = float(level_data.get("height", level_data.get("map_height", 1000.0)))

    for category in ("structures", "props", "traps", "enemies"):
        items = level_data.get(category, [])
        if not isinstance(items, list) or len(items) < 5:
            continue

        raw_deltas = Counter()
        mod_deltas = Counter()

        coords = [extract_xy(item) for item in items]
        for i in range(len(coords) - 1):
            x1, y1 = coords[i]
            x2, y2 = coords[i + 1]
            dx = round(x2 - x1, 2)
            dy = round(y2 - y1, 2)
            raw_deltas[(dx, dy)] += 1

            if width > 0 and height > 0:
                mdx = round((x2 - x1) % width, 2)
                mdy = round((y2 - y1) % height, 2)
                mod_deltas[(mdx, mdy)] += 1

        for vec, count in raw_deltas.items():
            if count > 3:
                errors.append(
                    f"[RULE 1 FAIL] Formulaic Loop Detected in '{category}': "
                    f"{count} consecutive pairs share identical step vector dx={vec[0]}, dy={vec[1]} (max allowed: 3)."
                )
        for vec, count in mod_deltas.items():
            if count > 3:
                if raw_deltas.get(vec, 0) <= 3:
                    errors.append(
                        f"[RULE 1 FAIL] Formulaic Loop Detected (Modulo Wrap) in '{category}': "
                        f"{count} consecutive pairs share modulo step vector dx={vec[0]} (mod {width}), dy={vec[1]} (mod {height})."
                    )
    return errors


def check_rule2_perimeter_walls(
    structures: List[Dict[str, Any]],
    props: List[Dict[str, Any]],
    all_building_walls: List[Tuple[Tuple[float, float], Tuple[float, float]]],
) -> List[str]:
    errors = []
    wall_segments = []
    gate_segments = []
    corner_posts = []

    for idx, s in enumerate(structures):
        stype = s.get("type", s.get("asset_id", ""))
        sid = s.get("id", f"struct_{idx}")
        if stype in WALL_SEGMENT_TYPES:
            p1, p2 = get_wall_segment_endpoints(s, WALL_SEGMENT_TYPES[stype])
            wall_segments.append({"id": sid, "type": stype, "p1": p1, "p2": p2})
        elif stype in GATE_TYPES:
            p1, p2 = get_wall_segment_endpoints(s, GATE_TYPES[stype])
            gate_segments.append({"id": sid, "type": stype, "p1": p1, "p2": p2})
        elif stype in CORNER_POST_TYPES:
            corner_posts.append(extract_xy(s))

    for p in props:
        ptype = p.get("type", p.get("asset_id", ""))
        if ptype in CORNER_POST_TYPES:
            corner_posts.append(extract_xy(p))

    if not wall_segments:
        errors.append("[RULE 2 FAIL] No perimeter wall/fence segments found in `structures`.")
        return errors

    all_seg_endpoints = []
    for i, w in enumerate(wall_segments):
        all_seg_endpoints.append(("wall", i, 1, w["p1"]))
        all_seg_endpoints.append(("wall", i, 2, w["p2"]))
    for j, g in enumerate(gate_segments):
        all_seg_endpoints.append(("gate", j, 1, g["p1"]))
        all_seg_endpoints.append(("gate", j, 2, g["p2"]))

    for i, w in enumerate(wall_segments):
        for ep_idx, ep in ((1, w["p1"]), (2, w["p2"])):
            snapped = False
            for kind, other_idx, _, other_pt in all_seg_endpoints:
                if kind == "wall" and other_idx == i:
                    continue
                if dist2d(ep, other_pt) <= SNAP_TOLERANCE:
                    snapped = True
                    break

            if not snapped:
                for cp in corner_posts:
                    if dist2d(ep, cp) <= SNAP_TOLERANCE:
                        other_connected = False
                        for kind, other_idx, _, other_pt in all_seg_endpoints:
                            if kind == "wall" and other_idx == i:
                                continue
                            if dist2d(cp, other_pt) <= SNAP_TOLERANCE:
                                other_connected = True
                                break
                        if not other_connected:
                            for bw1, bw2 in all_building_walls:
                                if point_to_segment_dist(cp, bw1, bw2) <= SNAP_TOLERANCE:
                                    other_connected = True
                                    break
                        if other_connected:
                            snapped = True
                            break

            if not snapped:
                for bw1, bw2 in all_building_walls:
                    if point_to_segment_dist(ep, bw1, bw2) <= SNAP_TOLERANCE:
                        snapped = True
                        break

            if not snapped:
                errors.append(
                    f"[RULE 2 FAIL] Disconnected Wall/Fence segment '{w['id']}' ({w['type']}): "
                    f"endpoint {ep_idx} at ({ep[0]:.2f}, {ep[1]:.2f}) does not snap within {SNAP_TOLERANCE}m "
                    f"to any wall, corner post, gate, or building wall."
                )

    return errors


def point_in_bounds(pt: Tuple[float, float], bounds: Tuple[float, float, float, float], tol: float = 0.05) -> bool:
    return (bounds[0] - tol <= pt[0] <= bounds[2] + tol) and (bounds[1] - tol <= pt[1] <= bounds[3] + tol)


def check_rule3_contextual_traps(
    traps: List[Dict[str, Any]],
    structures: List[Dict[str, Any]],
    props: List[Dict[str, Any]],
    zones: List[Dict[str, Any]],
    all_building_walls: List[Tuple[Tuple[float, float], Tuple[float, float]]],
    doorways: List[Tuple[float, float]],
    building_bounds: List[Tuple[float, float, float, float]],
) -> List[str]:
    errors = []

    mount_segments = list(all_building_walls)
    watchtowers = []
    valid_power_ids = set()

    for s in structures:
        stype = s.get("type", s.get("asset_id", ""))
        sid = s.get("id", "")
        if stype in WALL_SEGMENT_TYPES:
            mount_segments.append(get_wall_segment_endpoints(s, WALL_SEGMENT_TYPES[stype]))
        elif stype == "env_watchtower_metal_a":
            watchtowers.append((extract_xy(s), float(s.get("radius", 3.0))))
        if stype in POWER_SOURCE_TYPES and sid:
            valid_power_ids.add(sid)

    for p in props:
        ptype = p.get("type", p.get("asset_id", ""))
        pid = p.get("id", "")
        if ptype in POWER_SOURCE_TYPES and pid:
            valid_power_ids.add(pid)

    interior_bounds = list(building_bounds)
    for z in zones:
        ztype = z.get("zone_type", z.get("type", "")).lower()
        if ztype == "interior":
            if "bounds" in z and len(z["bounds"]) == 4:
                interior_bounds.append(tuple(float(v) for v in z["bounds"]))

    for idx, t in enumerate(traps):
        ttype = t.get("type", t.get("trap_id", ""))
        tid = t.get("id", f"trap_{idx}")
        pt = extract_xy(t)

        if ttype in ("T10", "T11"):
            min_d = float("inf")
            for seg_a, seg_b in mount_segments:
                d = point_to_segment_dist(pt, seg_a, seg_b)
                if d < min_d:
                    min_d = d
            for wt_pos, wt_rad in watchtowers:
                d = max(0.0, dist2d(pt, wt_pos) - wt_rad)
                if d < min_d:
                    min_d = d
            if min_d > CAMERA_MOUNT_TOLERANCE:
                errors.append(
                    f"[RULE 3 FAIL] Trap '{tid}' ({ttype}) at ({pt[0]:.2f}, {pt[1]:.2f}) is floating "
                    f"(min distance {min_d:.2f}m > {CAMERA_MOUNT_TOLERANCE}m from any structure wall or env_watchtower_metal_a)."
                )

        elif ttype in ("T13", "T14"):
            if not doorways:
                errors.append(
                    f"[RULE 3 FAIL] Door Trap '{tid}' ({ttype}) at ({pt[0]:.2f}, {pt[1]:.2f}) placed with no building doorways defined."
                )
            else:
                min_d = min(dist2d(pt, dp) for dp in doorways)
                if min_d > DOOR_SNAP_TOLERANCE:
                    errors.append(
                        f"[RULE 3 FAIL] Door Trap '{tid}' ({ttype}) at ({pt[0]:.2f}, {pt[1]:.2f}) does not snap "
                        f"to a building doorway (min distance {min_d:.2f}m > {DOOR_SNAP_TOLERANCE}m)."
                    )

        elif ttype in ("T5", "T7"):
            inside = any(point_in_bounds(pt, b) for b in interior_bounds)
            if not inside:
                errors.append(
                    f"[RULE 3 FAIL] Interior Trap '{tid}' ({ttype}) at ({pt[0]:.2f}, {pt[1]:.2f}) lies outside "
                    f"all `interior` zones and building room bounds."
                )

        elif ttype == "T12":
            linked_id = t.get("power_source_id", t.get("linked_id", ""))
            if not linked_id or linked_id not in valid_power_ids:
                errors.append(
                    f"[RULE 3 FAIL] Electric Fence '{tid}' (T12) has invalid or missing power source link "
                    f"'{linked_id}' (must reference a valid prop_breaker_box_a or prop_generator_diesel_a ID)."
                )

    return errors


def check_rule4_enemies_and_snipers(
    enemies: List[Dict[str, Any]],
    structures: List[Dict[str, Any]],
    zones: List[Dict[str, Any]],
    solid_wall_segments: List[Tuple[Tuple[float, float], Tuple[float, float]]],
    building_bounds: List[Tuple[float, float, float, float]],
) -> List[str]:
    errors = []

    watchtowers = []
    for s in structures:
        stype = s.get("type", s.get("asset_id", ""))
        if stype == "env_watchtower_metal_a":
            watchtowers.append((extract_xy(s), float(s.get("radius", 3.5))))

    cliff_zones = []
    for z in zones:
        ztype = z.get("zone_type", z.get("type", "")).lower()
        if ztype in ("cliff_ridge", "ridge", "high_ground"):
            if "bounds" in z and len(z["bounds"]) == 4:
                cliff_zones.append(tuple(float(v) for v in z["bounds"]))

    for idx, e in enumerate(enemies):
        eclass = e.get("class", e.get("type", e.get("enemy_class", "")))
        eid = e.get("id", f"enemy_{idx}")
        if eclass not in ENEMY_CLASSES:
            continue

        waypoints_raw = e.get("patrol_waypoints", e.get("waypoints", []))
        if not isinstance(waypoints_raw, list) or len(waypoints_raw) < 3:
            errors.append(
                f"[RULE 4 FAIL] Enemy '{eid}' ({eclass}) has {len(waypoints_raw) if isinstance(waypoints_raw, list) else 0} "
                f"waypoints; requires >= 3 waypoints."
            )
            waypoints = []
            for wp in waypoints_raw if isinstance(waypoints_raw, list) else []:
                if isinstance(wp, (list, tuple)) and len(wp) >= 2:
                    waypoints.append((float(wp[0]), float(wp[1])))
                elif isinstance(wp, dict):
                    waypoints.append(extract_xy(wp))
        else:
            waypoints = []
            for wp in waypoints_raw:
                if isinstance(wp, (list, tuple)) and len(wp) >= 2:
                    waypoints.append((float(wp[0]), float(wp[1])))
                elif isinstance(wp, dict):
                    waypoints.append(extract_xy(wp))

            distinct_wps = {(round(p[0], 2), round(p[1], 2)) for p in waypoints}
            if len(distinct_wps) < 3:
                errors.append(
                    f"[RULE 4 FAIL] Enemy '{eid}' ({eclass}) has fewer than 3 distinct waypoint coordinates."
                )

        elev = extract_elevation(e)
        mount_type = str(e.get("mount", e.get("surface", ""))).lower()
        is_rooftop = (mount_type == "roof") and (elev >= 3.0)

        if not is_rooftop and len(waypoints) >= 2:
            for i in range(len(waypoints) - 1):
                p1, p2 = waypoints[i], waypoints[i + 1]
                for w1, w2 in solid_wall_segments:
                    if segments_strictly_intersect(p1, p2, w1, w2):
                        errors.append(
                            f"[RULE 4 FAIL] Enemy '{eid}' ({eclass}) patrol segment {i}->{i+1} "
                            f"({p1} -> {p2}) intersects solid building wall ({w1} -> {w2})."
                        )
                        break

        if eclass == "E6":
            epos = extract_xy(e)
            on_watchtower = any(dist2d(epos, wt_pos) <= wt_rad for wt_pos, wt_rad in watchtowers) and elev >= 5.0
            on_roof = any(point_in_bounds(epos, b) for b in building_bounds) and (elev >= 3.0 or mount_type == "roof")
            on_cliff = (any(point_in_bounds(epos, cz) for cz in cliff_zones) or mount_type == "cliff_ridge") and elev >= 6.0

            if not (on_watchtower or on_roof or on_cliff):
                errors.append(
                    f"[RULE 4 FAIL] Sniper '{eid}' (E6) at ({epos[0]:.2f}, {epos[1]:.2f}, elev={elev:.1f}m) "
                    f"is not positioned on a valid high point (env_watchtower_metal_a >=5m, building roof >=3m, or cliff ridge >=6m)."
                )

    return errors


def check_mission_data_integrity(level_data: Dict[str, Any]) -> List[str]:
    """Validate cross-array identity and reference integrity without changing spawn rules."""
    errors: List[str] = []
    zones = level_data.get("zones", [])
    zone_ids = {z.get("id") for z in zones if isinstance(z, dict) and z.get("id")}
    global_ids: Dict[str, str] = {}
    global_items: Dict[str, Dict[str, Any]] = {}

    # Alarm panels are authored in props (the Unity runtime's spawn source).
    # The alarms array is an ID-only census/reference list, not another object set.
    for category, items in level_data.items():
        if category in {"objectives", "census", "player_start", "strict_exclusions_enforced", "routes"}:
            continue
        if not isinstance(items, list):
            continue
        for index, item in enumerate(items):
            if not isinstance(item, dict) or not item.get("id"):
                continue
            item_id = item["id"]
            location = f"{category}[{index}]"
            semantic_camera_alias = (
                item_id in global_items
                and {category, global_ids[item_id].split("[", 1)[0]} == {"traps", "cameras"}
                and item.get("type") == "T11"
                and global_items[item_id].get("type") == "T11"
            )
            if item_id in global_ids and not semantic_camera_alias:
                errors.append(
                    f"[DATA FAIL] Duplicate global id '{item_id}' in {location}; "
                    f"already defined at {global_ids[item_id]}."
                )
            else:
                global_ids[item_id] = location
                global_items[item_id] = item

    for index, zone in enumerate(zones):
        if not isinstance(zone, dict) or not zone.get("id"):
            errors.append(f"[DATA FAIL] Zone at zones[{index}] is missing a non-empty id.")

    def walk_zone_refs(value: Any, path: str = "") -> None:
        if isinstance(value, dict):
            if "zone" in value and value["zone"] not in zone_ids:
                errors.append(f"[DATA FAIL] Invalid zone reference '{value['zone']}' at {path}.")
            for key, child in value.items():
                walk_zone_refs(child, f"{path}.{key}" if path else key)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk_zone_refs(child, f"{path}[{index}]")

    walk_zone_refs(level_data)

    objectives = level_data.get("objectives", {})
    objective_ids = set()
    if isinstance(objectives, dict):
        for group, entries in objectives.items():
            if group == "extraction":
                entries = [entries]
            if not isinstance(entries, list):
                continue
            for index, objective in enumerate(entries):
                if not isinstance(objective, dict):
                    errors.append(f"[DATA FAIL] Objective at objectives.{group}[{index}] is not an object.")
                    continue
                objective_id = objective.get("id")
                if not objective_id:
                    errors.append(f"[DATA FAIL] Objective at objectives.{group}[{index}] is missing an id.")
                elif objective_id in objective_ids:
                    errors.append(f"[DATA FAIL] Duplicate objective id '{objective_id}'.")
                else:
                    objective_ids.add(objective_id)
                if "zone" in objective and objective["zone"] not in zone_ids:
                    errors.append(
                        f"[DATA FAIL] Objective '{objective_id or index}' references invalid zone "
                        f"'{objective['zone']}'."
                    )

    object_relationships = {
        "mounted_on", "monitor_id", "linked_monitor_id", "secondary_camera_id",
        "power_source_id", "controls_camera_id", "controls_camera_ids", "target_id",
        "required_pickups",
    }
    objective_relationships = {"objective_id", "disabled_by_objective"}

    def check_relationship(key: str, value: Any, path: str) -> None:
        values = value if isinstance(value, list) else [value]
        for target in values:
            if not isinstance(target, str):
                continue
            valid = target in objective_ids if key in objective_relationships else target in global_ids or target in objective_ids
            if not valid:
                errors.append(f"[DATA FAIL] Relationship {key} at {path} targets unknown id '{target}'.")

    def walk_relationships(value: Any, path: str = "") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{path}.{key}" if path else key
                if key in object_relationships or key in objective_relationships:
                    check_relationship(key, child, child_path)
                walk_relationships(child, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk_relationships(child, f"{path}[{index}]")

    walk_relationships(level_data)

    census = level_data.get("census", {})
    if isinstance(census, dict):
        for category, expected in census.items():
            if not isinstance(expected, int):
                errors.append(f"[DATA FAIL] Census count for '{category}' is not an integer.")
                continue
            actual_items = level_data.get(category)
            if isinstance(actual_items, list):
                actual = len(actual_items)
            elif category == "alarms":
                # M01 predates the metadata array; its alarm panels remain real props.
                actual = sum(
                    1 for item in level_data.get("props", [])
                    if isinstance(item, dict) and item.get("type") == "prop_alarm_panel_a"
                )
            else:
                errors.append(f"[DATA FAIL] Census category '{category}' has no corresponding array.")
                continue
            if actual != expected:
                errors.append(
                    f"[DATA FAIL] Census mismatch for '{category}': recorded {expected}, actual {actual}."
                )

    return errors


def validate_level_dict(level_data: Dict[str, Any], source_name: str = "<memory>") -> Tuple[bool, List[str]]:
    errors: List[str] = []

    structures = level_data.get("structures", [])
    props = level_data.get("props", [])
    traps = level_data.get("traps", [])
    enemies = level_data.get("enemies", [])
    zones = level_data.get("zones", [])

    errors.extend(check_mission_data_integrity(level_data))
    errors.extend(check_rule1_linear_modulo(level_data))
    all_building_walls, solid_wall_segments, doorways, building_bounds = get_building_walls_and_doors(structures)
    errors.extend(check_rule2_perimeter_walls(structures, props, all_building_walls))
    errors.extend(
        check_rule3_contextual_traps(
            traps, structures, props, zones, all_building_walls, doorways, building_bounds
        )
    )
    errors.extend(
        check_rule4_enemies_and_snipers(
            enemies, structures, zones, solid_wall_segments, building_bounds
        )
    )

    return (len(errors) == 0), errors


def validate_level_file(filepath: str) -> Tuple[bool, List[str]]:
    if not os.path.exists(filepath):
        return False, [f"[IO ERROR] File not found: {filepath}"]
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        return False, [f"[JSON ERROR] Failed to parse {filepath}: {exc}"]
    return validate_level_dict(data, source_name=filepath)


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python3 validate_levels_v3.py <level1.json> [level2.json ...]")
        return 1

    overall_ok = True
    for path in sys.argv[1:]:
        ok, errs = validate_level_file(path)
        if ok:
            print(f"[PASS] {path} passed all Anti-Cheat v3 checks.")
        else:
            overall_ok = False
            print(f"[FAIL] {path} failed Anti-Cheat v3 validation ({len(errs)} violation(s)):")
            for e in errs:
                print(f"  - {e}")

    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main())
