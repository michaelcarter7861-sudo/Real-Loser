#if UNITY_INCLUDE_TESTS
using System.Collections.Generic;
using System.IO;
using NUnit.Framework;
using UnityEngine;
using RealLoserStudio.Tactical.Core;

namespace RealLoserStudio.Tactical.Tests
{
    public sealed class MissionObjectiveRuntimeRegressionTests
    {
        private static readonly string[] MissionIds = { "M01", "M02", "M03", "M04", "M05", "M06", "M07", "M08", "M09", "M10" };

        [Test]
        public void AllTenMissionSchemasParseAndExposeObjectivesAndExtraction()
        {
            for (int i = 0; i < MissionIds.Length; i++)
            {
                string path = Path.Combine(Application.dataPath, "StreamingAssets/Missions/" + MissionIds[i] + ".json");
                Assert.IsTrue(File.Exists(path), "Missing schema: " + path);
                RuntimeMissionSpawner.MissionBlueprintData blueprint = JsonUtility.FromJson<RuntimeMissionSpawner.MissionBlueprintData>(File.ReadAllText(path));
                Assert.IsNotNull(blueprint, MissionIds[i] + " did not parse");
                Assert.AreEqual(MissionIds[i], blueprint.mission_id);
                Assert.IsNotNull(blueprint.objectives, MissionIds[i] + " has no objectives object");
                Assert.IsNotNull(blueprint.objectives.primary, MissionIds[i] + " has no primary list");
                Assert.Greater(blueprint.objectives.primary.Count, 0, MissionIds[i] + " has no primary objectives");
                Assert.IsNotNull(blueprint.objectives.secondary, MissionIds[i] + " has no secondary list");
                Assert.IsNotNull(blueprint.objectives.extraction, MissionIds[i] + " has no extraction");
                Assert.IsNotNull(blueprint.objectives.extraction.pos);
                Assert.GreaterOrEqual(blueprint.objectives.extraction.pos.Length, 2);
                List<MissionObjectiveDefinition> definitions = MissionObjectiveRuntime.BuildObjectiveDefinitionsForTests(blueprint);
                Assert.AreEqual(blueprint.objectives.primary.Count + blueprint.objectives.secondary.Count, definitions.Count, MissionIds[i] + " objective mapping count mismatch");
            }
        }

        [Test]
        public void ExplicitInteractionDoesNotAutoCompleteUntilActionIsRequested()
        {
            MissionObjectiveDefinition primary = new MissionObjectiveDefinition
            {
                id = "O1",
                primary = true,
                steps = new List<MissionObjectiveStep> {
                    new MissionObjectiveStep { id = "terminal", hasPosition = true, requiresExplicitInteraction = true }
                }
            };
            MissionObjectiveStateMachine machine = new MissionObjectiveStateMachine(new List<MissionObjectiveDefinition> { primary });
            Assert.AreEqual(MissionObjectiveState.Available, machine.GetState("O1"));
            Assert.IsFalse(machine.CanExtract());
            Assert.AreEqual(0, machine.GetNextInteractableStepIndex("O1"));
            Assert.IsTrue(machine.CompleteExplicitStep("O1", 0));
            Assert.AreEqual(MissionObjectiveState.Completed, machine.GetState("O1"));
            Assert.IsTrue(machine.CanExtract());
        }

        [Test]
        public void SelectedSpatialTargetMustMatchTheStepThatCompletes()
        {
            MissionObjectiveDefinition primary = new MissionObjectiveDefinition
            {
                id = "O1",
                primary = true,
                steps = new List<MissionObjectiveStep> {
                    new MissionObjectiveStep { id = "truck", hasPosition = true, requiresExplicitInteraction = true },
                    new MissionObjectiveStep { id = "checkpoint", hasPosition = true, requiresExplicitInteraction = true }
                }
            };
            MissionObjectiveStateMachine machine = new MissionObjectiveStateMachine(new List<MissionObjectiveDefinition> { primary });
            Assert.AreEqual(0, machine.GetNextInteractableStepIndex("O1"));
            Assert.IsFalse(machine.CompleteExplicitStep("O1", 1), "A later coordinate must not complete while the truck step is active.");
            Assert.IsTrue(machine.CompleteExplicitStep("O1", 0));
            Assert.AreEqual(1, machine.GetNextInteractableStepIndex("O1"));
            Assert.IsTrue(machine.CompleteExplicitStep("O1", 1));
            Assert.IsTrue(machine.IsCompleted("O1"));
        }

        [Test]
        public void OrderedEventStepBlocksLaterSpatialInteraction()
        {
            MissionObjectiveDefinition primary = new MissionObjectiveDefinition
            {
                id = "O1",
                primary = true,
                steps = new List<MissionObjectiveStep> {
                    new MissionObjectiveStep { id = "target", eventId = "target", requiresExplicitInteraction = false },
                    new MissionObjectiveStep { id = "uplink", hasPosition = true, requiresExplicitInteraction = true }
                }
            };
            MissionObjectiveStateMachine machine = new MissionObjectiveStateMachine(new List<MissionObjectiveDefinition> { primary });
            Assert.AreEqual(-1, machine.GetNextInteractableStepIndex("O1"));
            Assert.IsFalse(machine.CompleteExplicitStep("O1", 1));
            Assert.IsTrue(machine.MarkEvent("target"));
            Assert.AreEqual(1, machine.GetNextInteractableStepIndex("O1"));
            Assert.IsTrue(machine.CompleteExplicitStep("O1", 1));
            Assert.IsTrue(machine.CanExtract());
        }

        [Test]
        public void MultiStepObjectiveReportsProgressAndRequiresEveryStep()
        {
            MissionObjectiveDefinition primary = new MissionObjectiveDefinition
            {
                id = "O1",
                primary = true,
                steps = new List<MissionObjectiveStep> {
                    new MissionObjectiveStep { id = "A", requiresExplicitInteraction = true },
                    new MissionObjectiveStep { id = "B", requiresExplicitInteraction = true }
                }
            };
            MissionObjectiveStateMachine machine = new MissionObjectiveStateMachine(new List<MissionObjectiveDefinition> { primary });
            Assert.IsTrue(machine.CompleteNextExplicitStep("O1"));
            Assert.AreEqual(MissionObjectiveState.InProgress, machine.GetState("O1"));
            Assert.IsFalse(machine.CanExtract());
            Assert.IsTrue(machine.CompleteNextExplicitStep("O1"));
            Assert.AreEqual(MissionObjectiveState.Completed, machine.GetState("O1"));
        }

        [Test]
        public void EventStepsAndExtractionGateAreIndependentOfProximity()
        {
            MissionObjectiveDefinition primary = new MissionObjectiveDefinition
            {
                id = "O1",
                primary = true,
                steps = new List<MissionObjectiveStep> {
                    new MissionObjectiveStep { id = "boss", eventId = "boss", requiresExplicitInteraction = false },
                    new MissionObjectiveStep { id = "uplink", requiresExplicitInteraction = true }
                }
            };
            MissionObjectiveStateMachine machine = new MissionObjectiveStateMachine(new List<MissionObjectiveDefinition> { primary });
            Assert.IsTrue(machine.MarkEvent("boss"));
            Assert.AreEqual(MissionObjectiveState.InProgress, machine.GetState("O1"));
            Assert.IsFalse(machine.CanExtract());
            Assert.IsTrue(machine.CompleteNextExplicitStep("O1"));
            Assert.IsTrue(machine.CanExtract());
        }

        [Test]
        public void RestoreCompletedIdsAndRetryStateAreDeterministic()
        {
            List<MissionObjectiveDefinition> definitions = new List<MissionObjectiveDefinition> {
                new MissionObjectiveDefinition { id = "O1", primary = true, steps = new List<MissionObjectiveStep> { new MissionObjectiveStep { id = "a", requiresExplicitInteraction = true } } },
                new MissionObjectiveDefinition { id = "S1", primary = false, steps = new List<MissionObjectiveStep> { new MissionObjectiveStep { id = "b", requiresExplicitInteraction = true } } }
            };
            MissionObjectiveStateMachine machine = new MissionObjectiveStateMachine(definitions);
            machine.RestoreCompletedIds(new List<string> { "O1" });
            Assert.IsTrue(machine.IsCompleted("O1"));
            Assert.IsFalse(machine.IsCompleted("S1"));
            Assert.IsTrue(machine.CanExtract());
            Assert.AreEqual(1, machine.GetCompletedIds().Count);
        }
    }
}
#endif
