#!/usr/bin/env python3
"""Render deterministic top-down tactical map textures from M01-M10 JSON."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "Assets" / "Resources" / "MissionMaps"
CANVAS = (1536, 1024)
MAP_BOX = (72, 64, 1464, 862)
COLORS = {
    "bg": (18, 28, 25),
    "grid": (41, 57, 50),
    "zone_perimeter": (56, 83, 91, 90),
    "zone_camp": (76, 104, 72, 95),
    "zone_interior": (113, 98, 70, 105),
    "zone_extraction": (67, 108, 120, 110),
    "zone_default": (60, 84, 69, 75),
    "structure": (135, 139, 127),
    "wall": (179, 177, 150),
    "prop": (132, 118, 91),
    "trap": (208, 138, 44),
    "camera": (242, 193, 63),
    "enemy": (220, 73, 67),
    "objective": (255, 216, 90),
    "secondary": (236, 152, 67),
    "extract": (76, 197, 224),
    "start": (99, 222, 131),
    "silent": (70, 210, 173),
    "technical": (86, 163, 243),
    "loud": (237, 90, 77),
    "text": (220, 228, 213),
    "muted": (156, 171, 157),
}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for path in paths:
        if Path(path).is_file():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def pos2(point) -> tuple[float, float] | None:
    if isinstance(point, dict):
        return float(point.get("x", 0)), float(point.get("z", point.get("y", 0)))
    if isinstance(point, (list, tuple)) and len(point) >= 2:
        return float(point[0]), float(point[1])
    return None


def rect4(value) -> tuple[float, float, float, float] | None:
    if isinstance(value, (list, tuple)) and len(value) >= 4:
        x0, z0, x1, z1 = map(float, value[:4])
        return min(x0, x1), min(z0, z1), max(x0, x1), max(z0, z1)
    return None


def make_map(data: dict, out_path: Path) -> None:
    width = max(float(data.get("width", 300)), 1.0)
    height = max(float(data.get("height", 300)), 1.0)
    title = str(data.get("title", data.get("mission_id", "MISSION")))
    image = Image.new("RGB", CANVAS, COLORS["bg"])
    draw = ImageDraw.Draw(image, "RGBA")

    left, top, right, bottom = MAP_BOX
    map_w, map_h = right - left, bottom - top
    scale = min(map_w / width, map_h / height)
    world_w, world_h = width * scale, height * scale
    ox = left + (map_w - world_w) / 2
    oy = bottom - (map_h - world_h) / 2

    def xy(point) -> tuple[float, float] | None:
        p = pos2(point)
        if p is None:
            return None
        x, z = p
        return ox + x * scale, oy - z * scale

    def box(rect) -> tuple[float, float, float, float] | None:
        r = rect4(rect)
        if r is None:
            return None
        x0, z0, x1, z1 = r
        a = xy((x0, z0)); b = xy((x1, z1))
        if a is None or b is None:
            return None
        return min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])

    # Coordinate grid, with world-distance labels.
    for step in (25, 50, 100, 200):
        if width / step <= 24 and height / step <= 24:
            break
    for x in range(0, int(width) + 1, step):
        p0, p1 = xy((x, 0)), xy((x, height))
        if p0 and p1:
            draw.line((p0, p1), fill=COLORS["grid"], width=1)
            if x % max(step * 2, 1) == 0:
                draw.text((p0[0] + 2, bottom + 4), str(x), font=font(13), fill=COLORS["muted"])
    for z in range(0, int(height) + 1, step):
        p0, p1 = xy((0, z)), xy((width, z))
        if p0 and p1:
            draw.line((p0, p1), fill=COLORS["grid"], width=1)
            if z % max(step * 2, 1) == 0:
                draw.text((left + 2, p0[1] - 17), str(z), font=font(13), fill=COLORS["muted"])

    # Mission zones and structure footprints.
    for zone in data.get("zones", []) or []:
        r = box(zone.get("rect", zone.get("bounds")))
        if not r:
            continue
        kind = str(zone.get("zone_type", "")).lower()
        color = COLORS.get(f"zone_{kind}", COLORS["zone_default"])
        draw.rectangle(r, fill=color, outline=(117, 145, 118, 170), width=2)
        label = str(zone.get("id", zone.get("name", "ZONE"))).replace("ZONE_", "ZONE ")
        draw.text((r[0] + 5, r[1] + 4), label[:18], font=font(13, True), fill=COLORS["text"])

    for structure in data.get("structures", []) or []:
        r = box(structure.get("bounds"))
        if r:
            draw.rectangle(r, fill=(111, 118, 105, 175), outline=COLORS["structure"], width=2)
        start, end = xy(structure.get("start")), xy(structure.get("end"))
        if start and end:
            draw.line((start, end), fill=COLORS["wall"], width=4)

    # Optional prop/camera/trap intel.
    key_terms = ("generator", "breaker", "server", "radio", "radar", "antenna", "uplink", "armory", "locker", "hostage", "intel", "terminal", "mainframe", "truck", "helipad", "objective")
    for prop in data.get("props", []) or []:
        p = xy(prop.get("pos"))
        name = (str(prop.get("type", "")) + " " + str(prop.get("id", ""))).lower()
        if p and any(term in name for term in key_terms):
            radius = 5
            draw.ellipse((p[0]-radius, p[1]-radius, p[0]+radius, p[1]+radius), fill=COLORS["prop"])
    for trap in data.get("traps", []) or []:
        p = xy(trap.get("pos"))
        if p:
            rad = 6
            draw.polygon([(p[0], p[1]-rad), (p[0]+rad, p[1]), (p[0], p[1]+rad), (p[0]-rad, p[1])], fill=COLORS["trap"])
    for camera in data.get("cameras", []) or []:
        p = xy(camera.get("pos"))
        if p:
            draw.polygon([(p[0], p[1]-7), (p[0]+6, p[1]+5), (p[0]-6, p[1]+5)], fill=COLORS["camera"])

    # Three authored tactical routes.
    route_data = data.get("routes", {}) or {}
    for route_id, color_key in (("silent", "silent"), ("technical", "technical"), ("loud", "loud")):
        route = route_data.get(route_id, {}) if isinstance(route_data, dict) else {}
        points = [xy(wp) for wp in (route.get("waypoints", []) or [])]
        points = [p for p in points if p is not None]
        if len(points) >= 2:
            draw.line(points, fill=COLORS[color_key], width=5, joint="curve")
            for p in points:
                draw.ellipse((p[0]-3, p[1]-3, p[0]+3, p[1]+3), fill=COLORS[color_key])

    # Initial enemy positions (live HUD overlay can track patrol movement at runtime).
    for enemy in data.get("enemies", []) or []:
        p = xy(enemy.get("pos"))
        if p:
            draw.ellipse((p[0]-4, p[1]-4, p[0]+4, p[1]+4), fill=COLORS["enemy"], outline=(25, 23, 22), width=1)

    objectives = data.get("objectives", {}) or {}
    for objective in objectives.get("primary", []) or []:
        target = next((objective.get(k) for k in ("target_pos", "boss_pos", "cell_pos", "checkpoint_pos", "truck_pos", "uplink_pos") if objective.get(k)), None)
        p = xy(target)
        if p:
            r = 10
            draw.polygon([(p[0],p[1]-r),(p[0]+r,p[1]),(p[0],p[1]+r),(p[0]-r,p[1])], fill=COLORS["objective"], outline=(20,20,18))
            draw.text((p[0]+9,p[1]-18), str(objective.get("id", "O1")), font=font(16, True), fill=COLORS["objective"])
    for objective in objectives.get("secondary", []) or []:
        p = xy(objective.get("target_pos"))
        if p:
            r = 7
            draw.rectangle((p[0]-r,p[1]-r,p[0]+r,p[1]+r), fill=COLORS["secondary"], outline=(20,20,18))
            draw.text((p[0]+8,p[1]-14), str(objective.get("id", "S")), font=font(14, True), fill=COLORS["secondary"])
    extraction = objectives.get("extraction", {}) or {}
    p = xy(extraction.get("pos"))
    if p:
        draw.ellipse((p[0]-10,p[1]-10,p[0]+10,p[1]+10), outline=COLORS["extract"], width=4)
        draw.text((p[0]+12,p[1]-16), "EX", font=font(15, True), fill=COLORS["extract"])

    start = data.get("player_start", {}) or {}
    p = xy(start.get("pos"))
    if p:
        draw.polygon([(p[0],p[1]-10),(p[0]+8,p[1]+7),(p[0]-8,p[1]+7)], fill=COLORS["start"], outline=(15,25,16))
        draw.text((p[0]+10,p[1]-18), "START", font=font(13, True), fill=COLORS["start"])

    # Header and legend: explicitly describe the artifact as a tactical schematic, not satellite photography.
    draw.text((72, 14), f"{data.get('mission_id', out_path.stem)}  |  {title}", font=font(25, True), fill=COLORS["text"])
    draw.text((1100, 22), f"TACTICAL SCHEMATIC  ·  {int(width)}m × {int(height)}m", font=font(15, True), fill=COLORS["muted"])
    legend_y = 895
    legend_rows = [
        [("SILENT ROUTE", "silent"), ("TECH ROUTE", "technical"), ("LOUD ROUTE", "loud"), ("HOSTILE", "enemy"), ("CAMERA", "camera")],
        [("TRAP", "trap"), ("KEY PROP", "prop"), ("PRIMARY", "objective"), ("EXTRACTION", "extract"), ("START", "start")],
    ]
    for row, items in enumerate(legend_rows):
        x = 74
        y = legend_y + row * 30
        for label, key in items:
            col = COLORS[key]
            draw.line((x, y + 10, x + 24, y + 10), fill=col, width=5)
            draw.text((x + 31, y), label, font=font(14, True), fill=COLORS["text"])
            x += 270
    draw.text((72, 972), "North = +Z   ·   Coordinates in meters   ·   Red markers show authored starting positions; patrols move in runtime.", font=font(14), fill=COLORS["muted"])

    out_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(out_path, format="PNG", optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate existing generated map PNGs without rewriting")
    args = parser.parse_args()
    expected = [ROOT / f"M{i:02d}.json" for i in range(1, 11)]
    if args.check:
        missing = []
        for source in expected:
            out = OUT_DIR / (source.stem + ".png")
            if not out.is_file():
                missing.append(str(out))
                continue
            with Image.open(out) as im:
                if im.size != CANVAS or im.getbbox() is None:
                    missing.append(f"invalid image: {out}")
        if missing:
            print("FAIL: " + "; ".join(missing))
            return 1
        print(f"PASS: {len(expected)} tactical map textures exist and are non-empty ({CANVAS[0]}×{CANVAS[1]}).")
        return 0
    for source in expected:
        data = json.loads(source.read_text(encoding="utf-8"))
        out = OUT_DIR / (source.stem + ".png")
        make_map(data, out)
        print(f"Rendered {source.name} -> {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
