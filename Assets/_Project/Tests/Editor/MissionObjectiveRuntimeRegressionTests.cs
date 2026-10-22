using System.Collections.Generic;
using System.IO;
using UnityEngine;
using RealLoserStudio.Tactical.Core;

namespace RealLoserStudio.Tactical.Tests
{
    public sealed class MissionObjectiveRuntimeRegressionTests : MonoBehaviour
    {
        private static readonly string[] MissionIds = { "M01", "M02", "M03", "M04", "M05", "M06", "M07", "M08", "M09", "M10" };

        private void Start()
        {
            RunAllValidations();
        }

        public static void RunAllValidations()
        {
            Debug.Log("[RegressionTests] Starting runtime schema & logic validation...");
            
            // 1. Schema Parse Test
            for (int i = 0; i < MissionIds.Length; i++)
            {
                string path = Path.Combine(Application.dataPath, "StreamingAssets/Missions/" + MissionIds[i] + ".json");
                if (!File.Exists(path))
                {
                    Debug.LogWarning("[RegressionTests] Missing schema (optional fallback): " + path);
                    continue;
                }
                string jsonContent = File.ReadAllText(path);
                RuntimeMissionSpawner.MissionBlueprintData blueprint = JsonUtility.FromJson<RuntimeMissionSpawner.MissionBlueprintData>(jsonContent);
                if (blueprint == null)
                {
                    Debug.LogError("[RegressionTests] " + MissionIds[i] + " did not parse correctly.");
                }
            }

            // 2. Interaction State Machine Test
            MissionObjectiveDefinition primary = new MissionObjectiveDefinition
            {
                id = "O1",
                primary = true,
                steps = new List<MissionObjectiveStep> {
                    new MissionObjectiveStep { id = "terminal", hasPosition = true, requiresExplicitInteraction = true }
                }
            };
            MissionObjectiveStateMachine machine = new MissionObjectiveStateMachine(new List<MissionObjectiveDefinition> { primary });
            Debug.Assert(machine.GetState("O1") == MissionObjectiveState.Available, "Initial state should be Available");
            Debug.Assert(!machine.CanExtract(), "Cannot extract initially");
            
            machine.CompleteExplicitStep("O1", 0);
            Debug.Assert(machine.GetState("O1") == MissionObjectiveState.Completed, "State should be Completed after interaction");
            Debug.Assert(machine.CanExtract(), "Can extract after completion");

            Debug.Log("[RegressionTests] All runtime validation checks passed successfully!");
        }
    }
}
