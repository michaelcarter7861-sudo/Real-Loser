#!/usr/bin/env python3
"""Deterministic regression checks for EnemyAIFSMSystem local navigation.

These checks do not require Unity.  The geometry model mirrors the bounded candidate
selection used by the C# implementation closely enough to catch corner regressions,
while source assertions catch accidental removal of the obstacle-aware path.
"""

from __future__ import annotations

import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Assets/_Project/Scripts/AI/EnemyAIFSMSystem.cs"
CANDIDATE_ANGLES = (25.0, -25.0, 50.0, -50.0, 75.0, -75.0, 110.0, -110.0, 180.0)
AGENT_RADIUS = 0.42
PROBE_DISTANCE = 2.4
# A finite wall in the X/Y movement plane.  The test expands it by the agent radius.
WALL = (4.0, 6.0, -1.5, 1.5)  # min_x, max_x, min_y, max_y


def _expanded_wall():
    return (WALL[0] - AGENT_RADIUS, WALL[1] + AGENT_RADIUS,
            WALL[2] - AGENT_RADIUS, WALL[3] + AGENT_RADIUS)


def segment_hits_wall(origin, direction, distance):
    """Exact 2D slab intersection for a segment and the expanded test wall."""
    min_x, max_x, min_y, max_y = _expanded_wall()
    ox, oy = origin
    dx, dy = direction
    t_min, t_max = 0.0, distance
    for start, delta, low, high in ((ox, dx, min_x, max_x), (oy, dy, min_y, max_y)):
        if abs(delta) < 1e-9:
            if start < low or start > high:
                return False
            continue
        a, b = (low - start) / delta, (high - start) / delta
        if a > b:
            a, b = b, a
        t_min, t_max = max(t_min, a), min(t_max, b)
        if t_min > t_max:
            return False
    return t_max >= 0.0 and t_min <= distance


def unit_to_target(origin, target):
    dx, dy = target[0] - origin[0], target[1] - origin[1]
    length = math.hypot(dx, dy)
    return (dx / length, dy / length), length


def rotate(direction, degrees):
    radians = math.radians(degrees)
    c, s = math.cos(radians), math.sin(radians)
    return (c * direction[0] - s * direction[1], s * direction[0] + c * direction[1])


def choose_direction(origin, target):
    desired, target_distance = unit_to_target(origin, target)
    probe = min(max(AGENT_RADIUS * 2.0, PROBE_DISTANCE),
                max(AGENT_RADIUS * 2.0, target_distance))
    if not segment_hits_wall(origin, desired, probe):
        return desired
    best, best_score = None, float("-inf")
    for angle in CANDIDATE_ANGLES:
        candidate = rotate(desired, angle)
        if segment_hits_wall(origin, candidate, probe):
            continue
        score = candidate[0] * desired[0] + candidate[1] * desired[1]
        if score > best_score:
            best, best_score = candidate, score
    return best or (0.0, 0.0)


def strip_csharp_comments_and_strings(text):
    """Keep delimiters outside C# comments/strings for a small syntax sanity check."""
    out, i, state = [], 0, "code"
    while i < len(text):
        c = text[i]
        n = text[i + 1] if i + 1 < len(text) else ""
        if state == "code":
            if c == "/" and n == "/":
                state, i = "line", i + 2
                continue
            if c == "/" and n == "*":
                state, i = "block", i + 2
                continue
            if c == '"':
                state, i = "string", i + 1
                continue
            out.append(c)
            i += 1
        elif state == "line":
            if c == "\n":
                state = "code"
                out.append(c)
            i += 1
        elif state == "block":
            if c == "*" and n == "/":
                state, i = "code", i + 2
            else:
                i += 1
        else:  # regular string literal; escaped quotes are ignored
            if c == "\\":
                i += 2
            elif c == '"':
                state, i = "code", i + 1
            else:
                i += 1
    return "".join(out)


class EnemyNavigationRegression(unittest.TestCase):
    def test_source_has_bounded_obstacle_aware_route_and_preserves_fsm(self):
        source = SOURCE.read_text(encoding="utf-8")
        for required in (
            "Physics.CapsuleCastNonAlloc",
            "NavigationCandidateAngles",
            "navigationReplanInterval",
            "QueryTriggerInteraction.Ignore",
            "AIState.RadioCheckIn",
            "AIState.RepairCameraAndDisarmC4",
            "AIState.ReviveFallenAlly",
        ):
            self.assertIn(required, source)
        self.assertNotIn("FindPath", source, "Do not accidentally replace this lightweight bounded fallback with an unbounded search")

        cleaned = strip_csharp_comments_and_strings(source)
        stack = []
        pairs = {"}": "{", ")": "(", "]": "["}
        for character in cleaned:
            if character in "{([":
                stack.append(character)
            elif character in pairs:
                self.assertTrue(stack, f"unmatched closing delimiter {character}")
                self.assertEqual(stack.pop(), pairs[character])
        self.assertFalse(stack, f"unclosed C# delimiter(s): {stack}")

    def test_direct_wall_probe_selects_a_deterministic_detour(self):
        # Start close enough that the finite 2.4 m probe reaches the wall's
        # radius-expanded face; distant clear space is intentionally not a hit.
        origin, target = (2.0, 0.0), (10.0, 0.0)
        direct, _ = unit_to_target(origin, target)
        self.assertTrue(segment_hits_wall(origin, direct, PROBE_DISTANCE))
        first = choose_direction(origin, target)
        second = choose_direction(origin, target)
        self.assertEqual(first, second)
        self.assertNotEqual(first, direct)
        self.assertGreater(first[1], 0.0, "fixed +25 degree candidate should win the initial tie")

    def test_corner_route_reaches_target_without_entering_clearance(self):
        position, target = (0.0, 0.0), (10.0, 0.0)
        for _ in range(40):
            direction = choose_direction(position, target)
            self.assertGreater(math.hypot(*direction), 0.99)
            step = min(0.8, math.hypot(target[0] - position[0], target[1] - position[1]))
            self.assertFalse(segment_hits_wall(position, direction, step), position)
            position = (position[0] + direction[0] * step,
                        position[1] + direction[1] * step)
            if math.hypot(target[0] - position[0], target[1] - position[1]) < 0.8:
                break
        self.assertLess(math.hypot(target[0] - position[0], target[1] - position[1]), 0.8)

    def test_fully_blocked_probe_waits_instead_of_crossing(self):
        # A deliberately enclosed/overlapping spawn blocks every candidate probe.
        global WALL
        original = WALL
        try:
            WALL = (-20.0, 20.0, -20.0, 20.0)
            self.assertEqual(choose_direction((0.0, 0.0), (10.0, 0.0)), (0.0, 0.0))
        finally:
            WALL = original


if __name__ == "__main__":
    unittest.main()
