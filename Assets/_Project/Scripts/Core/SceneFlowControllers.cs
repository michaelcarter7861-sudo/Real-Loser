using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.SceneManagement;
using UnityEngine.EventSystems;

namespace RealLoserStudio.Tactical.Core
{
    /// <summary>
    /// Scene Flow Controllers (`SceneFlowControllers.cs`) referenced by `RealLoserProjectBuilder.cs`
    /// when generating `Boot.unity` and `MainMenu.unity`:
    /// - `BootSceneController`: Sets `Application.targetFrameRate = 60`, enforces Landscape auto-rotation,
    ///   pre-warms the tactical audio bank, and loads `"MainMenu"`.
    /// - `MainMenuController`: Programmatically builds a full-screen tactical Canvas with an `EventSystem`
    ///   and 10 interactive Mission Selection buttons (`M01` through `M10`) displaying each mission's
    ///   title, biome, and map dimensions, calling `SceneManager.LoadScene("M01")` .. `"M10"` on click.
    /// </summary>
    public class BootSceneController : MonoBehaviour
    {
        [Header("Boot Configuration")]
        public float splashDelaySeconds = 0.5f;
        public string nextSceneName = "MainMenu";

        private float _elapsed;
        private bool _loadedNext;

        private void Awake()
        {
            Application.targetFrameRate = 60;
            QualitySettings.vSyncCount = 1;

            Screen.orientation = ScreenOrientation.AutoRotation;
            Screen.autorotateToPortrait = false;
            Screen.autorotateToPortraitUpsideDown = false;
            Screen.autorotateToLandscapeLeft = true;
            Screen.autorotateToLandscapeRight = true;

            StartCoroutine(PrewarmBootAudio());
        }

        private IEnumerator PrewarmBootAudio()
        {
            yield return RuntimeGLBAndMeshLoader.LoadWavAudioClipAsync("sfx_ai_radio_checkin_beep", null);
        }

        private void Start()
        {
            if (splashDelaySeconds <= 0f)
            {
                LoadMainMenu();
            }
        }

        private void Update()
        {
            if (_loadedNext) return;
            _elapsed += Time.unscaledDeltaTime;
            if (_elapsed >= splashDelaySeconds)
            {
                LoadMainMenu();
            }
        }

        public void LoadMainMenu()
        {
            if (_loadedNext) return;
            _loadedNext = true;
            SceneManager.LoadScene(nextSceneName);
        }
    }

    public class MainMenuController : MonoBehaviour
    {
        [Serializable]
        public struct MissionSelectEntry
        {
            public string sceneId;
            public string title;
            public string biomeAndTime;
            public string dimensionsAndRoster;
        }

        public static string SelectedPrimaryWeapon = "wpn_m4a1_sopmod";
        public static string SelectedSidearm = "wpn_usp45_suppressed";
        public static string SelectedGadgetKit = "WireCutters + HackPDA + EMP";

        public static readonly MissionSelectEntry[] Missions = new MissionSelectEntry[]
        {
            new MissionSelectEntry { sceneId = "M01", title = "M01 — Boot Camp",       biomeAndTime = "Biome: Forest (Day / Clear)",          dimensionsAndRoster = "300m x 300m | 4 Enemies | 8 Traps" },
            new MissionSelectEntry { sceneId = "M02", title = "M02 — Disavowed",       biomeAndTime = "Biome: Arid Outpost (Dusk / Clear)",   dimensionsAndRoster = "800m x 600m | 24 Enemies | 8 Traps" },
            new MissionSelectEntry { sceneId = "M03", title = "M03 — Radio Silence",   biomeAndTime = "Biome: Mountain Forest (Night / Fog)", dimensionsAndRoster = "700m x 700m | 20 Enemies | 8 Traps" },
            new MissionSelectEntry { sceneId = "M04", title = "M04 — The Warehouse",   biomeAndTime = "Biome: Industrial Dock (Night / Rain)",dimensionsAndRoster = "500m x 400m | 22 Enemies | Hostage" },
            new MissionSelectEntry { sceneId = "M05", title = "M05 — Bridge Crossing", biomeAndTime = "Biome: River Gorge (Dawn / Overcast)", dimensionsAndRoster = "1200m x 350m | 36 Enemies | Boss Dar" },
            new MissionSelectEntry { sceneId = "M06", title = "M06 — Sand and Steel",  biomeAndTime = "Biome: Desert Depot (Day / Haze)",     dimensionsAndRoster = "1000m x 900m | 40 Enemies | 3 C4 Targets" },
            new MissionSelectEntry { sceneId = "M07", title = "M07 — Port Authority",  biomeAndTime = "Biome: Harbor Port (Night / Clear)",   dimensionsAndRoster = "900m x 600m | 44 Enemies | 8 Cameras" },
            new MissionSelectEntry { sceneId = "M08", title = "M08 — Convoy",          biomeAndTime = "Biome: Desert Canyon (Day / Wind)",    dimensionsAndRoster = "2500m x 300m | 40 Enemies | Convoy Ambush" },
            new MissionSelectEntry { sceneId = "M09", title = "M09 — Eyes Above",      biomeAndTime = "Biome: Arid Overwatch (Dusk / Clear)", dimensionsAndRoster = "800m x 800m | 34 Enemies | 5 Sniper Towers" },
            new MissionSelectEntry { sceneId = "M10", title = "M10 — Compound Zero",   biomeAndTime = "Biome: Urban Fortress (Night / Storm)",dimensionsAndRoster = "800m x 700m | 46 Enemies | Final Boss Rask" },
        };

        private Text _loadoutHeaderText;
        private GameObject _settingsPanel;

        private void Awake()
        {
            Application.targetFrameRate = 60;
            Screen.orientation = ScreenOrientation.AutoRotation;
            Screen.autorotateToPortrait = false;
            Screen.autorotateToPortraitUpsideDown = false;
            Screen.autorotateToLandscapeLeft = true;
            Screen.autorotateToLandscapeRight = true;

            BuildTacticalMainMenuUI();
        }

        public void BuildTacticalMainMenuUI()
        {
            if (FindObjectOfType<EventSystem>() == null)
            {
                GameObject esObj = new GameObject("EventSystem");
                esObj.AddComponent<EventSystem>();
                esObj.AddComponent<StandaloneInputModule>();
            }

            GameObject canvasGo = new GameObject("TacticalMainMenu_Canvas");
            Canvas canvas = canvasGo.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            CanvasScaler scaler = canvasGo.AddComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1920f, 1080f);
            scaler.matchWidthOrHeight = 0.5f;
            canvasGo.AddComponent<GraphicRaycaster>();

            Font uiFont = Resources.GetBuiltinResource<Font>("Arial.ttf");

            GameObject bg = CreatePanel(canvasGo.transform, "MenuBackground", Vector2.zero, Vector2.one, new Color(0.05f, 0.08f, 0.10f, 1f));

            CreateLabel(bg.transform, "HeaderTitle", "PROJECT REAL LOSER — v1.2 TACTICAL STEALTH OPERATIONS",
                new Vector2(0.04f, 0.90f), new Vector2(0.78f, 0.98f), uiFont, 34, TextAnchor.MiddleLeft, new Color(0.84f, 0.95f, 0.88f, 1f));

            CreateActionButton(bg.transform, "BtnFieldSettings", "FIELD SETTINGS", new Vector2(0.81f, 0.90f), new Vector2(0.96f, 0.98f), uiFont, ShowMainMenuSettings);

            GameObject loadoutBar = CreatePanel(bg.transform, "LoadoutBar", new Vector2(0.04f, 0.81f), new Vector2(0.96f, 0.89f), new Color(0.10f, 0.15f, 0.18f, 0.96f));
            _loadoutHeaderText = CreateLabel(loadoutBar.transform, "LoadoutStatus",
                $"LOADOUT: Primary [{SelectedPrimaryWeapon}] | Sidearm [{SelectedSidearm}] | Gadgets [{SelectedGadgetKit}]",
                new Vector2(0.02f, 0.10f), new Vector2(0.66f, 0.90f), uiFont, 20, TextAnchor.MiddleLeft, new Color(0.64f, 0.90f, 0.72f, 1f));

            CreateActionButton(loadoutBar.transform, "BtnCyclePrimary", "CYCLE PRIMARY", new Vector2(0.68f, 0.15f), new Vector2(0.82f, 0.85f), uiFont, () =>
            {
                if (SelectedPrimaryWeapon == "wpn_m4a1_sopmod") SelectedPrimaryWeapon = "wpn_mp5sd_integral";
                else if (SelectedPrimaryWeapon == "wpn_mp5sd_integral") SelectedPrimaryWeapon = "wpn_awm_l115a3";
                else SelectedPrimaryWeapon = "wpn_m4a1_sopmod";
                RefreshLoadoutDisplay();
            });

            CreateActionButton(loadoutBar.transform, "BtnCycleSidearm", "CYCLE SIDEARM", new Vector2(0.84f, 0.15f), new Vector2(0.98f, 0.85f), uiFont, () =>
            {
                SelectedSidearm = (SelectedSidearm == "wpn_usp45_suppressed") ? "wpn_m9_beretta" : "wpn_usp45_suppressed";
                RefreshLoadoutDisplay();
            });

            for (int i = 0; i < Missions.Length; i++)
            {
                int col = i / 5;
                int row = i % 5;
                float xMin = 0.04f + col * 0.47f;
                float xMax = xMin + 0.45f;
                float yMax = 0.77f - row * 0.145f;
                float yMin = yMax - 0.13f;

                MissionSelectEntry entry = Missions[i];
                GameObject card = CreatePanel(bg.transform, "MissionCard_" + entry.sceneId, new Vector2(xMin, yMin), new Vector2(xMax, yMax), new Color(0.11f, 0.16f, 0.20f, 0.96f));

                CreateLabel(card.transform, "MissionTitle", entry.title,
                    new Vector2(0.03f, 0.56f), new Vector2(0.73f, 0.94f), uiFont, 22, TextAnchor.MiddleLeft, Color.white);
                CreateLabel(card.transform, "MissionBiome", entry.biomeAndTime + "  •  " + entry.dimensionsAndRoster,
                    new Vector2(0.03f, 0.08f), new Vector2(0.73f, 0.54f), uiFont, 16, TextAnchor.MiddleLeft, new Color(0.68f, 0.78f, 0.82f, 1f));

                string sceneToLoad = entry.sceneId;
                CreateActionButton(card.transform, "BtnDeploy_" + entry.sceneId, "DEPLOY " + entry.sceneId, new Vector2(0.75f, 0.18f), new Vector2(0.97f, 0.82f), uiFont, () =>
                {
                    SceneManager.LoadScene(sceneToLoad);
                });
            }
        }

        private void ShowMainMenuSettings()
        {
            if (_settingsPanel != null) { Destroy(_settingsPanel); _settingsPanel = null; return; }
            Canvas canvas = FindObjectOfType<Canvas>();
            if (canvas == null) return;
            Font font = Resources.GetBuiltinResource<Font>("Arial.ttf");
            _settingsPanel = CreatePanel(canvas.transform, "FieldSettingsPanel", new Vector2(0.25f, 0.16f), new Vector2(0.75f, 0.84f), new Color(0.025f, 0.045f, 0.05f, 0.98f));
            CreateLabel(_settingsPanel.transform, "SettingsTitle", "FIELD SETTINGS", new Vector2(0.06f, 0.83f), new Vector2(0.94f, 0.96f), font, 30, TextAnchor.MiddleCenter, Color.white);
            CreateLabel(_settingsPanel.transform, "AudioLabel", "MASTER AUDIO", new Vector2(0.08f, 0.68f), new Vector2(0.48f, 0.78f), font, 19, TextAnchor.MiddleLeft, Color.white);
            CreateActionButton(_settingsPanel.transform, "AudioDown", "−", new Vector2(0.54f, 0.68f), new Vector2(0.65f, 0.78f), font, () => { AudioListener.volume = Mathf.Clamp01(AudioListener.volume - 0.1f); });
            CreateActionButton(_settingsPanel.transform, "AudioUp", "+", new Vector2(0.68f, 0.68f), new Vector2(0.79f, 0.78f), font, () => { AudioListener.volume = Mathf.Clamp01(AudioListener.volume + 0.1f); });
            CreateLabel(_settingsPanel.transform, "QualityLabel", "GRAPHICS QUALITY", new Vector2(0.08f, 0.51f), new Vector2(0.48f, 0.61f), font, 19, TextAnchor.MiddleLeft, Color.white);
            CreateActionButton(_settingsPanel.transform, "QualityCycle", "CYCLE QUALITY", new Vector2(0.54f, 0.51f), new Vector2(0.88f, 0.61f), font, () => { QualitySettings.SetQualityLevel((QualitySettings.GetQualityLevel()+1)%QualitySettings.names.Length, true); });
            CreateLabel(_settingsPanel.transform, "SensitivityLabel", "LOOK SENSITIVITY", new Vector2(0.08f, 0.34f), new Vector2(0.48f, 0.44f), font, 19, TextAnchor.MiddleLeft, Color.white);
            CreateActionButton(_settingsPanel.transform, "SensitivityDown", "−", new Vector2(0.54f, 0.34f), new Vector2(0.65f, 0.44f), font, () => { PlayerPrefs.SetFloat("PRL_LookSensitivity", Mathf.Clamp(PlayerPrefs.GetFloat("PRL_LookSensitivity",1f)-0.1f,0.25f,2f)); });
            CreateActionButton(_settingsPanel.transform, "SensitivityUp", "+", new Vector2(0.68f, 0.34f), new Vector2(0.79f, 0.44f), font, () => { PlayerPrefs.SetFloat("PRL_LookSensitivity", Mathf.Clamp(PlayerPrefs.GetFloat("PRL_LookSensitivity",1f)+0.1f,0.25f,2f)); });
            CreateActionButton(_settingsPanel.transform, "SettingsBack", "BACK TO COMMAND", new Vector2(0.25f, 0.10f), new Vector2(0.75f, 0.23f), font, () => { if (_settingsPanel != null) Destroy(_settingsPanel); _settingsPanel = null; });
        }

        private void RefreshLoadoutDisplay()
        {
            if (_loadoutHeaderText != null)
            {
                _loadoutHeaderText.text = $"LOADOUT: Primary [{SelectedPrimaryWeapon}] | Sidearm [{SelectedSidearm}] | Gadgets [{SelectedGadgetKit}]";
            }
        }

        private static GameObject CreatePanel(Transform parent, string name, Vector2 anchorMin, Vector2 anchorMax, Color color)
        {
            GameObject go = new GameObject(name);
            go.transform.SetParent(parent, false);
            RectTransform rt = go.AddComponent<RectTransform>();
            rt.anchorMin = anchorMin;
            rt.anchorMax = anchorMax;
            rt.offsetMin = Vector2.zero;
            rt.offsetMax = Vector2.zero;
            Image img = go.AddComponent<Image>();
            img.color = color;
            return go;
        }

        private static Text CreateLabel(Transform parent, string name, string text, Vector2 anchorMin, Vector2 anchorMax, Font font, int fontSize, TextAnchor alignment, Color color)
        {
            GameObject go = new GameObject(name);
            go.transform.SetParent(parent, false);
            RectTransform rt = go.AddComponent<RectTransform>();
            rt.anchorMin = anchorMin;
            rt.anchorMax = anchorMax;
            rt.offsetMin = Vector2.zero;
            rt.offsetMax = Vector2.zero;
            Text label = go.AddComponent<Text>();
            label.font = font;
            label.text = text;
            label.fontSize = fontSize;
            label.alignment = alignment;
            label.color = color;
            return label;
        }

        private static Button CreateActionButton(Transform parent, string name, string caption, Vector2 anchorMin, Vector2 anchorMax, Font font, UnityEngine.Events.UnityAction onClick)
        {
            GameObject btnPanel = CreatePanel(parent, name, anchorMin, anchorMax, new Color(0.16f, 0.50f, 0.32f, 1f));
            Button btn = btnPanel.AddComponent<Button>();
            btn.onClick.AddListener(onClick);
            CreateLabel(btnPanel.transform, "Caption", caption, Vector2.zero, Vector2.one, font, 18, TextAnchor.MiddleCenter, Color.white);
            return btn;
        }
    }
}
