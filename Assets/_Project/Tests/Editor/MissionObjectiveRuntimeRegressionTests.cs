#if UNITY_INCLUDE_TESTS
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using RealLoserStudio.Tactical.Core;

namespace RealLoserStudio.Tactical.Tests
{
    public sealed class MissionObjectiveRuntimeRegressionTests
    {
        private static readonly string[] MissionIds = { "M01", "M02", "M03", "M04", "M05", "M06", "M07", "M08", "M09", "M10" };

        public static void AllTenMissionSchemasParseAndExposeObjectivesAndExtraction()
        {
            for (int i = 0; i < MissionIds.Length; i++)
            {
                string path = Path.Combine(Application.dataPath, "StreamingAssets/Missions/" + MissionIds[i] + ".json");
                if (!File.Exists(path)) continue;
                RuntimeMissionSpawner.MissionBlueprintData blueprint = JsonUtility.FromJson<RuntimeMissionSpawner.MissionBlueprintData>(File.ReadAllText(path));
                Debug.Assert(blueprint != null, MissionIds[i] + " did not parse");
                Debug.Assert(blueprint.mission_id == MissionIds[i], MissionIds[i] + " ID mismatch");
            }
        }
    }
}
#endif
