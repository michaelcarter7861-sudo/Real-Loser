# Project Real Loser — Release Candidate 1.1

## Start playing
- **Standalone offline game:** open `playable/ProjectRealLoser.html` in a modern desktop or mobile browser.
- **Android source entry point:** `android/app/src/main/assets/index.html` contains the same standalone runtime.
- **Unity project:** open the project root using the Unity version recorded in `ProjectSettings/ProjectVersion.txt`.

## Gameplay in this build
- Ten selectable mission layouts with distinct environmental palettes.
- First-person ray-cast view, minimap, objective/extraction markers, enemy patrols and alert states.
- Player health, ammunition, reloading, shooting, line-of-sight, enemy return fire and death/failure state.
- Three weapon profiles: M4A1-style rifle, suppressed USP-style sidearm, and DMR-style marksman rifle, with different magazine sizes, damage, fire intervals, range, spread and reload behavior.
- Standing, crouching, prone stance, aiming/zoom, weapon switching, objective interaction and extraction.
- Keyboard/mouse and touch controls; no external CDN is required by the standalone runtime.

## Controls
Desktop: WASD move; mouse look; left click fire; right mouse button aim; R reload; E interact; C cycle stance; 1/2/3 select weapon; Shift sprint; Esc menu.
Mobile: use the left virtual pad to move, drag the play view to look, and use the on-screen buttons for fire, reload, interact, stance, weapon switching, and aim. Landscape is recommended.

## Validation performed
- JavaScript syntax check: passed using Node.js.
- Mission layout validator: all M01–M10 JSON files passed Anti-Cheat v3 checks.
- Character asset validator: 24 character GLB assets passed.
- Weapon asset validator: 26 weapon GLB assets passed.
- Audio validator: 34 audio assets passed.
- Phase 0 self-test: passed.
- ZIP integrity: checked when packaging.

## Important limitations
This is a **release candidate**, not a verified commercial release. The standalone version uses a procedural ray-cast renderer, not the full fidelity of a modern 3D engine. Unity C# source and original assets are retained, but Unity compilation, Android APK compilation, physical-device testing, performance profiling, and a complete gameplay QA pass were not possible in this environment. No APK is included. Build the Android project in Android Studio with a compatible SDK, and compile/playtest the Unity project in its recorded Unity version before public release.
