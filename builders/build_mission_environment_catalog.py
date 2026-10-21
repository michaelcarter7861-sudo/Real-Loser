#!/usr/bin/env python3
"""Build a procedural low-poly GLB catalog for environment types referenced by M01-M10.

The generator reads mission JSON as data only. It writes one real, single-material mesh per
missing `type` into Assets/_Project/Art/Environment (or --output-dir), without overwriting
existing GLBs unless --force is supplied. Textures/UVs can be added by tools/texture_glb_library.py.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import struct
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
ENV_DIR = ROOT / "Assets" / "_Project" / "Art" / "Environment"
MISSION_FILES = [ROOT / f"M{i:02d}.json" for i in range(1, 11)]

class Mesh:
    def __init__(self, seed: int):
        self.vertices: list[tuple[float,float,float]] = []
        self.normals: list[tuple[float,float,float]] = []
        self.indices: list[int] = []
        self.rng = random.Random(seed)

    def face(self, points: Iterable[tuple[float,float,float]], normal: tuple[float,float,float]) -> None:
        pts = list(points)
        if len(pts) < 3: return
        base = len(self.vertices)
        n = normalize(normal)
        self.vertices.extend(pts)
        self.normals.extend([n] * len(pts))
        for i in range(1, len(pts)-1):
            self.indices.extend((base, base+i, base+i+1))

    def box(self, center, size) -> None:
        cx,cy,cz = center; sx,sy,sz = [max(0.005, float(v)) for v in size]
        x0,x1=cx-sx/2,cx+sx/2; y0,y1=cy-sy/2,cy+sy/2; z0,z1=cz-sz/2,cz+sz/2
        self.face([(x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)],(0,0,1))
        self.face([(x1,y0,z0),(x0,y0,z0),(x0,y1,z0),(x1,y1,z0)],(0,0,-1))
        self.face([(x1,y0,z1),(x1,y0,z0),(x1,y1,z0),(x1,y1,z1)],(1,0,0))
        self.face([(x0,y0,z0),(x0,y0,z1),(x0,y1,z1),(x0,y1,z0)],(-1,0,0))
        self.face([(x0,y1,z1),(x1,y1,z1),(x1,y1,z0),(x0,y1,z0)],(0,1,0))
        self.face([(x0,y0,z0),(x1,y0,z0),(x1,y0,z1),(x0,y0,z1)],(0,-1,0))

    def cylinder(self, center, radius: float, height: float, axis: str="y", sides: int=12, top_radius: float|None=None) -> None:
        cx,cy,cz=center; r0=max(.005,float(radius)); r1=r0 if top_radius is None else max(.001,float(top_radius)); h=max(.005,float(height))
        def point(theta, axial):
            c=math.cos(theta); s=math.sin(theta)
            if axis=="y": return (cx+c*(r0 if axial<0 else r1), cy+axial*h/2, cz+s*(r0 if axial<0 else r1))
            if axis=="x": return (cx+axial*h/2, cy+c*(r0 if axial<0 else r1), cz+s*(r0 if axial<0 else r1))
            return (cx+c*(r0 if axial<0 else r1), cy+s*(r0 if axial<0 else r1), cz+axial*h/2)
        for i in range(max(6,sides)):
            a0=2*math.pi*i/sides; a1=2*math.pi*(i+1)/sides
            p0,p1,p2,p3=point(a0,-1),point(a0,1),point(a1,1),point(a1,-1)
            if axis=="y": n=(math.cos((a0+a1)/2),0,math.sin((a0+a1)/2))
            elif axis=="x": n=(0,math.cos((a0+a1)/2),math.sin((a0+a1)/2))
            else: n=(math.cos((a0+a1)/2),math.sin((a0+a1)/2),0)
            if axis=="y": self.face([p0,p1,p2,p3],n)
            else: self.face([p0,p3,p2,p1],n)
            if axis=="y": self.face([point(a0,-1),point(a1,-1),(cx,cy-h/2,cz)],(0,-1,0)); self.face([point(a1,1),point(a0,1),(cx,cy+h/2,cz)],(0,1,0))
            elif axis=="x": self.face([point(a1,-1),point(a0,-1),(cx-h/2,cy,cz)],(-1,0,0)); self.face([point(a0,1),point(a1,1),(cx+h/2,cy,cz)],(1,0,0))
            else: self.face([point(a1,-1),point(a0,-1),(cx,cy,cz-h/2)],(0,0,-1)); self.face([point(a0,1),point(a1,1),(cx,cy,cz+h/2)],(0,0,1))

    def sphere(self, center, scale, segments: int=10, rings: int=6, jitter: float=0.0) -> None:
        cx,cy,cz=center; sx,sy,sz=scale
        grid=[]
        for r in range(rings+1):
            phi=-math.pi/2+math.pi*r/rings; row=[]
            for s in range(segments):
                theta=2*math.pi*s/segments
                noise=1+self.rng.uniform(-jitter,jitter) if jitter else 1
                nx=math.cos(phi)*math.cos(theta); ny=math.sin(phi); nz=math.cos(phi)*math.sin(theta)
                row.append((cx+nx*sx*noise,cy+ny*sy*noise,cz+nz*sz*noise,normalize((nx/max(sx,.001),ny/max(sy,.001),nz/max(sz,.001)))))
            grid.append(row)
        for r in range(rings):
            for s in range(segments):
                a=grid[r][s]; b=grid[r][(s+1)%segments]; c=grid[r+1][(s+1)%segments]; d=grid[r+1][s]
                self.face([a[:3],b[:3],c[:3]],a[3]); self.face([a[:3],c[:3],d[:3]],d[3])

    def cone(self, center, radius: float, height: float, sides: int=10) -> None:
        self.cylinder(center,radius,height,"y",sides,top_radius=.015)

    def beam(self, start, end, width: float, depth: float|None=None) -> None:
        sx,sy,sz=start; ex,ey,ez=end; dx,dy,dz=ex-sx,ey-sy,ez-sz
        length=math.sqrt(dx*dx+dy*dy+dz*dz)
        if length < .01: return
        # Oriented rectangular beam around the segment; local Y is its long axis.
        direction=(dx/length,dy/length,dz/length)
        ref=(0,0,1) if abs(direction[1])>.95 else (0,1,0)
        right=normalize((direction[1]*ref[2]-direction[2]*ref[1],direction[2]*ref[0]-direction[0]*ref[2],direction[0]*ref[1]-direction[1]*ref[0]))
        forward=normalize((direction[1]*right[2]-direction[2]*right[1],direction[2]*right[0]-direction[0]*right[2],direction[0]*right[1]-direction[1]*right[0]))
        halfw=width/2; halfd=(depth if depth is not None else width)/2
        center=((sx+ex)/2,(sy+ey)/2,(sz+ez)/2); base=len(self.vertices)
        corners=[]
        for sign_y in (-1,1):
            for sign_r,sign_f in ((-1,-1),(1,-1),(1,1),(-1,1)):
                corners.append(tuple(center[k]+direction[k]*length*sign_y/2+right[k]*halfw*sign_r+forward[k]*halfd*sign_f for k in range(3)))
        # Reuse axis-aligned box faces after rotating each corner and use face normals from geometry.
        faces=[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]
        for idxs in faces:
            pts=[corners[i] for i in idxs]
            n=normalize(cross(sub(pts[1],pts[0]),sub(pts[2],pts[0])))
            self.face(pts,n)

    def bounds(self):
        return tuple((min(v[i] for v in self.vertices),max(v[i] for v in self.vertices)) for i in range(3))


def sub(a,b): return (a[0]-b[0],a[1]-b[1],a[2]-b[2])
def cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def normalize(v):
    n=math.sqrt(sum(x*x for x in v)) or 1.0
    return tuple(x/n for x in v)


def color_for(t: str):
    if any(x in t for x in ("tree","bush","scrub","palm","pine","foliage")): return [0.18,0.28,0.15,1]
    if any(x in t for x in ("sandbag","hesko","desert","adobe","sand","tent","camo")): return [0.52,0.43,0.29,1]
    if any(x in t for x in ("wood","timber","crate","pallet","cable_spool","log")): return [0.38,0.25,0.14,1]
    if any(x in t for x in ("rock","boulder","concrete","bunker","building","wall","pillbox","fort","bridge")): return [0.39,0.41,0.39,1]
    if any(x in t for x in ("vehicle","truck","jeep","boat","chopper","forklift")): return [0.25,0.31,0.24,1]
    if any(x in t for x in ("fuel","jerrycan","drum","generator")): return [0.48,0.42,0.19,1]
    if any(x in t for x in ("alarm","terminal","radio","server","radar","monitor","console")): return [0.20,0.26,0.24,1]
    if any(x in t for x in ("steel","metal","pipe","rack","ladder","door","gate","crane","grating","transformer")): return [0.30,0.34,0.34,1]
    return [0.40,0.41,0.37,1]


def crate(m: Mesh, dims=(.9,.75,.75), metal=False, crate_type=""):
    x,y,z=dims; m.box((0,y/2,0),(x,y,z))
    accent=[x for x in ("ammo","camouflage","classified") if x in crate_type]
    for side in (-1,1):
        if metal:
            for i in range(5): m.box((side*(x/2+.012),y*(i+1)/6,0),(.025,.025,z*.92))
            m.box((side*(x/2+.02),y*.5,0),(.035,.12,.22))
        else:
            for i in (-1,1): m.box((i*x*.36,y*.5,side*z*.51),(x*.06,y*.9,.035))
            m.box((0,y*.5,side*z*.52),(x*.7,.035,.035))
    m.box((0,y+.015,0),(x*.84,.03,z*.82))
    if not metal:
        for zz in (-1,1): m.box((0,y*.5,zz*z*.53),(x*.84,.035,.035))
    # lid handles and reinforced corner blocks
    for xx in (-1,1):
        for zz in (-1,1): m.box((xx*x*.46,y*.88,zz*z*.46),(x*.08,.18,z*.08))
    return m


def sandbag_wall(m: Mesh, length=3.2, height=1.0, depth=.7):
    rows=max(2,int(round(height/.32))); count=max(3,int(round(length/.62)))
    for r in range(rows):
        offset=(r%2)*.31
        for i in range(count):
            x=-length/2+.31+i*.62+offset
            if abs(x)>length/2-.12: continue
            m.sphere((x,.22+r*.29,0),(.34,.17,depth*.5),segments=8,rings=4,jitter=.04)


def barrel(m: Mesh, radius=.34, height=.85):
    m.cylinder((0,height/2,0),radius,height,"y",16)
    for y in (.12,height*.5,height-.12): m.cylinder((0,y,0),radius*1.04,.045,"y",16)
    m.cylinder((0,height+.012,0),radius*.94,.025,"y",16)


def desk(m: Mesh, size=(1.5,.78,.72), console=False):
    x,h,z=size; top=.72*h
    m.box((0,top,0),(x,.09*h,z))
    for sx in (-1,1):
        for sz in (-1,1): m.box((sx*x*.43,top/2,sz*z*.42),(.07*x,top,.07*z))
    m.box((0,top*.33,-z*.40),(x*.7,top*.6,.06))
    if console:
        m.box((0,top+.22,-z*.12),(x*.48,.36,.12))
        m.box((0,top+.38,-z*.05),(x*.32,.2,.03))
        for xoff in (-.33,.33): m.cylinder((xoff,top+.18,0),.025,.38,"y",8)
    else:
        m.box((x*.18,top+.14,0),(.32,.25,.25))
        m.cylinder((x*.28,top+.36,0),.018,.42,"y",8)
        m.box((-x*.22,top+.11,0),(.16,.16,.1))


def vehicle(m: Mesh, kind: str, dims=(5.0,2.5,2.4)):
    length,width,height=dims; ybase=.45
    if "boat" in kind:
        m.box((0,ybase+.24,0),(length*.76,.42,width*.72))
        m.cone((length*.34,ybase+.24,0),width*.37,.65,8)
        m.box((-.15,ybase+.85,0),(length*.34,.85,width*.44))
        m.box((-.15,ybase+1.36,0),(length*.28,.08,width*.42))
        m.cylinder((-.15,ybase+1.86,0),.035,.9,"y",8)
        return
    if "chopper" in kind:
        m.box((0,ybase+.75,0),(length*.48,.75,width*.48))
        m.sphere((length*.20,ybase+.85,0),(length*.2,.42,width*.23),10,6,.02)
        m.box((-length*.34,ybase+.92,0),(length*.25,.12,.25))
        m.cylinder((-length*.48,ybase+1.07,0),.045,.72,"y",8)
        m.beam((-length*.52,ybase+1.45,0),(length*.50,ybase+1.45,0),.055,.045)
        m.beam((0,ybase+1.45,-width*.42),(0,ybase+1.45,width*.42),.05,.04)
        m.box((-length*.47,ybase+.9,0),(length*.20,.42,.08))
        return
    if "forklift" in kind:
        m.box((0,ybase+.55,0),(length*.52,.75,width*.68))
        m.box((length*.08,ybase+1.13,0),(length*.42,.09,width*.67))
        for z in (-width*.29,width*.29):
            m.beam((length*.27,ybase+.08,z),(length*.55,ybase+.08,z),.08,.12)
            m.cylinder((-.20,ybase+.32,z),.32,.18,"x",12)
            m.cylinder((length*.22,ybase+.28,z),.23,.15,"x",12)
        for x in (-length*.32,length*.32): m.beam((x,ybase+.72,-width*.4),(x,ybase+1.85,-width*.4),.08,.08)
        m.beam((-length*.32,ybase+1.8,-width*.4),(length*.34,ybase+1.8,-width*.4),.07,.07)
        return
    # armored truck/jeep
    m.box((0,ybase+.48,0),(length*.94,.42,width*.78))
    cab_len=length*.40; cab_x=length*.11
    m.box((cab_x,ybase+.95,0),(cab_len,.92,width*.74))
    m.box((cab_x,ybase+1.43,0),(cab_len*.78,.07,width*.73))
    m.box((length*.32,ybase+1.05,0),(length*.11,.42,width*.72))
    # rear covered/cargo bed
    m.box((-length*.27,ybase+.91,0),(length*.38,.60,width*.75))
    m.box((-length*.27,ybase+1.25,0),(length*.34,.08,width*.76))
    # armored window panels
    for z in (-width*.38,width*.38):
        m.box((cab_x+.06,ybase+1.12,z),(.45,.40,.025))
        m.box((cab_x-.36,ybase+1.06,z),(.10,.44,.025))
    # wheels on each side (separate geometry fused into same mesh)
    axle_x=(-length*.32,0,length*.32) if length>4 else (-length*.28,length*.28)
    for x in axle_x:
        for z in (-width*.43,width*.43):
            m.cylinder((x,ybase+.33,z),.40,.24,"z",14)
            m.cylinder((x,ybase+.33,z*1.05),.20,.255,"z",10)
    m.box((length*.48,ybase+.35,0),(.18,.38,width*.88))
    m.box((-length*.48,ybase+.35,0),(.15,.32,width*.84))
    if "jeep" in kind:
        m.box((-.03,ybase+1.4,0),(length*.32,.08,width*.72))
        m.box((cab_x,ybase+.93,0),(cab_len,.65,width*.74))


def building(m: Mesh, kind: str):
    if "3story" in kind or "3f" in kind or "fortress" in kind: dims=(15.0,9.5,12.0)
    elif "warehouse" in kind: dims=(18.0,6.5,13.0)
    elif "barracks" in kind: dims=(14.0,4.2,8.0)
    elif "bunker" in kind or "pillbox" in kind or "command_fort" in kind: dims=(9.0,4.2,8.0)
    elif "guard_booth" in kind or "guardhouse" in kind or "hut" in kind: dims=(4.0,3.1,4.0)
    elif "tent" in kind or "carport" in kind or "canopy" in kind: dims=(6.0,3.5,5.0)
    elif "cabin" in kind: dims=(7.0,3.6,6.0)
    else: dims=(8.0,4.0,7.0)
    x,h,z=dims; wall_h=h*.78
    # Solid low-poly shell with inset doorway/windows; roof lip adds readable silhouette.
    m.box((0,wall_h/2,0),(x,wall_h,z))
    m.box((0,wall_h+.13,0),(x+.28,.26,z+.28))
    m.box((0,h-.06,0),(x*.88,.12,z*.88))
    door_w=min(1.35,x*.15); door_h=min(2.35,wall_h*.78)
    m.box((0,door_h/2,-z/2-.035),(door_w,door_h,.07))
    cols=max(1,int(x//3)); floors=max(1,int(wall_h//2.8))
    for f in range(floors):
        wy=1.1+f*2.5
        if wy+0.65 >= wall_h: continue
        for i in range(cols):
            wx=-x*.36+i*(x*.72/max(1,cols-1)) if cols>1 else x*.28
            if abs(wx)<door_w*.8 and f==0: continue
            m.box((wx,wy,-z/2-.045),(.72,.58,.05))
            m.box((wx,wy,z/2+.045),(.72,.58,.05))
    # corner pilasters, roof vents and sandbag/parapet edge
    for sx in (-1,1):
        for sz in (-1,1): m.box((sx*x*.48,wall_h*.5,sz*z*.48),(.18,wall_h,.18))
    for i in range(2):
        m.box((x*.25*(i-.5),h+.25,0),(.52,.38,.46))
    if "warehouse" in kind:
        m.box((0,1.65,-z/2-.08),(x*.38,2.7,.10))
        for i in range(9): m.box((-x*.17+i*x*.042,1.65,-z/2-.15),(.022,2.5,.04))
    if "bunker" in kind or "pillbox" in kind:
        m.box((0,h*.52,-z/2-.10),(x*.55,.18,.10))
    if "fort" in kind or "fortress" in kind:
        for sx in (-1,1): m.box((sx*x*.39,h+.4,-z*.39),(1.15,.55,1.15))


def make_asset(asset_id: str) -> tuple[Mesh,str]:
    seed=int.from_bytes(hashlib.sha256(asset_id.encode()).digest()[:4],"little")
    m=Mesh(seed); t=asset_id.lower()
    if "sandbag" in t or "hesko" in t:
        sandbag_wall(m,4.0 if "hesko" in t else 3.4,1.3 if "hesko" in t else .92,.8)
    elif "crate" in t or "cardboard" in t or "pallet" in t:
        dims=(1.0,.82,.78) if "ammo" in t else (.88,.72,.72)
        crate(m,dims,metal=("metal" in t),crate_type=t)
        if "pallet" in t:
            for x in (-.38,0,.38): m.box((x,.08,0),(.14,.16,.72))
    elif "boulder" in t or "rock" in t:
        m.sphere((0,.48,0),(1.15,.72,.92),segments=9,rings=5,jitter=.20)
    elif "fuel_drum" in t or "barrel" in t or "drum" in t:
        barrel(m,.34,.88)
    elif "jerrycan" in t:
        m.box((0,.38,0),(.46,.7,.30)); m.box((0,.78,0),(.25,.06,.14)); m.cylinder((.18,.71,0),.045,.10,"y",8)
        m.box((-.25,.40,0),(.045,.5,.30))
    elif "spool" in t:
        m.cylinder((0,.5,0),.52,.12,"y",12); m.cylinder((0,.50,0),.25,.75,"y",12); m.cylinder((0,.92,0),.52,.12,"y",12)
        for i in range(8):
            a=2*math.pi*i/8; m.box((math.cos(a)*.38,.52,math.sin(a)*.38),(.12,.68,.12))
    elif "radio_field_desk" in t or "terminal_desk" in t or "shipping_manifest_desk" in t or "radar_console" in t or "map_board" in t:
        desk(m,(1.65,.82,.85),console=("radar" in t or "terminal" in t or "radio" in t))
        if "map_board" in t:
            m.beam((0,.85,0),(0,1.8,.2),.07,.07); m.box((0,1.68,.16),(.95,.78,.07))
    elif "workbench" in t:
        desk(m,(1.75,.86,.82),False)
        for i in range(4): m.box((-.55+i*.36,.96,0),(.15,.13,.15))
        m.box((0,.22,-.35),(1.25,.38,.07))
    elif "server" in t or "mainframe" in t:
        m.box((0,1.1,0),(1.05,2.15,.92))
        for i in range(7):
            y=.24+i*.25; m.box((0,y,-.48),( .86,.18,.045))
            m.sphere((.28,y,.0),(.035,.035,.025),6,3)
    elif "workstation" in t or "locker" in t or "closet" in t or "wardrobe" in t:
        m.box((0,1.0,0),(.95,2.0,.62))
        for x in (-.22,.22): m.box((x,1.0,-.33),(.018,1.72,.03)); m.cylinder((x+.06,1.0,-.38),.025,.12,"z",8)
    elif "fuel_tank" in t or "manifold" in t or "pipe" in t or "cooling_unit" in t or "transformer" in t:
        if "tank" in t:
            m.cylinder((0,1.05,0),.65,2.3,"x",16); m.cylinder((-.9,1.05,0),.68,.08,"x",16); m.cylinder((.9,1.05,0),.68,.08,"x",16)
            for x in (-.62,.62): m.box((x,.32,0),(.18,.65,.18))
        else:
            m.box((0,.78,0),(1.45,1.55,.92))
            for y in (.38,.65,.92,1.19): m.box((0,y,-.49),(1.17,.035,.04))
            for x in (-.45,0,.45): m.cylinder((x,1.63,0),.11,.4,"y",10)
    elif "fuel" in t or "generator" in t:
        m.box((0,.64,0),(1.45,1.2,.86)); m.box((0,1.28,0),(1.18,.1,.78))
        for i in range(7): m.box((-.42+i*.14,.72,-.46),(.045,.68,.035))
        m.cylinder((.55,.2,.18),.11,.44,"y",10); m.box((-.62,.3,0),(.14,.46,.7))
    elif "radio_transmitter" in t or "alarm_panel" in t or "breaker_box" in t or "terminal" in t or "control" in t:
        m.box((0,.72,0),(.66,1.2,.3)); m.box((0,1.27,-.17),(.48,.22,.035))
        for i in range(5): m.cylinder((-.18+i*.09,.82,-.18),.025,.04,"z",8)
        m.cylinder((.23,1.42,0),.025,.46,"y",8)
    elif "weapon_rack" in t or "shelving" in t or "rack" in t:
        for x in (-.65,.65): m.box((x,1.25,0),(.08,2.5,.08))
        for y in (.18,.82,1.48,2.12): m.box((0,y,0),(1.4,.07,.5))
        if "weapon" in t:
            for i in range(5):
                x=-.45+i*.22; m.box((x,1.5,0),(.035,.86,.045)); m.box((x,1.9,0),(.07,.26,.06))
    elif "cot" in t or "bed" in t:
        m.box((0,.45,0),(1.9,.16,.78)); m.box((0,.57,0),(1.82,.12,.72))
        for x in (-.82,.82):
            for z in (-.28,.28): m.box((x,.22,z),(.06,.45,.06))
    elif "chair" in t:
        m.box((0,.48,0),(.62,.14,.62)); m.box((0,.94,-.25),(.62,.92,.12))
        for x in (-.24,.24):
            for z in (-.24,.24): m.box((x,.23,z),(.06,.46,.06))
        for x in (-.36,.36): m.box((x,.75,0),(.08,.54,.58))
    elif "container_" in t or "shipping_container" in t:
        length=12.0 if "40" in t else 6.0
        m.box((0,1.3,0),(length,2.6,2.45)); m.box((0,2.63,0),(length+.08,.1,2.5))
        for x in [(-length/2+.22)+i*.42 for i in range(int(length/.42))]:
            m.box((x,1.3,-1.24),(.045,2.48,.045)); m.box((x,1.3,1.24),(.045,2.48,.045))
        for z in (-1,1):
            m.box((length/2+.04,1.3,z*.34),(.04,2.5,.055))
    elif "tire" in t:
        for x in (-.35,.35):
            for y in (.38,.88):
                m.cylinder((x,y,0),.43,.24,"z",14); m.cylinder((x,y,-.14),.22,.26,"z",12)
    elif "traffic_cone" in t:
        m.cylinder((0,.06,0),.28,.12,"y",8); m.cone((0,.42,0),.22,.70,8); m.cylinder((0,.54,0),.15,.07,"y",8)
    elif "sign" in t or "milepost" in t or "marker" in t:
        m.box((0,1.35,0),(1.1,.72,.10)); m.box((0,.67,0),(.1,1.45,.1)); m.box((0,.09,0),(.44,.18,.42))
        if "extraction" in t or "helipad" in t:
            m.cylinder((0,.03,0),2.5,.06,"y",32)
            m.box((0,.09,0),(1.25,.02,.14)); m.box((0,.09,0),(.14,.02,1.25))
    elif "helipad" in t:
        m.cylinder((0,.035,0),4.0,.07,"y",32)
        m.box((0,.08,0),(2.4,.02,.18)); m.box((0,.08,0),(.18,.02,2.4))
        m.box((0,.08,0),(1.0,.02,.12))
    elif "radar_dish" in t or "dish_dome" in t:
        m.box((0,.35,0),(1.4,.55,1.2)); m.cylinder((0,1.2,0),.07,1.2,"y",10)
        m.sphere((0,2.0,0),(1.25,1.25,.20),segments=14,rings=8,jitter=.015)
        m.beam((0,1.0,0),(0,1.72,-.05),.09,.09)
        m.box((-.55,2.0,.0),(.12,2.15,.1))
    elif "tree" in t or "palm" in t or "pine" in t or "bush" in t or "scrub" in t:
        if "bush" in t or "scrub" in t:
            for _ in range(7):
                x=m.rng.uniform(-.55,.55); z=m.rng.uniform(-.45,.45); y=m.rng.uniform(.45,.95)
                m.sphere((x,y,z),(.42,.38,.42),segments=8,rings=5,jitter=.1)
        else:
            h=5.5 if "pine" in t else 4.8
            m.cylinder((0,h*.42,0),.22,h*.84,"y",10,top_radius=.10)
            if "palm" in t:
                for i in range(7):
                    a=2*math.pi*i/7; m.beam((0,h*.82,0),(math.cos(a)*1.5,h*.92-.35,math.sin(a)*1.5),.11,.07)
                    m.sphere((math.cos(a)*.95,h*.88,math.sin(a)*.95),(.72,.13,.28),8,4,.12)
            else:
                for i in range(4): m.cone((0,h*.45+i*.72,0),1.2-i*.20,2.3-i*.3,9)
    elif "ladder" in t:
        h=4.0 if "4m" in t else 9.0
        for x in (-.34,.34): m.box((x,h/2,0),(.08,h,.08))
        for i in range(int(h/.35)): m.box((0,.2+i*.35,0),(.72,.055,.075))
    elif "vent" in t or "shaft" in t or "chimney" in t:
        m.box((0,.12,0),(1.1,.24,1.1)); m.box((0,.78,0),(.72,1.2,.72)); m.box((0,1.42,0),(1.0,.16,1.0))
        for i in range(5): m.box((0,.55+i*.16,-.38),(.55,.035,.04))
    elif "ladder" in t:
        for x in (-.3,.3): m.box((x,1.7,0),(.06,3.4,.06))
    elif "bridge" in t or "platform" in t or "grating" in t or "roadblock" in t or "girder" in t or "timber_stack" in t or "log" in t:
        for i in range(5): m.box((0,.9,-.6+i*.3),(3.6,.12,.25))
        for x in (-1.5,1.5): m.box((x,.5,0),(.18,1.0,1.6))
        for x in (-1.6,1.6): m.box((x,1.3,0),(.08,.8,1.7))
    elif "crane" in t:
        for x in (-3,3):
            m.box((x,3,0),(.38,6,.38)); m.box((x,5.95,0),(.55,.32,.55))
        m.box((0,6,0),(6.5,.42,.48)); m.box((0,5.66,0),(.18,.18,.18)); m.beam((0,5.6,0),(0,3.0,0),.07,.07)
        m.box((0,2.85,0),(.36,.26,.36))
    elif "floodlight" in t or "searchlight" in t:
        m.box((0,.1,0),(.9,.18,.9)); m.cylinder((0,2.4,0),.075,4.6,"y",10); m.beam((0,4.5,0),(0,5.1,0),.12,.12)
        for x in (-.2,.2): m.box((x,5.12,-.1),(.38,.25,.12))
    elif "boat" in t or "chopper" in t or "forklift" in t or "veh_" in t:
        if "forklift" in t: vehicle(m,"forklift",(3.0,2.2,2.3))
        elif "boat" in t: vehicle(m,"boat_patrol",(6.5,2.4,2.1))
        elif "chopper" in t: vehicle(m,"chopper",(9.0,3.8,3.0))
        elif "jeep" in t: vehicle(m,"jeep",(4.2,2.2,2.3))
        else: vehicle(m,"truck",(5.7,2.7,2.5))
    elif "tent" in t or "canopy" in t:
        m.box((0,.16,0),(5.5,.2,4.5))
        for x in (-2.55,2.55): m.box((x,1.45,0),(.12,2.9,.12))
        for z in (-2.1,2.1): m.beam((-2.7,2.6,z),(2.7,2.6,z),.10,.10)
        m.beam((-2.5,2.6,-2.1),(0,3.35,0),.09,.09); m.beam((0,3.35,0),(2.5,2.6,2.1),.09,.09)
        m.beam((-2.5,2.6,2.1),(0,3.35,0),.09,.09); m.beam((0,3.35,0),(2.5,2.6,-2.1),.09,.09)
    elif "vault" in t or "safe" in t or "door" in t or "elevator" in t or "gate" in t:
        m.box((0,1.4,0),(1.45,2.8,.22)); m.box((0,1.4,-.14),(1.15,2.45,.06))
        for x in (-.63,.63): m.cylinder((x,1.4,-.2),.045,2.35,"y",8)
        m.cylinder((.32,1.42,-.24),.12,.11,"z",10); m.box((-.35,.28,-.24),(.25,.06,.05))
    else:
        # Deterministic detailed utility prop fallback: cabinet + legs + control panel.
        m.box((0,.75,0),(1.15,1.45,.75)); m.box((0,1.52,-.39),(.75,.28,.04))
        for x in (-.44,.44): m.box((x,.15,0),(.08,.3,.08))
        for i in range(3): m.cylinder((-.2+i*.2,1.05,-.41),.04,.05,"z",8)
    # Additional contextual detail for unique terms improves silhouette/readability.
    if "antenna" in t or "mast" in t:
        m.cylinder((0,2.9,0),.055,5.6,"y",8)
        for y in (1.0,2.0,3.2,4.2):
            m.beam((-.8,y,0),(.8,y,0),.055,.055); m.beam((0,y,-.8),(0,y,.8),.055,.055)
    if "manifold" in t:
        for x in (-.65,-.22,.22,.65): m.cylinder((x,.7,0),.07,1.2,"y",10)
        m.cylinder((0,1.2,0),.10,1.6,"x",12)
    return m, archetype_for(t)


def archetype_for(t: str) -> str:
    rules=[("sandbag","sandbag_wall"),("hesko","hesco_bastion"),("crate","crate"),("rock","boulder"),("boulder","boulder"),("barrel","drum"),("drum","drum"),("jerrycan","canister"),("spool","cable_spool"),("server","server_rack"),("mainframe","server_rack"),("tree","tree"),("pine","pine_tree"),("bush","bush"),("scrub","scrub"),("veh_","vehicle"),("tent","field_shelter"),("bldg","building"),("bunker","bunker"),("warehouse","warehouse"),("radar","console_or_radar"),("mast","antenna_mast"),("ladder","ladder"),("door","door"),("safe","safe")]
    for term,name in rules:
        if term in t: return name
    return "utility_prop"


def write_glb(path: Path, asset_id: str, mesh: Mesh, archetype: str) -> None:
    if len(mesh.vertices)>60000: raise ValueError(f"mesh exceeds uint16 index budget: {asset_id}")
    pos_raw=b"".join(struct.pack("<3f",*v) for v in mesh.vertices)
    norm_raw=b"".join(struct.pack("<3f",*v) for v in mesh.normals)
    idx_raw=b"".join(struct.pack("<H",i) for i in mesh.indices)
    binbuf=bytearray()
    views=[]
    for raw,target in ((pos_raw,34962),(norm_raw,34962),(idx_raw,34963)):
        while len(binbuf)%4: binbuf.append(0)
        off=len(binbuf); binbuf.extend(raw); views.append({"buffer":0,"byteOffset":off,"byteLength":len(raw),"target":target})
    mins=[min(v[i] for v in mesh.vertices) for i in range(3)]; maxs=[max(v[i] for v in mesh.vertices) for i in range(3)]
    color=color_for(asset_id)
    dims=[round(maxs[i]-mins[i],3) for i in range(3)]
    doc={
      "asset":{"version":"2.0","generator":"Project Real Loser RC1.6 procedural mission asset catalog"},
      "scene":0,"scenes":[{"name":"AssetScene","nodes":[0]}],
      "nodes":[{"name":asset_id,"mesh":0,"translation":[0,0,0],"rotation":[0,0,0,1],"scale":[1,1,1],"extras":{"asset_id":asset_id,"archetype":archetype,"dimensions":dims,"ground_pivot_y":round(mins[1],3)}}],
      "meshes":[{"name":asset_id+"_Mesh","primitives":[{"attributes":{"POSITION":0,"NORMAL":1},"indices":2,"material":0,"mode":4}]}],
      "materials":[{"name":asset_id+"_Mat","doubleSided":False,"pbrMetallicRoughness":{"baseColorFactor":color,"metallicFactor":0.18 if "metal" in asset_id or "steel" in asset_id else 0.05,"roughnessFactor":0.82}}],
      "accessors":[
        {"bufferView":0,"byteOffset":0,"componentType":5126,"count":len(mesh.vertices),"type":"VEC3","min":[round(x,5) for x in mins],"max":[round(x,5) for x in maxs]},
        {"bufferView":1,"byteOffset":0,"componentType":5126,"count":len(mesh.normals),"type":"VEC3"},
        {"bufferView":2,"byteOffset":0,"componentType":5123,"count":len(mesh.indices),"type":"SCALAR","min":[min(mesh.indices)],"max":[max(mesh.indices)]}],
      "bufferViews":views,"buffers":[{"byteLength":len(binbuf)}]
    }
    jraw=json.dumps(doc,separators=(",",":"),ensure_ascii=False).encode("utf-8")
    jraw+=b" "*((4-len(jraw)%4)%4)
    body=struct.pack("<II",len(jraw),0x4E4F534A)+jraw+struct.pack("<II",len(binbuf),0x004E4942)+binbuf
    total=12+len(body)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(struct.pack("<4sII",b"glTF",2,total)+body)


def referenced_types() -> set[str]:
    result=set()
    for path in MISSION_FILES:
        if not path.is_file(): raise FileNotFoundError(path)
        data=json.loads(path.read_text(encoding="utf-8"))
        for group in ("structures","props","cover","vegetation","hiding_spots"):
            for item in data.get(group,[]) or []:
                if item and item.get("type"): result.add(item["type"])
    return result


def validate_glb(path: Path) -> None:
    data=path.read_bytes()
    if len(data)<20: raise ValueError(f"short GLB: {path}")
    magic,version,total=struct.unpack_from("<4sII",data,0)
    if magic!=b"glTF" or version!=2 or total!=len(data): raise ValueError(f"bad GLB header: {path}")
    offset=12; doc=None; bin_len=0
    while offset+8<=len(data):
        size,kind=struct.unpack_from("<II",data,offset); offset+=8
        payload=data[offset:offset+size]; offset+=size
        if len(payload)!=size: raise ValueError(f"short chunk: {path}")
        if kind==0x4E4F534A: doc=json.loads(payload.decode("utf-8").rstrip(" \t\r\n\0"))
        elif kind==0x004E4942: bin_len=len(payload)
    if doc is None or len(doc.get("meshes",[]))!=1: raise ValueError(f"bad generated mesh: {path}")
    prim=doc["meshes"][0]["primitives"][0]
    pos=doc["accessors"][prim["attributes"]["POSITION"]]
    idx=doc["accessors"][prim["indices"]]
    if pos["count"]<3 or idx["count"]<3 or idx["count"]%3: raise ValueError(f"bad geometry counts: {path}")
    for view in doc.get("bufferViews",[]):
        if view["buffer"]!=0 or view["byteOffset"]+view["byteLength"]>bin_len: raise ValueError(f"buffer view out of bounds: {path}")
    if "NORMAL" not in prim["attributes"]: raise ValueError(f"missing normals: {path}")


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir",type=Path,default=ENV_DIR)
    parser.add_argument("--check",action="store_true",help="check all mission-referenced environment types have valid GLBs")
    parser.add_argument("--force",action="store_true",help="overwrite files produced by a previous run")
    args=parser.parse_args()
    types=referenced_types(); present={p.stem for p in ENV_DIR.glob("*.glb")}
    missing=sorted(types-present)
    if args.check:
        absent=[t for t in sorted(types) if not (args.output_dir/(t+".glb")).is_file()]
        if absent: print(f"FAIL: {len(absent)} referenced model files missing; first: {absent[:12]}"); return 1
        for t in sorted(types): validate_glb(args.output_dir/(t+".glb"))
        print(f"PASS: {len(types)} distinct referenced environment model types have valid GLB 2.0 geometry.")
        return 0
    args.output_dir.mkdir(parents=True,exist_ok=True); generated=0; skipped=0
    for asset_id in missing:
        path=args.output_dir/(asset_id+".glb")
        if path.exists() and not args.force: skipped+=1; continue
        seed=int.from_bytes(hashlib.sha256(asset_id.encode()).digest()[:4],"little")
        mesh,archetype=make_asset(asset_id)
        if not mesh.vertices or not mesh.indices: raise RuntimeError(f"empty mesh for {asset_id}")
        write_glb(path,asset_id,mesh,archetype); validate_glb(path); generated+=1
    print(f"Generated {generated} unique procedural GLB models; skipped existing {skipped}; mission references={len(types)}, already supplied={len(present)}; output={args.output_dir}")
    return 0

if __name__=="__main__": raise SystemExit(main())
