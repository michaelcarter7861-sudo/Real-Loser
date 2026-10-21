#!/usr/bin/env python3
"""Integrate RC1.6 mission environment GLBs and embed textures without modifying old art.

Run after builders/build_mission_environment_catalog.py and after placing generated
relay/truck GLBs in --generated-dir. Only the two named catalog entries are replaced;
all other already-existing assets (including the protected barrier) remain untouched.
"""
from __future__ import annotations
import argparse, hashlib, json, shutil, struct, sys, tempfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
DEFAULT_GENERATED = PROJECT.parent / "generated_rc16"
REPLACEMENTS = {
    "env_relay_mast_tall_a.glb": ("env_tower_radio_relay_steel_a.glb", (2.2, 7.5, 2.2)),
    "veh_armored_utility_truck_a.glb": ("veh_truck_cargo_a.glb", (5.8, 2.7, 2.5)),
}


def parse_glb(path: Path):
    data=path.read_bytes()
    if len(data)<20: raise ValueError(f"truncated GLB: {path}")
    magic,version,total=struct.unpack_from("<4sII",data,0)
    if magic!=b"glTF" or version!=2 or total!=len(data): raise ValueError(f"invalid GLB header: {path}")
    off=12; doc=None; bin_payload=None; chunks=[]
    while off<len(data):
        if off+8>len(data): raise ValueError(f"truncated chunk header: {path}")
        size,kind=struct.unpack_from("<II",data,off); off+=8
        payload=data[off:off+size]; off+=size
        if len(payload)!=size: raise ValueError(f"truncated chunk: {path}")
        chunks.append((kind,payload))
        if kind==0x4e4f534a:
            if doc is not None: raise ValueError("multiple JSON chunks")
            doc=json.loads(payload.decode("utf-8").rstrip(" \t\r\n\0"))
        elif kind==0x004e4942:
            if bin_payload is not None: raise ValueError("multiple BIN chunks")
            bin_payload=payload
    if doc is None or bin_payload is None: raise ValueError(f"missing GLB JSON/BIN: {path}")
    return doc,chunks,bin_payload


def pack_glb(doc,chunks,bin_payload):
    raw=json.dumps(doc,ensure_ascii=False,separators=(",",":")).encode("utf-8")
    raw+=b" "*((-len(raw))%4)
    out=[]; seen_json=seen_bin=False
    for kind,payload in chunks:
        if kind==0x4e4f534a and not seen_json: payload=raw; seen_json=True
        elif kind==0x004e4942 and not seen_bin: payload=bin_payload; seen_bin=True
        out.append(struct.pack("<II",len(payload),kind)+payload)
    if not seen_json or not seen_bin: raise ValueError("missing chunks while repacking")
    body=b"".join(out)
    return struct.pack("<4sII",b"glTF",2,12+len(body))+body


def normalize_model(source: Path, target: Path, desired_dims):
    doc,chunks,bin_payload=parse_glb(source)
    if len(doc.get("nodes",[]))!=1 or len(doc.get("meshes",[]))!=1:
        raise ValueError(f"generated model must be a single assembly: {source}")
    node=doc["nodes"][0]
    mesh=doc["meshes"][0]
    primitives=mesh.get("primitives",[])
    if not primitives: raise ValueError(f"model has no primitive: {source}")
    # Get actual local POSITION bounds for all primitives using glTF accessor metadata.
    low=[float("inf")]*3; high=[float("-inf")]*3
    for primitive in primitives:
        attrs=primitive.get("attributes",{})
        if "POSITION" not in attrs: raise ValueError("primitive is missing POSITION")
        acc=doc["accessors"][attrs["POSITION"]]
        if acc.get("componentType")!=5126 or acc.get("type")!="VEC3" or not acc.get("min") or not acc.get("max"):
            raise ValueError("POSITION accessor must have float VEC3 min/max bounds")
        for axis in range(3): low[axis]=min(low[axis],float(acc["min"][axis])); high[axis]=max(high[axis],float(acc["max"][axis]))
    source_dims=[high[i]-low[i] for i in range(3)]
    if any(v<=1e-5 for v in source_dims): raise ValueError(f"degenerate source bounds: {source_dims}")
    scale=[desired_dims[i]/source_dims[i] for i in range(3)]
    node["scale"]=scale
    node["translation"]=[0.0, desired_dims[1]/2.0-(low[1]+high[1])*0.5*scale[1], 0.0]
    node.setdefault("extras",{})["prl_normalized_dimensions_m"]=list(desired_dims)
    node["extras"]["prl_source_dimensions"]=source_dims
    node["extras"]["prl_ground_pivot"]=True
    node["name"]=Path(target).stem
    mesh["name"]=Path(target).stem+"_Mesh"
    doc.setdefault("asset",{})["generator"]="Project Real Loser RC1.6 generated mission asset integration"
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(pack_glb(doc,chunks,bin_payload))
    check,_,_=parse_glb(target)
    if check["nodes"][0].get("scale")!=scale: raise ValueError("normalized node scale did not round-trip")
    if len(check.get("images",[]))<1 or not check.get("textures"): raise ValueError("generated PBR texture references missing")
    return source_dims,scale


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--generated-dir",type=Path,default=DEFAULT_GENERATED)
    ap.add_argument("--check-only",action="store_true")
    args=ap.parse_args()
    sys.path.insert(0,str(PROJECT/"tools"))
    import texture_glb_library as textures
    art=PROJECT/"Assets/_Project/Art/Environment"
    stream=PROJECT/"Assets/StreamingAssets/Art/Environment"
    for source_name,(target_name,dims) in REPLACEMENTS.items():
        source=args.generated_dir/source_name; target=art/target_name
        if args.check_only:
            if not target.exists(): raise SystemExit(f"missing integrated model: {target}")
            doc,_,_=parse_glb(target); extras=doc["nodes"][0].get("extras",{})
            if extras.get("prl_normalized_dimensions_m")!=list(dims): raise SystemExit(f"wrong declared dimensions: {target}")
            if hashlib.sha256(target.read_bytes()).digest()!=hashlib.sha256((stream/target_name).read_bytes()).digest(): raise SystemExit(f"StreamingAssets mismatch: {target_name}")
            print(f"PASS {target_name}: {dims}m, textured GLB, mirror hash matches")
            continue
        if not source.exists():
            if not target.exists(): raise SystemExit(f"missing generated model source and integrated output: {source}")
            doc,_,_=parse_glb(target); extras=doc.get("nodes",[{}])[0].get("extras",{})
            if extras.get("prl_normalized_dimensions_m")!=list(dims): raise SystemExit(f"existing model has wrong dimensions: {target}")
            shutil.copyfile(target,stream/target_name)
            print(f"Kept archived normalized model {target_name}; source GLB not supplied")
            continue
        source_dims,scale=normalize_model(source,target,dims)
        shutil.copyfile(target,stream/target_name)
        print(f"Integrated {source_name} -> {target_name}; source bounds={source_dims}; scale={scale}; world dimensions={dims}m")

    if not args.check_only:
        # Texture only freshly-generated procedural models. Generated relay/truck have their
        # own PBR maps; prior library assets and the protected barrier are never reprocessed.
        sys.path.insert(0,str(PROJECT/"tools"))
        import texture_glb_library as textures
        env_dir=art
        source_files=[]
        for path in sorted(env_dir.glob("*.glb")):
            doc,_,_=textures.parse_glb(path)
            marker=doc.get("extras",{}).get(textures.MARKER_KEY) if isinstance(doc.get("extras"),dict) else None
            if marker: continue
            if path.name in ("prop_concrete_barrier_a.glb", "env_tower_radio_relay_steel_a.glb", "veh_truck_cargo_a.glb"): continue
            if doc.get("images") or doc.get("textures"): continue
            # limit processing to catalog assets emitted by the campaign asset generator
            if doc.get("asset",{}).get("generator")=="Project Real Loser RC1.6 procedural mission asset catalog": source_files.append(path)
        if len(source_files)!=102: raise SystemExit(f"Expected 102 new procedural models to texture, got {len(source_files)}")
        with tempfile.TemporaryDirectory(prefix="prl_rc16_texture_") as temp:
            temp=Path(temp); src=temp/"src"/"Environment"; out=temp/"out"/"Environment"
            for p in source_files:
                dst=src/p.name; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(p,dst)
            transformed=0
            for p in sorted(src.glob("*.glb")):
                transformed += int(textures.transform_one(p,out/p.name))
            candidates = list(sorted(src.glob("*.glb")))
            if len(candidates)!=102: raise SystemExit(f"Expected 102 catalog GLBs; got {len(candidates)}")
            for p in sorted(out.glob("*.glb")):
                doc,_,bn=textures.parse_glb(p)
                marker=doc.get("extras",{}).get(textures.MARKER_KEY) if isinstance(doc.get("extras"),dict) else None
                if not isinstance(marker,dict) or marker.get("version")!=textures.PIPELINE_VERSION: raise SystemExit(f"missing texture marker: {p.name}")
                if not doc.get("images") or not doc.get("textures"): raise SystemExit(f"no PBR textures: {p.name}")
                for img in doc["images"][-2:]:
                    view=doc["bufferViews"][img["bufferView"]]; payload=bn[view.get("byteOffset",0):view.get("byteOffset",0)+view["byteLength"]]
                    if not payload.startswith(b"\x89PNG\r\n\x1a\n"): raise SystemExit(f"bad embedded PNG: {p.name}")
                shutil.copyfile(p,art/p.name); shutil.copyfile(p,stream/p.name)
        print(f"Verified/mirrored 102 procedural environment GLBs; newly textured this run={transformed}")
        print("Original characters, weapons, traps, existing structures, and concrete barrier were not reprocessed.")
    else:
        # Also verify the 102 additional generated files and all mission references exist.
        for p in art.glob("*.glb"):
            doc,_,_=parse_glb(p)
            if doc.get("asset",{}).get("generator")=="Project Real Loser RC1.6 procedural mission asset catalog":
                if p.name=="env_tower_radio_relay_steel_a.glb" or p.name=="veh_truck_cargo_a.glb": continue
                if not doc.get("extras",{}).get(textures.MARKER_KEY): raise SystemExit(f"missing RC1.6 texture marker: {p.name}")
                if hashlib.sha256(p.read_bytes()).digest()!=hashlib.sha256((stream/p.name).read_bytes()).digest(): raise SystemExit(f"stream mirror mismatch: {p.name}")
        print("PASS: all integrated RC1.6 GLBs and mirrors verified.")

if __name__=="__main__": main()
