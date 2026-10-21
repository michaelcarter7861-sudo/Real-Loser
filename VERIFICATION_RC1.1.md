# Automated Verification — RC 1.1

| Check | Result |
|---|---|
| JavaScript parser (`node --check`) | PASS |
| Mission Anti-Cheat v3 validation, M01–M10 | PASS (10/10) |
| Character asset validator | PASS (24 GLB assets) |
| Weapon asset validator | PASS (26 GLB assets) |
| Audio asset validator | PASS (34 audio assets) |
| Phase 0 self-test | PASS |
| Standalone/Android entry point equality | PASS |
| Android APK build | NOT RUN (Android SDK/Gradle build environment unavailable) |
| Unity compilation / device playtest | NOT RUN |

Note: this environment emits an unrelated spreadsheet-runtime warmup warning at Python startup. The listed validation scripts still returned their stated pass results; the mission validator and phase-0 self-test exited successfully.
