using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using RealLoserStudio.Tactical.AI;
using RealLoserStudio.Tactical.Player;
using RealLoserStudio.Tactical.Stealth;
using RealLoserStudio.Tactical.Streaming;

namespace RealLoserStudio.Tactical.Core
{
    public enum MissionObjectiveState
    {
        Locked,
        Available,
        InProgress,
        Completed,
        Failed
    }

    [Serializable]
    public sealed class MissionObjectiveStep
    {
        public string id;
        public Vector3 position;
        public bool hasPosition;
        public bool requiresExplicitInteraction;
        public string eventId;
        public string alternativeGroup;
        public bool completed;
    }

    [Serializable]
    public sealed class MissionObjectiveDefinition
    {
        public string id;
        public string title;
        public bool primary;
        public List<MissionObjectiveStep> steps = new List<MissionObjectiveStep>();
    }

    /// <summary>
    /// Small, Unity-independent state machine used by the runtime and regression tests.
    /// Proximity only selects an interactable step; it never completes a step by itself.
    /// </summary>
    public sealed class MissionObjectiveStateMachine
    {
        private readonly List<MissionObjectiveDefinition> _definitions;
        private readonly Dictionary<string, MissionObjectiveState> _states = new Dictionary<string, MissionObjectiveState>(StringComparer.OrdinalIgnoreCase);
        private readonly Dictionary<string, int> _completedSteps = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);

        public MissionObjectiveStateMachine(List<MissionObjectiveDefinition> definitions)
        {
            _definitions = definitions ?? new List<MissionObjectiveDefinition>();
            for (int i = 0; i < _definitions.Count; i++)
            {
                MissionObjectiveDefinition definition = _definitions[i];
                if (definition == null || string.IsNullOrEmpty(definition.id)) continue;
                _states[definition.id] = MissionObjectiveState.Available;
                _completedSteps[definition.id] = 0;
            }
        }

        public IList<MissionObjectiveDefinition> Definitions { get { return _definitions; } }

        public MissionObjectiveState GetState(string id)
        {
            MissionObjectiveState state;
            return id != null && _states.TryGetValue(id, out state) ? state : MissionObjectiveState.Locked;
        }

        public int GetCompletedStepCount(string id)
        {
            int count;
            return id != null && _completedSteps.TryGetValue(id, out count) ? count : 0;
        }

        public bool IsCompleted(string id)
        {
            return GetState(id) == MissionObjectiveState.Completed;
        }

        public bool CompleteNextExplicitStep(string id)
        {
            MissionObjectiveDefinition definition = Find(id);
            if (definition == null || IsCompleted(id)) return false;
            int index = NextStepIndex(definition, true);
            if (index < 0) return false;
            definition.steps[index].completed = true;
            AdvanceState(definition);
            return true;
        }

        /// <summary>
        /// Returns the next required action only when it is spatial and explicitly interactable.
        /// Ordered event/condition steps block later spatial steps until they are satisfied.
        /// </summary>
        public int GetNextInteractableStepIndex(string id)
        {
            MissionObjectiveDefinition definition = Find(id);
            if (definition == null || IsCompleted(id)) return -1;
            for (int i = 0; i < definition.steps.Count; i++)
            {
                MissionObjectiveStep step = definition.steps[i];
                if (step.completed || IsAlternativeSatisfied(definition, step)) continue;
                return step.requiresExplicitInteraction && step.hasPosition ? i : -1;
            }
            return -1;
        }

        /// <summary>Completes exactly the step the player interacted with, never a different target.</summary>
        public bool CompleteExplicitStep(string id, int stepIndex)
        {
            MissionObjectiveDefinition definition = Find(id);
            if (definition == null || IsCompleted(id) || stepIndex < 0 || stepIndex >= definition.steps.Count) return false;
            if (GetNextInteractableStepIndex(id) != stepIndex) return false;
            MissionObjectiveStep step = definition.steps[stepIndex];
            if (step.completed || !step.requiresExplicitInteraction || !step.hasPosition) return false;
            step.completed = true;
            AdvanceState(definition);
            return true;
        }

        public bool MarkEvent(string eventId)
        {
            if (string.IsNullOrEmpty(eventId)) return false;
            bool changed = false;
            for (int i = 0; i < _definitions.Count; i++)
            {
                MissionObjectiveDefinition definition = _definitions[i];
                if (definition == null || IsCompleted(definition.id)) continue;
                for (int s = 0; s < definition.steps.Count; s++)
                {
                    MissionObjectiveStep step = definition.steps[s];
                    if (!step.completed && string.Equals(step.eventId, eventId, StringComparison.OrdinalIgnoreCase))
                    {
                        step.completed = true;
                        changed = true;
                        AdvanceState(definition);
                    }
                }
            }
            return changed;
        }

        public bool MarkConditionMet(string id)
        {
            MissionObjectiveDefinition definition = Find(id);
            if (definition == null || IsCompleted(id)) return false;
            for (int i = 0; i < definition.steps.Count; i++) definition.steps[i].completed = true;
            if (definition.steps.Count == 0) definition.steps.Add(new MissionObjectiveStep { id = id });
            AdvanceState(definition);
            return IsCompleted(id);
        }

        public bool CanExtract()
        {
            for (int i = 0; i < _definitions.Count; i++)
            {
                if (_definitions[i] != null && _definitions[i].primary && !IsCompleted(_definitions[i].id)) return false;
            }
            return true;
        }

        public List<string> GetCompletedIds()
        {
            List<string> result = new List<string>();
            for (int i = 0; i < _definitions.Count; i++)
            {
                MissionObjectiveDefinition definition = _definitions[i];
                if (definition != null && IsCompleted(definition.id)) result.Add(definition.id);
            }
            return result;
        }

        public void RestoreCompletedIds(IList<string> ids)
        {
            if (ids == null) return;
            for (int i = 0; i < ids.Count; i++) MarkConditionMet(ids[i]);
        }

        private MissionObjectiveDefinition Find(string id)
        {
            if (string.IsNullOrEmpty(id)) return null;
            for (int i = 0; i < _definitions.Count; i++)
            {
                if (_definitions[i] != null && string.Equals(_definitions[i].id, id, StringComparison.OrdinalIgnoreCase)) return _definitions[i];
            }
            return null;
        }

        private int NextStepIndex(MissionObjectiveDefinition definition, bool explicitOnly)
        {
            for (int i = 0; i < definition.steps.Count; i++)
            {
                MissionObjectiveStep step = definition.steps[i];
                if (!step.completed && !IsAlternativeSatisfied(definition, step) && (!explicitOnly || step.requiresExplicitInteraction)) return i;
            }
            return -1;
        }

        private void AdvanceState(MissionObjectiveDefinition definition)
        {
            int completed = 0;
            for (int i = 0; i < definition.steps.Count; i++) if (definition.steps[i].completed) completed++;
            _completedSteps[definition.id] = completed;
            _states[definition.id] = IsDefinitionComplete(definition)
                ? MissionObjectiveState.Completed
                : (completed > 0 ? MissionObjectiveState.InProgress : MissionObjectiveState.Available);
        }

        private static bool IsAlternativeSatisfied(MissionObjectiveDefinition definition, MissionObjectiveStep candidate)
        {
            if (string.IsNullOrEmpty(candidate.alternativeGroup)) return false;
            for (int i = 0; i < definition.steps.Count; i++)
            {
                MissionObjectiveStep step = definition.steps[i];
                if (step.completed && string.Equals(step.alternativeGroup, candidate.alternativeGroup, StringComparison.OrdinalIgnoreCase)) return true;
            }
            return false;
        }

        private static bool IsDefinitionComplete(MissionObjectiveDefinition definition)
        {
            for (int i = 0; i < definition.steps.Count; i++)
            {
                MissionObjectiveStep step = definition.steps[i];
                if (step.completed || IsAlternativeSatisfied(definition, step)) continue;
                return false;
            }
            return true;
        }
    }

    /// <summary>
    /// Runtime mission objective coordinator. It is deliberately event/interaction driven:
    /// walking into an anchor does not complete anything. E/Touch calls TryInteract, while
    /// enemy neutralization is observed as an objective event rather than proximity.
    /// </summary>
    public sealed class MissionObjectiveRuntime : MonoBehaviour
    {
        public const string MissionCompleteMarker = "__MISSION_COMPLETE__";

        [Header("Interaction")]
        public float interactionRadius = 4.5f;
        public float extractionHoldSeconds = 1.0f;

        public PlayerTacticalController playerController { get; private set; }
        public MissionObjectiveStateMachine StateMachine { get; private set; }
        public bool MissionCompleted { get; private set; }
        public bool ExtractionUnlocked { get { return StateMachine != null && StateMachine.CanExtract(); } }
        public string LastMessage { get; private set; }
        public string CheckpointPath { get; private set; }

        private RuntimeMissionSpawner.MissionBlueprintData _blueprint;
        private List<EnemyAIFSMSystem> _enemies;
        private MissionEventAndStreamingSystem _streamingSystem;
        private Vector3 _extractionPosition;
        private float _extractionRadius = 10f;
        private bool _initialized;
        private float _elapsed;
        private float _extractHold;
        private readonly HashSet<string> _observedEnemyEvents = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        public event Action<string, MissionObjectiveState> ObjectiveStateChanged;
        public event Action<string> MessageChanged;
        public event Action MissionCompletedEvent;

        public void Initialize(RuntimeMissionSpawner.MissionBlueprintData blueprint,
            PlayerTacticalController player, StealthAndDetectionSystem stealth,
            MissionEventAndStreamingSystem streaming, IList<EnemyAIFSMSystem> enemies,
            string checkpointPath)
        {
            _blueprint = blueprint;
            playerController = player;
            _streamingSystem = streaming;
            _enemies = enemies != null ? new List<EnemyAIFSMSystem>(enemies) : new List<EnemyAIFSMSystem>();
            CheckpointPath = string.IsNullOrEmpty(checkpointPath)
                ? Path.Combine(Application.persistentDataPath, "Missions", (blueprint != null ? blueprint.mission_id : "mission") + ".checkpoint.json")
                : checkpointPath;
            List<MissionObjectiveDefinition> definitions = BuildDefinitions(blueprint);
            StateMachine = new MissionObjectiveStateMachine(definitions);
            MissionCompleted = false;
            _extractHold = 0f;
            _elapsed = 0f;
            if (blueprint != null && blueprint.objectives != null && blueprint.objectives.extraction != null)
            {
                _extractionPosition = ToWorld(blueprint.objectives.extraction.pos);
                _extractionRadius = Mathf.Max(0.5f, blueprint.objectives.extraction.radius);
            }
            MissionSaveData save = MissionEventAndStreamingSystem.LoadCheckpoint(CheckpointPath);
            if (save != null && string.Equals(save.missionId, blueprint != null ? blueprint.mission_id : string.Empty, StringComparison.OrdinalIgnoreCase))
            {
                StateMachine.RestoreCompletedIds(save.completedObjectives);
                for (int savedIndex = 0; save.completedObjectives != null && savedIndex < save.completedObjectives.Count; savedIndex++)
                {
                    if (string.Equals(save.completedObjectives[savedIndex], MissionCompleteMarker, StringComparison.OrdinalIgnoreCase))
                    {
                        MissionCompleted = true;
                        break;
                    }
                }
                LastMessage = "Checkpoint restored";
            }
            _initialized = true;
            PublishMessage(LastMessage ?? "Objectives ready");
        }

        public void TickObjectiveRuntime(float deltaTime)
        {
            if (!_initialized || StateMachine == null || MissionCompleted) return;
            _elapsed += Mathf.Max(0f, deltaTime);
            for (int i = 0; i < _enemies.Count; i++)
            {
                EnemyAIFSMSystem enemy = _enemies[i];
                if (enemy == null || !enemy.IsNeutralized || string.IsNullOrEmpty(enemy.agentId)) continue;
                if (_observedEnemyEvents.Add(enemy.agentId) && StateMachine.MarkEvent(enemy.agentId))
                {
                    PublishMessage("Target neutralized: " + enemy.agentId);
                    SaveCheckpoint();
                    PublishAllStates();
                }
            }
        }

        public bool TryInteract()
        {
            if (!_initialized || playerController == null || StateMachine == null || MissionCompleted) return false;
            MissionObjectiveDefinition bestDefinition = null;
            int bestStepIndex = -1;
            float bestDistance = float.MaxValue;
            for (int i = 0; i < StateMachine.Definitions.Count; i++)
            {
                MissionObjectiveDefinition definition = StateMachine.Definitions[i];
                if (definition == null || StateMachine.IsCompleted(definition.id)) continue;
                int s = StateMachine.GetNextInteractableStepIndex(definition.id);
                if (s < 0) continue;
                MissionObjectiveStep step = definition.steps[s];
                float distance = Vector3.Distance(playerController.transform.position, step.position);
                if (distance <= interactionRadius && distance < bestDistance)
                {
                    bestDistance = distance;
                    bestDefinition = definition;
                    bestStepIndex = s;
                }
            }
            if (bestDefinition != null)
            {
                string id = bestDefinition.id;
                bool changed = StateMachine.CompleteExplicitStep(id, bestStepIndex);
                if (changed)
                {
                    PublishMessage(StateMachine.IsCompleted(id) ? "Objective complete: " + id : "Objective progress: " + id);
                    SaveCheckpoint();
                    PublishState(id);
                    return true;
                }
            }
            if (ExtractionUnlocked && Vector3.Distance(playerController.transform.position, _extractionPosition) <= Mathf.Max(_extractionRadius, interactionRadius))
            {
                MissionCompleted = true;
                _extractHold = 0f;
                SaveCheckpoint(true);
                PublishMessage("Mission complete: extraction confirmed");
                if (MissionCompletedEvent != null) MissionCompletedEvent();
                return true;
            }
            PublishMessage(ExtractionUnlocked ? "No interactable target in range" : "Required objectives incomplete");
            return false;
        }

        public bool NotifyObjectiveEvent(string eventId)
        {
            if (StateMachine == null || string.IsNullOrEmpty(eventId)) return false;
            bool changed = StateMachine.MarkEvent(eventId);
            if (changed)
            {
                PublishMessage("Objective event: " + eventId);
                SaveCheckpoint();
                PublishAllStates();
            }
            return changed;
        }

        public bool NotifyObjectiveConditionMet(string objectiveId)
        {
            if (StateMachine == null) return false;
            bool changed = StateMachine.MarkConditionMet(objectiveId);
            if (changed)
            {
                PublishMessage("Condition complete: " + objectiveId);
                SaveCheckpoint();
                PublishState(objectiveId);
            }
            return changed;
        }

        public bool RetryFromCheckpoint()
        {
            if (StateMachine == null) return false;
            MissionSaveData save = MissionEventAndStreamingSystem.LoadCheckpoint(CheckpointPath);
            if (save == null) return false;
            StateMachine = new MissionObjectiveStateMachine(BuildDefinitions(_blueprint));
            StateMachine.RestoreCompletedIds(save.completedObjectives);
            MissionCompleted = false;
            _extractHold = 0f;
            if (playerController != null) playerController.transform.position = save.playerPosition;
            PublishMessage("Retrying from checkpoint");
            PublishAllStates();
            return true;
        }

        public void RetryMission()
        {
            StateMachine = new MissionObjectiveStateMachine(BuildDefinitions(_blueprint));
            MissionCompleted = false;
            _extractHold = 0f;
            if (File.Exists(CheckpointPath)) File.Delete(CheckpointPath);
            PublishMessage("Mission restarted");
            PublishAllStates();
        }

        public string GetHudSummary()
        {
            if (StateMachine == null) return "OBJECTIVES: loading";
            List<string> completed = StateMachine.GetCompletedIds();
            int total = StateMachine.Definitions.Count;
            return MissionCompleted ? "MISSION COMPLETE" : "OBJECTIVES " + completed.Count + "/" + total + (ExtractionUnlocked ? " | EXTRACT UNLOCKED" : "");
        }

        public string GetObjectiveReadout()
        {
            if (StateMachine == null) return "Objectives loading";
            for (int i = 0; i < StateMachine.Definitions.Count; i++)
            {
                MissionObjectiveDefinition d = StateMachine.Definitions[i];
                if (d != null && !StateMachine.IsCompleted(d.id))
                {
                    return (d.primary ? "PRIMARY " : "SECONDARY ") + d.id + ": " + d.title;
                }
            }
            return ExtractionUnlocked ? "EXTRACTION: interact at the marked LZ" : "All objectives complete";
        }

        public static List<MissionObjectiveDefinition> BuildObjectiveDefinitionsForTests(RuntimeMissionSpawner.MissionBlueprintData blueprint)
        {
            return BuildDefinitions(blueprint);
        }

        private void SaveCheckpoint(bool missionComplete = false)
        {
            if (StateMachine == null || _blueprint == null) return;
            MissionSaveData data = new MissionSaveData
            {
                missionId = _blueprint.mission_id,
                playerPosition = playerController != null ? playerController.transform.position : Vector3.zero,
                playerHealth = 100f,
                completedObjectives = StateMachine.GetCompletedIds()
            };
            if (missionComplete) data.completedObjectives.Add(MissionCompleteMarker);
            try { MissionEventAndStreamingSystem.SaveCheckpoint(data, CheckpointPath); }
            catch (Exception ex) { Debug.LogWarning("[MissionObjectiveRuntime] Checkpoint save failed: " + ex.Message); }
        }

        private void PublishState(string id)
        {
            if (ObjectiveStateChanged != null) ObjectiveStateChanged(id, StateMachine.GetState(id));
        }

        private void PublishAllStates()
        {
            if (StateMachine == null) return;
            for (int i = 0; i < StateMachine.Definitions.Count; i++)
            {
                if (StateMachine.Definitions[i] != null) PublishState(StateMachine.Definitions[i].id);
            }
        }

        private void PublishMessage(string message)
        {
            LastMessage = message;
            if (MessageChanged != null) MessageChanged(message);
        }

        private static List<MissionObjectiveDefinition> BuildDefinitions(RuntimeMissionSpawner.MissionBlueprintData blueprint)
        {
            List<MissionObjectiveDefinition> result = new List<MissionObjectiveDefinition>();
            if (blueprint == null || blueprint.objectives == null) return result;
            AddPrimaryDefinitions(result, blueprint);
            AddSecondaryDefinitions(result, blueprint);
            return result;
        }

        private static void AddPrimaryDefinitions(List<MissionObjectiveDefinition> result, RuntimeMissionSpawner.MissionBlueprintData b)
        {
            if (b.objectives.primary == null) return;
            for (int i = 0; i < b.objectives.primary.Count; i++)
            {
                RuntimeMissionSpawner.PrimaryObjectiveData p = b.objectives.primary[i];
                if (p == null || string.IsNullOrEmpty(p.id)) continue;
                MissionObjectiveDefinition d = NewDefinition(p.id, p.title, true);
                int targetStepStart = d.steps.Count;
                if (IsEnemyId(b, p.target_id) && RequiresNeutralization(p.title)) AddEventStep(d, p.target_id);
                else AddPositionStep(d, p.target_id, p.target_pos);
                AddPositionStep(d, "cell", p.cell_pos);
                AddPositionStep(d, "checkpoint", p.checkpoint_pos);
                AddPositionStep(d, "truck", p.truck_pos);
                AddAxisStep(d, "checkpoint_alpha", p.checkpoint_alpha_x, p.truck_pos);
                AddAxisStep(d, "checkpoint_bravo", p.checkpoint_bravo_x, p.truck_pos);
                AddPositionStep(d, "uplink", p.uplink_pos);
                AddPositionStep(d, p.boss_id, p.boss_pos, !string.IsNullOrEmpty(p.boss_id));
                AddPositionStep(d, "delivery", p.delivery_pos);
                AddPositionStep(d, "extraction", p.extraction_pos);
                AddPositionStep(d, p.alternate_target_id, p.alternate_pos, false);
                if (!string.IsNullOrEmpty(p.alternate_target_id) && d.steps.Count > targetStepStart)
                {
                    for (int alternateIndex = targetStepStart; alternateIndex < d.steps.Count; alternateIndex++)
                    {
                        if (string.Equals(d.steps[alternateIndex].id, p.target_id, StringComparison.OrdinalIgnoreCase) ||
                            string.Equals(d.steps[alternateIndex].id, p.alternate_target_id, StringComparison.OrdinalIgnoreCase))
                        {
                            d.steps[alternateIndex].alternativeGroup = "alternate_target";
                        }
                    }
                }
                AddPositionStep(d, p.manifolds != null && p.manifolds.Length > 0 ? "manifolds" : null, null);
                if (p.manifolds != null) for (int m = 0; m < p.manifolds.Length; m++) if (p.manifolds[m] != null) AddPositionStep(d, p.manifolds[m].id, p.manifolds[m].pos);
                AddResolvedExplicitSteps(d, b, p.target_vehicles);
                AddEventSteps(d, p.required_snipers);
                if (d.steps.Count == 0) d.steps.Add(new MissionObjectiveStep { id = p.id, requiresExplicitInteraction = true });
                result.Add(d);
            }
        }

        private static void AddSecondaryDefinitions(List<MissionObjectiveDefinition> result, RuntimeMissionSpawner.MissionBlueprintData b)
        {
            if (b.objectives.secondary == null) return;
            for (int i = 0; i < b.objectives.secondary.Count; i++)
            {
                RuntimeMissionSpawner.SecondaryObjectiveData s = b.objectives.secondary[i];
                if (s == null || string.IsNullOrEmpty(s.id)) continue;
                MissionObjectiveDefinition d = NewDefinition(s.id, s.title, false);
                if (IsEnemyId(b, s.target_id) && RequiresNeutralization(s.title)) AddEventStep(d, s.target_id);
                else AddPositionStep(d, s.target_id, s.target_pos);
                AddPositionStep(d, s.target_pickup_id, FindPickupCoordinates(b, s.target_pickup_id));
                AddResolvedExplicitSteps(d, b, s.target_ids);
                AddResolvedExplicitSteps(d, b, s.required_pickups);
                AddEventSteps(d, s.target_enemies);
                if (s.control_boxes != null) for (int c = 0; c < s.control_boxes.Length; c++) if (s.control_boxes[c] != null) AddPositionStep(d, s.control_boxes[c].id, s.control_boxes[c].pos);
                AddResolvedExplicitStep(d, b, s.breaker_id);
                AddResolvedExplicitSteps(d, b, s.disabled_cameras);
                AddPositionStep(d, "fallback", FindPickupCoordinates(b, s.fallback_safe_id));
                if (d.steps.Count == 0) d.steps.Add(new MissionObjectiveStep { id = s.id, requiresExplicitInteraction = false });
                result.Add(d);
            }
        }

        private static MissionObjectiveDefinition NewDefinition(string id, string title, bool primary)
        {
            return new MissionObjectiveDefinition { id = id, title = title ?? string.Empty, primary = primary };
        }

        private static void AddEventSteps(MissionObjectiveDefinition d, string[] ids)
        {
            if (ids == null) return;
            for (int i = 0; i < ids.Length; i++) AddEventStep(d, ids[i]);
        }

        private static void AddResolvedExplicitSteps(MissionObjectiveDefinition d, RuntimeMissionSpawner.MissionBlueprintData b, string[] ids)
        {
            if (ids == null) return;
            for (int i = 0; i < ids.Length; i++) AddResolvedExplicitStep(d, b, ids[i]);
        }

        private static void AddResolvedExplicitStep(MissionObjectiveDefinition d, RuntimeMissionSpawner.MissionBlueprintData b, string id)
        {
            if (string.IsNullOrEmpty(id)) return;
            float[] coordinates = FindAnyCoordinates(b, id);
            if (coordinates != null) AddPositionStep(d, id, coordinates);
            else AddEventStep(d, id);
        }

        private static void AddEventStep(MissionObjectiveDefinition d, string id)
        {
            if (d == null || string.IsNullOrEmpty(id)) return;
            d.steps.Add(new MissionObjectiveStep { id = id, eventId = id, requiresExplicitInteraction = false });
        }

        private static void AddPositionStep(MissionObjectiveDefinition d, string id, float[] coordinates, bool eventBacked = false)
        {
            if (d == null || coordinates == null || coordinates.Length < 2) return;
            d.steps.Add(new MissionObjectiveStep { id = string.IsNullOrEmpty(id) ? d.id : id, position = ToWorld(coordinates), hasPosition = true, requiresExplicitInteraction = !eventBacked, eventId = eventBacked ? id : null });
        }

        private static void AddAxisStep(MissionObjectiveDefinition d, string id, float x, float[] reference)
        {
            if (Mathf.Abs(x) < 0.001f || reference == null || reference.Length < 2) return;
            AddPositionStep(d, id, new[] { x, reference[1], reference.Length > 2 ? reference[2] : 0f });
        }

        private static bool IsEnemyId(RuntimeMissionSpawner.MissionBlueprintData b, string id)
        {
            if (b == null || b.enemies == null || string.IsNullOrEmpty(id)) return false;
            for (int i = 0; i < b.enemies.Count; i++) if (b.enemies[i] != null && string.Equals(b.enemies[i].id, id, StringComparison.OrdinalIgnoreCase)) return true;
            return false;
        }

        private static bool RequiresNeutralization(string title)
        {
            if (string.IsNullOrEmpty(title)) return false;
            string normalized = title.ToLowerInvariant();
            return normalized.Contains("eliminate") || normalized.Contains("assassinate") || normalized.Contains("kill") || normalized.Contains("neutralize");
        }

        private static float[] FindAnyCoordinates(RuntimeMissionSpawner.MissionBlueprintData b, string id)
        {
            if (b == null || string.IsNullOrEmpty(id)) return null;
            if (b.enemies != null) for (int i = 0; i < b.enemies.Count; i++) if (b.enemies[i] != null && string.Equals(b.enemies[i].id, id, StringComparison.OrdinalIgnoreCase)) return b.enemies[i].pos;
            if (b.pickups != null) for (int i = 0; i < b.pickups.Count; i++) if (b.pickups[i] != null && string.Equals(b.pickups[i].id, id, StringComparison.OrdinalIgnoreCase)) return b.pickups[i].pos;
            if (b.props != null) for (int i = 0; i < b.props.Count; i++) if (b.props[i] != null && string.Equals(b.props[i].id, id, StringComparison.OrdinalIgnoreCase)) return b.props[i].pos;
            if (b.structures != null) for (int i = 0; i < b.structures.Count; i++) if (b.structures[i] != null && string.Equals(b.structures[i].id, id, StringComparison.OrdinalIgnoreCase)) return b.structures[i].pos;
            if (b.traps != null) for (int i = 0; i < b.traps.Count; i++) if (b.traps[i] != null && string.Equals(b.traps[i].id, id, StringComparison.OrdinalIgnoreCase)) return b.traps[i].pos;
            if (b.cameras != null) for (int i = 0; i < b.cameras.Count; i++) if (b.cameras[i] != null && string.Equals(b.cameras[i].id, id, StringComparison.OrdinalIgnoreCase)) return b.cameras[i].pos;
            return null;
        }

        private static float[] FindPickupCoordinates(RuntimeMissionSpawner.MissionBlueprintData b, string id)
        {
            if (b == null || b.pickups == null || string.IsNullOrEmpty(id)) return null;
            for (int i = 0; i < b.pickups.Count; i++) if (b.pickups[i] != null && string.Equals(b.pickups[i].id, id, StringComparison.OrdinalIgnoreCase)) return b.pickups[i].pos;
            return null;
        }

        private static Vector3 ToWorld(float[] a)
        {
            if (a == null || a.Length < 2) return Vector3.zero;
            return new Vector3(a[0], a.Length > 2 ? a[2] : 0f, a[1]);
        }
    }
}
