# Release notes — Project Real Loser RC1.5

## Code aur content updates

- Added generated tactical schematic PNGs for M01–M10 and wired them into the Unity HUD, with a projected player marker and live enemy markers connected to spawned enemy transforms.
- Added a reproducible content test for map assets, HUD wiring, the normalized barrier GLB, and character rig import source.
- Added a textured concrete barrier candidate at 2.40×1.05×0.60m, ground pivot 0, simplified to 2,568 triangles; mirrored runtime copy verified by SHA-256.
- Runtime GLB loading now caches parsed prefab templates and clones them for repeated placements; supports UV0, embedded base-colour textures, normal textures, and active-render-pipeline-aware shader fallback.
- Added glTF JOINTS_0/WEIGHTS_0 and inverse-bind matrix import into SkinnedMeshRenderer; added procedural idle/walk locomotion for imported rigs with expected humanoid bone names.
- Existing RC1.4 source fixes remain: async Android/WebGL StreamingAssets preload, explicit mission coordinates, camera spawning, weapon/player binding, reload cleanup, gameplay regression repairs, validators and legacy HTML hang correction.

## Verified checks

- Phase-0 self-test, M01–M10 anti-cheat/level validation, 10 mission verifier scripts, character/weapon/audio validators, map generator check, and `tests/test_rc15_content.py` completed successfully in Sandbox.
- All 24 character GLBs' joint/weight/MAT4 schemas and weight sums were independently checked; all passed.
- C# grammar parser: 24/24 source files (Scripts + Editor) parsed without syntax errors. This is not a Unity compilation result.
- All 81 art GLBs were inventoried: 24 character, 26 weapon, 16 trap and 15 environment models. There are 0 authored animation clips. Only the new barrier GLB has UV0 and embedded image textures; 80 existing models have no UV/image textures.
- Asset topology check corrected an earlier suspicion: each shipped mesh has one primitive. Each weapon has four separate mesh nodes and all 26 weapons use material 0, so the loader's first-primitive/material path does not currently drop shipped weapon parts/materials.

## Known limitations

- Unity Editor/compiler, Play Mode, Android APK build, controls on device, frame-time, memory and rendering appearance were not verified here. The archive is a patched source candidate, not a tested release.
- The procedural locomotion is a minimal fallback—not authored combat, aim, reload, recoil, reaction, cover, crouch, vault, death or cinematic animation.
- Character LOD1/LOD2 are not used by runtime LODGroup switching; the loader currently skips those meshes and renders LOD0.
- Most 3D models remain untextured/factor-coloured generated geometry. One new barrier does not constitute a complete art pass.
- Mission-specific objective sequences still need implementation and end-to-end verification; runtime enemy movement lacks full NavMesh/path obstacle avoidance.
- This release is not proven to be better than Project I.G.I.; see `RC1.5_AUDIT_DELTA.md` for the evidence-based comparison and priorities.


## Packaging integrity

Added stable `.meta` sidecars for all 12 Unity scenes, matching the GUIDs already listed in `EditorBuildSettings.asset`; verified all 22 serialized custom script references resolve and all 31 metadata GUIDs are unique. Added a stable MonoImporter sidecar for the new procedural humanoid motion script.
