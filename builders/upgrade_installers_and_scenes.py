#!/usr/bin/env python3
from pathlib import Path
"""
Upgrades all 10 Mission Scene Installers (M01..M10), generates full Unity 2022.3 YAML scenes
(Boot.unity, MainMenu.unity, M01.unity..M10.unity), generate .meta files with deterministic GUIDs,
and populates Assets/StreamingAssets/ with all M01-M10.json, 80 .glb models, and 34 .wav audio files.
"""

import os
import shutil

ROOT_DIR = str(Path(__file__).resolve().parents[1])

MISSION_INSTALLER_CONFIGS = [
    {
        "id": "M01",
        "class_name": "M01_BootCampSceneInstaller",
        "title": "Boot Camp",
        "start_pos": "(20.0f, 0.0f, 10.0f)",
        "o1_pos": "(220.0f, 0.0f, 230.0f)",
        "s1_pos": "(222.0f, 0.0f, 52.0f)",
        "ext_pos": "(150.0f, 0.0f, 295.0f)",
        "enable_ziplines": "false",
        "reward_name": "P-9 Compact",
        "script_guid": "a1b2c3d4e5f60718293a4b5c6d7e8f01",
    },
    {
        "id": "M02",
        "class_name": "M02_DisavowedSceneInstaller",
        "title": "Disavowed",
        "start_pos": "(700.0f, 0.0f, 15.0f)",
        "o1_pos": "(450.0f, 0.0f, 490.0f)",
        "s1_pos": "(235.0f, 0.0f, 185.0f)",
        "ext_pos": "(40.0f, 0.0f, 320.0f)",
        "enable_ziplines": "true",
        "reward_name": "MP-9 Whisper",
        "script_guid": "a1b2c3d4e5f60718293a4b5c6d7e8f02",
    },
    {
        "id": "M03",
        "class_name": "M03_RadioSilenceSceneInstaller",
        "title": "Radio Silence",
        "start_pos": "(350.0f, 0.0f, 10.0f)",
        "o1_pos": "(370.0f, 0.0f, 600.0f)",
        "s1_pos": "(190.0f, 0.0f, 380.0f)",
        "ext_pos": "(640.0f, 0.0f, 40.0f)",
        "enable_ziplines": "true",
        "reward_name": "Kestrel-9",
        "script_guid": "a1b2c3d4e5f60718293a4b5c6d7e8f03",
    },
    {
        "id": "M04",
        "class_name": "M04_WarehouseSceneInstaller",
        "title": "The Warehouse",
        "start_pos": "(30.0f, 0.0f, 20.0f)",
        "o1_pos": "(190.0f, 0.0f, 290.0f)",
        "s1_pos": "(420.0f, 0.0f, 150.0f)",
        "ext_pos": "(470.0f, 0.0f, 380.0f)",
        "enable_ziplines": "true",
        "reward_name": "AR-9 Carbine",
        "script_guid": "a1b2c3d4e5f60718293a4b5c6d7e8f04",
    },
    {
        "id": "M05",
        "class_name": "M05_BridgeCrossingSceneInstaller",
        "title": "Bridge Crossing",
        "start_pos": "(40.0f, 0.0f, 175.0f)",
        "o1_pos": "(600.0f, 0.0f, 175.0f)",
        "s1_pos": "(920.0f, 0.0f, 180.0f)",
        "ext_pos": "(1160.0f, 0.0f, 320.0f)",
        "enable_ziplines": "true",
        "reward_name": "Scout-7",
        "script_guid": "a1b2c3d4e5f60718293a4b5c6d7e8f05",
    },
    {
        "id": "M06",
        "class_name": "M06_SandAndSteelSceneInstaller",
        "title": "Sand and Steel",
        "start_pos": "(480.0f, 0.0f, 10.0f)",
        "o1_pos": "(500.0f, 0.0f, 570.0f)",
        "s1_pos": "(510.0f, 0.0f, 285.0f)",
        "ext_pos": "(980.0f, 0.0f, 600.0f)",
        "enable_ziplines": "true",
        "reward_name": "AR-5 Tactical",
        "script_guid": "a1b2c3d4e5f60718293a4b5c6d7e8f06",
    },
    {
        "id": "M07",
        "class_name": "M07_PortAuthoritySceneInstaller",
        "title": "Port Authority",
        "start_pos": "(800.0f, 0.0f, 10.0f)",
        "o1_pos": "(410.0f, 4.2f, 470.0f)",
        "s1_pos": "(390.0f, 4.2f, 445.0f)",
        "ext_pos": "(60.0f, 0.0f, 40.0f)",
        "enable_ziplines": "true",
        "reward_name": "SG-12 Pump",
        "script_guid": "a1b2c3d4e5f60718293a4b5c6d7e8f07",
    },
    {
        "id": "M08",
        "class_name": "M08_ConvoySceneInstaller",
        "title": "Convoy",
        "start_pos": "(60.0f, 0.0f, 200.0f)",
        "o1_pos": "(390.0f, 0.0f, 130.0f)",
        "s1_pos": "(1185.0f, 0.0f, 145.0f)",
        "ext_pos": "(2400.0f, 0.0f, 170.0f)",
        "enable_ziplines": "true",
        "reward_name": "AR-12 Burst",
        "script_guid": "a1b2c3d4e5f60718293a4b5c6d7e8f08",
    },
    {
        "id": "M09",
        "class_name": "M09_EyesAboveSceneInstaller",
        "title": "Eyes Above",
        "start_pos": "(400.0f, 0.0f, 10.0f)",
        "o1_pos": "(400.0f, 0.0f, 400.0f)",
        "s1_pos": "(575.0f, 0.0f, 205.0f)",
        "ext_pos": "(760.0f, 0.0f, 40.0f)",
        "enable_ziplines": "true",
        "reward_name": "Longbow .338",
        "script_guid": "a1b2c3d4e5f60718293a4b5c6d7e8f09",
    },
    {
        "id": "M10",
        "class_name": "M10_CompoundZeroSceneInstaller",
        "title": "Compound Zero",
        "start_pos": "(100.0f, 0.0f, 10.0f)",
        "o1_pos": "(400.0f, 8.4f, 530.0f)",
        "s1_pos": "(304.0f, 4.2f, 350.0f)",
        "ext_pos": "(400.0f, 0.0f, 450.0f)",
        "enable_ziplines": "true",
        "reward_name": "Whisper",
        "script_guid": "a1b2c3d4e5f60718293a4b5c6d7e8f10",
    },
]

SPAWNER_GUID = "b2c3d4e5f60718293a4b5c6d7e8f9000"
BOOT_CTRL_GUID = "b2c3d4e5f60718293a4b5c6d7e8f9001"
MENU_CTRL_GUID = "b2c3d4e5f60718293a4b5c6d7e8f9002"


def write_csharp_meta(cs_path: str, guid: str) -> None:
    meta_content = f"""fileFormatVersion: 2
guid: {guid}
MonoImporter:
  externalObjects: {{}}
  serializedVersion: 2
  defaultReferences: []
  executionOrder: 0
  icon: {{instanceID: 0}}
  userData: 
  assetBundleName: 
  assetBundleVariant: 
"""
    with open(cs_path + ".meta", "w", encoding="utf-8") as f:
        f.write(meta_content)


def build_installer_cs(cfg: dict) -> str:
    mid = cfg["id"]
    cname = cfg["class_name"]
    title = cfg["title"]
    spos = cfg["start_pos"]
    o1pos = cfg["o1_pos"]
    s1pos = cfg["s1_pos"]
    extpos = cfg["ext_pos"]
    zips = cfg["enable_ziplines"]
    reward = cfg["reward_name"]

    return f"""using System;
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
{{
    /// <summary>
    /// Full Runtime Scene Installer & Objective Evaluator for Mission {mid} ("{title}").
    /// Automatically invokes `RuntimeMissionSpawner` on `Awake()` to parse `StreamingAssets/Missions/{mid}.json`
    /// and instantiate all structures, walls, props, cover, traps (`T1`–`T16`), cameras, enemies (`E1`–`E14`),
    /// first-person weapon viewmodels, and the Android Mobile Touch HUD & Satellite ME Map.
    /// Evaluates Primary Objective O1, Secondary Objectives S1 & S2, and Extraction in real time.
    /// </summary>
    public class {cname} : MonoBehaviour
    {{
        [Header("Mission {mid} Blueprint & Spawner")]
        public string missionId = "{mid}";
        public string missionJsonPath = "Assets/_Project/Missions/{mid}.json";
        public bool enforceStrictExclusions = true;
        public RuntimeMissionSpawner runtimeSpawner;

        [Header("Runtime System Bindings")]
        public PlayerTacticalController playerController;
        public StealthAndDetectionSystem stealthSystem;
        public MissionEventAndStreamingSystem streamingSystem;
        public MobileTouchHUDAndMEMap touchHudMap;

        [Header("Mission {mid} Coordinates & Objective State")]
        public Vector3 playerSpawnPoint = new Vector3{spos};
        public Vector3 primaryObjectiveO1Point = new Vector3{o1pos};
        public Vector3 secondaryObjectiveS1Point = new Vector3{s1pos};
        public Vector3 extractionPoint = new Vector3{extpos};
        public float interactionRadiusMeters = 6.5f;
        public float extractionRadiusMeters = 10.0f;

        public bool primaryObjectiveO1Complete;
        public bool secondaryObjectiveS1Complete;
        public bool secondaryObjectiveS2Complete;
        public bool ghostMedalEligible = true;
        public bool missionExtractedAndWon;
        public string unlockedWeaponReward = "{reward}";
        public float missionElapsedSeconds;

        private void Awake()
        {{
            runtimeSpawner = GetComponent<RuntimeMissionSpawner>();
            if (runtimeSpawner == null)
            {{
                runtimeSpawner = gameObject.AddComponent<RuntimeMissionSpawner>();
            }}
            runtimeSpawner.LoadAndSpawnMission(missionId);

            playerController = runtimeSpawner.spawnedPlayer;
            stealthSystem = runtimeSpawner.stealthSystem;
            streamingSystem = runtimeSpawner.streamingSystem;
            touchHudMap = runtimeSpawner.touchHud;

            if (playerController != null)
            {{
                playerController.enableZipLinesInMission = {zips};
            }}
            if (stealthSystem != null)
            {{
                stealthSystem.OnAlertLevelChanged += HandleAlertLevelChanged;
            }}
        }}

        private void OnDestroy()
        {{
            if (stealthSystem != null)
            {{
                stealthSystem.OnAlertLevelChanged -= HandleAlertLevelChanged;
            }}
        }}

        private void Update()
        {{
            if (missionExtractedAndWon || playerController == null) return;

            missionElapsedSeconds += Time.deltaTime;
            Vector3 pPos = playerController.transform.position;

            // 1. Evaluate Primary Objective O1 Proximity / Completion
            if (!primaryObjectiveO1Complete)
            {{
                float distO1 = Vector2.Distance(new Vector2(pPos.x, pPos.z), new Vector2(primaryObjectiveO1Point.x, primaryObjectiveO1Point.z));
                if (distO1 <= interactionRadiusMeters)
                {{
                    CompletePrimaryObjectiveO1();
                }}
            }}

            // 2. Evaluate Secondary Objective S1 Proximity / Completion
            if (!secondaryObjectiveS1Complete)
            {{
                float distS1 = Vector2.Distance(new Vector2(pPos.x, pPos.z), new Vector2(secondaryObjectiveS1Point.x, secondaryObjectiveS1Point.z));
                if (distS1 <= interactionRadiusMeters)
                {{
                    CompleteSecondaryObjectiveS1();
                }}
            }}

            // 3. Evaluate Extraction Point once O1 is complete
            if (primaryObjectiveO1Complete && !missionExtractedAndWon)
            {{
                float distExt = Vector2.Distance(new Vector2(pPos.x, pPos.z), new Vector2(extractionPoint.x, extractionPoint.z));
                if (distExt <= extractionRadiusMeters)
                {{
                    TriggerMissionExtraction();
                }}
            }}
        }}

        private void HandleAlertLevelChanged(CompoundAlertLevel newLevel)
        {{
            if (newLevel >= CompoundAlertLevel.Alert2_CompoundAlarm)
            {{
                ghostMedalEligible = false;
            }}
        }}

        public void CompletePrimaryObjectiveO1()
        {{
            if (primaryObjectiveO1Complete) return;
            primaryObjectiveO1Complete = true;
            AudioClip cue = RuntimeGLBAndMeshLoader.LoadWavAudioClip("sfx_gadget_pda_hack_complete");
            if (cue != null && playerController != null)
            {{
                AudioSource.PlayClipAtPoint(cue, playerController.transform.position, 0.9f);
            }}
            Debug.Log($"[{cname}] Primary Objective O1 COMPLETE! Extraction unlocked at {{extractionPoint}}.");
        }}

        public void CompleteSecondaryObjectiveS1()
        {{
            if (secondaryObjectiveS1Complete) return;
            secondaryObjectiveS1Complete = true;

            TrapAndHazardSystem cam = runtimeSpawner != null ? runtimeSpawner.GetTrapById("{mid}_CAM_01") : null;
            if (cam != null)
            {{
                cam.isArmed = false;
            }}
            Debug.Log($"[{cname}] Secondary Objective S1 COMPLETE!");
        }}

        public void TriggerMissionExtraction()
        {{
            if (!primaryObjectiveO1Complete || missionExtractedAndWon) return;
            missionExtractedAndWon = true;
            secondaryObjectiveS2Complete = ghostMedalEligible;

            MissionSaveData save = new MissionSaveData
            {{
                missionId = missionId,
                alertLevel = stealthSystem != null ? (int)stealthSystem.currentAlertLevel : 0,
                playerHealth = 100f,
                playerPosition = playerController != null ? playerController.transform.position : extractionPoint,
                playerPosture = playerController != null ? (int)playerController.CurrentPosture : 0,
                completedObjectives = new List<string> {{ "O1" }}
            }};
            if (secondaryObjectiveS1Complete) save.completedObjectives.Add("S1");
            if (secondaryObjectiveS2Complete) save.completedObjectives.Add("S2_GhostMedal");

            string savePath = System.IO.Path.Combine(Application.persistentDataPath, missionId + "_completed.json");
            MissionEventAndStreamingSystem.SaveCheckpoint(save, savePath);
            Debug.Log($"[{cname}] MISSION {mid} ('{title}') EXTRACTED! Reward Unlocked: {{unlockedWeaponReward}} | Ghost Medal: {{ghostMedalEligible}}");
        }}
    }}
}}
"""


def build_mission_scene_yaml(mid: str, title: str, installer_class: str, installer_guid: str) -> str:
    return f"""%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!29 &1
OcclusionCullingSettings:
  m_ObjectHideFlags: 0
  serializedVersion: 2
  m_OcclusionBakeSettings:
    smallestOccluder: 5
    smallestHole: 0.25
    backfaceThreshold: 100
  m_SceneGUID: 00000000000000000000000000000000
  m_OcclusionCullingData: {{fileID: 0}}
--- !u!104 &2
RenderSettings:
  m_ObjectHideFlags: 0
  serializedVersion: 9
  m_Fog: 1
  m_FogColor: {{r: 0.55, g: 0.64, b: 0.58, a: 1}}
  m_FogMode: 3
  m_FogDensity: 0.0035
  m_LinearFogStart: 0
  m_LinearFogEnd: 300
  m_AmbientSkyColor: {{r: 0.45, g: 0.52, b: 0.48, a: 1}}
  m_AmbientEquatorColor: {{r: 0.25, g: 0.28, b: 0.26, a: 1}}
  m_AmbientGroundColor: {{r: 0.12, g: 0.14, b: 0.12, a: 1}}
  m_AmbientIntensity: 1
  m_AmbientMode: 0
  m_SubtractiveShadowColor: {{r: 0.42, g: 0.478, b: 0.627, a: 1}}
  m_SkyboxMaterial: {{fileID: 10304, guid: 0000000000000000f000000000000000, type: 0}}
  m_HaloStrength: 0.5
  m_FlareStrength: 1
  m_FlareFadeSpeed: 3
  m_HaloTexture: {{fileID: 0}}
  m_SpotCookie: {{fileID: 10001, guid: 0000000000000000e000000000000000, type: 0}}
  m_DefaultReflectionMode: 0
  m_DefaultReflectionResolution: 128
  m_ReflectionBounces: 1
  m_ReflectionIntensity: 1
  m_CustomReflection: {{fileID: 0}}
  m_Sun: {{fileID: 202}}
  m_UseRadianceAmbientProbe: 0
--- !u!157 &3
LightmapSettings:
  m_ObjectHideFlags: 0
  serializedVersion: 12
  m_GIWorkflowMode: 1
  m_GISettings:
    serializedVersion: 2
    m_BounceScale: 1
    m_IndirectOutputScale: 1
    m_AlbedoBoost: 1
    m_EnvironmentLightingMode: 0
    m_EnableBakedLightmaps: 1
    m_EnableRealtimeLightmaps: 0
  m_LightmapEditorSettings:
    serializedVersion: 12
    m_Resolution: 2
    m_BakeResolution: 40
    m_AtlasSize: 1024
    m_AO: 0
    m_AOMaxDistance: 1
    m_CompAOExponent: 1
    m_CompAOExponentDirect: 0
    m_ExtractAmbientOcclusion: 0
    m_Padding: 2
    m_LightmapParameters: {{fileID: 0}}
    m_LightmapsBakeMode: 1
    m_TextureCompression: 1
    m_FinalGather: 0
    m_FinalGatherFiltering: 1
    m_FinalGatherRayCount: 256
    m_ReflectionCompression: 2
    m_MixedBakeMode: 2
    m_BakeBackend: 1
    m_PVRSampling: 1
    m_PVRDirectSampleCount: 32
    m_PVRSampleCount: 512
    m_PVRBounces: 2
    m_PVREnvironmentSampleCount: 256
    m_PVREnvironmentReferencePointCount: 2048
    m_PVRFilteringMode: 1
    m_PVRDenoiserTypeDirect: 1
    m_PVRDenoiserTypeIndirect: 1
    m_PVRDenoiserTypeAO: 1
    m_PVRFilterTypeDirect: 0
    m_PVRFilterTypeIndirect: 0
    m_PVRFilterTypeAO: 0
    m_PVREnvironmentMIS: 1
    m_PVRCulling: 1
    m_PVRFilteringGaussRadiusDirect: 1
    m_PVRFilteringGaussRadiusIndirect: 5
    m_PVRFilteringGaussRadiusAO: 2
    m_PVRFilteringAtrousPositionSigmaDirect: 0.5
    m_PVRFilteringAtrousPositionSigmaIndirect: 2
    m_PVRFilteringAtrousPositionSigmaAO: 1
    m_ExportTrainingData: 0
    m_TrainingDataDestination: TrainingData
    m_LightProbeSampleCountMultiplier: 4
  m_LightingDataAsset: {{fileID: 0}}
  m_LightingSettings: {{fileID: 0}}
--- !u!196 &4
NavMeshSettings:
  serializedVersion: 2
  m_ObjectHideFlags: 0
  m_BuildSettings:
    serializedVersion: 3
    agentTypeID: 0
    agentRadius: 0.4
    agentHeight: 1.8
    agentSlope: 45
    agentClimb: 0.4
    ledgeDropHeight: 0
    maxJumpAcrossDistance: 0
    minRegionArea: 2
    manualCellSize: 0
    cellSize: 0.13333334
    manualTileSize: 0
    tileSize: 256
    buildHeightMesh: 0
    maxJobWorkers: 0
    preserveTilesOutsideBounds: 0
    debug:
      m_Flags: 0
  m_NavMeshData: {{fileID: 0}}
--- !u!1 &100
GameObject:
  m_ObjectHideFlags: 0
  serializedVersion: 6
  m_Component:
  - component: {{fileID: 101}}
  - component: {{fileID: 102}}
  - component: {{fileID: 103}}
  m_Name: RuntimeMissionBootstrapper_{mid}
  m_TagString: Untagged
  m_Icon: {{fileID: 0}}
  m_NavMeshLayer: 0
  m_StaticEditorFlags: 0
  m_IsActive: 1
--- !u!4 &101
Transform:
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {{fileID: 0}}
  m_PrefabInstance: {{fileID: 0}}
  m_PrefabAsset: {{fileID: 0}}
  m_GameObject: {{fileID: 100}}
  serializedVersion: 2
  m_LocalRotation: {{x: 0, y: 0, z: 0, w: 1}}
  m_LocalPosition: {{x: 0, y: 0, z: 0}}
  m_LocalScale: {{x: 1, y: 1, z: 1}}
  m_ConstrainProportionsScale: 0
  m_Children: []
  m_Father: {{fileID: 0}}
  m_LocalEulerAnglesHint: {{x: 0, y: 0, z: 0}}
--- !u!114 &102
MonoBehaviour:
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {{fileID: 0}}
  m_PrefabInstance: {{fileID: 0}}
  m_PrefabAsset: {{fileID: 0}}
  m_GameObject: {{fileID: 100}}
  m_Enabled: 1
  m_EditorHideFlags: 0
  m_Script: {{fileID: 11500000, guid: {SPAWNER_GUID}, type: 3}}
  m_Name: 
  m_EditorClassIdentifier: RealLoserStudio.Tactical.Core.RuntimeMissionSpawner
  missionId: {mid}
--- !u!114 &103
MonoBehaviour:
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {{fileID: 0}}
  m_PrefabInstance: {{fileID: 0}}
  m_PrefabAsset: {{fileID: 0}}
  m_GameObject: {{fileID: 100}}
  m_Enabled: 1
  m_EditorHideFlags: 0
  m_Script: {{fileID: 11500000, guid: {installer_guid}, type: 3}}
  m_Name: 
  m_EditorClassIdentifier: RealLoserStudio.Tactical.Core.{installer_class}
  missionId: {mid}
  missionJsonPath: Assets/_Project/Missions/{mid}.json
  enforceStrictExclusions: 1
--- !u!1 &200
GameObject:
  m_ObjectHideFlags: 0
  serializedVersion: 6
  m_Component:
  - component: {{fileID: 201}}
  - component: {{fileID: 202}}
  m_Name: Directional Light
  m_TagString: Untagged
  m_Icon: {{fileID: 0}}
  m_NavMeshLayer: 0
  m_StaticEditorFlags: 0
  m_IsActive: 1
--- !u!4 &201
Transform:
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {{fileID: 0}}
  m_PrefabInstance: {{fileID: 0}}
  m_PrefabAsset: {{fileID: 0}}
  m_GameObject: {{fileID: 200}}
  serializedVersion: 2
  m_LocalRotation: {{x: 0.40821788, y: -0.23456968, z: 0.10938163, w: 0.8754261}}
  m_LocalPosition: {{x: 0, y: 50, z: 0}}
  m_LocalScale: {{x: 1, y: 1, z: 1}}
  m_ConstrainProportionsScale: 0
  m_Children: []
  m_Father: {{fileID: 0}}
  m_LocalEulerAnglesHint: {{x: 50, y: -30, z: 0}}
--- !u!108 &202
Light:
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {{fileID: 0}}
  m_PrefabInstance: {{fileID: 0}}
  m_PrefabAsset: {{fileID: 0}}
  m_GameObject: {{fileID: 200}}
  m_Enabled: 1
  serializedVersion: 10
  m_Type: 1
  m_Shape: 0
  m_Color: {{r: 1, g: 0.96, b: 0.88, a: 1}}
  m_Intensity: 1.15
  m_Range: 10
  m_SpotAngle: 30
  m_InnerSpotAngle: 21.80208
  m_CookieSize: 10
  m_Shadows:
    m_Type: 2
    m_Resolution: -1
    m_CustomResolution: -1
    m_Strength: 1
    m_Bias: 0.05
    m_NormalBias: 0.4
    m_NearPlane: 0.2
  m_Cookie: {{fileID: 0}}
  m_DrawHalo: 0
  m_Flare: {{fileID: 0}}
  m_RenderMode: 0
  m_CullingMask:
    serializedVersion: 2
    m_Bits: 4294967295
  m_RenderingLayerMask: 1
  m_Lightmapping: 4
  m_LightShadowCasterMode: 0
  m_AreaSize: {{x: 1, y: 1}}
  m_BounceIntensity: 1
  m_ColorTemperature: 6570
  m_UseColorTemperature: 0
  m_BoundingSphereOverride: {{x: 0, y: 0, z: 0, w: 0}}
  m_UseBoundingSphereOverride: 0
  m_UseViewFrustumForShadowCasterCull: 1
  m_ShadowRadius: 0
  m_ShadowAngle: 0
--- !u!1 &300
GameObject:
  m_ObjectHideFlags: 0
  serializedVersion: 6
  m_Component:
  - component: {{fileID: 301}}
  - component: {{fileID: 302}}
  - component: {{fileID: 303}}
  m_Name: Main Camera
  m_TagString: MainCamera
  m_Icon: {{fileID: 0}}
  m_NavMeshLayer: 0
  m_StaticEditorFlags: 0
  m_IsActive: 1
--- !u!4 &301
Transform:
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {{fileID: 0}}
  m_PrefabInstance: {{fileID: 0}}
  m_PrefabAsset: {{fileID: 0}}
  m_GameObject: {{fileID: 300}}
  serializedVersion: 2
  m_LocalRotation: {{x: 0, y: 0, z: 0, w: 1}}
  m_LocalPosition: {{x: 20, y: 1.7, z: 10}}
  m_LocalScale: {{x: 1, y: 1, z: 1}}
  m_ConstrainProportionsScale: 0
  m_Children: []
  m_Father: {{fileID: 0}}
  m_LocalEulerAnglesHint: {{x: 0, y: 0, z: 0}}
--- !u!20 &302
Camera:
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {{fileID: 0}}
  m_PrefabInstance: {{fileID: 0}}
  m_PrefabAsset: {{fileID: 0}}
  m_GameObject: {{fileID: 300}}
  m_Enabled: 1
  serializedVersion: 2
  m_ClearFlags: 1
  m_BackGroundColor: {{r: 0.12, g: 0.16, b: 0.14, a: 0}}
  m_projectionMatrixMode: 1
  m_GateFitMode: 2
  m_FOVAxisMode: 0
  m_Iso: 200
  m_ShutterSpeed: 0.005
  m_Aperture: 16
  m_FocusDistance: 10
  m_FocalLength: 50
  m_BladeCount: 5
  m_Curvature: {{x: 2, y: 11}}
  m_BarrelClipping: 0.25
  m_Anamorphism: 0
  m_SensorSize: {{x: 36, y: 24}}
  m_LensShift: {{x: 0, y: 0}}
  m_NormalizedViewPortRect:
    serializedVersion: 2
    x: 0
    y: 0
    width: 1
    height: 1
  near clip plane: 0.08
  far clip plane: 450
  field of view: 70
  orthographic: 0
  orthographic size: 5
  m_Depth: -1
  m_CullingMask:
    serializedVersion: 2
    m_Bits: 4294967295
  m_RenderingPath: -1
  m_TargetTexture: {{fileID: 0}}
  m_TargetDisplay: 0
  m_TargetEye: 3
  m_HDR: 1
  m_AllowMSAA: 1
  m_AllowDynamicResolution: 0
  m_ForceIntoRT: 0
  m_OcclusionCulling: 1
  m_StereoConvergence: 10
  m_StereoSeparation: 0.022
--- !u!81 &303
AudioListener:
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {{fileID: 0}}
  m_PrefabInstance: {{fileID: 0}}
  m_PrefabAsset: {{fileID: 0}}
  m_GameObject: {{fileID: 300}}
  m_Enabled: 1
"""


def build_boot_or_menu_scene_yaml(scene_title: str, ctrl_class: str, ctrl_guid: str) -> str:
    return f"""%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!29 &1
OcclusionCullingSettings:
  m_ObjectHideFlags: 0
  serializedVersion: 2
  m_OcclusionBakeSettings:
    smallestOccluder: 5
    smallestHole: 0.25
    backfaceThreshold: 100
  m_SceneGUID: 00000000000000000000000000000000
  m_OcclusionCullingData: {{fileID: 0}}
--- !u!104 &2
RenderSettings:
  m_ObjectHideFlags: 0
  serializedVersion: 9
  m_Fog: 0
  m_AmbientMode: 0
--- !u!157 &3
LightmapSettings:
  m_ObjectHideFlags: 0
  serializedVersion: 12
--- !u!196 &4
NavMeshSettings:
  serializedVersion: 2
  m_ObjectHideFlags: 0
--- !u!1 &100
GameObject:
  m_ObjectHideFlags: 0
  serializedVersion: 6
  m_Component:
  - component: {{fileID: 101}}
  - component: {{fileID: 102}}
  m_Name: {scene_title}_ControllerRoot
  m_TagString: Untagged
  m_IsActive: 1
--- !u!4 &101
Transform:
  m_ObjectHideFlags: 0
  m_GameObject: {{fileID: 100}}
  serializedVersion: 2
  m_LocalRotation: {{x: 0, y: 0, z: 0, w: 1}}
  m_LocalPosition: {{x: 0, y: 0, z: 0}}
  m_LocalScale: {{x: 1, y: 1, z: 1}}
--- !u!114 &102
MonoBehaviour:
  m_ObjectHideFlags: 0
  m_GameObject: {{fileID: 100}}
  m_Enabled: 1
  m_EditorHideFlags: 0
  m_Script: {{fileID: 11500000, guid: {ctrl_guid}, type: 3}}
  m_Name: 
  m_EditorClassIdentifier: RealLoserStudio.Tactical.Core.{ctrl_class}
--- !u!1 &300
GameObject:
  m_ObjectHideFlags: 0
  serializedVersion: 6
  m_Component:
  - component: {{fileID: 301}}
  - component: {{fileID: 302}}
  - component: {{fileID: 303}}
  m_Name: Main Camera
  m_TagString: MainCamera
  m_IsActive: 1
--- !u!4 &301
Transform:
  m_ObjectHideFlags: 0
  m_GameObject: {{fileID: 300}}
  serializedVersion: 2
  m_LocalRotation: {{x: 0, y: 0, z: 0, w: 1}}
  m_LocalPosition: {{x: 0, y: 1, z: -10}}
  m_LocalScale: {{x: 1, y: 1, z: 1}}
--- !u!20 &302
Camera:
  m_ObjectHideFlags: 0
  m_GameObject: {{fileID: 300}}
  m_Enabled: 1
  serializedVersion: 2
  m_ClearFlags: 2
  m_BackGroundColor: {{r: 0.05, g: 0.07, b: 0.09, a: 1}}
  near clip plane: 0.1
  far clip plane: 100
  field of view: 60
--- !u!81 &303
AudioListener:
  m_ObjectHideFlags: 0
  m_GameObject: {{fileID: 300}}
  m_Enabled: 1
"""


def main():
    core_dir = os.path.join(ROOT_DIR, "Assets/_Project/Scripts/Core")
    scenes_dir = os.path.join(ROOT_DIR, "Assets/_Project/Scenes")
    out_dir = os.path.join(ROOT_DIR, "artifacts/file_generation/ttl=63d/output")
    os.makedirs(core_dir, exist_ok=True)
    os.makedirs(scenes_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)

    # Write deterministic .meta for RuntimeMissionSpawner, RuntimeGLBAndMeshLoader, BootAndMainMenuControllers
    write_csharp_meta(os.path.join(core_dir, "RuntimeMissionSpawner.cs"), SPAWNER_GUID)
    write_csharp_meta(os.path.join(core_dir, "RuntimeGLBAndMeshLoader.cs"), "b2c3d4e5f60718293a4b5c6d7e8f9003")
    write_csharp_meta(os.path.join(core_dir, "BootAndMainMenuControllers.cs"), BOOT_CTRL_GUID)

    # Write Boot.unity and MainMenu.unity
    with open(os.path.join(scenes_dir, "Boot.unity"), "w", encoding="utf-8") as f:
        f.write(build_boot_or_menu_scene_yaml("Boot", "BootSceneController", BOOT_CTRL_GUID))
    with open(os.path.join(scenes_dir, "MainMenu.unity"), "w", encoding="utf-8") as f:
        f.write(build_boot_or_menu_scene_yaml("MainMenu", "MainMenuController", BOOT_CTRL_GUID))

    # Write all 10 Mission Installers and M01.unity..M10.unity
    for cfg in MISSION_INSTALLER_CONFIGS:
        cs_code = build_installer_cs(cfg)
        cs_path = os.path.join(core_dir, cfg["class_name"] + ".cs")
        with open(cs_path, "w", encoding="utf-8") as f:
            f.write(cs_code)
        with open(os.path.join(out_dir, cfg["class_name"] + ".cs"), "w", encoding="utf-8") as f:
            f.write(cs_code)
        write_csharp_meta(cs_path, cfg["script_guid"])

        scene_yaml = build_mission_scene_yaml(cfg["id"], cfg["title"], cfg["class_name"], cfg["script_guid"])
        scene_path = os.path.join(scenes_dir, cfg["id"] + ".unity")
        with open(scene_path, "w", encoding="utf-8") as f:
            f.write(scene_yaml)
        with open(os.path.join(out_dir, cfg["id"] + ".unity"), "w", encoding="utf-8") as f:
            f.write(scene_yaml)

    # Ensure M01.json..M10.json are present in root, Assets/_Project/Missions/, and Assets/StreamingAssets/Missions/
    streaming_root = os.path.join(ROOT_DIR, "Assets/StreamingAssets")
    streaming_missions = os.path.join(streaming_root, "Missions")
    os.makedirs(streaming_missions, exist_ok=True)

    for i in range(1, 11):
        mfile = f"M{i:02d}.json"
        proj_m = os.path.join(ROOT_DIR, "Assets/_Project/Missions", mfile)
        root_m = os.path.join(ROOT_DIR, mfile)
        out_m = os.path.join(out_dir, mfile)
        stream_m = os.path.join(streaming_missions, mfile)

        src = proj_m if os.path.exists(proj_m) else (out_m if os.path.exists(out_m) else root_m)
        for dst in (proj_m, root_m, out_m, stream_m):
            if os.path.abspath(src) != os.path.abspath(dst):
                shutil.copy2(src, dst)

    # Copy all 80 .glb files into Assets/StreamingAssets/Art/
    for sub in ("Characters", "Weapons", "Traps", "Environment"):
        sdir = os.path.join(ROOT_DIR, "Assets/_Project/Art", sub)
        ddir = os.path.join(streaming_root, "Art", sub)
        os.makedirs(ddir, exist_ok=True)
        for fn in os.listdir(sdir):
            if fn.endswith(".glb"):
                shutil.copy2(os.path.join(sdir, fn), os.path.join(ddir, fn))

    # Copy all 34 .wav files and audio_manifest.json into Assets/StreamingAssets/Audio/
    asrc = os.path.join(ROOT_DIR, "Assets/_Project/Audio")
    adst = os.path.join(streaming_root, "Audio")
    os.makedirs(adst, exist_ok=True)
    for fn in os.listdir(asrc):
        if fn.endswith(".wav") or fn == "audio_manifest.json":
            shutil.copy2(os.path.join(asrc, fn), os.path.join(adst, fn))

    # Restore verify_m09_eyesabove.py and verify_m10_compoundzero.py into tests/
    for vfile in ("verify_m09_eyesabove.py", "verify_m10_compoundzero.py"):
        vsrc = os.path.join(out_dir, vfile)
        vdst = os.path.join(ROOT_DIR, "tests", vfile)
        if os.path.exists(vsrc):
            shutil.copy2(vsrc, vdst)

    print("[UPGRADE COMPLETE] Upgraded all 10 Scene Installers, 12 Unity Scenes, and populated Assets/StreamingAssets/.")


if __name__ == "__main__":
    main()
