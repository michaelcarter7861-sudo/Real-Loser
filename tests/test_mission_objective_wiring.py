#!/usr/bin/env python3
"""Static regression checks for the RC1.6 objective runtime wiring (not a C# execution test)."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    runtime_path = ROOT / "Assets/_Project/Scripts/Core/MissionObjectiveRuntime.cs"
    spawner_path = ROOT / "Assets/_Project/Scripts/Core/RuntimeMissionSpawner.cs"
    hud_path = ROOT / "Assets/_Project/Scripts/UI/MobileTouchHUDAndMEMap.cs"
    runtime = runtime_path.read_text(encoding="utf-8")
    spawner = spawner_path.read_text(encoding="utf-8")
    hud = hud_path.read_text(encoding="utf-8")
    errors = []

    for method in (
        "GetNextInteractableStepIndex",
        "CompleteExplicitStep",
        "TryInteract",
        "CanExtract",
        "RetryFromCheckpoint",
        "RetryMission",
        "NotifyObjectiveConditionMet",
    ):
        if method not in runtime:
            errors.append(f"objective runtime missing {method}")
    if "bestStepIndex = s" not in runtime or "CompleteExplicitStep(id, bestStepIndex)" not in runtime:
        errors.append("interaction does not complete the exact spatial step selected by range")
    if "GetNextInteractableStepIndex(definition.id)" not in runtime:
        errors.append("interaction does not restrict candidates to the first required ordered step")
    if "return step.requiresExplicitInteraction && step.hasPosition ? i : -1;" not in runtime:
        errors.append("pending event/condition steps no longer block later spatial steps")
    if "ExtractionUnlocked && Vector3.Distance" not in runtime:
        errors.append("extraction is not gated by primary completion and extraction radius")
    if "SetupMissionObjectiveRuntime();" not in spawner or "BindObjectiveRuntime(objectiveRuntime)" not in spawner:
        errors.append("spawner/objective runtime/HUD binding incomplete")
    if "objectiveRuntime.TryInteract()" not in hud or "OnContextInteractNearestTrap()" not in hud:
        errors.append("touch interaction/trap fallback missing")
    if "Input.GetKeyDown(KeyCode.E)" not in hud:
        errors.append("keyboard E interaction missing")

    total = 0
    for i in range(1, 11):
        path = ROOT / f"M{i:02d}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        objectives = data.get("objectives", {})
        primary = objectives.get("primary", []) or []
        secondary = objectives.get("secondary", []) or []
        if not primary or not isinstance(secondary, list):
            errors.append(f"{path.name}: malformed primary/secondary objective lists")
        if not objectives.get("extraction", {}).get("pos"):
            errors.append(f"{path.name}: extraction position missing")
        total += len(primary) + len(secondary)
        for item in primary + secondary:
            if not item.get("id"):
                errors.append(f"{path.name}: objective without id")
    if total < 20:
        errors.append(f"expected at least 20 campaign objective records; saw {total}")

    if errors:
        print("FAIL")
        for error in errors:
            print("  " + error)
        return 1
    print(f"PASS: static objective wiring covers M01-M10 ({total} objective records), ordered target selection, exact-step completion, extraction gating, touch/E controls and checkpoint APIs. C# execution was not run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
