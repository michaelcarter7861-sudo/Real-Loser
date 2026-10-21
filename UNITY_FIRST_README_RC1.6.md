# Project Real Loser RC1.6 — Unity source candidate

This is the Unity 3D source project; `playable/ProjectRealLoser.html` and the Android WebView wrapper are legacy prototypes, not the game. The editor version is **Unity 2022.3.40f1**. The active project render pipeline remains Built-in, despite the URP package being present. This package contains Unity source and assets, **not a built APK**.

## What changed in RC1.6

- Added **104 environment GLBs** for the types referenced by the ten mission JSON files. Across M01–M10, all **118 distinct environment asset types** now resolve to a model file. The 104 additions include 102 unique procedural low-poly meshes, normalized/textured 3D relay mast and armored cargo-truck assets, plus embedded albedo/normal maps for the procedural catalog. The truck is 5.8 × 2.7 × 2.5 m; the relay is 2.2 × 7.5 × 2.2 m. Existing Art/StreamingAssets pairs were hash-checked; the concrete barrier stays unchanged.
- The previous **80/81** baseline GLBs have generated UV0 plus embedded base-colour and normal PNGs; the 2 generated RC1.6 assets already contain their own UV/PBR image sets. Thus the project carries **185 GLBs** across character, weapon, trap, and environment folders (24/26/16/119 respectively). These procedurally generated maps are an art baseline, not artist-authored texture atlases or a substitute for in-Unity material review.
- Added `builders/build_mission_environment_catalog.py` for repeatable mission-type model generation and `tools/integrate_rc16_assets.py` for normalized model integration, texture processing and mirror checks.
- Added a mission-objective runtime that exposes E/touch interactions, step progress, objective-gated extraction and checkpoint/retry APIs. Fixed a target-selection bug: the objective step completed is now the same ordered spatial target the player interacted with; a blocked event step cannot be skipped by walking to a later coordinate. The new Unity NUnit file contains an exact-target regression test.
- Enemy movement has a lightweight, bounded local obstacle-avoidance steering pass. This is **not** a baked NavMesh or full global pathfinder.

## Static validation run in this environment

The following checks passed after restoring the original textured assets and synchronizing their StreamingAssets copies:

- `python3 tests/test_texture_glb_library.py`: original 81-file baseline semantics, 104 additions, 185 Art/StreamingAssets hash-matched files, and protected barrier hash.
- `python3 builders/build_mission_environment_catalog.py --check`: all 118 referenced environment type paths contain valid GLB 2.0 geometry.
- `python3 tools/integrate_rc16_assets.py --check-only`: generated model dimensions and mirror hashes.
- `python3 tests/test_rc15_content.py`, `python3 tests/test_enemy_navigation_regression.py`: passed.
- `python3 tests/test_mission_objective_wiring.py`: static wiring and M01–M10 data coverage passed; this does not execute C# behaviour.
- Character, weapon, audio, campaign level validator, and M01–M10 mission-verification scripts: passed.
- Tree-sitter parsed all 26 C# source/editor/test files with zero grammar errors. This is a grammar-level check, **not a Unity C# compilation**.

The architecture/anti-cheat `tests/run_phase0_selftest.py` was changed to build and validate generated assets only inside a disposable temporary directory. The safe self-test passed, and the texture regression run immediately afterward confirmed all 185 final Art/StreamingAssets models remained intact and hash-matched.

## Open and build locally

1. Install Unity **2022.3.40f1** with Android Build Support, Android SDK & NDK Tools and OpenJDK if you want an APK.
2. Extract the ZIP and open the `prl_ui_audit/` folder (the folder containing `Assets/`, `Packages/` and `ProjectSettings/`) from Unity Hub.
3. Wait for import/compilation. Resolve any Unity Console errors before building. Run **Tools → Real Loser → Sync StreamingAssets & Generate Scenes** to refresh StreamingAssets and regenerate the 12 scenes.
4. Open `Assets/_Project/Scenes/Boot.unity`, enter Play Mode, and test missions, player movement/aim/fire/reload, weapons, enemy detection/combat, trap disarm, map markers, objective interactions, extraction, checkpoint/retry, and scene transitions.
5. Only after Play Mode is clean, use **Tools → Real Loser → Build All**. It configures Android ARM64/IL2CPP, landscape, minimum SDK 24 and target SDK 34, then writes `Builds/Android/ProjectRealLoser_v1.0.apk`. On a device, also verify touch controls, permissions, loading time, memory, thermal behaviour, and crash logs.

## Important limitations — not a claim of being better than IGI 1

No Unity Editor, Unity compiler, Android build toolchain or target device was available in this session. Consequently, Unity import, shader/material appearance, C# semantic compilation, Play Mode, APK creation, real touch input, full campaign completion, crash-free operation, FPS, memory, battery/thermal load, and performance on a specific phone have **not** been verified. The 17,771 placed environment records across M01–M10 make real-device profiling especially important; the static model/path checks do not establish a frame-rate budget.

The texture workflow uses deterministic, object-space UV projections and procedural tileable PBR detail. It does not provide manual seam-aware unwraps, handcrafted wear/decals, artist review or a matching authored art direction. The two generated hero props were checked structurally, but not rendered or approved in Unity. Humanoid assets contain rigs but no authored animation clips; procedural locomotion is a basic placeholder, not an authored tactical animation set. LOD assets exist but runtime LOD switching is not implemented.

The new objective system is a usable interaction foundation, **not a completed simulation of every mission rule**. Hacking durations, C4 placement/detonation, actual driveable convoy handling, hostage-follow behaviour, camera/power-system effects, alert/stealth/kill constraints, and several conditional medal outcomes still need mission-specific gameplay producers and playtesting. Do not treat every objective title as proof its full described mechanic is implemented. AI avoidance is local steering; it can still fail around complex geometry and needs in-engine testing.

Therefore RC1.6 is a substantially expanded, statically checked Unity source candidate, but it is **not a verified finished release and no honest claim can be made that it is better than Project I.G.I.: I'm Going In** until the Unity build, full playthrough, art review and target-device performance tests are complete.
