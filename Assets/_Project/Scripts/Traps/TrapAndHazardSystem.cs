using System;
using System.Collections.Generic;
using UnityEngine;
using RealLoserStudio.Tactical.Player;
using RealLoserStudio.Tactical.Stealth;

namespace RealLoserStudio.Tactical.Traps
{
    public enum TrapType
    {
        T1_TripwireAlarm = 1,       // Ankle wire -> 40m noise + Alert 2; Counter: Wire Cutters 2s
        T2_TripwireGrenade = 2,     // Wire -> 120 dmg 6m radius; Counter: Cut wire 2s
        T3_DirectionalMine = 3,     // 150 dmg 60° cone 15m; Counter: Disarm 3s
        T4_BuriedMine = 4,          // 1.2m step -> 200 dmg; Counter: Prone disarm 4s
        T5_LaserGrid = 5,           // Break beam -> Alarm + Alert 2; Counter: Panel / EMP 20s
        T6_MotionSensor = 6,        // Move >1.2 m/s in 12m -> Alert 2; Counter: Prone crawl <1.2 m/s or EMP
        T7_PressurePlate = 7,       // Step -> Alarm; Counter: Jump 1.0m or disarm
        T8_NoiseTrap = 8,           // Cans/gravel -> 15m noise; Counter: Crouch/avoid
        T9_SentryTurret = 9,        // 60° 25m arc -> 12 dmg/shot @ 600 RPM; Counter: Hack 8s or EMP
        T10_SearchlightTower = 10,  // Sweeping beam -> Visibility x1.6; Counter: Shoot lamp or time gap
        T11_SecurityCamera = 11,    // 70° cone 35m -> Alarm; Counter: EMP, hack monitor, or shoot
        T12_ElectricFence = 12,     // 40 dmg + sparks; Counter: Cut generator/breaker power
        T13_AlarmedDoor = 13,       // Open without key/code -> Alarm; Counter: Keycard or Hack PDA 6s
        T14_BoobyTrappedDoor = 14,  // Open fast -> 120 dmg; Counter: Slow peek + disarm wire 3s
        T15_DogPatrolHazard = 15,   // 20m scent cone -> bark alert + 25 dmg bite; Counter: Stay downwind or throw meat
        T16_EnvironmentalHazard = 16 // Thin ice / live rail / steam vent
    }

    public enum EnvironmentalHazardSubType
    {
        ThinIce = 0,
        LiveRail = 1,
        SteamVent = 2
    }

    public enum CounterToolType
    {
        None = 0,
        WireCutters = 1,
        DisarmHands = 2,
        HackPDA = 3,
        EMPPulse = 4,
        Keycard = 5,
        SlowPeek = 6,
        DistractionMeat = 7,
        ValveWheel = 8
    }

    /// <summary>
    /// Power Source node (`prop_breaker_box_a` or `prop_generator_diesel_a`) that powers T12 Electric Fences
    /// or T5 Laser Grids.
    /// </summary>
    public class PowerSourceNode : MonoBehaviour
    {
        public string powerSourceId = "prop_breaker_box_a_01";
        public string assetType = "prop_breaker_box_a"; // or prop_generator_diesel_a
        public bool isPoweredOn = true;

        public event Action<bool> OnPowerStateChanged;

        public void CutPower()
        {
            if (!isPoweredOn) return;
            isPoweredOn = false;
            OnPowerStateChanged?.Invoke(false);
        }
    }

    /// <summary>
    /// Complete implementation of all 16 Trap & Hazard Systems (T1–T16) with exact trigger, cue, and counter logic.
    /// </summary>
    public class TrapAndHazardSystem : MonoBehaviour
    {
        [Header("Trap Identity")]
        public string trapId = "trap_01";
        public TrapType trapType = TrapType.T1_TripwireAlarm;
        public EnvironmentalHazardSubType envSubType = EnvironmentalHazardSubType.SteamVent;

        [Header("State")]
        public bool isArmed = true;
        public bool isDestroyed;
        public float hitPoints = 30f; // For destructible T10 Searchlight lamp / T11 Security Camera
        public PowerSourceNode linkedPowerSource; // Required for T12 Electric Fence

        [Header("Security Camera Declaration")]
        // Camera records can override the T11 defaults without changing trap behavior.
        public float cameraFovDegrees = T11_CONE_DEG;
        public float cameraRangeMeters = T11_RANGE;
        public string monitorId;

        private float _empDisableTimer;
        private float _turretFireAccumulator;
        private float _sweepAnglePhase;
        private float _dogMeatDistractionTimer;
        private bool _doorSlowPeeked;
        private float _alarmCooldownTimer;
        private float _damageCooldownTimer;

        // Repeating sensors use a cooldown so a player standing in a volume does not
        // emit an alarm or damage event every frame. One-shot traps still disarm on trigger.
        private const float ALARM_RETRIGGER_COOLDOWN = 1.0f;
        private const float DAMAGE_RETRIGGER_COOLDOWN = 0.25f;

        // Exact Specification Constants
        public const float T1_NOISE_RADIUS = 40.0f;
        public const float T1_CUT_TIME = 2.0f;

        public const float T2_DAMAGE = 120.0f;
        public const float T2_BLAST_RADIUS = 6.0f;
        public const float T2_CUT_TIME = 2.0f;

        public const float T3_DAMAGE = 150.0f;
        public const float T3_CONE_DEG = 60.0f;
        public const float T3_RANGE = 15.0f;
        public const float T3_DISARM_TIME = 3.0f;

        public const float T4_STEP_RADIUS = 1.2f;
        public const float T4_DAMAGE = 200.0f;
        public const float T4_PRONE_DISARM_TIME = 4.0f;

        public const float T5_EMP_DISABLE_DURATION = 20.0f;

        public const float T6_SPEED_THRESHOLD = 1.2f;
        public const float T6_RANGE = 12.0f;

        public const float T7_JUMP_CLEARANCE = 1.0f;

        public const float T8_NOISE_RADIUS = 15.0f;

        public const float T9_ARC_DEG = 60.0f;
        public const float T9_RANGE = 25.0f;
        public const float T9_DAMAGE_PER_SHOT = 12.0f;
        public const float T9_RPM = 600.0f; // 10 shots/sec
        public const float T9_HACK_TIME = 8.0f;

        public const float T10_VISIBILITY_MULT = 1.6f;

        public const float T11_CONE_DEG = 70.0f;
        public const float T11_RANGE = 35.0f;

        public const float T12_SHOCK_DAMAGE = 40.0f;

        public const float T13_HACK_PDA_TIME = 6.0f;

        public const float T14_DAMAGE = 120.0f;
        public const float T14_DISARM_TIME = 3.0f;

        public const float T15_SCENT_CONE_RANGE = 20.0f;
        public const float T15_BITE_DAMAGE = 25.0f;

        public event Action<TrapAndHazardSystem, float> OnPlayerDamaged;

        private void Start()
        {
            if (linkedPowerSource != null)
            {
                linkedPowerSource.OnPowerStateChanged += HandlePowerChanged;
            }
        }

        private void HandlePowerChanged(bool powered)
        {
            if (trapType == TrapType.T12_ElectricFence && !powered)
            {
                isArmed = false;
            }
        }

        public bool IsCurrentlyActive => isArmed && !isDestroyed && _empDisableTimer <= 0f;

        /// <summary>
        /// Returns required interaction duration (seconds) for the player's Context Action button.
        /// </summary>
        public float GetCounterInteractionDuration(CounterToolType tool, PlayerPosture posture)
        {
            switch (trapType)
            {
                case TrapType.T1_TripwireAlarm:
                case TrapType.T2_TripwireGrenade:
                    return tool == CounterToolType.WireCutters ? T1_CUT_TIME : -1f;

                case TrapType.T3_DirectionalMine:
                    return (tool == CounterToolType.DisarmHands || tool == CounterToolType.WireCutters) ? T3_DISARM_TIME : -1f;

                case TrapType.T4_BuriedMine:
                    // Must be prone and use a real disarm tool (hands or cutters).
                    return (posture == PlayerPosture.Prone &&
                            (tool == CounterToolType.DisarmHands || tool == CounterToolType.WireCutters))
                        ? T4_PRONE_DISARM_TIME : -1f;

                case TrapType.T5_LaserGrid:
                    return (tool == CounterToolType.HackPDA || tool == CounterToolType.EMPPulse) ? 1.5f : -1f; // Wall panel toggle

                case TrapType.T7_PressurePlate:
                    return (tool == CounterToolType.DisarmHands || tool == CounterToolType.WireCutters) ? 2.5f : -1f;

                case TrapType.T9_SentryTurret:
                    return tool == CounterToolType.HackPDA ? T9_HACK_TIME : -1f;

                case TrapType.T11_SecurityCamera:
                    return tool == CounterToolType.HackPDA ? 4.0f : -1f;

                case TrapType.T13_AlarmedDoor:
                    if (tool == CounterToolType.Keycard) return 0.5f;
                    return tool == CounterToolType.HackPDA ? T13_HACK_PDA_TIME : -1f;

                case TrapType.T14_BoobyTrappedDoor:
                    if (!_doorSlowPeeked && tool == CounterToolType.SlowPeek) return 1.2f;
                    if (_doorSlowPeeked && (tool == CounterToolType.WireCutters || tool == CounterToolType.DisarmHands))
                        return T14_DISARM_TIME;
                    return -1f;

                case TrapType.T16_EnvironmentalHazard:
                    return (envSubType == EnvironmentalHazardSubType.SteamVent && tool == CounterToolType.ValveWheel) ? 2.5f : -1f;

                default:
                    return -1f;
            }
        }

        /// <summary>
        /// Applies a player countermeasure to disarm, disable, or bypass this trap.
        /// </summary>
        public bool ApplyCountermeasure(CounterToolType tool, PlayerTacticalController player)
        {
            if (!IsCurrentlyActive || player == null) return false;

            if (tool == CounterToolType.EMPPulse)
            {
                if (trapType == TrapType.T5_LaserGrid ||
                    trapType == TrapType.T6_MotionSensor ||
                    trapType == TrapType.T9_SentryTurret ||
                    trapType == TrapType.T11_SecurityCamera)
                {
                    _empDisableTimer = T5_EMP_DISABLE_DURATION; // 20s EMP disable
                    return true;
                }
            }

            if (trapType == TrapType.T15_DogPatrolHazard && tool == CounterToolType.DistractionMeat)
            {
                _dogMeatDistractionTimer = 25.0f;
                return true;
            }

            if (trapType == TrapType.T14_BoobyTrappedDoor && tool == CounterToolType.SlowPeek && !_doorSlowPeeked)
            {
                _doorSlowPeeked = true;
                return true;
            }

            float reqTime = GetCounterInteractionDuration(tool, player != null ? player.CurrentPosture : PlayerPosture.Stand);
            if (reqTime >= 0f)
            {
                isArmed = false;
                return true;
            }

            return false;
        }

        public void ApplyBallisticDamage(float damage)
        {
            if (isDestroyed) return;
            if (trapType == TrapType.T10_SearchlightTower || trapType == TrapType.T11_SecurityCamera)
            {
                hitPoints -= damage;
                if (hitPoints <= 0f)
                {
                    isDestroyed = true;
                    isArmed = false;
                    if (trapType == TrapType.T10_SearchlightTower && StealthAndDetectionSystem.Instance != null)
                    {
                        StealthAndDetectionSystem.Instance.SetPlayerInSearchlight(false);
                    }
                }
            }
        }

        /// <summary>
        /// Evaluates trap sensor / proximity / trigger logic against the player on each tick.
        /// </summary>
        public void EvaluateTrapTick(PlayerTacticalController player, float deltaTime)
        {
            if (_empDisableTimer > 0f)
            {
                _empDisableTimer -= deltaTime;
            }
            if (_dogMeatDistractionTimer > 0f)
            {
                _dogMeatDistractionTimer -= deltaTime;
            }
            if (_alarmCooldownTimer > 0f) _alarmCooldownTimer -= deltaTime;
            if (_damageCooldownTimer > 0f) _damageCooldownTimer -= deltaTime;

            if (!IsCurrentlyActive || player == null) return;

            Vector3 toPlayer = player.transform.position - transform.position;
            float dist = toPlayer.magnitude;
            Vector3 dirToPlayer = dist > 0.001f ? (toPlayer / dist) : transform.forward;
            float angleDeg = Vector3.Angle(transform.forward, dirToPlayer);

            switch (trapType)
            {
                case TrapType.T1_TripwireAlarm:
                    if (dist <= 1.1f)
                    {
                        TriggerT1TripwireAlarm();
                    }
                    break;

                case TrapType.T2_TripwireGrenade:
                    if (dist <= 1.1f)
                    {
                        TriggerT2TripwireGrenade(dist);
                    }
                    break;

                case TrapType.T3_DirectionalMine:
                    if (dist <= T3_RANGE && angleDeg <= (T3_CONE_DEG * 0.5f))
                    {
                        TriggerT3DirectionalMine(dist);
                    }
                    break;

                case TrapType.T4_BuriedMine:
                    if (dist <= T4_STEP_RADIUS && player.CurrentPosture != PlayerPosture.Prone)
                    {
                        TriggerT4BuriedMine();
                    }
                    break;

                case TrapType.T5_LaserGrid:
                    if (dist <= 1.25f)
                    {
                        TriggerT5LaserGrid();
                    }
                    break;

                case TrapType.T6_MotionSensor:
                    // Evaded by Prone crawl (< 1.2 m/s) or EMP
                    if (dist <= T6_RANGE && player.CurrentHorizontalSpeed > T6_SPEED_THRESHOLD)
                    {
                        TriggerT6MotionSensor();
                    }
                    break;

                case TrapType.T7_PressurePlate:
                    // Evaded by jumping >= 1.0m over plate
                    float verticalHeightAbovePlate = player.transform.position.y - transform.position.y;
                    if (dist <= 0.95f && verticalHeightAbovePlate < T7_JUMP_CLEARANCE)
                    {
                        TriggerT7PressurePlate();
                    }
                    break;

                case TrapType.T8_NoiseTrap:
                    // Countered by Crouch or avoiding
                    if (dist <= 1.2f && player.CurrentPosture == PlayerPosture.Stand && player.CurrentHorizontalSpeed > 0.5f)
                    {
                        TriggerT8NoiseTrap();
                    }
                    break;

                case TrapType.T9_SentryTurret:
                    if (dist <= T9_RANGE && angleDeg <= (T9_ARC_DEG * 0.5f))
                    {
                        FireT9SentryTurret(deltaTime);
                    }
                    break;

                case TrapType.T10_SearchlightTower:
                    _sweepAnglePhase += deltaTime * 25.0f;
                    bool inBeam = (dist <= 45.0f && angleDeg <= 18.0f);
                    if (StealthAndDetectionSystem.Instance != null)
                    {
                        StealthAndDetectionSystem.Instance.SetPlayerInSearchlight(inBeam);
                    }
                    break;

                case TrapType.T11_SecurityCamera:
                    if (dist <= cameraRangeMeters && angleDeg <= (cameraFovDegrees * 0.5f))
                    {
                        if (StealthAndDetectionSystem.Instance != null)
                        {
                            TriggerAlarmNoise(35.0f);
                        }
                    }
                    break;

                case TrapType.T12_ElectricFence:
                    if (linkedPowerSource != null && !linkedPowerSource.isPoweredOn)
                    {
                        isArmed = false;
                        break;
                    }
                    if (dist <= 0.85f)
                    {
                        TriggerT12ElectricFence();
                    }
                    break;

                case TrapType.T15_DogPatrolHazard:
                    if (_dogMeatDistractionTimer <= 0f && StealthAndDetectionSystem.Instance != null)
                    {
                        if (StealthAndDetectionSystem.Instance.IsPlayerScentReachingDog(player.transform.position, transform.position, T15_SCENT_CONE_RANGE))
                        {
                            TriggerAlarmNoise(28.0f, NoiseCategory.DogBark);
                            if (dist <= 1.8f && _damageCooldownTimer <= 0f)
                            {
                                _damageCooldownTimer = DAMAGE_RETRIGGER_COOLDOWN;
                                OnPlayerDamaged?.Invoke(this, T15_BITE_DAMAGE);
                            }
                        }
                    }
                    break;

                case TrapType.T16_EnvironmentalHazard:
                    EvaluateT16EnvironmentalHazard(player, dist, deltaTime);
                    break;
            }
        }

        public void TriggerDoorOpenedFast()
        {
            if (!IsCurrentlyActive) return;
            if (trapType == TrapType.T13_AlarmedDoor)
            {
                TriggerAlarmNoise(45.0f);
            }
            else if (trapType == TrapType.T14_BoobyTrappedDoor)
            {
                isArmed = false;
                OnPlayerDamaged?.Invoke(this, T14_DAMAGE);
                StealthAndDetectionSystem.Instance?.EmitNoise(transform.position, 50.0f, NoiseCategory.Explosion, true);
            }
        }

        private void TriggerT1TripwireAlarm()
        {
            isArmed = false;
            StealthAndDetectionSystem.Instance?.EmitNoise(transform.position, T1_NOISE_RADIUS, NoiseCategory.AlarmSiren, true);
        }

        private void TriggerT2TripwireGrenade(float playerDist)
        {
            isArmed = false;
            if (playerDist <= T2_BLAST_RADIUS)
            {
                OnPlayerDamaged?.Invoke(this, T2_DAMAGE);
            }
            StealthAndDetectionSystem.Instance?.EmitNoise(transform.position, 55.0f, NoiseCategory.Explosion, true);
        }

        private void TriggerT3DirectionalMine(float playerDist)
        {
            isArmed = false;
            if (playerDist <= T3_RANGE)
            {
                OnPlayerDamaged?.Invoke(this, T3_DAMAGE);
            }
            StealthAndDetectionSystem.Instance?.EmitNoise(transform.position, 60.0f, NoiseCategory.Explosion, true);
        }

        private void TriggerT4BuriedMine()
        {
            isArmed = false;
            OnPlayerDamaged?.Invoke(this, T4_DAMAGE);
            StealthAndDetectionSystem.Instance?.EmitNoise(transform.position, 65.0f, NoiseCategory.Explosion, true);
        }

        private void TriggerT5LaserGrid()
        {
            TriggerAlarmNoise(45.0f);
        }

        private void TriggerT6MotionSensor()
        {
            TriggerAlarmNoise(35.0f);
        }

        private void TriggerT7PressurePlate()
        {
            isArmed = false;
            StealthAndDetectionSystem.Instance?.EmitNoise(transform.position, 40.0f, NoiseCategory.AlarmSiren, true);
        }

        private void TriggerT8NoiseTrap()
        {
            TriggerAlarmNoise(T8_NOISE_RADIUS, NoiseCategory.TrapNoise, false);
        }

        private void FireT9SentryTurret(float deltaTime)
        {
            float shotsPerSec = T9_RPM / 60.0f; // 600 RPM = 10 shots/sec
            _turretFireAccumulator += deltaTime * shotsPerSec;
            while (_turretFireAccumulator >= 1.0f)
            {
                _turretFireAccumulator -= 1.0f;
                OnPlayerDamaged?.Invoke(this, T9_DAMAGE_PER_SHOT);
            }
        }

        private void TriggerT12ElectricFence()
        {
            if (_damageCooldownTimer <= 0f)
            {
                _damageCooldownTimer = DAMAGE_RETRIGGER_COOLDOWN;
                OnPlayerDamaged?.Invoke(this, T12_SHOCK_DAMAGE);
            }
            TriggerAlarmNoise(14.0f, NoiseCategory.TrapNoise, false);
        }

        private void TriggerAlarmNoise(float radius, NoiseCategory category = NoiseCategory.AlarmSiren, bool escalates = true)
        {
            if (_alarmCooldownTimer > 0f) return;
            _alarmCooldownTimer = ALARM_RETRIGGER_COOLDOWN;
            StealthAndDetectionSystem.Instance?.EmitNoise(transform.position, radius, category, escalates);
        }

        private void ApplyPeriodicDamage(float damagePerSecond)
        {
            if (_damageCooldownTimer > 0f) return;
            _damageCooldownTimer = DAMAGE_RETRIGGER_COOLDOWN;
            OnPlayerDamaged?.Invoke(this, damagePerSecond * DAMAGE_RETRIGGER_COOLDOWN);
        }

        private void EvaluateT16EnvironmentalHazard(PlayerTacticalController player, float dist, float deltaTime)
        {
            if (dist > 1.8f) return;
            switch (envSubType)
            {
                case EnvironmentalHazardSubType.ThinIce:
                    if (player.CurrentPosture != PlayerPosture.Prone)
                    {
                        isArmed = false;
                        OnPlayerDamaged?.Invoke(this, 85.0f);
                        StealthAndDetectionSystem.Instance?.EmitNoise(transform.position, 18.0f, NoiseCategory.TrapNoise, false);
                    }
                    break;
                case EnvironmentalHazardSubType.LiveRail:
                    if (linkedPowerSource == null || linkedPowerSource.isPoweredOn)
                    {
                        ApplyPeriodicDamage(180.0f);
                    }
                    break;
                case EnvironmentalHazardSubType.SteamVent:
                    ApplyPeriodicDamage(35.0f);
                    break;
            }
        }
    }
}
