# Project Real Loser — 3D Art Direction Brief (RC1.5)

## Purpose and current state

Define a coherent 3D art target for the tactical FPS environment/prop families. This is a deliberate upgrade from the current flat-factor, ultra-low-poly prototype assets. The uploaded project currently has no active verified URP setup, no authored material/texture pipeline in its custom loader, and no Unity Editor for in-engine approval; generated models remain **candidates** until these gates pass.

## Visual system

- **Identity:** grounded military reconnaissance in isolated border compounds, industrial sites, and rural approaches; original designs, with no copied IGI assets, marks, labels, or real-world unit insignia.
- **Shape language:** readable medium-scale silhouettes; boxy industrial structures, weighty cover, clear mechanical affordances; no tiny detail that disappears at normal gameplay distance.
- **Palette:** dust-tan and concrete gray for architecture, olive drab for military equipment, oxidized steel for industrial objects, and restrained amber/red only for interactive or hazardous elements.
- **Materials:** physically plausible concrete, painted steel, canvas/sandbags, rubber, glass, soil and vegetation; PBR texture sets with no baked directional lighting. UVs and texture channels must be inspected rather than assumed.
- **Lighting:** neutral reference lighting, high-to-low value separation, avoid baked shadows in albedo; final appearance must be checked in the actual runtime renderer.
- **Camera/readability:** first-person scale; props should read at 5–30 m, maintain clean ground contact, and use a ground-centered pivot. Long barriers align along local X; vertical is +Y.

## Technical frame

- Engine: Unity 2022.3.40f1; Android ARM64 is a stated target, but Android build/runtime is not currently verified.
- Existing custom loader: reads only the first primitive and POSITION/NORMAL/indices plus baseColorFactor; ignores UVs, image textures, per-primitive materials and LOD selection. Therefore textured candidates must not be called integrated until the loader or glTFast runtime path is validated.
- Repeated cover/props: target <=3,500 triangles per asset where practical; one main material; texture atlas <=1024² for repeated modular props; avoid geometry compression until the custom parser is retired or proven compatible.
- Pivots/scale: GLB local +Y up, one Unity unit = one meter, pivot at center of the ground-contact footprint. Validate bounding box dimensions and orientation from the GLB metadata.
- Collision: simple purpose-fit collider, independent of render-mesh triangle density. Existing combined BoxCollider fallback is not accepted as a final collision design.

## First representative asset target

`prop_concrete_barrier_a`: one original modular anti-vehicle concrete barrier, approximately 2.4 m long × 1.05 m high × 0.6 m deep, weathered slate-gray concrete, readable trapezoidal silhouette, chipped edges and subtle aggregate/grime, no text or stencil. It is selected because the mission data references 1,427 instances across the campaign.

## Acceptance gates before bulk production

1. Validate GLB 2.0 integrity, dimensions, face count, UV0, material slots, embedded PBR images and node transforms.
2. Confirm the exact asset is resolved by Unity's actual runtime asset path and that generated geometry/materials render correctly.
3. Inspect it in a Unity Play Mode capture at native gameplay scale against mission lighting and cover; compare silhouette and color to existing assets.
4. Check collider footprint, ground contact, occlusion/cover behavior, draw-call/material cost, and Android memory/performance.
5. Record generation provenance and retain the source prompt; do not label a candidate production-ready before these checks.
