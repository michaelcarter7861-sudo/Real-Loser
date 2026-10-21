using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.SceneManagement;
using RealLoserStudio.Tactical.Player;
using RealLoserStudio.Tactical.Stealth;
using RealLoserStudio.Tactical.Traps;
using RealLoserStudio.Tactical.AI;
using RealLoserStudio.Tactical.UI;
using RealLoserStudio.Tactical.Streaming;

namespace RealLoserStudio.Tactical.Core
{
    /// <summary>
    /// Full Runtime Scene Installer & Objective Evaluator for Mission M03 ("Radio Silence").
    /// Automatically invokes `RuntimeMissionSpawner` on `Awake()` to parse `StreamingAssets/Missions/M03.json`
    /// and instantiate all structures, walls, props, cover, traps (`T1`–`T16`), cameras, enemies (`E1`–`E14`),
    /// first-person weapon viewmodels, and the Android Mobile Touch HUD & Satellite ME Map.
    /// Evaluates Primary Objective O1, Secondary Objectives S1 & S2, and Extraction in real time.
    /// </summary>
    public class M03_RadioSilenceSceneInstaller : MonoBehaviour
    {
        [Header("Mission M03 Blueprint & Spawner")]
        public string missionId = "M03";
        public string missionJsonPath = "Assets/_Project/Missions/M03.json";
        public bool enforceStrictExclusions = true;
        public RuntimeMissionSpawner runtimeSpawner;

        [Header("Runtime System Bindings")]
        public PlayerTacticalController playerController;
        public StealthAndDetectionSystem stealthSystem;
        public MissionEventAndStreamingSystem streamingSystem;
        public MobileTouchHUDAndMEMap touchHudMap;

        [Header("Mission M03 Coordinates & Objective State")]
        public Vector3 playerSpawnPoint = new Vector3(350.0f, 0.0f, 10.0f);
        public Vector3 primaryObjectiveO1Point = new Vector3(370.0f, 0.0f, 600.0f);
        public Vector3 secondaryObjectiveS1Point = new Vector3(190.0f, 0.0f, 380.0f);
        public Vector3 extractionPoint = new Vector3(640.0f, 0.0f, 40.0f);
        public float interactionRadiusMeters = 6.5f;
        public float extractionRadiusMeters = 10.0f;

        public bool primaryObjectiveO1Complete;
        public bool secondaryObjectiveS1Complete;
        public bool secondaryObjectiveS2Complete;
        public bool ghostMedalEligible = true;
        public bool missionExtractedAndWon;
        public string unlockedWeaponReward = "Kestrel-9";
        public float missionElapsedSeconds;

        private void Awake()
        {
            runtimeSpawner = GetComponent<RuntimeMissionSpawner>();
            if (runtimeSpawner == null)
            {
                runtimeSpawner = gameObject.AddComponent<RuntimeMissionSpawner>();
            }
            runtimeSpawner.LoadAndSpawnMission(missionId, BindRuntimeMission);
        }

        private void BindRuntimeMission(RuntimeMissionSpawner spawner)
        {
            playerController = spawner.spawnedPlayer;
            stealthSystem = spawner.stealthSystem;
            streamingSystem = spawner.streamingSystem;
            touchHudMap = spawner.touchHud;
            // JSON objectives are authoritative; serialized inspector coordinates remain the fallback.
            Vector3 parsedObjectivePosition;
            if (spawner.TryGetPlayerStartPosition(out parsedObjectivePosition))
            {
                playerSpawnPoint = parsedObjectivePosition;
            }
            if (spawner.TryGetPrimaryObjectivePosition(out parsedObjectivePosition))
            {
                primaryObjectiveO1Point = parsedObjectivePosition;
            }
            if (spawner.TryGetSecondaryObjectivePosition(out parsedObjectivePosition))
            {
                secondaryObjectiveS1Point = parsedObjectivePosition;
            }
            float parsedExtractionRadius;
            if (spawner.TryGetExtractionPosition(out parsedObjectivePosition, out parsedExtractionRadius))
            {
                extractionPoint = parsedObjectivePosition;
                extractionRadiusMeters = parsedExtractionRadius;
            }
            if (playerController != null) playerController.enableZipLinesInMission = true;
            if (stealthSystem != null) stealthSystem.OnAlertLevelChanged += HandleAlertLevelChanged;
        }

        private void OnDestroy()
        {
            if (stealthSystem != null)
            {
                stealthSystem.OnAlertLevelChanged -= HandleAlertLevelChanged;
            }
        }

        private void Update()
        {
            if (missionExtractedAndWon || playerController == null) return;

            missionElapsedSeconds += Time.deltaTime;
            Vector3 pPos = playerController.transform.position;

            // 1. Evaluate Primary Objective O1 Proximity / Completion
            if (!primaryObjectiveO1Complete)
            {
                float distO1 = Vector2.Distance(new Vector2(pPos.x, pPos.z), new Vector2(primaryObjectiveO1Point.x, primaryObjectiveO1Point.z));
                if (distO1 <= interactionRadiusMeters)
                {
                    CompletePrimaryObjectiveO1();
                }
            }

            // 2. Evaluate Secondary Objective S1 Proximity / Completion
            if (!secondaryObjectiveS1Complete)
            {
                float distS1 = Vector2.Distance(new Vector2(pPos.x, pPos.z), new Vector2(secondaryObjectiveS1Point.x, secondaryObjectiveS1Point.z));
                if (distS1 <= interactionRadiusMeters)
                {
                    CompleteSecondaryObjectiveS1();
                }
            }

            // 3. Evaluate Extraction Point once O1 is complete
            if (primaryObjectiveO1Complete && !missionExtractedAndWon)
            {
                float distExt = Vector2.Distance(new Vector2(pPos.x, pPos.z), new Vector2(extractionPoint.x, extractionPoint.z));
                if (distExt <= extractionRadiusMeters)
                {
                    TriggerMissionExtraction();
                }
            }
        }

        private void HandleAlertLevelChanged(CompoundAlertLevel newLevel)
        {
            if (newLevel >= CompoundAlertLevel.Alert2_CompoundAlarm)
            {
                ghostMedalEligible = false;
            }
        }

        public void CompletePrimaryObjectiveO1()
        {
            if (primaryObjectiveO1Complete) return;
            primaryObjectiveO1Complete = true;
            AudioClip cue = RuntimeGLBAndMeshLoader.LoadWavAudioClip("sfx_gadget_pda_hack_complete");
            if (cue != null && playerController != null)
            {
                AudioSource.PlayClipAtPoint(cue, playerController.transform.position, 0.9f);
            }
            Debug.Log($"[M03_RadioSilenceSceneInstaller] Primary Objective O1 COMPLETE! Extraction unlocked at {extractionPoint}.");
        }

        public void CompleteSecondaryObjectiveS1()
        {
            if (secondaryObjectiveS1Complete) return;
            secondaryObjectiveS1Complete = true;

            TrapAndHazardSystem cam = runtimeSpawner != null ? runtimeSpawner.GetTrapById("M03_CAM_01") : null;
            if (cam != null)
            {
                cam.isArmed = false;
            }
            Debug.Log($"[M03_RadioSilenceSceneInstaller] Secondary Objective S1 COMPLETE!");
        }

        public void TriggerMissionExtraction()
        {
            if (!primaryObjectiveO1Complete || missionExtractedAndWon) return;
            missionExtractedAndWon = true;
            secondaryObjectiveS2Complete = ghostMedalEligible;

            MissionSaveData save = new MissionSaveData
            {
                missionId = missionId,
                alertLevel = stealthSystem != null ? (int)stealthSystem.currentAlertLevel : 0,
                playerHealth = 100f,
                playerPosition = playerController != null ? playerController.transform.position : extractionPoint,
                playerPosture = playerController != null ? (int)playerController.CurrentPosture : 0,
                completedObjectives = new List<string> { "O1" }
            };
            if (secondaryObjectiveS1Complete) save.completedObjectives.Add("S1");
            if (secondaryObjectiveS2Complete) save.completedObjectives.Add("S2_GhostMedal");

            string savePath = System.IO.Path.Combine(Application.persistentDataPath, missionId + "_completed.json");
            MissionEventAndStreamingSystem.SaveCheckpoint(save, savePath);
            Debug.Log($"[M03_RadioSilenceSceneInstaller] MISSION M03 ('Radio Silence') EXTRACTED! Reward Unlocked: {unlockedWeaponReward} | Ghost Medal: {ghostMedalEligible}");
        }
    }
}
