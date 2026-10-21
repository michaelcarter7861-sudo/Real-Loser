using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using UnityEngine;

namespace RealLoserStudio.Tactical.Streaming
{
    [Serializable]
    public struct GridTileCoord : IEquatable<GridTileCoord>
    {
        public int x;
        public int z;

        public GridTileCoord(int x, int z)
        {
            this.x = x;
            this.z = z;
        }

        public bool Equals(GridTileCoord other) => x == other.x && z == other.z;
        public override bool Equals(object obj) => obj is GridTileCoord other && Equals(other);
        public override int GetHashCode() => (x * 73856093) ^ (z * 19349663);
    }

    public class StreamingTileCell
    {
        public GridTileCoord coord;
        public Bounds worldBounds;
        public bool isLoaded;
        public readonly List<GameObject> tileObjects = new List<GameObject>();
    }

    [Serializable]
    public class MissionSaveData
    {
        public string missionId = "M00_Test";
        public int alertLevel;
        public float playerHealth = 100f;
        public Vector3 playerPosition;
        public int playerPosture;
        public List<string> neutralizedEnemyIds = new List<string>();
        public List<string> disarmedTrapIds = new List<string>();
        public List<string> completedObjectives = new List<string>();
    }

    /// <summary>
    /// Mobile Performance Tile Streaming (`150x150m` tiles, `3x3` active window = `450x450m`)
    /// & integrity-protected plain checkpoint save system for Android ARM64 IL2CPP (>= 30 FPS target).
    /// The checksum detects corruption; it is not a secret and is not encryption/authentication.
    /// </summary>
    [Serializable]
    public class MissionSaveEnvelope
    {
        public int formatVersion = 1;
        public string payloadJson;
        public string payloadSha256;
    }

    public class MissionEventAndStreamingSystem : MonoBehaviour
    {
        public const float TILE_SIZE_METERS = 150.0f;
        public const int ACTIVE_GRID_RADIUS = 1; // 3x3 window (-1..+1 in X and Z = 450x450m)
        public const float ACTIVE_WINDOW_METERS = 450.0f;
        public const int TARGET_MOBILE_FPS = 30;

        [Header("Streaming Configuration")]
        public Transform playerTransform;
        public float streamingCheckInterval = 0.25f;

        private readonly Dictionary<GridTileCoord, StreamingTileCell> _tiles = new Dictionary<GridTileCoord, StreamingTileCell>();
        private GridTileCoord _currentCenterTile = new GridTileCoord(int.MinValue, int.MinValue);
        private float _timer;

        public int ActiveTileCount { get; private set; }

        private void Awake()
        {
            Application.targetFrameRate = 60;
            QualitySettings.vSyncCount = 0;
        }

        public static GridTileCoord WorldToTileCoord(Vector3 worldPos)
        {
            int tx = Mathf.FloorToInt(worldPos.x / TILE_SIZE_METERS);
            int tz = Mathf.FloorToInt(worldPos.z / TILE_SIZE_METERS);
            return new GridTileCoord(tx, tz);
        }

        public void RegisterWorldObjectToTile(GameObject obj)
        {
            if (obj == null) return;
            GridTileCoord coord = WorldToTileCoord(obj.transform.position);
            if (!_tiles.TryGetValue(coord, out StreamingTileCell cell))
            {
                Vector3 center = new Vector3((coord.x + 0.5f) * TILE_SIZE_METERS, 0f, (coord.z + 0.5f) * TILE_SIZE_METERS);
                bool isInsideActiveWindow = _currentCenterTile.x == int.MinValue || IsTileInActiveWindow(coord, _currentCenterTile);
                cell = new StreamingTileCell
                {
                    coord = coord,
                    worldBounds = new Bounds(center, new Vector3(TILE_SIZE_METERS, 200f, TILE_SIZE_METERS)),
                    isLoaded = isInsideActiveWindow
                };
                _tiles[coord] = cell;
            }
            cell.tileObjects.Add(obj);
            // Objects registered after the player has crossed a tile boundary must obey the
            // current 3x3 window immediately; otherwise they remain active until the next move.
            obj.SetActive(cell.isLoaded);
        }

        /// <summary>
        /// Drops all registered tile references. This is safe while an old mission root is
        /// being destroyed and prevents the next mission from touching destroyed objects.
        /// </summary>
        public void ClearRegisteredObjects()
        {
            foreach (KeyValuePair<GridTileCoord, StreamingTileCell> kvp in _tiles)
            {
                kvp.Value.tileObjects.Clear();
            }
            _tiles.Clear();
            ActiveTileCount = 0;
        }

        /// <summary>
        /// Clears registered objects and returns streaming to its pre-player state.
        /// </summary>
        public void ResetStreamingTiles()
        {
            ClearRegisteredObjects();
            _currentCenterTile = new GridTileCoord(int.MinValue, int.MinValue);
            _timer = 0f;
        }

        public void TickStreaming(float deltaTime)
        {
            _timer += deltaTime;
            if (_timer < streamingCheckInterval || playerTransform == null) return;
            _timer = 0f;

            GridTileCoord centerTile = WorldToTileCoord(playerTransform.position);
            if (centerTile.Equals(_currentCenterTile)) return;

            _currentCenterTile = centerTile;
            UpdateActiveTileWindow(centerTile);
        }

        /// <summary>
        /// Activates the 3x3 (450x450m) tile neighborhood around `centerTile` and hibernates distant tiles.
        /// </summary>
        public bool IsTileActive(GridTileCoord coord)
        {
            return _currentCenterTile.x != int.MinValue && IsTileInActiveWindow(coord, _currentCenterTile);
        }

        private static bool IsTileInActiveWindow(GridTileCoord coord, GridTileCoord centerTile)
        {
            return Mathf.Abs(coord.x - centerTile.x) <= ACTIVE_GRID_RADIUS &&
                   Mathf.Abs(coord.z - centerTile.z) <= ACTIVE_GRID_RADIUS;
        }

        public void UpdateActiveTileWindow(GridTileCoord centerTile)
        {
            int activeCount = 0;
            foreach (KeyValuePair<GridTileCoord, StreamingTileCell> kvp in _tiles)
            {
                GridTileCoord c = kvp.Key;
                StreamingTileCell cell = kvp.Value;
                bool shouldBeActive = IsTileInActiveWindow(c, centerTile);

                if (shouldBeActive) activeCount++;

                if (cell.isLoaded != shouldBeActive)
                {
                    cell.isLoaded = shouldBeActive;
                    for (int i = 0; i < cell.tileObjects.Count; i++)
                    {
                        if (cell.tileObjects[i] != null)
                        {
                            cell.tileObjects[i].SetActive(shouldBeActive);
                        }
                    }
                }
            }
            ActiveTileCount = activeCount;
        }

        // --- Checkpoint Save / Load System ---
        // This is deliberately plain JSON with a SHA-256 checksum. There is no embedded secret,
        // so it must not be described as encryption or treated as protection from a hostile editor.

        public static void SaveCheckpoint(MissionSaveData data, string filePath)
        {
            if (data == null) throw new ArgumentNullException(nameof(data));
            if (string.IsNullOrEmpty(filePath)) throw new ArgumentException("A save path is required.", nameof(filePath));

            string payload = JsonUtility.ToJson(data, true);
            MissionSaveEnvelope envelope = new MissionSaveEnvelope
            {
                payloadJson = payload,
                payloadSha256 = ComputeSha256(payload)
            };
            string serialized = JsonUtility.ToJson(envelope, true);
            string directory = Path.GetDirectoryName(filePath);
            if (!string.IsNullOrEmpty(directory)) Directory.CreateDirectory(directory);
            File.WriteAllText(filePath, serialized, Encoding.UTF8);
        }

        public static MissionSaveData LoadCheckpoint(string filePath)
        {
            if (!File.Exists(filePath)) return null;
            string serialized = File.ReadAllText(filePath, Encoding.UTF8);
            MissionSaveEnvelope envelope = JsonUtility.FromJson<MissionSaveEnvelope>(serialized);
            if (envelope == null || envelope.formatVersion != 1 || string.IsNullOrEmpty(envelope.payloadJson) ||
                !ConstantTimeEquals(envelope.payloadSha256, ComputeSha256(envelope.payloadJson)))
            {
                Debug.LogWarning("Checkpoint rejected: missing or invalid integrity checksum.");
                return null;
            }
            return JsonUtility.FromJson<MissionSaveData>(envelope.payloadJson);
        }

        private static string ComputeSha256(string value)
        {
            using (SHA256 sha = SHA256.Create())
            {
                byte[] digest = sha.ComputeHash(Encoding.UTF8.GetBytes(value ?? string.Empty));
                StringBuilder builder = new StringBuilder(digest.Length * 2);
                for (int i = 0; i < digest.Length; i++) builder.Append(digest[i].ToString("x2"));
                return builder.ToString();
            }
        }

        private static bool ConstantTimeEquals(string left, string right)
        {
            if (left == null || right == null || left.Length != right.Length) return false;
            int difference = 0;
            for (int i = 0; i < left.Length; i++) difference |= left[i] ^ right[i];
            return difference == 0;
        }
    }
}
