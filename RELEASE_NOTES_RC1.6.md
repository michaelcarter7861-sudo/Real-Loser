# RC1.6 — Unity source and mission environment expansion

## Added

- A deterministic procedural environment catalog builder that creates missing mission-referenced prop/building/vehicle/vegetation meshes as separate GLB assets rather than routing all missing paths to one fallback.
- 102 catalog models with generated UV0 and embedded base-colour/normal PNG maps; two textured generated assets integrated into campaign identities: `env_tower_radio_relay_steel_a.glb` (2.2 × 7.5 × 2.2 m) and `veh_truck_cargo_a.glb` (5.8 × 2.7 × 2.5 m).
- `MissionObjectiveRuntime` for data-driven interaction steps, explicit extraction gating, checkpoint/retry APIs and HUD interaction binding.
- Bounded local obstacle-avoidance steering for enemy movement.
- Stable metadata for the objective runtime and Editor regression test; expanded checks for original plus additive asset inventory.

## Fixed

- Runtime objective interaction previously found a nearby target but could complete another, earlier objective step. It now resolves the first required step and completes exactly the selected step; later spatial steps cannot be triggered out of order, and pending event steps block following spatial interactions.
- Added a Unity NUnit regression for wrong-target selection, ordered multi-step progression and event gating.

## Verification

- All 118 distinct environment `type` values referenced in M01–M10 resolve to GLB files.
- 185 GLBs across Art and StreamingAssets have matching SHA-256 mirrors; the original 81-file texture baseline validates and the concrete barrier hash remains preserved.
- All 104 additive environment assets passed structural GLB/UV/image checks (102 generated catalog models plus the 2 generated PBR assets).
- Character (24), weapon (26), audio (34), M01–M10 anti-cheat/mission validators passed. RC1.5 map/content checks and four enemy-navigation regression checks passed.
- 26 C# files passed Tree-sitter C# grammar parsing. Unity Editor compilation, NUnit execution, Play Mode, APK build and device tests were not available and are not claimed.

## Known incomplete features

Mission-specific hacking timers, C4 plant/detonate, real vehicle driving/convoy control, hostage escort, security-camera/power consequences, stealth/alert/kill constraints and conditional medal rules need gameplay event producers and Play Mode validation. Procedural textures/models need visual approval; character authored animation and runtime LOD switching remain incomplete. The local enemy steering is not NavMesh/global pathfinding. See `UNITY_FIRST_README_RC1.6.md` for setup steps and release gates.

The Phase-0 self-test now builds temporary art/audio outputs in an auto-deleted directory instead of overwriting textured project deliverables. The safe self-test passed, and the full asset-mirror regression passed immediately afterward.
