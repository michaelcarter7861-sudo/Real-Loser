#!/usr/bin/env python3
"""
Project Real Loser — Procedural Tactical Audio Bank Synthesizer (build_audio_bank.py)
Target Engine: Unity 2022.3.40f1 LTS (URP, Android ARM64 IL2CPP)

Synthesizes 34 multi-layered 16-bit PCM `.wav` sound files and `audio_manifest.json`
in `Assets/_Project/Audio/` passing `validate_audio.py`.
"""

import os
import sys
import json
import math
import wave
import struct
import random
from typing import Dict, Any, List, Tuple

SAMPLE_RATE = 22050

# (event_id, duration_sec, base_freq, decay_rate, noise_mix, mod_freq, category, noise_radius_m)
AUDIO_SPECS = [
    ("sfx_footstep_concrete_stand",     0.22, 140.0, 18.0, 0.45,  8.0, "footstep", 7.5),
    ("sfx_footstep_concrete_crouch",    0.20, 115.0, 22.0, 0.35,  6.0, "footstep", 3.4),
    ("sfx_footstep_metal_stand",        0.26, 420.0, 14.0, 0.30, 32.0, "footstep", 11.0),
    ("sfx_footstep_gravel_stand",       0.28, 260.0, 12.0, 0.75, 45.0, "footstep", 12.5),
    ("sfx_footstep_grass_prone",        0.24,  95.0, 16.0, 0.60, 14.0, "footstep", 0.8),
    ("sfx_wpn_pistol_fire",             0.38, 190.0, 11.0, 0.65, 22.0, "weapon",   38.0),
    ("sfx_wpn_pistol_suppressed",       0.22, 310.0, 24.0, 0.55, 18.0, "weapon",    8.5),
    ("sfx_wpn_rifle_fire",              0.46, 155.0,  9.5, 0.72, 28.0, "weapon",   62.0),
    ("sfx_wpn_sniper_fire",             0.68, 110.0,  6.5, 0.78, 16.0, "weapon",   95.0),
    ("sfx_wpn_shotgun_fire",            0.55, 125.0,  7.5, 0.82, 19.0, "weapon",   72.0),
    ("sfx_wpn_reload_mag",              0.32, 540.0, 15.0, 0.25, 38.0, "weapon",    3.0),
    ("sfx_melee_knife_slash",           0.20, 680.0, 20.0, 0.50, 25.0, "melee",     2.5),
    ("sfx_melee_garrote_choke",         0.35, 180.0, 10.0, 0.40, 12.0, "melee",     0.8),
    ("sfx_trap_t1_tripwire_alarm",      0.65, 880.0,  4.5, 0.15, 16.0, "trap",     40.0),
    ("sfx_trap_t2_grenade_detonate",    0.75,  85.0,  5.0, 0.85, 12.0, "trap",     55.0),
    ("sfx_trap_t3_claymore_blast",      0.78,  92.0,  4.8, 0.86, 15.0, "trap",     60.0),
    ("sfx_trap_t4_mine_click_blast",    0.82,  78.0,  4.2, 0.88, 11.0, "trap",     65.0),
    ("sfx_trap_t5_laser_hum_alarm",     0.50, 740.0,  6.0, 0.18, 24.0, "trap",     45.0),
    ("sfx_trap_t6_motion_sensor_chirp", 0.34, 1250.0, 11.0, 0.12, 30.0, "trap",    35.0),
    ("sfx_trap_t7_pressure_plate_click",0.25, 380.0, 19.0, 0.30, 14.0, "trap",     40.0),
    ("sfx_trap_t8_noise_cans_rattle",   0.48, 620.0,  8.5, 0.55, 42.0, "trap",     15.0),
    ("sfx_trap_t9_turret_servo_burst",  0.56, 290.0,  7.0, 0.48, 35.0, "trap",     50.0),
    ("sfx_trap_t10_searchlight_hum",    0.45, 120.0,  5.5, 0.22,  9.0, "trap",      6.0),
    ("sfx_trap_t11_camera_servo_beep",  0.36, 960.0,  9.0, 0.15, 20.0, "trap",     35.0),
    ("sfx_trap_t12_electric_fence_arc", 0.42, 460.0,  8.0, 0.68, 55.0, "trap",     14.0),
    ("sfx_trap_t13_alarmed_door_siren", 0.70, 790.0,  4.0, 0.20, 10.0, "trap",     45.0),
    ("sfx_trap_t14_booby_door_snap",    0.64, 105.0,  5.8, 0.80, 18.0, "trap",     50.0),
    ("sfx_trap_t15_guard_dog_bark",     0.44, 240.0,  8.5, 0.42, 15.0, "trap",     28.0),
    ("sfx_trap_t16_steam_vent_hiss",    0.58, 520.0,  6.2, 0.82, 26.0, "trap",     12.0),
    ("sfx_gadget_emp_pulse",            0.52, 340.0,  7.5, 0.45, 48.0, "gadget",   10.0),
    ("sfx_gadget_pda_hack_complete",    0.30, 1120.0, 12.0, 0.10, 22.0, "gadget",   1.5),
    ("sfx_gadget_wire_cutter_snip",     0.20, 820.0, 24.0, 0.32, 19.0, "gadget",   1.2),
    ("sfx_ai_radio_checkin_beep",       0.32, 1040.0, 10.5, 0.18, 28.0, "ai_comms", 4.0),
    ("sfx_compound_klaxon_alert2",      0.85, 660.0,  3.6, 0.24,  7.5, "alarm",    80.0),
]


def synthesize_wav(
    filepath: str,
    seed_idx: int,
    duration: float,
    base_freq: float,
    decay_rate: float,
    noise_mix: float,
    mod_freq: float,
) -> None:
    rng = random.Random(1000 + seed_idx * 97)
    nframes = int(SAMPLE_RATE * duration)
    samples = []

    for i in range(nframes):
        t = i / float(SAMPLE_RATE)
        # Sharp transient attack + multi-stage exponential decay so crest factor is realistic (> 2.0)
        attack = min(1.0, i / 45.0)
        env = attack * math.exp(-decay_rate * t)
        # Secondary burst pulse for mechanical/echo character
        if t > duration * 0.35:
            env += 0.28 * math.exp(-decay_rate * 1.4 * (t - duration * 0.35))

        fm = math.sin(2.0 * math.pi * mod_freq * t) * 0.25
        tonal = (
            0.65 * math.sin(2.0 * math.pi * base_freq * (1.0 + fm) * t)
            + 0.25 * math.sin(2.0 * math.pi * (base_freq * 1.98) * t)
            + 0.10 * math.cos(2.0 * math.pi * (base_freq * 3.12) * t)
        )
        noise = rng.uniform(-1.0, 1.0)
        val = env * ((1.0 - noise_mix) * tonal + noise_mix * noise)
        pcm = max(-32767, min(32767, int(val * 28500.0)))
        samples.append(pcm)

    with wave.open(filepath, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))


def build_audio_bank(out_dir: str = "Assets/_Project/Audio") -> int:
    os.makedirs(out_dir, exist_ok=True)
    manifest: Dict[str, Any] = {
        "engine": "Unity 2022.3.40f1 LTS",
        "sample_rate": SAMPLE_RATE,
        "events": {},
    }

    for idx, (ev_id, dur, freq, decay, n_mix, m_freq, cat, n_rad) in enumerate(AUDIO_SPECS):
        wav_path = os.path.join(out_dir, f"{ev_id}.wav")
        synthesize_wav(wav_path, idx, dur, freq, decay, n_mix, m_freq)
        manifest["events"][ev_id] = {
            "file": f"{ev_id}.wav",
            "category": cat,
            "duration_sec": dur,
            "noise_radius_m": n_rad,
        }

    manifest_path = os.path.join(out_dir, "audio_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"[BUILD SUCCESS] Generated {len(AUDIO_SPECS)} tactical .wav files and audio_manifest.json in '{out_dir}'.")
    return 0


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "Assets/_Project/Audio"
    sys.exit(build_audio_bank(target))
