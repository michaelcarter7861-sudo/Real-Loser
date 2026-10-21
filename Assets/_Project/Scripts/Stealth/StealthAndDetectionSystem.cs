using System;
using System.Collections.Generic;
using UnityEngine;
using RealLoserStudio.Tactical.Player;

namespace RealLoserStudio.Tactical.Stealth
{
    public enum CompoundAlertLevel
    {
        Alert0_Unaware = 0,
        Alert1_Suspicious = 1,
        Alert2_CompoundAlarm = 2,
        Alert3_CombatLock = 3
    }

    public enum SurfaceMaterialType
    {
        Concrete = 0,
        Metal = 1,
        Gravel = 2,
        Wood = 3,
        Grass = 4,
        Snow = 5,
        Water = 6
    }

    public enum NoiseCategory
    {
        Footstep = 0,
        DistractionBait = 1,
        TrapNoise = 2,
        SuppressedGunshot = 3,
        UnsuppressedGunshot = 4,
        Explosion = 5,
        AlarmSiren = 6,
        DogBark = 7
    }

    [Serializable]
    public struct NoiseStimulus
    {
        public Vector3 origin;
        public float effectiveRadiusMeters;
        public NoiseCategory category;
        public float timestamp;
        public bool escalatesToAlert2;
    }

    /// <summary>
    /// Central Stealth, Acoustic Propagation, Visibility & Compound Alert Network Manager.
    /// Zero-GC hot-path evaluations for Android ARM64 IL2CPP.
    /// </summary>
    public class StealthAndDetectionSystem : MonoBehaviour
    {
        public static StealthAndDetectionSystem Instance { get; private set; }

        [Header("Compound Alert State")]
        public CompoundAlertLevel currentAlertLevel = CompoundAlertLevel.Alert0_Unaware;
        public float alert2CooldownSeconds = 90.0f;
        private float _alertTimer;

        [Header("Environmental & Wind Parameters")]
        public Vector3 windDirectionNormalized = new Vector3(0f, 0f, 1f); // Used by T15 Dog Patrol downwind check
        [Range(0.1f, 1.5f)] public float ambientLightFactor = 0.85f;
        public float searchlightVisibilityMultiplier = 1.60f; // T10 Searchlight Tower multiplier

        private bool _isPlayerInSearchlightBeam;
        private bool _isPlayerInStealthFoliage;

        public event Action<NoiseStimulus> OnNoiseEmitted;
        public event Action<CompoundAlertLevel> OnAlertLevelChanged;

        private void Awake()
        {
            Instance = this;
            if (windDirectionNormalized.sqrMagnitude > 0.001f)
                windDirectionNormalized.Normalize();
        }

        private void Update()
        {
            if (currentAlertLevel == CompoundAlertLevel.Alert2_CompoundAlarm ||
                currentAlertLevel == CompoundAlertLevel.Alert1_Suspicious)
            {
                if (_alertTimer > 0f)
                {
                    _alertTimer -= Time.deltaTime;
                    if (_alertTimer <= 0f)
                    {
                        SetAlertLevel(CompoundAlertLevel.Alert0_Unaware);
                    }
                }
            }
        }

        public void SetPlayerInSearchlight(bool inBeam)
        {
            _isPlayerInSearchlightBeam = inBeam;
        }

        public void SetPlayerInStealthFoliage(bool inFoliage)
        {
            _isPlayerInStealthFoliage = inFoliage;
        }

        /// <summary>
        /// Computes effective player visibility factor:
        /// Stand = 1.0, Crouch = 0.65 (-35%), Prone = 0.30 (-70%),
        /// multiplied by T10 Searchlight (x1.6) if illuminated.
        /// </summary>
        public float ComputePlayerVisibilityFactor(PlayerTacticalController player)
        {
            if (player == null) return 1.0f;
            float vis = player.ActiveProfile.visibilityMultiplier * ambientLightFactor;
            if (_isPlayerInStealthFoliage && player.CurrentPosture != PlayerPosture.Stand)
            {
                vis *= 0.45f;
            }
            if (_isPlayerInSearchlightBeam)
            {
                vis *= searchlightVisibilityMultiplier; // Exact x1.6 spec for T10 Searchlight Tower
            }
            return vis;
        }

        /// <summary>
        /// Computes footstep acoustic radius in meters given posture and surface material.
        /// Stand = 100%, Crouch = -55% (0.45x), Prone = -85% (0.15x).
        /// </summary>
        public float ComputeFootstepNoiseRadius(PlayerTacticalController player, SurfaceMaterialType surface, bool isSprinting)
        {
            if (player == null) return 0f;
            float baseSurfaceRadius = GetBaseSurfaceNoiseMeters(surface);
            if (isSprinting && player.CurrentPosture == PlayerPosture.Stand)
            {
                baseSurfaceRadius *= 1.65f;
            }
            return baseSurfaceRadius * player.ActiveProfile.noiseMultiplier;
        }

        public void EmitNoise(Vector3 origin, float radiusMeters, NoiseCategory category, bool triggersAlert2 = false)
        {
            NoiseStimulus stim = new NoiseStimulus
            {
                origin = origin,
                effectiveRadiusMeters = radiusMeters,
                category = category,
                timestamp = Time.time,
                escalatesToAlert2 = triggersAlert2
            };

            if (triggersAlert2)
            {
                EscalateToAlert(CompoundAlertLevel.Alert2_CompoundAlarm);
            }
            else if (currentAlertLevel == CompoundAlertLevel.Alert0_Unaware && radiusMeters >= 12.0f)
            {
                EscalateToAlert(CompoundAlertLevel.Alert1_Suspicious);
            }

            OnNoiseEmitted?.Invoke(stim);
        }

        public void EscalateToAlert(CompoundAlertLevel targetLevel)
        {
            if (targetLevel > currentAlertLevel)
            {
                SetAlertLevel(targetLevel);
            }
            _alertTimer = alert2CooldownSeconds;
        }

        public void SetAlertLevel(CompoundAlertLevel level)
        {
            if (currentAlertLevel == level) return;
            currentAlertLevel = level;
            _alertTimer = alert2CooldownSeconds;
            OnAlertLevelChanged?.Invoke(currentAlertLevel);
        }

        /// <summary>
        /// Checks whether targetPos is upwind of the dog (i.e. wind carries player scent toward the dog).
        /// Counterplay for T15 Dog Patrol: stay downwind of the dog so scent does not travel toward the dog.
        /// </summary>
        public bool IsPlayerScentReachingDog(Vector3 playerPos, Vector3 dogPos, float scentRangeMeters = 20.0f)
        {
            Vector3 playerToDog = dogPos - playerPos;
            float dist = playerToDog.magnitude;
            if (dist > scentRangeMeters || dist < 0.01f) return false;

            Vector3 dirPlayerToDog = playerToDog / dist;
            // If wind blows from player toward dog (dot > 0.35), dog smells player within 20m scent cone
            float windAlignment = Vector3.Dot(dirPlayerToDog, windDirectionNormalized);
            return windAlignment > 0.35f;
        }

        private static float GetBaseSurfaceNoiseMeters(SurfaceMaterialType surface)
        {
            switch (surface)
            {
                case SurfaceMaterialType.Metal: return 11.0f;
                case SurfaceMaterialType.Gravel: return 12.5f;
                case SurfaceMaterialType.Water: return 10.0f;
                case SurfaceMaterialType.Wood: return 8.5f;
                case SurfaceMaterialType.Concrete: return 7.5f;
                case SurfaceMaterialType.Snow: return 6.5f;
                case SurfaceMaterialType.Grass: return 5.5f;
                default: return 7.5f;
            }
        }
    }
}
