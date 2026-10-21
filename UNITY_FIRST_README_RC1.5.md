# Project Real Loser RC1.5 — Unity-first source candidate

Yeh **Unity 3D source project** hai; `playable/ProjectRealLoser.html` aur Android WebView HTML purane prototypes hain, final game nahi. Is project ka Unity version `2022.3.40f1` hai. `ProjectSettings/GraphicsSettings.asset` mein active custom render pipeline null hai, is liye abhi Built-in pipeline active hai; URP package dependency installed hona URP render pipeline active hone ka saboot nahi.

## Unity mein open aur build

1. Unity Hub mein **Unity 2022.3.40f1** install karein. Android APK ke liye isi editor ka Android Build Support, Android SDK & NDK Tools aur OpenJDK install hona chahiye.
2. ZIP extract karke andar ke `prl_ui_audit/` folder ko Unity Hub se **Add project from disk** karein—isi folder mein `Assets/`, `Packages/` aur `ProjectSettings/` hain.
3. Project import ke baad Unity menu se **Tools → Real Loser → Sync StreamingAssets & Generate Scenes** chalaein. Builder `Assets/_Project/Editor/RealLoserProjectBuilder.cs` mein hai.
4. `Assets/_Project/Scenes/Boot.unity` se Play Mode chalayein. Console errors ko pehle resolve karein; phir M01 se M10 tak controls, weapons, hit/damage, AI, objective interactions, extraction, checkpoint/retry, maps aur scene reload ko test karein.
5. Android modules maujood hon to **Tools → Real Loser → Build All** use karein. Is archive mein Unity-built APK shamil nahi hai.

## RC1.5 mein ki gayi source/asset tabdeeliyan

- Mission JSON se M01–M10 ke 1536×1024 top-down tactical schematics generate kiye: zones/buildings, silent/technical/loud routes, starting hostiles, traps/cameras, primary/secondary objective markers, extraction aur player start. Textures `Assets/Resources/MissionMaps/` mein hain. HUD unhein `Resources.Load` karta hai; player marker world/map projection par chalta hai, aur spawner se linked enemy blips active patrol transforms follow karte hain. Yeh data-derived schematics hain, satellite photographs nahi.
- Runtime GLB path ab ek asset ko pehli baar parse karke inactive prefab template cache karta hai aur baad ki repeated placements uski clones banati hain; is se repeated GLB decode/material creation ka kaam kam hota hai. GLB UV0, embedded base-colour aur linear normal textures load kiye jate hain. Shader choice active render pipeline ko dekhti hai, taa ke Built-in project mein URP package ko ghalti se pehli preference na mile.
- Character importer `JOINTS_0`, `WEIGHTS_0`, 15-joint inverse bind matrices aur `SkinnedMeshRenderer` banata hai. Shipped humanoid files mein authored animation clips nahi mile, is liye `ProceduralHumanoidMotion` simple idle/walk locomotion fallback deta hai. Yeh authored run/aim/reload/recoil/cover/hit/death animations ka badal nahi.
- Ek naya concrete barrier GLB candidate add kiya: source mesh simplify karke 2,568 triangles, normalized bounds 2.40×1.05×0.60m aur ground-level pivot diya; embedded base-colour/normal texture refs maujood hain. `_Project/Art` aur `StreamingAssets/Art` copies SHA-256 se same verify hui. Yeh ek asset hai, poori environment art pass nahi; Unity mein final visual approval abhi baqi hai.
- `tools/build_mission_maps.py`, `tools/normalize_glb.py` aur `tests/test_rc15_content.py` repeatable generation/validation ke liye shamil hain.

## Is environment mein huay checks

- M01–M10 anti-cheat/level validator pass; M01–M10 mission verifier scripts pass.
- Phase-0 self-test pass (expected negative anti-cheat case ko reject karta hai aur positive sandbox ko pass karta hai).
- Character validator 24/24 rigged character GLBs pass; weapon validator 26/26; audio validator 34/34.
- 24/24 rigged character GLBs ke JOINTS/WEIGHTS, joint index ranges, normalized weights aur MAT4 bindpose schemas locally parse/check huay.
- 10/10 tactical map PNGs aur `tests/test_rc15_content.py` pass.
- All 24 C# files (Scripts + Editor) C# grammar parser se parse huay. Yeh **C# grammar check** hai—Unity compiler ya Play Mode pass nahi.
- Project art inventory: 81 GLBs (24 characters, 26 weapons, 16 traps, 15 environment assets); 24 GLBs weighted rigs ke saath, 0 GLBs authored animation clips ke saath. Naye barrier ke ilawa existing 80 assets mein UV0/image textures nahi; woh material colour factors par depend karte hain.
- Sabhi weapon models ke char alag one-primitive mesh nodes hain; 26/26 ke primitives material 0 use karte hain. Is liye current project files mein loader ka first-primitive/first-material behavior measured weapon geometry drop nahi kar raha.

## Release blockers / jo abhi fix ya verify baqi hai

**IGI 1 se behtar hone ka claim abhi durust nahi.** Is project mein 10 campaign missions hain; IGI 1 ke liye cited contemporary/reference material 14-mission campaign batata hai. Mission files mein 10,110 props, 5,674 cover items, 1,141 structures, 310 enemies, 88 traps aur 38 cameras hain, magar yeh counts game ko “heavier” ya achha mehsoos hone ka saboot nahi—actual playtest aur performance profile chahiye.

Environment art abhi zyada tar untextured/generated geometry hai. 80/81 GLBs mein UV0 aur image textures nahi; sab ke normals aur factor-based materials hone se textured production art nahi banti. Naya barrier sirf ek localized texture pass hai. Characters ke 24 rigs import ho sakte hain, lekin animation authored nahi; procedural walk/idle quality aur joint axis Play Mode mein dekhna zaroori hai. Importer abhi character LOD1/LOD2 ko render se skip karta hai—runtime LODGroup switching implemented nahi.

Mission-specific multi-step objective rules abhi poore implement/verify nahi; pichle guide mein documented generic proximity objective flow abhi release blocker hai. Enemy movement direct transform motion hai, full NavMesh/path-obstacle avoidance nahi. Mission files ka bada object census streaming system ke bawajood frame-time, memory aur Android hardware load ko materially affect kar sakta hai; koi measured FPS/memory result maujood nahi.

Is Sandbox session mein Unity Editor/compiler, Android build toolchain ya target device se build/launch nahi kiya gaya. Is liye **Unity compile, Play Mode, APK, touch controls, actual GLB texture/skin appearance, mission completion, crash-free runtime aur device performance sab unverified hain**. RC1.5 ko patched source candidate samjhein—verified release ya IGI-se-better final game nahi.

## External reference notes

Technical sources aur version cautions `EXTERNAL_TECH_RESEARCH_NOTES_RC1.5.md` mein URL ke saath saved hain. IGI comparison sources mein IGN ki contemporary coverage aur campaign reference shamil hain; comparison report ko hands-on Play Mode tests ke baghair final quality verdict na samjhein.


## Unity scene identity metadata fix

RC1.5 mein Boot, MainMenu aur M01–M10 ke scene `.meta` sidecars add kiye gaye. Unke GUIDs `EditorBuildSettings.asset` ke 12 records se exact match karte hain; 22 serialized custom scene-script GUID references bhi available metadata mein resolve huay. Is se Unity first-import par scene IDs/build list drift ka risk kam hota hai. Baqi generated/image/model files ke missing `.meta` sidecars Unity apne normal project import par bana sakta hai; stable scenes/scripts ke liye yeh pehle se mandatory GUID match issue tha.
