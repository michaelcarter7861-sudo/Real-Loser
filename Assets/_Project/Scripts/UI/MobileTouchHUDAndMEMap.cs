using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.EventSystems;
using RealLoserStudio.Tactical.Player;
using RealLoserStudio.Tactical.Stealth;
using RealLoserStudio.Tactical.Weapons;
using RealLoserStudio.Tactical.Traps;
using RealLoserStudio.Tactical.AI;
using RealLoserStudio.Tactical.Core;

namespace RealLoserStudio.Tactical.UI
{
    public enum TacticalRouteType
    {
        Silent = 0,     // Low visibility, vents, wire cutters, garrote/suppressed
        Technical = 1,  // Breaker boxes, PDA hacking, camera loops, EMP
        Loud = 2        // Heavy breach, sniper overwatch, C4/RPG
    }

    [Serializable]
    public struct SatelliteMapZone
    {
        public string zoneId;
        public string zoneType; // exterior, interior, cliff_ridge, extraction
        public Rect worldBounds;
    }

    [Serializable]
    public struct TacticalRouteOverlay
    {
        public TacticalRouteType routeType;
        public string routeLabel;
        public List<Vector3> worldWaypoints;
    }

    /// <summary>
    /// Android Landscape Touch HUD & IGI Top-Down Satellite Map (`ME Map`) Controller.
    /// Implements:
    /// - Virtual Joystick (inner walk zone / outer sprint zone) + WASD fallback
    /// - Touch-Drag Look + Scope FOV sensitivity scaling + Mouse Look fallback
    /// - Lean Left / Lean Right (±18°) buttons
    /// - Stance Button (Tap = Crouch, Hold = Prone)
    /// - Fire, ADS Scope, Reload, Switch Weapon, and Context Action Button with radial timer ring
    /// - Live Top-Down IGI Satellite Map (`ME Map`) with zones, tagged enemies, camera cones, and 3 tactical routes
    /// </summary>
    public class MobileTouchHUDAndMEMap : MonoBehaviour
    {
        [Header("Player & System Bindings")]
        public PlayerTacticalController playerController;
        public WeaponAndBallisticsSystem weaponSystem;
        public StealthAndDetectionSystem stealthSystem;
        public MissionObjectiveRuntime objectiveRuntime;

        [Header("Virtual Joystick (Walk / Sprint Zones)")]
        public float joystickDeadZone = 0.12f;
        public float joystickSprintThreshold = 0.78f;
        public Vector2 currentJoystickInput { get; private set; }
        public bool isSprintZoneActive { get; private set; }

        [Header("Touch-Drag Look & Scope Scaling")]
        public float baseTouchSensitivity = 0.18f;
        public float baseFieldOfView = 70.0f;
        public float currentScopeFieldOfView = 70.0f;
        public bool isScopeActive { get; private set; }
        private Vector2 _pendingLookDelta;

        [Header("Stance Button (Tap = Crouch, Hold = Prone)")]
        public float proneHoldThresholdSeconds = 0.28f;
        private float _stancePressTimer;
        private bool _isStanceButtonHeld;
        private bool _proneTriggeredOnHold;

        [Header("Context Action Button & Progress Ring")]
        public bool isContextActionActive { get; private set; }
        public float contextActionProgress01 { get; private set; }
        private float _contextActionRequiredDuration;
        private float _contextActionElapsed;
        private TrapAndHazardSystem _activeTargetTrap;
        private CounterToolType _activeTool = CounterToolType.WireCutters;

        [Header("Live Top-Down IGI Satellite Map (ME Map)")]
        public bool isMEMapOpen;
        public TacticalRouteType highlightedRoute = TacticalRouteType.Silent;
        public List<SatelliteMapZone> mapZones = new List<SatelliteMapZone>();
        public List<TacticalRouteOverlay> tacticalRoutes = new List<TacticalRouteOverlay>(3);
        public readonly List<Transform> taggedEnemies = new List<Transform>();
        public readonly List<TrapAndHazardSystem> trackedCamerasAndSearchlights = new List<TrapAndHazardSystem>();

        // Runtime uGUI Elements
        private Text _statusBannerText;
        private Text _weaponBannerText;
        private GameObject _meMapPanel;
        private RectTransform _meMapPlayerDot;
        private RectTransform _mapTextureRect;
        private int _mapTextureWidth = 1536;
        private int _mapTextureHeight = 1024;
        private bool _mapUsesGeneratedSchematic;
        private sealed class EnemyMapBlip
        {
            public Transform target;
            public RectTransform dot;
        }
        private readonly List<EnemyMapBlip> _enemyMapBlips = new List<EnemyMapBlip>();
        private Vector2 _missionMapDimensions = new Vector2(300f, 300f);
        public Vector2 mapWorldOrigin = Vector2.zero;

        private void Update()
        {
            float dt = Time.deltaTime;
            TickHUD(dt);

            // Desktop/editor fallback for the same action exposed by the touch button.
            if (Input.GetKeyDown(KeyCode.E)) OnContextInteract();

            if (playerController != null)
            {
                Vector2 move = currentJoystickInput;
                bool sprint = isSprintZoneActive;

                // Keyboard fallback for Editor/Desktop testing alongside Android Touch
                float kx = Input.GetAxisRaw("Horizontal");
                float ky = Input.GetAxisRaw("Vertical");
                if (Mathf.Abs(kx) > 0.01f || Mathf.Abs(ky) > 0.01f)
                {
                    move = new Vector2(kx, ky);
                    sprint = Input.GetKey(KeyCode.LeftShift);
                }

                playerController.UpdateMovement(move, _pendingLookDelta, sprint, dt);
                _pendingLookDelta = Vector2.zero;
            }

            UpdateStatusReadout();
            UpdateMEMapDot();
        }

        public void OnVirtualJoystickUpdate(Vector2 rawNormalizedJoystick)
        {
            float mag = rawNormalizedJoystick.magnitude;
            if (mag < joystickDeadZone)
            {
                currentJoystickInput = Vector2.zero;
                isSprintZoneActive = false;
                return;
            }

            isSprintZoneActive = (mag >= joystickSprintThreshold);
            currentJoystickInput = Vector2.ClampMagnitude(rawNormalizedJoystick, 1.0f);
        }

        // Explicit pointer lifecycle hooks prevent a released/cancelled touch from leaving
        // a D-pad direction latched. They are also safe for callers using a real drag joystick.
        public void OnVirtualJoystickPointerDown(Vector2 input) => OnVirtualJoystickUpdate(input);
        public void OnVirtualJoystickPointerUp() => OnVirtualJoystickUpdate(Vector2.zero);
        public void OnVirtualJoystickPointerCancel() => OnVirtualJoystickUpdate(Vector2.zero);

        private void OnDisable()
        {
            OnVirtualJoystickPointerCancel();
        }

        public Vector2 ComputeScaledLookDelta(Vector2 rawTouchPixelDelta)
        {
            float fovScale = Mathf.Clamp(currentScopeFieldOfView / Mathf.Max(baseFieldOfView, 1f), 0.08f, 1.0f);
            return rawTouchPixelDelta * (baseTouchSensitivity * Mathf.Clamp(PlayerPrefs.GetFloat("PRL_LookSensitivity", 1f), 0.25f, 2f) * fovScale);
        }

        public void OnLeanButtonInput(float leanDirection)
        {
            if (playerController != null)
            {
                playerController.SetLeanInput(leanDirection);
            }
        }

        public void OnStanceButtonDown()
        {
            _isStanceButtonHeld = true;
            _stancePressTimer = 0f;
            _proneTriggeredOnHold = false;
        }

        public void OnStanceButtonUp()
        {
            if (!_isStanceButtonHeld) return;
            _isStanceButtonHeld = false;

            if (!_proneTriggeredOnHold && playerController != null)
            {
                PlayerPosture next = (playerController.CurrentPosture == PlayerPosture.Crouch)
                    ? PlayerPosture.Stand
                    : PlayerPosture.Crouch;
                playerController.SetPosture(next);
            }
        }

        public void OnFireButtonPressed()
        {
            if (weaponSystem == null || playerController == null) return;
            Transform camT = playerController.firstPersonCamera != null
                ? playerController.firstPersonCamera.transform
                : playerController.transform;

            // WeaponSystem owns ammo, cadence, raycast and authoritative damage. The HUD only
            // requests a shot and plays presentation effects after the request succeeds.
            bool fired = weaponSystem.TryFireActiveWeapon(camT.position + camT.forward * 0.4f, camT.forward, out _);
            if (!fired) return;

            var def = weaponSystem.ActiveWeapon;
            string sfx = def.isSuppressed ? "sfx_wpn_pistol_suppressed" : "sfx_wpn_rifle_fire";
            AudioClip clip = RuntimeGLBAndMeshLoader.LoadWavAudioClip(sfx);
            if (clip != null)
            {
                AudioSource.PlayClipAtPoint(clip, camT.position, 0.85f);
            }
        }

        public void OnScopeButtonToggle()
        {
            isScopeActive = !isScopeActive;
            currentScopeFieldOfView = isScopeActive ? 24.0f : baseFieldOfView;
            if (playerController != null && playerController.firstPersonCamera != null)
            {
                playerController.firstPersonCamera.fieldOfView = currentScopeFieldOfView;
            }
        }

        public void OnCycleWeaponButton()
        {
            if (weaponSystem == null) return;
            weaponSystem.activeWeaponIndex = (weaponSystem.activeWeaponIndex + 1) % WeaponAndBallisticsSystem.All26Weapons.Length;
        }

        public void OnContextInteractNearestTrap()
        {
            if (playerController == null) return;
            TrapAndHazardSystem[] allTraps = FindObjectsOfType<TrapAndHazardSystem>();
            TrapAndHazardSystem nearest = null;
            float bestDist = 4.5f;
            for (int i = 0; i < allTraps.Length; i++)
            {
                if (!allTraps[i].isArmed || allTraps[i].isDestroyed) continue;
                float d = Vector3.Distance(playerController.transform.position, allTraps[i].transform.position);
                if (d < bestDist)
                {
                    bestDist = d;
                    nearest = allTraps[i];
                }
            }

            // Never flip isArmed directly from a button. BeginContextAction validates the
            // selected tool and posture, then TickHUD supplies the required interaction time.
            if (nearest != null) BeginContextAction(nearest, _activeTool);
        }

        /// <summary>Attempts a mission objective/extraction interaction, then falls back to trap disarm.</summary>
        public void OnContextInteract()
        {
            if (objectiveRuntime != null && objectiveRuntime.TryInteract()) return;
            OnContextInteractNearestTrap();
        }

        public void BindObjectiveRuntime(MissionObjectiveRuntime runtime)
        {
            objectiveRuntime = runtime;
        }

        public void BeginContextAction(TrapAndHazardSystem trap, CounterToolType tool)
        {
            if (trap == null || playerController == null) return;
            float duration = trap.GetCounterInteractionDuration(tool, playerController.CurrentPosture);
            if (duration < 0f) return;

            _activeTargetTrap = trap;
            _activeTool = tool;
            _contextActionRequiredDuration = Mathf.Max(duration, 0.05f);
            _contextActionElapsed = 0f;
            isContextActionActive = true;
            contextActionProgress01 = 0f;
        }

        public void CancelContextAction()
        {
            isContextActionActive = false;
            contextActionProgress01 = 0f;
            _activeTargetTrap = null;
        }

        public void ToggleMEMap()
        {
            isMEMapOpen = !isMEMapOpen;
            if (_meMapPanel != null)
            {
                _meMapPanel.SetActive(isMEMapOpen);
            }
        }

        public void SelectTacticalRoute(TacticalRouteType route)
        {
            highlightedRoute = route;
        }

        public void TickHUD(float deltaTime)
        {
            if (_isStanceButtonHeld)
            {
                _stancePressTimer += deltaTime;
                if (!_proneTriggeredOnHold && _stancePressTimer >= proneHoldThresholdSeconds && playerController != null)
                {
                    _proneTriggeredOnHold = true;
                    PlayerPosture next = (playerController.CurrentPosture == PlayerPosture.Prone)
                        ? PlayerPosture.Stand
                        : PlayerPosture.Prone;
                    playerController.SetPosture(next);
                }
            }

            if (isContextActionActive && _activeTargetTrap != null)
            {
                if (playerController == null || !_activeTargetTrap.IsCurrentlyActive ||
                    Vector3.Distance(playerController.transform.position, _activeTargetTrap.transform.position) > 4.5f)
                {
                    CancelContextAction();
                    return;
                }
                _contextActionElapsed += deltaTime;
                contextActionProgress01 = Mathf.Clamp01(_contextActionElapsed / _contextActionRequiredDuration);
                if (contextActionProgress01 >= 1.0f)
                {
                    _activeTargetTrap.ApplyCountermeasure(_activeTool, playerController);
                    CancelContextAction();
                }
            }
        }

        /// <summary>
        /// Programmatically builds the complete Android landscape touch HUD & Satellite ME Map overlay.
        /// </summary>
        public void BuildCompleteMobileTouchControls(string missionId, string missionTitle, Vector2 mapSize)
        {
            _missionMapDimensions = new Vector2(Mathf.Max(100f, mapSize.x), Mathf.Max(100f, mapSize.y));
            Font font = Resources.GetBuiltinResource<Font>("Arial.ttf");

            // 1. Top Tactical Status Bar
            GameObject topBar = CreateHUDPanel(transform, "TopStatusBar", new Vector2(0.02f, 0.91f), new Vector2(0.98f, 0.98f), new Color(0.05f, 0.08f, 0.10f, 0.82f));
            _statusBannerText = CreateHUDText(topBar.transform, "StatusText",
                $"{missionId}: {missionTitle} | ALERT: 0 (UNAWARE) | POSTURE: STAND",
                new Vector2(0.02f, 0.1f), new Vector2(0.58f, 0.9f), font, 20, TextAnchor.MiddleLeft, new Color(0.72f, 0.96f, 0.78f));
            _weaponBannerText = CreateHUDText(topBar.transform, "WeaponText",
                "WEAPON: USP .45 Suppressed",
                new Vector2(0.60f, 0.1f), new Vector2(0.84f, 0.9f), font, 20, TextAnchor.MiddleRight, new Color(0.90f, 0.92f, 0.78f));

            CreateHUDButton(topBar.transform, "BtnMEMap", "ME SATELLITE MAP", new Vector2(0.86f, 0.12f), new Vector2(0.99f, 0.88f), font, new Color(0.14f, 0.42f, 0.56f, 0.95f), () =>
            {
                ToggleMEMap();
            });

            // 2. Center Crosshair
            GameObject crosshair = CreateHUDPanel(transform, "Crosshair", new Vector2(0.497f, 0.494f), new Vector2(0.503f, 0.506f), new Color(0.25f, 0.95f, 0.45f, 0.85f));

            // 3. Left Virtual Joystick Pad (D-Pad + Drag Stick)
            GameObject joyPad = CreateHUDPanel(transform, "VirtualJoystickPad", new Vector2(0.03f, 0.06f), new Vector2(0.23f, 0.42f), new Color(0.10f, 0.14f, 0.16f, 0.55f));
            CreateJoystickButton(joyPad.transform, "MoveFwd", "FWD", new Vector2(0.34f, 0.66f), new Vector2(0.66f, 0.96f), font, new Color(0.2f, 0.3f, 0.25f, 0.8f), new Vector2(0f, 1f));
            CreateJoystickButton(joyPad.transform, "MoveBack", "BACK", new Vector2(0.34f, 0.04f), new Vector2(0.66f, 0.34f), font, new Color(0.2f, 0.3f, 0.25f, 0.8f), new Vector2(0f, -0.7f));
            CreateJoystickButton(joyPad.transform, "MoveLeft", "LEFT", new Vector2(0.04f, 0.35f), new Vector2(0.33f, 0.65f), font, new Color(0.2f, 0.3f, 0.25f, 0.8f), new Vector2(-0.75f, 0f));
            CreateJoystickButton(joyPad.transform, "MoveRight", "RIGHT", new Vector2(0.67f, 0.35f), new Vector2(0.96f, 0.65f), font, new Color(0.2f, 0.3f, 0.25f, 0.8f), new Vector2(0.75f, 0f));
            CreateJoystickButton(joyPad.transform, "MoveStop", "STOP", new Vector2(0.35f, 0.36f), new Vector2(0.65f, 0.64f), font, new Color(0.35f, 0.22f, 0.22f, 0.8f), Vector2.zero);

            // 4. Right Touch Look Pad & Action Buttons
            GameObject lookPad = CreateHUDPanel(transform, "TouchLookZone", new Vector2(0.52f, 0.28f), new Vector2(0.96f, 0.86f), new Color(0f, 0f, 0f, 0.02f));
            EventTrigger lookTrig = lookPad.AddComponent<EventTrigger>();
            EventTrigger.Entry dragEntry = new EventTrigger.Entry { eventID = EventTriggerType.Drag };
            dragEntry.callback.AddListener((data) =>
            {
                PointerEventData ped = (PointerEventData)data;
                _pendingLookDelta += ComputeScaledLookDelta(ped.delta);
            });
            lookTrig.triggers.Add(dragEntry);

            // Tactical Action Cluster (Right Side)
            CreateHUDButton(transform, "BtnFire", "FIRE", new Vector2(0.84f, 0.08f), new Vector2(0.96f, 0.24f), font, new Color(0.72f, 0.18f, 0.16f, 0.90f), OnFireButtonPressed);
            CreateHUDButton(transform, "BtnScope", "SCOPE", new Vector2(0.71f, 0.08f), new Vector2(0.82f, 0.20f), font, new Color(0.18f, 0.42f, 0.52f, 0.88f), OnScopeButtonToggle);
            CreateHUDButton(transform, "BtnCrouch", "CROUCH", new Vector2(0.58f, 0.08f), new Vector2(0.69f, 0.20f), font, new Color(0.22f, 0.36f, 0.28f, 0.88f), () =>
            {
                if (playerController != null)
                {
                    playerController.SetPosture(playerController.CurrentPosture == PlayerPosture.Crouch ? PlayerPosture.Stand : PlayerPosture.Crouch);
                }
            });
            CreateHUDButton(transform, "BtnProne", "PRONE", new Vector2(0.45f, 0.08f), new Vector2(0.56f, 0.20f), font, new Color(0.22f, 0.32f, 0.42f, 0.88f), () =>
            {
                if (playerController != null)
                {
                    playerController.SetPosture(playerController.CurrentPosture == PlayerPosture.Prone ? PlayerPosture.Stand : PlayerPosture.Prone);
                }
            });
            CreateHUDButton(transform, "BtnLeanL", "LEAN L", new Vector2(0.26f, 0.22f), new Vector2(0.35f, 0.32f), font, new Color(0.26f, 0.28f, 0.32f, 0.85f), () => OnLeanButtonInput(-1f));
            CreateHUDButton(transform, "BtnLeanC", "CENTER", new Vector2(0.36f, 0.22f), new Vector2(0.44f, 0.32f), font, new Color(0.26f, 0.28f, 0.32f, 0.85f), () => OnLeanButtonInput(0f));
            CreateHUDButton(transform, "BtnLeanR", "LEAN R", new Vector2(0.45f, 0.22f), new Vector2(0.54f, 0.32f), font, new Color(0.26f, 0.28f, 0.32f, 0.85f), () => OnLeanButtonInput(1f));
            CreateHUDButton(transform, "BtnDisarm", "INTERACT / DISARM", new Vector2(0.26f, 0.08f), new Vector2(0.43f, 0.20f), font, new Color(0.62f, 0.46f, 0.14f, 0.90f), OnContextInteract);
            CreateHUDButton(transform, "BtnSwitchWpn", "NEXT WPN", new Vector2(0.84f, 0.26f), new Vector2(0.96f, 0.36f), font, new Color(0.28f, 0.36f, 0.24f, 0.88f), OnCycleWeaponButton);

            // 5. Top-Down Satellite ME Map Modal Overlay
            _meMapPanel = CreateHUDPanel(transform, "MESatelliteMapOverlay", new Vector2(0.18f, 0.16f), new Vector2(0.82f, 0.88f), new Color(0.04f, 0.10f, 0.08f, 0.94f));
            CreateHUDText(_meMapPanel.transform, "MapTitle",
                $"TACTICAL RECON MAP ({missionId} — {_missionMapDimensions.x:0}m x {_missionMapDimensions.y:0}m)",
                new Vector2(0.03f, 0.90f), new Vector2(0.97f, 0.98f), font, 22, TextAnchor.MiddleLeft, new Color(0.45f, 0.98f, 0.62f));

            GameObject mapArea = CreateHUDPanel(_meMapPanel.transform, "MissionMapArea", new Vector2(0.03f, 0.12f), new Vector2(0.97f, 0.88f), new Color(0.03f, 0.06f, 0.05f, 0.98f));
            GameObject mapImageObj = new GameObject("MissionMapTexture");
            mapImageObj.transform.SetParent(mapArea.transform, false);
            RectTransform mapImageRect = mapImageObj.AddComponent<RectTransform>();
            mapImageRect.anchorMin = Vector2.zero;
            mapImageRect.anchorMax = Vector2.one;
            mapImageRect.offsetMin = Vector2.zero;
            mapImageRect.offsetMax = Vector2.zero;
            RawImage mapImage = mapImageObj.AddComponent<RawImage>();
            mapImage.raycastTarget = false;
            Texture2D missionMap = Resources.Load<Texture2D>("MissionMaps/" + missionId);
            if (missionMap != null)
            {
                mapImage.texture = missionMap;
                _mapTextureWidth = missionMap.width;
                _mapTextureHeight = missionMap.height;
                _mapUsesGeneratedSchematic = true;
            }
            AspectRatioFitter aspect = mapImageObj.AddComponent<AspectRatioFitter>();
            aspect.aspectMode = AspectRatioFitter.AspectMode.FitInParent;
            aspect.aspectRatio = missionMap != null ? (float)missionMap.width / Mathf.Max(1, missionMap.height) : 1.5f;
            _mapTextureRect = mapImageRect;

            GameObject playerDotObj = new GameObject("PlayerMapBlip");
            playerDotObj.transform.SetParent(_mapTextureRect, false);
            RectTransform playerDotRect = playerDotObj.AddComponent<RectTransform>();
            playerDotRect.anchorMin = new Vector2(0.5f, 0.5f);
            playerDotRect.anchorMax = new Vector2(0.5f, 0.5f);
            playerDotRect.sizeDelta = new Vector2(18f, 18f);
            Image playerDotImage = playerDotObj.AddComponent<Image>();
            playerDotImage.color = new Color(0.2f, 1.0f, 0.4f, 1f);
            playerDotImage.raycastTarget = false;
            _meMapPlayerDot = playerDotObj.GetComponent<RectTransform>();
            _meMapPanel.SetActive(false);
        }

        public void ConfigureMissionMapEnemies(List<EnemyAIFSMSystem> enemies)
        {
            for (int i = 0; i < _enemyMapBlips.Count; i++)
            {
                if (_enemyMapBlips[i].dot != null) Destroy(_enemyMapBlips[i].dot.gameObject);
            }
            _enemyMapBlips.Clear();
            taggedEnemies.Clear();
            if (_mapTextureRect == null || enemies == null) return;

            for (int i = 0; i < enemies.Count; i++)
            {
                EnemyAIFSMSystem enemy = enemies[i];
                if (enemy == null) continue;
                GameObject dotObject = new GameObject("EnemyMapBlip_" + i);
                dotObject.transform.SetParent(_mapTextureRect, false);
                RectTransform dotRect = dotObject.AddComponent<RectTransform>();
                dotRect.anchorMin = new Vector2(0.5f, 0.5f);
                dotRect.anchorMax = new Vector2(0.5f, 0.5f);
                dotRect.sizeDelta = new Vector2(9f, 9f);
                Image dotImage = dotObject.AddComponent<Image>();
                dotImage.color = new Color(0.96f, 0.20f, 0.16f, 0.95f);
                dotImage.raycastTarget = false;
                _enemyMapBlips.Add(new EnemyMapBlip { target = enemy.transform, dot = dotRect });
                taggedEnemies.Add(enemy.transform);
            }
        }

        private void UpdateStatusReadout()
        {
            if (_statusBannerText != null && playerController != null)
            {
                string alertStr = stealthSystem != null ? stealthSystem.currentAlertLevel.ToString() : "Alert0_Unaware";
                string objectiveStr = objectiveRuntime != null ? objectiveRuntime.GetHudSummary() : "OBJECTIVES: unavailable";
                _statusBannerText.text = $"POS: ({playerController.transform.position.x:0}, {playerController.transform.position.z:0}) | ALERT: {alertStr} | POSTURE: {playerController.CurrentPosture} | {objectiveStr}";
            }
            if (_weaponBannerText != null && weaponSystem != null)
            {
                _weaponBannerText.text = $"WPN: {weaponSystem.ActiveWeapon.displayName}";
            }
        }

        private void UpdateMEMapDot()
        {
            if (!isMEMapOpen || _meMapPlayerDot == null || playerController == null) return;
            SetMapDotAnchor(_meMapPlayerDot, WorldToMapAnchor(playerController.transform.position));
            for (int i = 0; i < _enemyMapBlips.Count; i++)
            {
                EnemyMapBlip blip = _enemyMapBlips[i];
                if (blip.target == null || blip.dot == null)
                {
                    if (blip.dot != null) blip.dot.gameObject.SetActive(false);
                    continue;
                }
                bool visible = blip.target.gameObject.activeInHierarchy;
                if (blip.dot.gameObject.activeSelf != visible) blip.dot.gameObject.SetActive(visible);
                if (visible) SetMapDotAnchor(blip.dot, WorldToMapAnchor(blip.target.position));
            }
        }

        private Vector2 WorldToMapAnchor(Vector3 worldPosition)
        {
            float nx = Mathf.Clamp01((worldPosition.x - mapWorldOrigin.x) / Mathf.Max(1f, _missionMapDimensions.x));
            float nz = Mathf.Clamp01((worldPosition.z - mapWorldOrigin.y) / Mathf.Max(1f, _missionMapDimensions.y));
            if (!_mapUsesGeneratedSchematic) return new Vector2(nx, nz);

            // These extents match tools/build_mission_maps.py's drawable world rectangle.
            const float leftPx = 72f;
            const float topPx = 64f;
            const float rightPx = 1464f;
            const float bottomPx = 862f;
            float left = leftPx / _mapTextureWidth;
            float top = topPx / _mapTextureHeight;
            float mapWidth = (rightPx - leftPx) / _mapTextureWidth;
            float mapHeight = (bottomPx - topPx) / _mapTextureHeight;
            float scale = Mathf.Min(mapWidth / Mathf.Max(1f, _missionMapDimensions.x), mapHeight / Mathf.Max(1f, _missionMapDimensions.y));
            float worldWidth = _missionMapDimensions.x * scale;
            float worldHeight = _missionMapDimensions.y * scale;
            float x = left + (mapWidth - worldWidth) * 0.5f + nx * worldWidth;
            float yFromTop = top + (mapHeight - worldHeight) * 0.5f + (1f - nz) * worldHeight;
            return new Vector2(Mathf.Clamp01(x), Mathf.Clamp01(1f - yFromTop));
        }

        private static void SetMapDotAnchor(RectTransform dot, Vector2 anchor)
        {
            if (dot == null) return;
            dot.anchorMin = anchor;
            dot.anchorMax = anchor;
            dot.anchoredPosition = Vector2.zero;
        }

        private static GameObject CreateHUDPanel(Transform parent, string name, Vector2 min, Vector2 max, Color col)
        {
            GameObject go = new GameObject(name);
            go.transform.SetParent(parent, false);
            RectTransform rt = go.AddComponent<RectTransform>();
            rt.anchorMin = min;
            rt.anchorMax = max;
            rt.offsetMin = Vector2.zero;
            rt.offsetMax = Vector2.zero;
            Image img = go.AddComponent<Image>();
            img.color = col;
            return go;
        }

        private static Text CreateHUDText(Transform parent, string name, string text, Vector2 min, Vector2 max, Font font, int size, TextAnchor align, Color col)
        {
            GameObject go = new GameObject(name);
            go.transform.SetParent(parent, false);
            RectTransform rt = go.AddComponent<RectTransform>();
            rt.anchorMin = min;
            rt.anchorMax = max;
            rt.offsetMin = Vector2.zero;
            rt.offsetMax = Vector2.zero;
            Text t = go.AddComponent<Text>();
            t.font = font;
            t.text = text;
            t.fontSize = size;
            t.alignment = align;
            t.color = col;
            return t;
        }

        private Button CreateJoystickButton(Transform parent, string name, string label, Vector2 min, Vector2 max, Font font, Color bgCol, Vector2 input)
        {
            Button button = CreateHUDButton(parent, name, label, min, max, font, bgCol, () => { });
            EventTrigger trigger = button.gameObject.AddComponent<EventTrigger>();
            AddPointerEntry(trigger, EventTriggerType.PointerDown, () => OnVirtualJoystickPointerDown(input));
            AddPointerEntry(trigger, EventTriggerType.PointerUp, OnVirtualJoystickPointerUp);
            AddPointerEntry(trigger, EventTriggerType.PointerExit, OnVirtualJoystickPointerCancel);
            AddPointerEntry(trigger, EventTriggerType.PointerCancel, OnVirtualJoystickPointerCancel);
            return button;
        }

        private static void AddPointerEntry(EventTrigger trigger, EventTriggerType eventType, UnityEngine.Events.UnityAction action)
        {
            EventTrigger.Entry entry = new EventTrigger.Entry { eventID = eventType };
            entry.callback.AddListener((data) => action());
            trigger.triggers.Add(entry);
        }

        private static Button CreateHUDButton(Transform parent, string name, string label, Vector2 min, Vector2 max, Font font, Color bgCol, UnityEngine.Events.UnityAction onClick)
        {
            GameObject p = CreateHUDPanel(parent, name, min, max, bgCol);
            Button b = p.AddComponent<Button>();
            b.onClick.AddListener(onClick);
            CreateHUDText(p.transform, "Lbl", label, Vector2.zero, Vector2.one, font, 16, TextAnchor.MiddleCenter, Color.white);
            return b;
        }
    }
}
