# Project Real Loser RC1.4 — Unity-first source package

Yeh package **Unity 3D project** hai. `playable/ProjectRealLoser.html` aur `android/app/src/main/assets/index.html` sirf legacy browser/WebView prototype hain; inhein final game ya Unity 3D build na samjhein. Actual game ka source `Assets/_Project/Scripts`, Unity scenes aur `Assets/_Project/Missions` mein hai.

## Unity mein open aur build

1. Unity Hub mein **Unity 2022.3.40f1 LTS** install karein. Android APK chahiye to usi editor ke saath Android Build Support, Android SDK & NDK Tools, aur OpenJDK bhi install karein.
2. Unity Hub mein **Add project from disk** chunein aur archive ka `prl_ui_audit/` folder add karein—isi folder ke andar `Assets/`, `Packages/` aur `ProjectSettings/` hain.
3. Import/compile ke baad Unity menu se **Tools → Real Loser → Sync StreamingAssets & Generate Scenes** chalaein. `Assets/_Project/Editor/RealLoserProjectBuilder.cs` project ka builder menu deta hai.
4. `Assets/_Project/Scenes/Boot.unity` khol kar Play karein; pehle Console ke compile/import errors resolve karein. Har mission ko alag test karke AI, controls, combat, objectives, extraction, retry aur performance check karein.
5. Android support install ho to **Tools → Real Loser → Build All** chalaein. Expected APK path `Builds/Android/ProjectRealLoser_v1.0.apk` hai.

## RC1.4 mein patched

Android/WebGL StreamingAssets ke sync busy-wait ko coroutine-based loading se replace kiya gaya; mission JSON, referenced GLBs aur WAVs async preload hote hain. Camera JSON entries ab spawn/register hoti hain, existing PlayerTacticalController ke saath weapon system bind hota hai, aur mission reload purane streaming tiles clear karta hai. Mission target/extraction coordinates all 10 installers mein JSON se liye jate hain.

Combat firing ko centralized ammo/cadence/damage path par laya, trap disarm ko timed context action banaya, enemy vision mein wall occlusion add ki, hazards ke repeat triggers aur touch joystick release ko control kiya. Pause/settings Back, late tile registration aur checkpoint integrity verification sudhare gaye. M01/M02 zone references, M05 camera mount target aur alarm-record duplication durust kiye gaye; validator mein ID/zone/link/objective/census checks barhaye gaye.

Legacy HTML spawn loop ko bhi fix kiya, bounded deterministic placement fallback aur pointer-safe right-click aim lagaya. Yeh prototype ab hang nahi karta magar phir bhi 2D raycaster hai—Unity 3D game ka substitute nahi.

## Verification aur release limitations

Verified here: M01–M10 level validator pass; phase-0 self-test aur dason mission verifier scripts pass; Python validators/tests compile; mission ki 40 copies byte-identical; 23 C# files C# grammar parser se pass; camera/player/streaming/objective binding ke source assertions pass; HTML syntax aur 10 deterministic generation tests pass.

**Mission objective execution abhi generic proximity checks hai.** JSON-derived target positions sahi kar di gayi hain, lekin mission-specific multi-step rules—misal ke taur par M06 ke tamam manifolds aur detonation distance, M08 truck/checkpoint delivery, required target kills/hacks, event order aur mission-specific extraction gates—poori tarah implement/verify nahi. Is build ko IGI 1 se behtar, complete ya release-ready kehna durust nahi.

**Unity Editor compile, Play Mode, Android APK build, device controls aur performance verify nahi hue.** Is environment mein Unity Editor, Android SDK/Gradle aur test device maujood nahi the. Isay patched Unity source candidate samjhein, verified APK nahi; device release se pehle Unity Console errors aur M01–M10 end-to-end QA zaroori hai.

Checkpoint SHA-256 checksum accidental corruption detect karta hai; yeh secret-key authentication ya encryption nahi. Pehle ka plaintext checkpoint format compatibility ke liye auto-load nahi hota.
