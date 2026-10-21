using System;
using System.Collections.Generic;
using UnityEngine;
using RealLoserStudio.Tactical.Player;
using RealLoserStudio.Tactical.Stealth;
using RealLoserStudio.Tactical.Traps;

namespace RealLoserStudio.Tactical.AI
{
    public enum EnemyClassId
    {
        E1_Recruit = 1,
        E2_Rifleman = 2,
        E3_Officer = 3,          // RadioCheckIn every 45s
        E4_Shotgunner = 4,
        E5_SMGRunner = 5,
        E6_Sniper = 6,           // High-ground overwatch (watchtower, roof, cliff ridge)
        E7_HeavyGunner = 7,
        E8_ShieldBreacher = 8,
        E9_Technician = 9,       // RepairCameraAndDisarmC4
        E10_DogHandler = 10,
        E11_Medic = 11,          // ReviveFallenAlly
        E12_EliteCommando = 12,
        E13_GhillieSpotter = 13,
        E14_Juggernaut = 14,
        Civ_Worker = 15,
        Civ_Scientist = 16,
        Civ_Hostage = 17,
        Civ_Technician = 18,
        NPC_DrMirza = 19,
        NPC_Informant = 20,
        Boss_CaptainDar = 21,
        Boss_CommanderRask = 22,
        Boss_ViktorHale = 23
    }

    public enum AIState
    {
        Idle = 0,
        Patrol = 1,
        InvestigateNoise = 2,
        InspectBody = 3,
        RunToAlarm = 4,
        CombatCover = 5,
        Flank = 6,
        RadioCheckIn = 7,            // E3 Officer every 45s
        RepairCameraAndDisarmC4 = 8, // E9 Technician
        ReviveFallenAlly = 9,        // E11 Medic
        IncapacitatedOrDead = 10
    }

    /// <summary>
    /// Full Tactical Enemy & Civilian AI FSM for Project Real Loser (Unity 2022.3 LTS).
    /// Supports E1–E14, Civilians, Key NPCs, and 3 Bosses with specialized states:
    /// - E3 Officer: RadioCheckIn every 45.0s
    /// - E9 Technician: RepairCameraAndDisarmC4
    /// - E11 Medic: ReviveFallenAlly
    /// - E6 Sniper: High-point overwatch
    /// </summary>
    public class EnemyAIFSMSystem : MonoBehaviour
    {
        [Header("Identity & Archetype")]
        public string agentId = "enemy_01";
        public EnemyClassId classId = EnemyClassId.E2_Rifleman;
        public AIState currentState = AIState.Patrol;

        [Header("Patrol Waypoints (>= 3 Required for E1-E14)")]
        public List<Vector3> patrolWaypoints = new List<Vector3>();
        private int _currentWaypointIndex;
        public float patrolMoveSpeed = 2.6f;
        public float combatMoveSpeed = 4.4f;

        [Header("Lightweight Obstacle-Aware Navigation")]
        [Tooltip("World geometry and cover colliders. Runtime mission primitives and GLB proxy colliders use the default layer, so ~0 is intentional unless a project adds dedicated layers.")]
        public LayerMask navigationObstacleMask = ~0;
        [Min(0.1f)] public float navigationAgentRadius = 0.42f;
        [Min(0.5f)] public float navigationBodyHeight = 1.7f;
        [Min(0.1f)] public float navigationProbeDistance = 2.4f;
        [Min(0.05f)] public float navigationReplanInterval = 0.16f;
        private const int NavigationHitBufferSize = 16;
        private static readonly RaycastHit[] NavigationHitBuffer = new RaycastHit[NavigationHitBufferSize];
        private static readonly float[] NavigationCandidateAngles = { 25f, -25f, 50f, -50f, 75f, -75f, 110f, -110f, 180f };
        private Vector3 _cachedNavigationDirection;
        private Vector3 _cachedNavigationTarget;
        private float _navigationReplanTimer;
        private bool _hasCachedNavigationDirection;

        [Header("Perception & Combat Parameters")]
        public float sightRangeMeters = 42.0f;
        public float sightConeAngleDegrees = 85.0f;
        [Tooltip("Layers that can block line of sight. Keep world geometry included; triggers are ignored.")]
        public LayerMask visionOcclusionMask = ~0;
        public float visionOriginHeight = 1.55f;
        public float playerVisionTargetHeight = 1.0f;
        public float maxHitPoints = 100.0f;
        public float currentHitPoints = 100.0f;
        public bool isKnockedOut;
        public bool isDead;

        [Header("Special Role Timers (E3, E9, E11)")]
        public const float E3_RADIO_CHECKIN_INTERVAL = 45.0f;
        private float _radioCheckInTimer = E3_RADIO_CHECKIN_INTERVAL;
        private float _stateActionTimer;

        // Contextual targets
        private Vector3 _investigateTargetPos;
        private EnemyAIFSMSystem _targetFallenAlly;
        private TrapAndHazardSystem _targetDamagedCamera;
        private Transform _nearestAlarmPanel;
        private Transform _nearestCoverNode;

        [Header("Civilian Alarm Routing")]
        [Tooltip("Optional explicit alarm panels. If empty, active objects tagged AlarmPanel or named with alarm+panel are used.")]
        public Transform[] alarmPanels = new Transform[0];

        public bool IsNeutralized => isDead || isKnockedOut;

        private void OnEnable()
        {
            if (StealthAndDetectionSystem.Instance != null)
            {
                StealthAndDetectionSystem.Instance.OnNoiseEmitted += HandleNoiseStimulus;
            }
        }

        private void OnDisable()
        {
            if (StealthAndDetectionSystem.Instance != null)
            {
                StealthAndDetectionSystem.Instance.OnNoiseEmitted -= HandleNoiseStimulus;
            }
        }

        public void TickFSM(PlayerTacticalController player, List<EnemyAIFSMSystem> squadList, List<TrapAndHazardSystem> trapList, float deltaTime)
        {
            if (IsNeutralized)
            {
                currentState = AIState.IncapacitatedOrDead;
                return;
            }

            // E3 Officer: Periodic 45-second Radio Check-In
            if (classId == EnemyClassId.E3_Officer)
            {
                _radioCheckInTimer -= deltaTime;
                if (_radioCheckInTimer <= 0f && currentState != AIState.CombatCover && currentState != AIState.Flank)
                {
                    _radioCheckInTimer = E3_RADIO_CHECKIN_INTERVAL;
                    TransitionToState(AIState.RadioCheckIn, 3.0f);
                }
            }

            // E9 Technician: Scan for destroyed/disabled T11 Security Cameras or planted C4
            if (classId == EnemyClassId.E9_Technician && currentState == AIState.Patrol && trapList != null)
            {
                for (int i = 0; i < trapList.Count; i++)
                {
                    TrapAndHazardSystem t = trapList[i];
                    if (t != null && t.trapType == TrapType.T11_SecurityCamera && (t.isDestroyed || !t.isArmed))
                    {
                        _targetDamagedCamera = t;
                        TransitionToState(AIState.RepairCameraAndDisarmC4, 6.0f);
                        break;
                    }
                }
            }

            // E11 Medic: Scan for knocked-out or downed allies
            if (classId == EnemyClassId.E11_Medic && currentState != AIState.ReviveFallenAlly && squadList != null)
            {
                for (int i = 0; i < squadList.Count; i++)
                {
                    EnemyAIFSMSystem ally = squadList[i];
                    if (ally != null && ally != this && ally.isKnockedOut && !ally.isDead && ally.gameObject.activeInHierarchy)
                    {
                        _targetFallenAlly = ally;
                        TransitionToState(AIState.ReviveFallenAlly, 5.0f);
                        break;
                    }
                }
            }

            // Perception Check against Player
            if (player != null && CanSeePlayer(player))
            {
                if (IsCivilian(classId))
                {
                    if (currentState != AIState.RunToAlarm)
                    {
                        _nearestAlarmPanel = FindNearestAlarmPanel();
                        TransitionToState(AIState.RunToAlarm, 8.0f);
                    }
                }
                else if (classId == EnemyClassId.E5_SMGRunner || classId == EnemyClassId.E12_EliteCommando)
                {
                    TransitionToState(AIState.Flank, 10.0f);
                }
                else
                {
                    TransitionToState(AIState.CombatCover, 12.0f);
                }
            }

            // Execute State Logic
            switch (currentState)
            {
                case AIState.Idle:
                    if (patrolWaypoints.Count >= 3)
                        TransitionToState(AIState.Patrol, 0f);
                    break;

                case AIState.Patrol:
                    UpdatePatrolState(deltaTime);
                    break;

                case AIState.InvestigateNoise:
                    MoveTowardPoint(_investigateTargetPos, patrolMoveSpeed * 1.15f, deltaTime);
                    if (Vector3.Distance(transform.position, _investigateTargetPos) < 1.2f)
                    {
                        _stateActionTimer -= deltaTime;
                        if (_stateActionTimer <= 0f)
                            TransitionToState(AIState.Patrol, 0f);
                    }
                    break;

                case AIState.InspectBody:
                    if (_targetFallenAlly != null)
                    {
                        MoveTowardPoint(_targetFallenAlly.transform.position, combatMoveSpeed, deltaTime);
                        if (Vector3.Distance(transform.position, _targetFallenAlly.transform.position) < 2.0f)
                        {
                            StealthAndDetectionSystem.Instance?.EscalateToAlert(CompoundAlertLevel.Alert2_CompoundAlarm);
                            TransitionToState(AIState.RunToAlarm, 6.0f);
                        }
                    }
                    else
                    {
                        TransitionToState(AIState.Patrol, 0f);
                    }
                    break;

                case AIState.RunToAlarm:
                    if (_nearestAlarmPanel != null && _nearestAlarmPanel.gameObject.activeInHierarchy)
                    {
                        MoveTowardPoint(_nearestAlarmPanel.position, combatMoveSpeed, deltaTime);
                        if (Vector3.Distance(transform.position, _nearestAlarmPanel.position) < 1.5f)
                        {
                            StealthAndDetectionSystem.Instance?.EmitNoise(transform.position, 60.0f, NoiseCategory.AlarmSiren, true);
                            TransitionToState(AIState.CombatCover, 10.0f);
                        }
                    }
                    else
                    {
                        StealthAndDetectionSystem.Instance?.EscalateToAlert(CompoundAlertLevel.Alert2_CompoundAlarm);
                        TransitionToState(AIState.CombatCover, 10.0f);
                    }
                    break;

                case AIState.CombatCover:
                    if (_nearestCoverNode != null)
                        MoveTowardPoint(_nearestCoverNode.position, combatMoveSpeed, deltaTime);
                    break;

                case AIState.Flank:
                    if (player != null)
                    {
                        Vector3 flankOffset = Vector3.Cross(Vector3.up, (player.transform.position - transform.position).normalized) * 6.5f;
                        MoveTowardPoint(player.transform.position + flankOffset, combatMoveSpeed * 1.15f, deltaTime);
                    }
                    break;

                case AIState.RadioCheckIn:
                    _stateActionTimer -= deltaTime;
                    if (_stateActionTimer <= 0f)
                    {
                        // Completed E3 45s radio check-in
                        TransitionToState(AIState.Patrol, 0f);
                    }
                    break;

                case AIState.RepairCameraAndDisarmC4:
                    if (_targetDamagedCamera != null)
                    {
                        MoveTowardPoint(_targetDamagedCamera.transform.position, patrolMoveSpeed * 1.25f, deltaTime);
                        if (Vector3.Distance(transform.position, _targetDamagedCamera.transform.position) <= 2.2f)
                        {
                            _stateActionTimer -= deltaTime;
                            if (_stateActionTimer <= 0f)
                            {
                                _targetDamagedCamera.isDestroyed = false;
                                _targetDamagedCamera.isArmed = true;
                                _targetDamagedCamera.hitPoints = 30.0f;
                                _targetDamagedCamera = null;
                                TransitionToState(AIState.Patrol, 0f);
                            }
                        }
                    }
                    else
                    {
                        TransitionToState(AIState.Patrol, 0f);
                    }
                    break;

                case AIState.ReviveFallenAlly:
                    if (_targetFallenAlly != null && _targetFallenAlly.isKnockedOut && !_targetFallenAlly.isDead)
                    {
                        MoveTowardPoint(_targetFallenAlly.transform.position, combatMoveSpeed, deltaTime);
                        if (Vector3.Distance(transform.position, _targetFallenAlly.transform.position) <= 1.8f)
                        {
                            _stateActionTimer -= deltaTime;
                            if (_stateActionTimer <= 0f)
                            {
                                _targetFallenAlly.isKnockedOut = false;
                                _targetFallenAlly.currentHitPoints = _targetFallenAlly.maxHitPoints * 0.5f;
                                _targetFallenAlly.TransitionToState(AIState.CombatCover, 10.0f);
                                _targetFallenAlly = null;
                                TransitionToState(AIState.CombatCover, 10.0f);
                            }
                        }
                    }
                    else
                    {
                        TransitionToState(AIState.Patrol, 0f);
                    }
                    break;
            }
        }

        private void UpdatePatrolState(float deltaTime)
        {
            if (patrolWaypoints == null || patrolWaypoints.Count == 0) return;

            Vector3 targetWp = patrolWaypoints[_currentWaypointIndex];
            MoveTowardPoint(targetWp, patrolMoveSpeed, deltaTime);

            Vector2 pos2D = new Vector2(transform.position.x, transform.position.z);
            Vector2 wp2D = new Vector2(targetWp.x, targetWp.z);
            if (Vector2.Distance(pos2D, wp2D) <= 0.45f)
            {
                _currentWaypointIndex = (_currentWaypointIndex + 1) % patrolWaypoints.Count;
            }
        }

        private void MoveTowardPoint(Vector3 target, float speed, float deltaTime)
        {
            Vector3 diff = target - transform.position;
            diff.y = 0f;
            float dist = diff.magnitude;
            if (dist < 0.05f) return;

            _navigationReplanTimer -= Mathf.Max(0f, deltaTime);
            bool targetChanged = !_hasCachedNavigationDirection ||
                (_cachedNavigationTarget - target).sqrMagnitude > 1.0f;
            bool needsReplan = targetChanged || _navigationReplanTimer <= 0f;
            if (needsReplan)
            {
                _cachedNavigationTarget = target;
                ReplanNavigationDirection();
            }

            Vector3 dir = _cachedNavigationDirection;
            // A short safety probe runs every tick, while the more expensive candidate
            // search is rate-limited. This prevents a moving target or a corner from
            // carrying a cached direction through an obstacle.
            float safetyDistance = Mathf.Min(
                Mathf.Max(navigationAgentRadius * 1.5f, speed * Mathf.Max(0f, deltaTime) + navigationAgentRadius),
                Mathf.Max(navigationAgentRadius * 2f, navigationProbeDistance));
            if (_hasCachedNavigationDirection && IsNavigationBlocked(transform.position, dir, safetyDistance))
            {
                _navigationReplanTimer = 0f;
                ReplanNavigationDirection();
                dir = _cachedNavigationDirection;
            }

            if (dir.sqrMagnitude < 0.0001f) return;
            transform.rotation = Quaternion.Slerp(transform.rotation, Quaternion.LookRotation(dir, Vector3.up), deltaTime * 8.0f);
            transform.position += dir * Mathf.Min(dist, speed * deltaTime);
        }

        private void ReplanNavigationDirection()
        {
            Vector3 toTarget = _cachedNavigationTarget - transform.position;
            toTarget.y = 0f;
            if (toTarget.sqrMagnitude < 0.0025f)
            {
                _cachedNavigationDirection = Vector3.zero;
                _hasCachedNavigationDirection = true;
                _navigationReplanTimer = navigationReplanInterval;
                return;
            }

            _cachedNavigationDirection = FindSafeNavigationDirection(toTarget.normalized);
            // A blocked corner is treated as a short wait rather than falling back to
            // unsafe direct motion. The next bounded replan can select a new side.
            _hasCachedNavigationDirection = true;
            if (_cachedNavigationDirection.sqrMagnitude < 0.0001f) _cachedNavigationDirection = Vector3.zero;
            _navigationReplanTimer = Mathf.Max(0.05f, navigationReplanInterval);
        }

        private Vector3 FindSafeNavigationDirection(Vector3 desiredDirection)
        {
            float probeDistance = Mathf.Min(
                Mathf.Max(navigationAgentRadius * 2f, navigationProbeDistance),
                Mathf.Max(navigationAgentRadius * 2f, Vector3.Distance(transform.position, _cachedNavigationTarget)));
            if (!IsNavigationBlocked(transform.position, desiredDirection, probeDistance))
                return desiredDirection;

            // Fixed candidates keep CPU and allocations bounded. Candidate order is
            // deterministic, which avoids left/right oscillation at identical corners.
            Vector3 bestDirection = Vector3.zero;
            float bestScore = float.NegativeInfinity;
            for (int i = 0; i < NavigationCandidateAngles.Length; i++)
            {
                Vector3 candidate = Quaternion.AngleAxis(NavigationCandidateAngles[i], Vector3.up) * desiredDirection;
                if (IsNavigationBlocked(transform.position, candidate, probeDistance)) continue;
                float score = Vector3.Dot(candidate, desiredDirection);
                if (score > bestScore)
                {
                    bestScore = score;
                    bestDirection = candidate;
                }
            }
            return bestDirection;
        }

        private bool IsNavigationBlocked(Vector3 origin, Vector3 direction, float distance)
        {
            if (navigationObstacleMask.value == 0 || direction.sqrMagnitude < 0.0001f || distance <= 0.01f)
                return false;

            direction.y = 0f;
            direction.Normalize();
            float radius = Mathf.Max(0.1f, navigationAgentRadius);
            float bodyHeight = Mathf.Max(radius * 2f, navigationBodyHeight);
            Vector3 capsuleBottom = origin + Vector3.up * radius;
            Vector3 capsuleTop = origin + Vector3.up * Mathf.Max(radius, bodyHeight - radius);
            int hitCount = Physics.CapsuleCastNonAlloc(
                capsuleBottom,
                capsuleTop,
                radius,
                direction,
                NavigationHitBuffer,
                distance,
                navigationObstacleMask,
                QueryTriggerInteraction.Ignore);
            for (int i = 0; i < hitCount; i++)
            {
                Collider hitCollider = NavigationHitBuffer[i].collider;
                if (hitCollider == null) continue;
                // Ignore this agent's generated root collider (and any child colliders);
                // all other runtime primitive/GLB proxy colliders remain obstacles.
                if (hitCollider.transform == transform || hitCollider.transform.IsChildOf(transform)) continue;
                return true;
            }
            return false;
        }

        public bool CanSeePlayer(PlayerTacticalController player)
        {
            if (player == null) return false;
            float visFactor = StealthAndDetectionSystem.Instance != null
                ? StealthAndDetectionSystem.Instance.ComputePlayerVisibilityFactor(player)
                : player.ActiveProfile.visibilityMultiplier;

            float effectiveRange = sightRangeMeters * visFactor;
            if (classId == EnemyClassId.E6_Sniper || classId == EnemyClassId.E13_GhillieSpotter)
            {
                effectiveRange *= 1.85f;
            }

            Vector3 toPlayer = player.transform.position - transform.position;
            float dist = toPlayer.magnitude;
            if (dist > effectiveRange) return false;

            float angle = Vector3.Angle(transform.forward, toPlayer.normalized);
            if (angle > (sightConeAngleDegrees * 0.5f)) return false;

            // A cone/range test alone lets AI see through walls. Raycast from an eye-height
            // origin to the player's torso and accept only the player's own collider as the
            // first hit. Trigger volumes are ignored so invisible sensor triggers do not block sight.
            Vector3 origin = transform.position + Vector3.up * Mathf.Max(0f, visionOriginHeight);
            Vector3 target = player.transform.position + Vector3.up * Mathf.Max(0f, playerVisionTargetHeight);
            Vector3 sightVector = target - origin;
            float sightDistance = sightVector.magnitude;
            if (sightDistance <= 0.01f) return true;
            if (Physics.Raycast(origin, sightVector / sightDistance, out RaycastHit hit, sightDistance, visionOcclusionMask, QueryTriggerInteraction.Ignore))
            {
                PlayerTacticalController hitPlayer = hit.collider.GetComponentInParent<PlayerTacticalController>();
                if (hitPlayer != player) return false;
            }

            return true;
        }

        private Transform FindNearestAlarmPanel()
        {
            Transform nearest = null;
            float bestDistance = float.PositiveInfinity;

            if (alarmPanels != null)
            {
                for (int i = 0; i < alarmPanels.Length; i++)
                {
                    Transform candidate = alarmPanels[i];
                    if (candidate == null || !candidate.gameObject.activeInHierarchy) continue;
                    float distance = (candidate.position - transform.position).sqrMagnitude;
                    if (distance < bestDistance)
                    {
                        bestDistance = distance;
                        nearest = candidate;
                    }
                }
            }

            // FindGameObjectsWithTag throws when a project has not declared the tag; treat
            // that as an absent optional integration rather than breaking civilian AI.
            try
            {
                GameObject[] taggedPanels = GameObject.FindGameObjectsWithTag("AlarmPanel");
                for (int i = 0; i < taggedPanels.Length; i++)
                {
                    GameObject candidate = taggedPanels[i];
                    if (candidate == null || !candidate.activeInHierarchy) continue;
                    float distance = (candidate.transform.position - transform.position).sqrMagnitude;
                    if (distance < bestDistance)
                    {
                        bestDistance = distance;
                        nearest = candidate.transform;
                    }
                }
            }
            catch (UnityException)
            {
                // Optional tag is not configured. Use the name-based fallback below.
            }

            if (nearest != null) return nearest;

            Transform[] sceneTransforms = FindObjectsOfType<Transform>();
            for (int i = 0; i < sceneTransforms.Length; i++)
            {
                Transform candidate = sceneTransforms[i];
                if (candidate == null || !candidate.gameObject.activeInHierarchy) continue;
                string candidateName = candidate.name.ToLowerInvariant();
                if (!candidateName.Contains("alarm") || !candidateName.Contains("panel")) continue;
                float distance = (candidate.position - transform.position).sqrMagnitude;
                if (distance < bestDistance)
                {
                    bestDistance = distance;
                    nearest = candidate;
                }
            }
            return nearest;
        }

        private void HandleNoiseStimulus(NoiseStimulus stim)
        {
            if (IsNeutralized) return;
            float dist = Vector3.Distance(transform.position, stim.origin);
            if (dist <= stim.effectiveRadiusMeters)
            {
                _investigateTargetPos = stim.origin;
                if (currentState == AIState.Idle || currentState == AIState.Patrol)
                {
                    TransitionToState(AIState.InvestigateNoise, 8.0f);
                }
            }
        }

        public void ApplyDamage(float dmg, bool nonLethalTakedown = false)
        {
            if (IsNeutralized) return;
            if (nonLethalTakedown)
            {
                isKnockedOut = true;
                currentHitPoints = 1f;
                currentState = AIState.IncapacitatedOrDead;
                return;
            }

            currentHitPoints -= dmg;
            if (currentHitPoints <= 0f)
            {
                isDead = true;
                currentHitPoints = 0f;
                currentState = AIState.IncapacitatedOrDead;
            }
        }

        public void TransitionToState(AIState nextState, float actionDuration)
        {
            currentState = nextState;
            _stateActionTimer = actionDuration;
        }

        public static bool IsCivilian(EnemyClassId id)
        {
            return id == EnemyClassId.Civ_Worker ||
                   id == EnemyClassId.Civ_Scientist ||
                   id == EnemyClassId.Civ_Hostage ||
                   id == EnemyClassId.Civ_Technician;
        }
    }
}
