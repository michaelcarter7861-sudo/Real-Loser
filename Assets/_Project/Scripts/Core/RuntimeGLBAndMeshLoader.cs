using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Text;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Networking;

namespace RealLoserStudio.Tactical.Core
{
    /// <summary>
    /// Self-contained binary glTF 2.0 (.glb) and RIFF PCM (.wav) runtime loader.
    /// Reads binary headers (0x46546C67 'glTF', JSON chunk 0x4E4F534A, BIN chunk 0x004E4942),
    /// extracts POSITION, NORMAL, JOINTS_0, WEIGHTS_0, and INDICES buffers via BitConverter,
    /// constructs Unity Mesh, MeshFilter, MeshRenderer, BoxCollider/MeshCollider hierarchies,
    /// creates shader-safe URP/Standard fallback Materials, and decodes 16-bit PCM .wav AudioClips.
    /// </summary>
    public static class RuntimeGLBAndMeshLoader
    {
        public const uint GLTF_MAGIC = 0x46546C67;       // "glTF"
        public const uint CHUNK_JSON = 0x4E4F534A;       // "JSON"
        public const uint CHUNK_BIN  = 0x004E4942;       // "BIN\0"

        public const int COMPONENT_UNSIGNED_BYTE  = 5121;
        public const int COMPONENT_UNSIGNED_SHORT = 5123;
        public const int COMPONENT_UNSIGNED_INT   = 5125;
        public const int COMPONENT_FLOAT          = 5126;

        private static readonly Dictionary<string, GameObject> _prefabTemplateCache = new Dictionary<string, GameObject>();
        private static GameObject _templateCacheRoot;
        private static readonly Dictionary<string, AudioClip> _audioClipCache = new Dictionary<string, AudioClip>();
        private static readonly Dictionary<string, Texture2D> _textureCache = new Dictionary<string, Texture2D>();
        private static readonly Dictionary<string, byte[]> _byteCache = new Dictionary<string, byte[]>();
        private static Shader _cachedLitShader;

        [Serializable]
        private class GltfRoot
        {
            public List<GltfNode> nodes;
            public List<GltfMesh> meshes;
            public List<GltfAccessor> accessors;
            public List<GltfBufferView> bufferViews;
            public List<GltfMaterial> materials;
            public List<GltfTexture> textures;
            public List<GltfImage> images;
            public List<GltfSkin> skins;
        }

        [Serializable]
        private class GltfNode
        {
            public string name;
            public int mesh = -1;
            public int skin = -1;
            public float[] translation;
            public float[] rotation;
            public float[] scale;
            public int[] children;
        }

        [Serializable]
        private class GltfSkin
        {
            public string name;
            public int skeleton = -1;
            public int[] joints;
            public int inverseBindMatrices = -1;
        }

        [Serializable]
        private class GltfMesh
        {
            public string name;
            public List<GltfPrimitive> primitives;
        }

        [Serializable]
        private class GltfAttributes
        {
            public int POSITION = -1;
            public int NORMAL = -1;
            public int TEXCOORD_0 = -1;
            public int JOINTS_0 = -1;
            public int WEIGHTS_0 = -1;
        }

        [Serializable]
        private class GltfPrimitive
        {
            public GltfAttributes attributes;
            public int indices = -1;
            public int material = 0;
            public int mode = 4;
        }

        [Serializable]
        private class GltfAccessor
        {
            public int bufferView = -1;
            public int byteOffset = 0;
            public int componentType = 5126;
            public int count = 0;
            public string type = "SCALAR";
            public bool normalized;
        }

        [Serializable]
        private class GltfBufferView
        {
            public int buffer = 0;
            public int byteOffset = 0;
            public int byteLength = 0;
            public int byteStride = 0;
        }

        [Serializable]
        private class GltfPbrMetallicRoughness
        {
            public float[] baseColorFactor;
            public GltfTextureInfo baseColorTexture;
            public GltfTextureInfo metallicRoughnessTexture;
            public float metallicFactor = 0.25f;
            public float roughnessFactor = 0.70f;
        }

        [Serializable]
        private class GltfTextureInfo
        {
            public int index = -1;
            public int texCoord;
            public float scale = 1f;
        }

        [Serializable]
        private class GltfTexture
        {
            public int source = -1;
        }

        [Serializable]
        private class GltfImage
        {
            public string mimeType;
            public int bufferView = -1;
            public string uri;
        }

        [Serializable]
        private class GltfMaterial
        {
            public string name;
            public GltfPbrMetallicRoughness pbrMetallicRoughness;
            public GltfTextureInfo normalTexture;
        }

        public static Shader GetSafeLitShader()
        {
            if (_cachedLitShader != null) return _cachedLitShader;

            bool hasActiveScriptablePipeline = GraphicsSettings.currentRenderPipeline != null;
            string[] candidateShaders = hasActiveScriptablePipeline
                ? new string[] { "Universal Render Pipeline/Lit", "Universal Render Pipeline/Simple Lit", "Standard", "Legacy Shaders/Diffuse", "Mobile/Diffuse", "Sprites/Default" }
                : new string[] { "Standard", "Legacy Shaders/Diffuse", "Mobile/Diffuse", "Universal Render Pipeline/Lit", "Sprites/Default" };

            for (int i = 0; i < candidateShaders.Length; i++)
            {
                Shader s = Shader.Find(candidateShaders[i]);
                if (s != null)
                {
                    _cachedLitShader = s;
                    return s;
                }
            }
            return Shader.Find("Hidden/InternalErrorShader");
        }

        public static Material CreateSafeMaterial(string name, Color baseColor, float metallic = 0.2f, float smoothness = 0.35f)
        {
            Shader shader = GetSafeLitShader();
            Material mat = new Material(shader);
            mat.name = name;
            mat.color = baseColor;
            if (mat.HasProperty("_BaseColor")) mat.SetColor("_BaseColor", baseColor);
            if (mat.HasProperty("_Color")) mat.SetColor("_Color", baseColor);
            if (mat.HasProperty("_Metallic")) mat.SetFloat("_Metallic", metallic);
            if (mat.HasProperty("_Smoothness")) mat.SetFloat("_Smoothness", smoothness);
            if (mat.HasProperty("_Glossiness")) mat.SetFloat("_Glossiness", smoothness);
            return mat;
        }

        private static Texture2D LoadGltfTexture(string assetName, GltfTextureInfo textureInfo, GltfRoot gltf, byte[] binBuffer, bool linear = false)
        {
            if (textureInfo == null || gltf == null || gltf.textures == null || gltf.images == null || gltf.bufferViews == null || binBuffer == null)
                return null;
            if (textureInfo.index < 0 || textureInfo.index >= gltf.textures.Count) return null;
            int imageIndex = gltf.textures[textureInfo.index].source;
            if (imageIndex < 0 || imageIndex >= gltf.images.Count) return null;
            string cacheKey = assetName + "|image=" + imageIndex + "|linear=" + (linear ? "1" : "0");
            if (_textureCache.TryGetValue(cacheKey, out Texture2D cached) && cached != null) return cached;

            GltfImage image = gltf.images[imageIndex];
            if (image.bufferView < 0 || image.bufferView >= gltf.bufferViews.Count) return null;
            GltfBufferView view = gltf.bufferViews[image.bufferView];
            int offset = view.byteOffset;
            int length = view.byteLength;
            if (offset < 0 || length <= 0 || offset + length > binBuffer.Length) return null;

            byte[] encodedImage = new byte[length];
            Buffer.BlockCopy(binBuffer, offset, encodedImage, 0, length);
            Texture2D texture = new Texture2D(2, 2, TextureFormat.RGBA32, true, linear);
            if (!ImageConversion.LoadImage(texture, encodedImage, false))
            {
                UnityEngine.Object.Destroy(texture);
                return null;
            }
            texture.name = assetName + "_glTFImage_" + imageIndex;
            texture.wrapMode = TextureWrapMode.Repeat;
            texture.filterMode = FilterMode.Bilinear;
            texture.anisoLevel = 2;
            _textureCache[cacheKey] = texture;
            return texture;
        }

        public static byte[] ReadStreamingOrProjectBytes(string relativeSubPath)
        {
            string cacheKey = NormalizeRelativePath(relativeSubPath);
            if (_byteCache.TryGetValue(cacheKey, out byte[] cachedBytes))
            {
                return cachedBytes;
            }

            string streamingPath = Path.Combine(Application.streamingAssetsPath, relativeSubPath);
            // StreamingAssets is a URI on Android/WebGL. A synchronous caller must never
            // start a UnityWebRequest: return null and let the coroutine API below load it.
            if (!IsUriPath(streamingPath) && File.Exists(streamingPath))
            {
                return CacheBytes(cacheKey, File.ReadAllBytes(streamingPath));
            }

            string projectArtPath = Path.Combine(Application.dataPath, "_Project", relativeSubPath);
            if (File.Exists(projectArtPath))
            {
                return CacheBytes(cacheKey, File.ReadAllBytes(projectArtPath));
            }

            string rootFallback = Path.Combine(Directory.GetCurrentDirectory(), relativeSubPath);
            if (File.Exists(rootFallback))
            {
                return CacheBytes(cacheKey, File.ReadAllBytes(rootFallback));
            }

            return null;
        }

        /// <summary>
        /// Loads one StreamingAssets/project file without blocking the main thread. On Android
        /// and WebGL the UnityWebRequest is yielded until complete; editor/local file fallbacks
        /// remain synchronous only because they are ordinary filesystem reads.
        /// </summary>
        public static IEnumerator ReadStreamingOrProjectBytesAsync(string relativeSubPath, Action<byte[]> completed)
        {
            byte[] result = null;
            string cacheKey = NormalizeRelativePath(relativeSubPath);
            if (_byteCache.TryGetValue(cacheKey, out result))
            {
                if (completed != null) completed(result);
                yield break;
            }

            string streamingPath = Path.Combine(Application.streamingAssetsPath, relativeSubPath);
            if (IsUriPath(streamingPath))
            {
                using (UnityWebRequest uwr = UnityWebRequest.Get(streamingPath))
                {
                    yield return uwr.SendWebRequest();
                    if (uwr.result == UnityWebRequest.Result.Success && uwr.downloadHandler != null)
                    {
                        result = uwr.downloadHandler.data;
                    }
                }
            }
            else
            {
                result = ReadStreamingOrProjectBytes(relativeSubPath);
            }

            if (result == null)
            {
                // A failed URI request still gets the same editor/project/root fallbacks.
                string projectArtPath = Path.Combine(Application.dataPath, "_Project", relativeSubPath);
                if (File.Exists(projectArtPath)) result = File.ReadAllBytes(projectArtPath);
                else
                {
                    string rootFallback = Path.Combine(Directory.GetCurrentDirectory(), relativeSubPath);
                    if (File.Exists(rootFallback)) result = File.ReadAllBytes(rootFallback);
                }
            }

            if (result != null) CacheBytes(cacheKey, result);
            if (completed != null) completed(result);
        }

        /// <summary>Preloads a unique set of files sequentially, yielding each request.</summary>
        public static IEnumerator PreloadStreamingOrProjectBytes(IEnumerable<string> relativeSubPaths, Action<bool> completed)
        {
            bool allLoaded = true;
            HashSet<string> uniquePaths = new HashSet<string>();
            if (relativeSubPaths != null)
            {
                foreach (string path in relativeSubPaths)
                {
                    if (!string.IsNullOrEmpty(path)) uniquePaths.Add(NormalizeRelativePath(path));
                }
            }

            foreach (string path in uniquePaths)
            {
                byte[] result = null;
                yield return ReadStreamingOrProjectBytesAsync(path, bytes => result = bytes);
                if (result == null) allLoaded = false;
            }
            if (completed != null) completed(allLoaded);
        }

        private static bool IsUriPath(string path)
        {
            return !string.IsNullOrEmpty(path) && (path.Contains("://") || path.Contains(":///"));
        }

        private static string NormalizeRelativePath(string path)
        {
            return string.IsNullOrEmpty(path) ? string.Empty : path.Replace('\\', '/');
        }

        private static GameObject GetTemplateCacheRoot()
        {
            if (_templateCacheRoot == null)
            {
                _templateCacheRoot = new GameObject("__PRL_GLBTemplateCache");
                _templateCacheRoot.SetActive(false);
            }
            return _templateCacheRoot;
        }

        private static byte[] CacheBytes(string cacheKey, byte[] bytes)
        {
            if (bytes != null && bytes.Length > 0) _byteCache[cacheKey] = bytes;
            return bytes;
        }

        public static string ReadStreamingOrProjectText(string relativeSubPath)
        {
            byte[] raw = ReadStreamingOrProjectBytes(relativeSubPath);
            if (raw != null && raw.Length > 0)
            {
                return Encoding.UTF8.GetString(raw);
            }
            return null;
        }

        public static GameObject InstantiateGLB(string relativeGlbPath, Vector3 worldPos, Quaternion worldRot, Transform parent = null, bool addCollider = true)
        {
            string assetName = Path.GetFileNameWithoutExtension(relativeGlbPath);
            string cacheKey = NormalizeRelativePath(relativeGlbPath) + "|collider=" + (addCollider ? "1" : "0");
            if (!_prefabTemplateCache.TryGetValue(cacheKey, out GameObject template) || template == null)
            {
                byte[] glbBytes = ReadStreamingOrProjectBytes(relativeGlbPath);
                template = glbBytes != null && glbBytes.Length >= 20
                    ? ParseAndBuildGLBGameObject(assetName, glbBytes, addCollider)
                    : BuildProceduralFallbackObject(assetName, addCollider);
                template.name = "__GLBTemplate_" + assetName + (addCollider ? "_Collider" : "_NoCollider");
                template.transform.SetParent(GetTemplateCacheRoot().transform, false);
                template.SetActive(false);
                _prefabTemplateCache[cacheKey] = template;
            }

            GameObject instance = UnityEngine.Object.Instantiate(template, parent, false);
            instance.name = assetName;
            instance.transform.position = worldPos;
            instance.transform.rotation = worldRot;
            instance.SetActive(true);
            return instance;
        }

        public static GameObject ParseAndBuildGLBGameObject(string assetName, byte[] data, bool addCollider)
        {
            uint magic = BitConverter.ToUInt32(data, 0);
            uint version = BitConverter.ToUInt32(data, 4);
            uint totalLen = BitConverter.ToUInt32(data, 8);

            if (magic != GLTF_MAGIC || version != 2 || totalLen > data.Length)
            {
                return BuildProceduralFallbackObject(assetName, addCollider);
            }

            uint jsonLen = BitConverter.ToUInt32(data, 12);
            uint jsonType = BitConverter.ToUInt32(data, 16);
            if (jsonType != CHUNK_JSON || 20 + jsonLen > data.Length)
            {
                return BuildProceduralFallbackObject(assetName, addCollider);
            }

            string jsonText = Encoding.UTF8.GetString(data, 20, (int)jsonLen);
            int binHeaderOffset = 20 + (int)jsonLen;
            byte[] binBuffer = null;

            if (binHeaderOffset + 8 <= data.Length)
            {
                uint binLen = BitConverter.ToUInt32(data, binHeaderOffset);
                uint binType = BitConverter.ToUInt32(data, binHeaderOffset + 4);
                if (binType == CHUNK_BIN && binHeaderOffset + 8 + (int)binLen <= data.Length)
                {
                    binBuffer = new byte[binLen];
                    Buffer.BlockCopy(data, binHeaderOffset + 8, binBuffer, 0, (int)binLen);
                }
            }

            if (binBuffer == null)
            {
                return BuildProceduralFallbackObject(assetName, addCollider);
            }

            GltfRoot gltf = JsonUtility.FromJson<GltfRoot>(jsonText);
            if (gltf == null || gltf.meshes == null || gltf.meshes.Count == 0)
            {
                return BuildProceduralFallbackObject(assetName, addCollider);
            }

            GameObject rootObj = new GameObject(assetName);

            // Build materials from glTF PBR factors
            List<Material> unityMaterials = new List<Material>();
            if (gltf.materials != null && gltf.materials.Count > 0)
            {
                for (int m = 0; m < gltf.materials.Count; m++)
                {
                    var gm = gltf.materials[m];
                    Color col = new Color(0.45f, 0.48f, 0.46f, 1f);
                    float metallic = 0.25f;
                    float roughness = 0.70f;
                    if (gm.pbrMetallicRoughness != null)
                    {
                        if (gm.pbrMetallicRoughness.baseColorFactor != null && gm.pbrMetallicRoughness.baseColorFactor.Length >= 4)
                        {
                            col = new Color(
                                gm.pbrMetallicRoughness.baseColorFactor[0],
                                gm.pbrMetallicRoughness.baseColorFactor[1],
                                gm.pbrMetallicRoughness.baseColorFactor[2],
                                gm.pbrMetallicRoughness.baseColorFactor[3]
                            );
                        }
                        metallic = gm.pbrMetallicRoughness.metallicFactor;
                        roughness = gm.pbrMetallicRoughness.roughnessFactor;
                    }
                    Material material = CreateSafeMaterial(gm.name ?? (assetName + "_Mat"), col, metallic, 1.0f - roughness);
                    if (gm.pbrMetallicRoughness != null)
                    {
                        Texture2D baseTexture = LoadGltfTexture(assetName, gm.pbrMetallicRoughness.baseColorTexture, gltf, binBuffer);
                        if (baseTexture != null)
                        {
                            if (material.HasProperty("_BaseMap")) material.SetTexture("_BaseMap", baseTexture);
                            if (material.HasProperty("_MainTex")) material.SetTexture("_MainTex", baseTexture);
                            material.mainTexture = baseTexture;
                        }
                    }
                    Texture2D normalTexture = LoadGltfTexture(assetName, gm.normalTexture, gltf, binBuffer, linear: true);
                    if (normalTexture != null)
                    {
                        if (material.HasProperty("_BumpMap")) material.SetTexture("_BumpMap", normalTexture);
                        if (material.HasProperty("_NormalMap")) material.SetTexture("_NormalMap", normalTexture);
                        if (material.HasProperty("_BumpScale")) material.SetFloat("_BumpScale", gm.normalTexture.scale);
                        material.EnableKeyword("_NORMALMAP");
                    }
                    unityMaterials.Add(material);
                }
            }
            else
            {
                unityMaterials.Add(CreateSafeMaterial(assetName + "_DefaultMat", new Color(0.45f, 0.48f, 0.46f, 1f)));
            }

            // Build Unity Meshes for each glTF Mesh (skip LOD1/LOD2 at runtime so only LOD0 renders)
            List<Mesh> builtMeshes = new List<Mesh>();
            for (int mi = 0; mi < gltf.meshes.Count; mi++)
            {
                var gMesh = gltf.meshes[mi];
                string mName = gMesh.name ?? (assetName + "_Mesh_" + mi);
                if (mName.EndsWith("_LOD1") || mName.EndsWith("_LOD2"))
                {
                    builtMeshes.Add(null);
                    continue;
                }
                Mesh uMesh = BuildUnityMeshFromPrimitive(mName, gMesh, gltf.accessors, gltf.bufferViews, binBuffer);
                builtMeshes.Add(uMesh);
            }

            // Instantiate Node Hierarchy (including 15-bone rigs and 6 weapon reference empties)
            if (gltf.nodes != null && gltf.nodes.Count > 0)
            {
                Transform[] nodeTransforms = new Transform[gltf.nodes.Count];
                bool[] hasParent = new bool[gltf.nodes.Count];

                for (int ni = 0; ni < gltf.nodes.Count; ni++)
                {
                    var gNode = gltf.nodes[ni];
                    string nName = string.IsNullOrEmpty(gNode.name) ? ("Node_" + ni) : gNode.name;
                    GameObject nObj = new GameObject(nName);
                    nodeTransforms[ni] = nObj.transform;

                    if (gNode.translation != null && gNode.translation.Length >= 3)
                    {
                        nObj.transform.localPosition = new Vector3(-gNode.translation[0], gNode.translation[1], gNode.translation[2]);
                    }
                    if (gNode.rotation != null && gNode.rotation.Length >= 4)
                    {
                        nObj.transform.localRotation = new Quaternion(gNode.rotation[0], -gNode.rotation[1], -gNode.rotation[2], gNode.rotation[3]);
                    }
                    if (gNode.scale != null && gNode.scale.Length >= 3)
                    {
                        nObj.transform.localScale = new Vector3(gNode.scale[0], gNode.scale[1], gNode.scale[2]);
                    }

                }

                // Attach renderers only after every node transform exists, because skin joints
                // may appear before or after the mesh node in arbitrary glTF node ordering.
                for (int ni = 0; ni < gltf.nodes.Count; ni++)
                {
                    GltfNode gNode = gltf.nodes[ni];
                    if (gNode.mesh < 0 || gNode.mesh >= builtMeshes.Count || builtMeshes[gNode.mesh] == null) continue;
                    Mesh mesh = builtMeshes[gNode.mesh];
                    bool skinned = TryAttachSkinnedRenderer(nodeTransforms[ni], mesh, gNode, gltf, nodeTransforms, unityMaterials[0], binBuffer);
                    if (!skinned)
                    {
                        MeshFilter mf = nodeTransforms[ni].gameObject.AddComponent<MeshFilter>();
                        mf.sharedMesh = mesh;
                        MeshRenderer mr = nodeTransforms[ni].gameObject.AddComponent<MeshRenderer>();
                        mr.sharedMaterial = unityMaterials[0];
                    }
                }

                for (int ni = 0; ni < gltf.nodes.Count; ni++)
                {
                    var gNode = gltf.nodes[ni];
                    if (gNode.children != null)
                    {
                        for (int ci = 0; ci < gNode.children.Length; ci++)
                        {
                            int childIdx = gNode.children[ci];
                            if (childIdx >= 0 && childIdx < nodeTransforms.Length && childIdx != ni)
                            {
                                nodeTransforms[childIdx].SetParent(nodeTransforms[ni], false);
                                hasParent[childIdx] = true;
                            }
                        }
                    }
                }

                for (int ni = 0; ni < nodeTransforms.Length; ni++)
                {
                    if (!hasParent[ni])
                    {
                        nodeTransforms[ni].SetParent(rootObj.transform, false);
                    }
                }
            }

            if (addCollider)
            {
                Bounds combined = CalculateCombinedBounds(rootObj);
                BoxCollider bc = rootObj.AddComponent<BoxCollider>();
                bc.center = combined.center;
                bc.size = new Vector3(
                    Mathf.Max(0.2f, combined.size.x),
                    Mathf.Max(0.2f, combined.size.y),
                    Mathf.Max(0.2f, combined.size.z)
                );
            }

            if (rootObj.GetComponentInChildren<SkinnedMeshRenderer>(true) != null)
            {
                ProceduralHumanoidMotion motion = rootObj.AddComponent<ProceduralHumanoidMotion>();
                motion.BindRig(rootObj.transform);
            }

            return rootObj;
        }

        private static Mesh BuildUnityMeshFromPrimitive(
            string meshName,
            GltfMesh gMesh,
            List<GltfAccessor> accessors,
            List<GltfBufferView> bufferViews,
            byte[] binBuffer)
        {
            if (gMesh.primitives == null || gMesh.primitives.Count == 0) return null;
            var prim = gMesh.primitives[0];
            if (prim.attributes == null || prim.attributes.POSITION < 0 || prim.attributes.POSITION >= accessors.Count)
                return null;

            Vector3[] positions = ReadVec3Accessor(accessors[prim.attributes.POSITION], bufferViews, binBuffer, flipX: true);
            if (positions == null || positions.Length == 0) return null;

            Vector3[] normals = null;
            if (prim.attributes.NORMAL >= 0 && prim.attributes.NORMAL < accessors.Count)
            {
                normals = ReadVec3Accessor(accessors[prim.attributes.NORMAL], bufferViews, binBuffer, flipX: true);
            }

            Vector2[] uvs = null;
            if (prim.attributes.TEXCOORD_0 >= 0 && prim.attributes.TEXCOORD_0 < accessors.Count)
            {
                uvs = ReadVec2Accessor(accessors[prim.attributes.TEXCOORD_0], bufferViews, binBuffer);
            }

            int[] indices = null;
            if (prim.indices >= 0 && prim.indices < accessors.Count)
            {
                indices = ReadIndicesAccessor(accessors[prim.indices], bufferViews, binBuffer);
            }
            else
            {
                indices = new int[positions.Length];
                for (int i = 0; i < positions.Length; i++) indices[i] = i;
            }

            Mesh mesh = new Mesh();
            mesh.name = meshName;
            mesh.vertices = positions;
            if (normals != null && normals.Length == positions.Length)
            {
                mesh.normals = normals;
            }
            if (uvs != null && uvs.Length == positions.Length)
            {
                mesh.uv = uvs;
            }
            BoneWeight[] boneWeights = ReadBoneWeights(prim, accessors, bufferViews, binBuffer, positions.Length);
            if (boneWeights != null && boneWeights.Length == positions.Length)
            {
                mesh.boneWeights = boneWeights;
            }
            mesh.triangles = indices;
            if (normals == null || normals.Length != positions.Length)
            {
                mesh.RecalculateNormals();
            }
            mesh.RecalculateBounds();
            return mesh;
        }

        private static bool TryAttachSkinnedRenderer(
            Transform meshTransform,
            Mesh mesh,
            GltfNode node,
            GltfRoot gltf,
            Transform[] nodeTransforms,
            Material material,
            byte[] binBuffer)
        {
            if (node.skin < 0 || gltf.skins == null || node.skin >= gltf.skins.Count || mesh.boneWeights == null)
                return false;
            GltfSkin skin = gltf.skins[node.skin];
            if (skin.joints == null || skin.joints.Length == 0) return false;
            Matrix4x4[] bindposes = ReadMat4Accessor(skin.inverseBindMatrices, gltf.accessors, gltf.bufferViews, binBuffer);
            if (bindposes == null || bindposes.Length != skin.joints.Length) return false;

            Transform[] bones = new Transform[skin.joints.Length];
            for (int i = 0; i < skin.joints.Length; i++)
            {
                int jointIndex = skin.joints[i];
                if (jointIndex < 0 || jointIndex >= nodeTransforms.Length || nodeTransforms[jointIndex] == null) return false;
                bones[i] = nodeTransforms[jointIndex];
            }
            BoneWeight[] weights = mesh.boneWeights;
            for (int i = 0; i < weights.Length; i++)
            {
                BoneWeight w = weights[i];
                if ((w.weight0 > 0f && w.boneIndex0 >= bones.Length) ||
                    (w.weight1 > 0f && w.boneIndex1 >= bones.Length) ||
                    (w.weight2 > 0f && w.boneIndex2 >= bones.Length) ||
                    (w.weight3 > 0f && w.boneIndex3 >= bones.Length)) return false;
            }

            mesh.bindposes = bindposes;
            SkinnedMeshRenderer renderer = meshTransform.gameObject.AddComponent<SkinnedMeshRenderer>();
            renderer.sharedMesh = mesh;
            renderer.sharedMaterial = material;
            renderer.bones = bones;
            renderer.rootBone = skin.skeleton >= 0 && skin.skeleton < nodeTransforms.Length
                ? nodeTransforms[skin.skeleton]
                : bones[0];
            renderer.localBounds = mesh.bounds;
            renderer.updateWhenOffscreen = false;
            return true;
        }

        private static BoneWeight[] ReadBoneWeights(GltfPrimitive primitive, List<GltfAccessor> accessors, List<GltfBufferView> views, byte[] bin, int vertexCount)
        {
            if (primitive.attributes == null || primitive.attributes.JOINTS_0 < 0 || primitive.attributes.WEIGHTS_0 < 0 ||
                primitive.attributes.JOINTS_0 >= accessors.Count || primitive.attributes.WEIGHTS_0 >= accessors.Count) return null;
            Vector4[] joints = ReadVec4Accessor(accessors[primitive.attributes.JOINTS_0], views, bin);
            Vector4[] weights = ReadVec4Accessor(accessors[primitive.attributes.WEIGHTS_0], views, bin);
            if (joints == null || weights == null || joints.Length != vertexCount || weights.Length != vertexCount) return null;

            BoneWeight[] result = new BoneWeight[vertexCount];
            for (int i = 0; i < vertexCount; i++)
            {
                Vector4 j = joints[i];
                Vector4 w = weights[i];
                float sum = Mathf.Max(0f, w.x) + Mathf.Max(0f, w.y) + Mathf.Max(0f, w.z) + Mathf.Max(0f, w.w);
                if (sum <= 0.000001f) { w = new Vector4(1f, 0f, 0f, 0f); sum = 1f; }
                result[i] = new BoneWeight
                {
                    boneIndex0 = Mathf.Max(0, Mathf.RoundToInt(j.x)),
                    boneIndex1 = Mathf.Max(0, Mathf.RoundToInt(j.y)),
                    boneIndex2 = Mathf.Max(0, Mathf.RoundToInt(j.z)),
                    boneIndex3 = Mathf.Max(0, Mathf.RoundToInt(j.w)),
                    weight0 = Mathf.Max(0f, w.x) / sum,
                    weight1 = Mathf.Max(0f, w.y) / sum,
                    weight2 = Mathf.Max(0f, w.z) / sum,
                    weight3 = Mathf.Max(0f, w.w) / sum
                };
            }
            return result;
        }

        private static Matrix4x4[] ReadMat4Accessor(int accessorIndex, List<GltfAccessor> accessors, List<GltfBufferView> views, byte[] bin)
        {
            if (accessorIndex < 0 || accessorIndex >= accessors.Count) return null;
            GltfAccessor accessor = accessors[accessorIndex];
            if (accessor.componentType != COMPONENT_FLOAT || accessor.type != "MAT4" || accessor.bufferView < 0 || accessor.bufferView >= views.Count) return null;
            GltfBufferView view = views[accessor.bufferView];
            int stride = view.byteStride > 0 ? view.byteStride : 64;
            int baseOffset = view.byteOffset + accessor.byteOffset;
            Matrix4x4[] matrices = new Matrix4x4[accessor.count];
            Matrix4x4 reflection = Matrix4x4.Scale(new Vector3(-1f, 1f, 1f));
            for (int i = 0; i < accessor.count; i++)
            {
                int offset = baseOffset + i * stride;
                if (offset < 0 || offset + 64 > bin.Length) return null;
                Matrix4x4 matrix = new Matrix4x4();
                for (int column = 0; column < 4; column++)
                {
                    int columnOffset = offset + column * 16;
                    matrix.SetColumn(column, new Vector4(
                        BitConverter.ToSingle(bin, columnOffset),
                        BitConverter.ToSingle(bin, columnOffset + 4),
                        BitConverter.ToSingle(bin, columnOffset + 8),
                        BitConverter.ToSingle(bin, columnOffset + 12)));
                }
                matrices[i] = reflection * matrix * reflection;
            }
            return matrices;
        }

        private static Vector4[] ReadVec4Accessor(GltfAccessor accessor, List<GltfBufferView> views, byte[] bin)
        {
            if (accessor.bufferView < 0 || accessor.bufferView >= views.Count) return null;
            int componentBytes = accessor.componentType == COMPONENT_FLOAT ? 4 :
                (accessor.componentType == COMPONENT_UNSIGNED_SHORT ? 2 :
                (accessor.componentType == COMPONENT_UNSIGNED_BYTE ? 1 : 0));
            if (componentBytes == 0) return null;
            GltfBufferView view = views[accessor.bufferView];
            int stride = view.byteStride > 0 ? view.byteStride : componentBytes * 4;
            int baseOffset = view.byteOffset + accessor.byteOffset;
            Vector4[] result = new Vector4[accessor.count];
            for (int i = 0; i < accessor.count; i++)
            {
                int offset = baseOffset + i * stride;
                if (offset < 0 || offset + componentBytes * 4 > bin.Length) return null;
                float[] values = new float[4];
                for (int component = 0; component < 4; component++)
                {
                    int componentOffset = offset + component * componentBytes;
                    if (accessor.componentType == COMPONENT_FLOAT) values[component] = BitConverter.ToSingle(bin, componentOffset);
                    else if (accessor.componentType == COMPONENT_UNSIGNED_SHORT)
                    {
                        float value = BitConverter.ToUInt16(bin, componentOffset);
                        values[component] = accessor.normalized ? value / 65535f : value;
                    }
                    else
                    {
                        float value = bin[componentOffset];
                        values[component] = accessor.normalized ? value / 255f : value;
                    }
                }
                result[i] = new Vector4(values[0], values[1], values[2], values[3]);
            }
            return result;
        }

        private static Vector3[] ReadVec3Accessor(GltfAccessor acc, List<GltfBufferView> views, byte[] bin, bool flipX)
        {
            if (acc.bufferView < 0 || acc.bufferView >= views.Count) return null;
            var bv = views[acc.bufferView];
            int stride = bv.byteStride > 0 ? bv.byteStride : 12;
            int baseOffset = bv.byteOffset + acc.byteOffset;
            Vector3[] result = new Vector3[acc.count];

            for (int i = 0; i < acc.count; i++)
            {
                int off = baseOffset + i * stride;
                if (off + 12 > bin.Length) break;
                float vx = BitConverter.ToSingle(bin, off);
                float vy = BitConverter.ToSingle(bin, off + 4);
                float vz = BitConverter.ToSingle(bin, off + 8);
                result[i] = new Vector3(flipX ? -vx : vx, vy, vz);
            }
            return result;
        }

        private static Vector2[] ReadVec2Accessor(GltfAccessor acc, List<GltfBufferView> views, byte[] bin)
        {
            if (acc.bufferView < 0 || acc.bufferView >= views.Count) return null;
            int componentBytes = acc.componentType == COMPONENT_FLOAT ? 4 : (acc.componentType == COMPONENT_UNSIGNED_SHORT ? 2 : (acc.componentType == COMPONENT_UNSIGNED_BYTE ? 1 : 0));
            if (componentBytes == 0) return null;
            GltfBufferView view = views[acc.bufferView];
            int stride = view.byteStride > 0 ? view.byteStride : componentBytes * 2;
            int baseOffset = view.byteOffset + acc.byteOffset;
            Vector2[] result = new Vector2[acc.count];
            for (int i = 0; i < acc.count; i++)
            {
                int offset = baseOffset + i * stride;
                if (offset + componentBytes * 2 > bin.Length) break;
                float u;
                float v;
                if (acc.componentType == COMPONENT_FLOAT)
                {
                    u = BitConverter.ToSingle(bin, offset);
                    v = BitConverter.ToSingle(bin, offset + 4);
                }
                else if (acc.componentType == COMPONENT_UNSIGNED_SHORT)
                {
                    u = BitConverter.ToUInt16(bin, offset) / (acc.normalized ? 65535f : 1f);
                    v = BitConverter.ToUInt16(bin, offset + 2) / (acc.normalized ? 65535f : 1f);
                }
                else
                {
                    u = bin[offset] / (acc.normalized ? 255f : 1f);
                    v = bin[offset + 1] / (acc.normalized ? 255f : 1f);
                }
                result[i] = new Vector2(u, v);
            }
            return result;
        }

        private static int[] ReadIndicesAccessor(GltfAccessor acc, List<GltfBufferView> views, byte[] bin)
        {
            if (acc.bufferView < 0 || acc.bufferView >= views.Count) return null;
            var bv = views[acc.bufferView];
            int baseOffset = bv.byteOffset + acc.byteOffset;
            int[] raw = new int[acc.count];

            if (acc.componentType == COMPONENT_UNSIGNED_SHORT)
            {
                for (int i = 0; i < acc.count; i++)
                {
                    int off = baseOffset + i * 2;
                    if (off + 2 > bin.Length) break;
                    raw[i] = BitConverter.ToUInt16(bin, off);
                }
            }
            else if (acc.componentType == COMPONENT_UNSIGNED_INT)
            {
                for (int i = 0; i < acc.count; i++)
                {
                    int off = baseOffset + i * 4;
                    if (off + 4 > bin.Length) break;
                    raw[i] = (int)BitConverter.ToUInt32(bin, off);
                }
            }
            else if (acc.componentType == COMPONENT_UNSIGNED_BYTE)
            {
                for (int i = 0; i < acc.count; i++)
                {
                    int off = baseOffset + i;
                    if (off + 1 > bin.Length) break;
                    raw[i] = bin[off];
                }
            }

            // Flip triangle winding for left-handed X-axis reflection
            for (int t = 0; t + 2 < raw.Length; t += 3)
            {
                int tmp = raw[t + 1];
                raw[t + 1] = raw[t + 2];
                raw[t + 2] = tmp;
            }
            return raw;
        }

        private static Bounds CalculateCombinedBounds(GameObject root)
        {
            MeshFilter[] filters = root.GetComponentsInChildren<MeshFilter>();
            SkinnedMeshRenderer[] skinned = root.GetComponentsInChildren<SkinnedMeshRenderer>();
            bool initialized = false;
            Bounds combined = new Bounds(new Vector3(0f, 1.0f, 0f), new Vector3(1f, 2f, 1f));
            if (filters != null)
            {
                for (int i = 0; i < filters.Length; i++)
                {
                    if (filters[i] == null || filters[i].sharedMesh == null) continue;
                    EncapsulateRendererBounds(filters[i].sharedMesh.bounds, filters[i].transform, root.transform, ref combined, ref initialized);
                }
            }
            if (skinned != null)
            {
                for (int i = 0; i < skinned.Length; i++)
                {
                    if (skinned[i] == null || skinned[i].sharedMesh == null) continue;
                    EncapsulateRendererBounds(skinned[i].localBounds, skinned[i].transform, root.transform, ref combined, ref initialized);
                }
            }
            return initialized ? combined : new Bounds(new Vector3(0f, 1.0f, 0f), new Vector3(1f, 2f, 1f));
        }

        private static void EncapsulateRendererBounds(Bounds localBounds, Transform rendererTransform, Transform rootTransform, ref Bounds combined, ref bool initialized)
        {
            Vector3 extents = localBounds.extents;
            for (int x = -1; x <= 1; x += 2)
            {
                for (int y = -1; y <= 1; y += 2)
                {
                    for (int z = -1; z <= 1; z += 2)
                    {
                        Vector3 localCorner = localBounds.center + Vector3.Scale(extents, new Vector3(x, y, z));
                        Vector3 rootLocalCorner = rootTransform.InverseTransformPoint(rendererTransform.TransformPoint(localCorner));
                        if (!initialized)
                        {
                            combined = new Bounds(rootLocalCorner, Vector3.zero);
                            initialized = true;
                        }
                        else combined.Encapsulate(rootLocalCorner);
                    }
                }
            }
        }

        public static GameObject BuildProceduralFallbackObject(string assetName, bool addCollider)
        {
            GameObject go = GameObject.CreatePrimitive(PrimitiveType.Cube);
            go.name = assetName;
            if (!addCollider)
            {
                Collider col = go.GetComponent<Collider>();
                if (col != null) UnityEngine.Object.Destroy(col);
            }
            MeshRenderer mr = go.GetComponent<MeshRenderer>();
            if (mr != null)
            {
                Color c = new Color(0.42f, 0.45f, 0.43f, 1f);
                if (assetName.Contains("wall_brick")) c = new Color(0.58f, 0.28f, 0.22f, 1f);
                else if (assetName.Contains("wall_adobe")) c = new Color(0.72f, 0.58f, 0.42f, 1f);
                else if (assetName.Contains("bush") || assetName.Contains("tree")) c = new Color(0.20f, 0.42f, 0.22f, 1f);
                else if (assetName.Contains("trap")) c = new Color(0.75f, 0.22f, 0.18f, 1f);
                mr.sharedMaterial = CreateSafeMaterial(assetName + "_FallbackMat", c);
            }
            return go;
        }

        /// <summary>
        /// Decodes a 16-bit PCM RIFF .wav file from StreamingAssets/Audio into a playable Unity AudioClip.
        /// </summary>
        public static AudioClip LoadWavAudioClip(string eventId)
        {
            if (string.IsNullOrEmpty(eventId)) return null;
            if (_audioClipCache.TryGetValue(eventId, out AudioClip cached) && cached != null)
            {
                return cached;
            }

            string relPath = Path.Combine("Audio", eventId.EndsWith(".wav") ? eventId : (eventId + ".wav"));
            byte[] wavBytes = ReadStreamingOrProjectBytes(relPath);
            if (wavBytes == null || wavBytes.Length < 44) return null;

            int channels = BitConverter.ToInt16(wavBytes, 22);
            int sampleRate = BitConverter.ToInt32(wavBytes, 24);
            int bitsPerSample = BitConverter.ToInt16(wavBytes, 34);
            if (channels <= 0) channels = 1;
            if (sampleRate <= 0) sampleRate = 22050;

            int dataOffset = 12;
            int dataSize = 0;
            while (dataOffset + 8 <= wavBytes.Length)
            {
                string chunkId = Encoding.ASCII.GetString(wavBytes, dataOffset, 4);
                int chunkSize = BitConverter.ToInt32(wavBytes, dataOffset + 4);
                if (chunkId == "data")
                {
                    dataOffset += 8;
                    dataSize = Mathf.Min(chunkSize, wavBytes.Length - dataOffset);
                    break;
                }
                dataOffset += 8 + chunkSize;
            }

            if (dataSize <= 0 || bitsPerSample != 16) return null;

            int sampleCount = dataSize / 2;
            float[] floatSamples = new float[sampleCount];
            for (int i = 0; i < sampleCount; i++)
            {
                short pcm = BitConverter.ToInt16(wavBytes, dataOffset + i * 2);
                floatSamples[i] = pcm / 32768.0f;
            }

            AudioClip clip = AudioClip.Create(eventId, sampleCount / channels, channels, sampleRate, false);
            clip.SetData(floatSamples, 0);
            _audioClipCache[eventId] = clip;
            return clip;
        }

        public static IEnumerator LoadWavAudioClipAsync(string eventId, Action<AudioClip> completed)
        {
            if (string.IsNullOrEmpty(eventId))
            {
                if (completed != null) completed(null);
                yield break;
            }
            if (_audioClipCache.TryGetValue(eventId, out AudioClip cached) && cached != null)
            {
                if (completed != null) completed(cached);
                yield break;
            }

            string relPath = Path.Combine("Audio", eventId.EndsWith(".wav") ? eventId : (eventId + ".wav"));
            byte[] wavBytes = null;
            yield return ReadStreamingOrProjectBytesAsync(relPath, bytes => wavBytes = bytes);
            AudioClip clip = wavBytes != null && wavBytes.Length >= 44 ? LoadWavAudioClip(eventId) : null;
            if (completed != null) completed(clip);
        }
    }
}
