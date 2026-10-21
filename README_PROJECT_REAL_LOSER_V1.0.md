# Project Real Loser — Unity Source Candidate (RC1.6)
Target Engine: Unity 2022.3.40f1 LTS (active Built-in render pipeline; Android ARM64 target)

> **RC1.6 Unity-first status:** Use [UNITY_FIRST_README_RC1.6.md](UNITY_FIRST_README_RC1.6.md) for current open/build instructions, evidence and remaining release gates. The files under `playable/` and the Android WebView wrapper are legacy prototypes, not the intended 3D Unity game. This is source only: Unity compilation, Play Mode, APK/device testing and an IGI 1 superiority claim remain unverified.

## Package Contents
1. **Unity Project Assets (`Assets/_Project/`)**:
   - `Assets/_Project/Missions/M01.json` – `M10.json` (All 10 Handcrafted Campaign Mission Blueprints)
   - `Assets/_Project/Scenes/M01.unity` – `M10.unity` (All 10 Unity 2022.3 YAML Mission Scenes)
   - `Assets/_Project/Scripts/` (7 Core Tactical Gameplay Systems + 10 Mission Scene Installers)
   - `Assets/_Project/Art/Characters/` (24 Rigged 15-Bone Humanoid `.glb` Models with LOD0/LOD1/LOD2)
   - `Assets/_Project/Art/Weapons/` (26 Articulated 4-Submesh Weapon `.glb` Models with 6 Reference Empties)
   - `Assets/_Project/Art/Traps/` (16 Tactical Trap `.glb` Models `T1`–`T16`)
   - `Assets/_Project/Art/Environment/` (119 `.glb` models: 15 baseline models plus 104 RC1.6 mission-referenced additions)
   - `Assets/_Project/Audio/` (34 Synthesized 16-Bit PCM `.wav` Sound Cues + `audio_manifest.json`)
2. **Root Mission Blueprints (`M01.json` – `M10.json`)**
3. **Anti-Cheat Validation Suite v3 (`validate_*.py`)**:
   - `validate_levels_v3.py`
   - `validate_characters.py`
   - `validate_weapons.py`
   - `validate_audio.py`
4. **Builders (`builders/`) & Verification Suite (`tests/`)**:
   - `builders/build_mission_m01.py` – `build_mission_m10.py`
   - `builders/build_characters_glb.py`, `build_weapons_glb.py`, `build_traps_and_architecture_glb.py`, `build_audio_bank.py`
   - `tests/run_phase0_selftest.py`
   - `tests/verify_m01_bootcamp.py` – `tests/verify_m10_compoundzero.py`


## Patch notes — v1.0.1 gameplay stabilization

This maintenance pass keeps the original mission data and assets and improves the Android WebView runtime:

- Added an offline first-person ray-cast fallback when the Three.js CDN is unavailable. Online devices can still load the Three.js renderer.
- Declared Android INTERNET permission for the optional remote Three.js dependency and made OpenGL ES 3 non-mandatory so compatible WebView fallback devices can launch.
- Added player health, pistol ammunition, reload, basic enemy detection/chase/return fire, alert HUD updates, and mission failure on player down.
- Added basic collision against structure footprints and line-of-sight checks for shots and enemy detection.
- Added simplified rendering for mission props, cover, and vegetation in the Three.js scene.
- Corrected objective interactions so they require proximity to the objective/extraction; interaction no longer completes the mission from anywhere. Nearby traps can be disarmed independently.
- Added objective and extraction markers to the tactical map.
- Replaced hard-coded developer paths in mission builder and mission-verification scripts with paths relative to each script.

### Verification performed

- JavaScript syntax check (`node --check`): passed.
- Python compile check for builders, tests, and validators: passed.
- Phase 0 asset/anti-cheat self-test: passed (including its expected negative anti-cheat test and positive sandbox test).
- Mission-specific verification scripts M01–M10: passed.

### Known limitations

This is a gameplay stabilization patch, not a claim of IGI-level production completeness. The Android app was not compiled or device-playtested in this environment because Android/Gradle tooling is not installed. The offline fallback is a lightweight ray-cast renderer rather than full polygonal 3D. Enemy AI, collision, objectives, and rendering remain simplified; Unity editor playtesting, proper navmesh/pathfinding, full animation integration, and device performance profiling are still needed. The online Three.js path requires a network connection unless a local Three.js library is bundled by the developer.
