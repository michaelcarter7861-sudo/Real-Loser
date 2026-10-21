using System;
using System.Collections.Generic;
using UnityEngine;

namespace RealLoserStudio.Tactical.Core
{
    /// <summary>
    /// Runtime-built tactical 3D set dressing. Generates a lightweight, mission-specific
    /// environment shell around the mission blueprint so maps have readable landmarks,
    /// approach lanes, cover, elevation, and skyline silhouettes even before art pass.
    /// All geometry is generated from Unity primitives and is mobile-friendly.
    /// </summary>
    public class TacticalWorldBuilder : MonoBehaviour
    {
        public int seed = 147;
        public float mapWidth = 240f;
        public float mapDepth = 240f;
        public bool buildOnStart = true;
        private readonly List<GameObject> generated = new List<GameObject>();
        private Material groundMat, roadMat, concreteMat, metalMat, foliageMat, accentMat, snowMat;

        void Start()
        {
            if (buildOnStart) BuildWorld();
        }

        [ContextMenu("Build Tactical World")]
        public void BuildWorld()
        {
            if (generated.Count > 0) return;
            string mission = gameObject.name;
            seed = StableSeed(mission);
            UnityEngine.Random.InitState(seed);
            string id = mission.Contains("M10") ? "M10" : mission.Contains("M09") ? "M09" : mission.Contains("M08") ? "M08" : mission.Contains("M07") ? "M07" : mission.Contains("M06") ? "M06" : mission.Contains("M05") ? "M05" : mission.Contains("M04") ? "M04" : mission.Contains("M03") ? "M03" : mission.Contains("M02") ? "M02" : "M01";
            bool snow = id == "M05";
            bool desert = id == "M02" || id == "M06" || id == "M08" || id == "M09";
            bool industrial = id == "M04" || id == "M07" || id == "M10";
            bool forest = id == "M01" || id == "M03";
            groundMat = MakeMat(snow ? new Color(.66f,.70f,.72f) : desert ? new Color(.48f,.37f,.22f) : forest ? new Color(.16f,.24f,.16f) : new Color(.22f,.25f,.23f));
            roadMat = MakeMat(new Color(.12f,.14f,.14f));
            concreteMat = MakeMat(new Color(.34f,.36f,.34f));
            metalMat = MakeMat(new Color(.19f,.23f,.24f));
            foliageMat = MakeMat(snow ? new Color(.25f,.32f,.31f) : desert ? new Color(.25f,.24f,.13f) : new Color(.12f,.22f,.13f));
            accentMat = MakeMat(new Color(.68f,.34f,.12f));
            snowMat = MakeMat(new Color(.79f,.82f,.82f));

            switch (id) {
                case "M01": mapWidth=300f; mapDepth=300f; break;
                case "M02": mapWidth=800f; mapDepth=600f; break;
                case "M03": mapWidth=700f; mapDepth=700f; break;
                case "M04": mapWidth=500f; mapDepth=400f; break;
                case "M05": mapWidth=1200f; mapDepth=350f; break;
                case "M06": mapWidth=1000f; mapDepth=900f; break;
                case "M07": mapWidth=900f; mapDepth=600f; break;
                case "M08": mapWidth=2500f; mapDepth=300f; break;
                case "M09": mapWidth=800f; mapDepth=800f; break;
                case "M10": mapWidth=800f; mapDepth=700f; break;
            }
            float w = mapWidth, d = mapDepth;
            CreatePrimitive("World Ground", PrimitiveType.Cube, new Vector3(w/2f,-1f,d/2f), new Vector3(w,2f,d), snow ? snowMat : groundMat);
            CreatePrimitive("Main Approach Road", PrimitiveType.Cube, new Vector3(w/2f,.03f,d*.52f), new Vector3(w*.82f,.08f,8f), roadMat);
            CreatePrimitive("Cross Service Road", PrimitiveType.Cube, new Vector3(w*.52f,.035f,d*.50f), new Vector3(7f,.09f,d*.78f), roadMat);
            // Painted lane marks make routes legible from the ground.
            int roadMarkCount = Mathf.Clamp(Mathf.RoundToInt(w / 18f), 16, 100);
            for (int i=0;i<roadMarkCount;i++) {
                float markX = 14f + i * ((w - 28f) / Mathf.Max(roadMarkCount - 1, 1));
                CreatePrimitive("Road Mark", PrimitiveType.Cube, new Vector3(markX,.09f,d*.52f), new Vector3(5f,.025f,.18f), accentMat);
            }

            // Perimeter fencing and guard towers define a readable compound.
            for (float x=8f; x<w-4f; x+=12f) {
                FencePost(x, 5f); FencePost(x, d-5f);
            }
            for (float z=10f; z<d-4f; z+=12f) {
                FencePost(5f, z); FencePost(w-5f, z);
            }
            Tower(18f, 18f); Tower(w-22f, 20f); Tower(20f, d-22f); Tower(w-22f, d-22f);

            // Three major structures create interior/exterior combat lanes and skyline.
            Building(w*.34f,d*.28f, new Vector3(34f,7f,24f), industrial ? metalMat : concreteMat, "Command Building");
            Building(w*.69f,d*.30f, new Vector3(28f,6f,22f), concreteMat, "Barracks");
            Building(w*.55f,d*.72f, new Vector3(42f,8f,27f), industrial ? metalMat : concreteMat, "Operations Hangar");
            // Door-like openings and loading bays are visual landmarks; gameplay entry is handled by mission logic.
            for(int i=0;i<4;i++) {
                float x=w*.55f-13f+i*8f;
                CreatePrimitive("Hangar Bay", PrimitiveType.Cube, new Vector3(x,2.3f,d*.72f-13.7f), new Vector3(3.4f,4.6f,.12f), roadMat);
            }

            // Signature landmarks make the missions read differently instead of sharing
            // only a generic compound silhouette.
            if (id == "M05") {
                Material waterMat = MakeMat(new Color(.08f,.20f,.25f));
                CreatePrimitive("River Gorge",PrimitiveType.Cube,new Vector3(w*.50f,-.05f,d*.50f),new Vector3(24f,.12f,d),waterMat);
                CreatePrimitive("Bridge Deck",PrimitiveType.Cube,new Vector3(w*.50f,.65f,d*.52f),new Vector3(42f,1.3f,15f),concreteMat);
                for(int side=-1;side<=1;side+=2) {
                    CreatePrimitive("Bridge Guardrail",PrimitiveType.Cube,new Vector3(w*.50f,.95f,d*.52f+side*7f),new Vector3(42f,.6f,.35f),metalMat);
                    for(int i=0;i<8;i++) CreatePrimitive("Bridge Support",PrimitiveType.Cube,new Vector3(w*.50f-18f+i*5.2f,-2.5f,d*.52f+side*4f),new Vector3(.8f,6f,.8f),metalMat);
                }
            } else if (id == "M07") {
                for(int i=0;i<4;i++) {
                    float x=w*.24f+i*w*.17f;
                    CreatePrimitive("Port Container Stack",PrimitiveType.Cube,new Vector3(x,2f,d*.62f),new Vector3(18f,4f,7f),i%2==0?metalMat:accentMat);
                    CreatePrimitive("Cargo Crane Mast",PrimitiveType.Cube,new Vector3(x,13f,d*.78f),new Vector3(1.4f,26f,1.4f),accentMat);
                    CreatePrimitive("Cargo Crane Boom",PrimitiveType.Cube,new Vector3(x+8f,25f,d*.78f),new Vector3(18f,1.2f,1.2f),metalMat);
                }
            } else if (id == "M08") {
                for(int i=0;i<9;i++) {
                    float x=20f+i*(w-40f)/8f;
                    CreatePrimitive("Convoy Route Barrier",PrimitiveType.Cube,new Vector3(x,1f,d*.38f),new Vector3(5f,2f,1.4f),concreteMat);
                    CreatePrimitive("Convoy Route Marker",PrimitiveType.Cylinder,new Vector3(x,1.1f,d*.66f),new Vector3(.35f,2.2f,.35f),accentMat);
                }
            } else if (id == "M06") {
                // Refinery / desert industrial yard: tank silhouettes, pipe runs and loading gantries.
                for (int i = 0; i < 4; i++) {
                    float x = w * .22f + i * w * .17f;
                    CreatePrimitive("Refinery Storage Tank", PrimitiveType.Cylinder,
                        new Vector3(x, 5f, d * .30f), new Vector3(10f, 10f, 10f), metalMat);
                    CreatePrimitive("Refinery Pipe Run", PrimitiveType.Cube,
                        new Vector3(x + 12f, 4.5f, d * .30f), new Vector3(24f, .7f, .7f), accentMat);
                    CreatePrimitive("Loading Gantry", PrimitiveType.Cube,
                        new Vector3(x, 8f, d * .38f), new Vector3(1f, 16f, 1f), concreteMat);
                }
            } else if (id == "M09") {
                // Underground installation approach: hillside portal, retaining walls and access road.
                CreatePrimitive("Tunnel Portal", PrimitiveType.Cube,
                    new Vector3(w * .52f, 5f, d * .17f), new Vector3(24f, 10f, 3f), concreteMat);
                CreatePrimitive("Tunnel Opening", PrimitiveType.Cube,
                    new Vector3(w * .52f, 2.5f, d * .15f), new Vector3(10f, 5f, 3.2f), roadMat);
                for (int side = -1; side <= 1; side += 2) {
                    CreatePrimitive("Tunnel Retaining Wall", PrimitiveType.Cube,
                        new Vector3(w * .52f + side * 14f, 2f, d * .20f), new Vector3(2f, 4f, 34f), concreteMat);
                }
                for (int i = 0; i < 5; i++) {
                    CreatePrimitive("Tunnel Approach Light", PrimitiveType.Cylinder,
                        new Vector3(w * .52f + (i - 2) * 5f, 4f, d * .25f + i * 5f), new Vector3(.25f, 8f, .25f), accentMat);
                }
            } else if (id == "M10") {
                // Inner defensive ring gives the final compound a second layer to breach.
                for(float x=w*.28f;x<w*.73f;x+=10f) {
                    CreatePrimitive("Inner Defense Wall",PrimitiveType.Cube,new Vector3(x,1.7f,d*.57f),new Vector3(9.5f,3.4f,.65f),concreteMat);
                }
                CreatePrimitive("Final Command Block",PrimitiveType.Cube,new Vector3(w*.72f,5f,d*.28f),new Vector3(52f,10f,36f),metalMat);
                CreatePrimitive("Command Block Roof",PrimitiveType.Cube,new Vector3(w*.72f,10.2f,d*.28f),new Vector3(54f,.4f,38f),accentMat);
            }

            // Container rows / cover stacks.
            for(int row=0;row<3;row++) for(int col=0;col<5;col++) {
                float x=26f+col*11f, z=55f+row*13f;
                if (x < w-20f && z < d-20f) {
                    CreatePrimitive("Cargo Container", PrimitiveType.Cube, new Vector3(x,1.5f,z), new Vector3(8f,3f,4f), (col%2==0?metalMat:concreteMat));
                    if(row==1) CreatePrimitive("Container Top Rib", PrimitiveType.Cube, new Vector3(x,3.1f,z), new Vector3(7.8f,.12f,3.8f), accentMat);
                }
            }
            // Mission-biome silhouettes.
            if (forest) {
                for(int i=0;i<48;i++) Tree(UnityEngine.Random.Range(10f,w-10f), UnityEngine.Random.Range(10f,d-10f));
            } else if (desert) {
                for(int i=0;i<18;i++) {
                    float x=UnityEngine.Random.Range(12f,w-12f), z=UnityEngine.Random.Range(12f,d-12f);
                    CreatePrimitive("Rock Outcrop", PrimitiveType.Sphere, new Vector3(x,.6f,z), new Vector3(UnityEngine.Random.Range(2f,5f),UnityEngine.Random.Range(1f,3f),UnityEngine.Random.Range(2f,5f)), groundMat);
                }
            } else {
                for(int i=0;i<18;i++) {
                    float x=UnityEngine.Random.Range(12f,w-12f), z=UnityEngine.Random.Range(12f,d-12f);
                    CreatePrimitive("Concrete Barrier", PrimitiveType.Cube, new Vector3(x,.65f,z), new Vector3(3.5f,1.3f,1.2f), concreteMat);
                }
            }
            // Light poles at corners and route junctions.
            for(int i=0;i<8;i++) Lamp(15f+(i%4)*(w-30f)/3f, (i<4?22f:d-22f));
            // Distant ridge silhouettes add depth without costly terrain meshes.
            for(int i=0;i<9;i++) {
                float x=10f+i*(w-20f)/8f;
                CreatePrimitive("Distant Ridge", PrimitiveType.Sphere, new Vector3(x,4f,d+16f), new Vector3(28f,14f,26f), foliageMat);
            }
            RenderSettings.ambientLight = snow ? new Color(.48f,.52f,.56f) : new Color(.42f,.43f,.39f);
            RenderSettings.fog = true;
            RenderSettings.fogColor = snow ? new Color(.60f,.65f,.68f) : desert ? new Color(.52f,.44f,.34f) : new Color(.30f,.34f,.30f);
            RenderSettings.fogMode = FogMode.Linear;
            RenderSettings.fogStartDistance = 100f;
            RenderSettings.fogEndDistance = 360f;
            Debug.Log("[ProjectRealLoser] Tactical world shell generated for " + id);
        }


        static int StableSeed(string value)
        {
            unchecked
            {
                int hash = 23;
                for (int i = 0; i < value.Length; i++) hash = hash * 31 + value[i];
                return Mathf.Abs(hash == int.MinValue ? 0 : hash) % 100000;
            }
        }

        Material MakeMat(Color color) {
            Shader shader = Shader.Find("Universal Render Pipeline/Lit");
            if(shader == null) shader = Shader.Find("Standard");
            Material m = new Material(shader); m.color = color; return m;
        }
        GameObject CreatePrimitive(string name, PrimitiveType type, Vector3 pos, Vector3 scale, Material mat) {
            GameObject go = GameObject.CreatePrimitive(type); go.name = name; go.transform.position = pos; go.transform.localScale = scale;
            Renderer r=go.GetComponent<Renderer>(); if(r!=null) r.sharedMaterial=mat;
            generated.Add(go); return go;
        }
        void Building(float x,float z,Vector3 size,Material mat,string label) {
            CreatePrimitive(label,PrimitiveType.Cube,new Vector3(x,size.y*.5f,z),size,mat);
            CreatePrimitive(label+" Roof",PrimitiveType.Cube,new Vector3(x,size.y+.15f,z),new Vector3(size.x+1f,.3f,size.z+1f),metalMat);
            for(float dx=-size.x*.36f;dx<=size.x*.36f;dx+=size.x*.24f)
                CreatePrimitive(label+" Window",PrimitiveType.Cube,new Vector3(x+dx,size.y*.68f,z-size.z*.501f),new Vector3(2f,1f,.12f),accentMat);
            CreatePrimitive(label+" Entry",PrimitiveType.Cube,new Vector3(x,size.y*.20f,z-size.z*.505f),new Vector3(3f,2.6f,.15f),roadMat);
        }
        void FencePost(float x,float z) {
            CreatePrimitive("Fence Post",PrimitiveType.Cube,new Vector3(x,1.5f,z),new Vector3(.22f,3f,.22f),metalMat);
            CreatePrimitive("Fence Rail",PrimitiveType.Cube,new Vector3(x,2.5f,z),new Vector3(12f,.12f,.12f),metalMat);
        }
        void Tower(float x,float z) {
            CreatePrimitive("Watchtower Legs",PrimitiveType.Cube,new Vector3(x,3.3f,z),new Vector3(2.8f,6.6f,2.8f),metalMat);
            CreatePrimitive("Watchtower Platform",PrimitiveType.Cube,new Vector3(x,6.7f,z),new Vector3(7f,.45f,7f),concreteMat);
            CreatePrimitive("Watchtower Cabin",PrimitiveType.Cube,new Vector3(x,8.2f,z),new Vector3(4.5f,2.6f,4.5f),metalMat);
            CreatePrimitive("Watchtower Roof",PrimitiveType.Cube,new Vector3(x,9.6f,z),new Vector3(5.3f,.3f,5.3f),accentMat);
        }
        void Tree(float x,float z) {
            CreatePrimitive("Tree Trunk",PrimitiveType.Cylinder,new Vector3(x,1.7f,z),new Vector3(.7f,3.4f,.7f),concreteMat);
            CreatePrimitive("Tree Canopy",PrimitiveType.Sphere,new Vector3(x,4.2f,z),new Vector3(4.8f,5.5f,4.8f),foliageMat);
        }
        void Lamp(float x,float z) {
            CreatePrimitive("Lamp Pole",PrimitiveType.Cylinder,new Vector3(x,4f,z),new Vector3(.18f,8f,.18f),metalMat);
            GameObject bulb=CreatePrimitive("Lamp Head",PrimitiveType.Sphere,new Vector3(x,8.2f,z),new Vector3(.5f,.35f,.5f),snowMat);
            Light light=bulb.AddComponent<Light>(); light.type=LightType.Point; light.range=18f; light.intensity=.65f;
        }
    }
}
