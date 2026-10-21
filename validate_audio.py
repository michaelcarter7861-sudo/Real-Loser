#!/usr/bin/env python3
"""
Project Real Loser — Tactical Audio Bank Validator (validate_audio.py)
Target Engine: Unity 2022.3.40f1 LTS (URP, Android ARM64 IL2CPP)
"""

import os
import sys
import json
import wave
import math
import struct
import hashlib
from typing import Dict, List, Tuple, Any

REQUIRED_AUDIO_EVENTS = [
    "sfx_footstep_concrete_stand",
    "sfx_footstep_concrete_crouch",
    "sfx_footstep_metal_stand",
    "sfx_footstep_gravel_stand",
    "sfx_footstep_grass_prone",
    "sfx_wpn_pistol_fire",
    "sfx_wpn_pistol_suppressed",
    "sfx_wpn_rifle_fire",
    "sfx_wpn_sniper_fire",
    "sfx_wpn_shotgun_fire",
    "sfx_wpn_reload_mag",
    "sfx_melee_knife_slash",
    "sfx_melee_garrote_choke",
    "sfx_trap_t1_tripwire_alarm",
    "sfx_trap_t2_grenade_detonate",
    "sfx_trap_t3_claymore_blast",
    "sfx_trap_t4_mine_click_blast",
    "sfx_trap_t5_laser_hum_alarm",
    "sfx_trap_t6_motion_sensor_chirp",
    "sfx_trap_t7_pressure_plate_click",
    "sfx_trap_t8_noise_cans_rattle",
    "sfx_trap_t9_turret_servo_burst",
    "sfx_trap_t10_searchlight_hum",
    "sfx_trap_t11_camera_servo_beep",
    "sfx_trap_t12_electric_fence_arc",
    "sfx_trap_t13_alarmed_door_siren",
    "sfx_trap_t14_booby_door_snap",
    "sfx_trap_t15_guard_dog_bark",
    "sfx_trap_t16_steam_vent_hiss",
    "sfx_gadget_emp_pulse",
    "sfx_gadget_pda_hack_complete",
    "sfx_gadget_wire_cutter_snip",
    "sfx_ai_radio_checkin_beep",
    "sfx_compound_klaxon_alert2",
]


def inspect_wav(filepath: str) -> Tuple[bool, List[str], str]:
    errors: List[str] = []
    try:
        with wave.open(filepath, "rb") as wf:
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            nframes = wf.getnframes()
            raw = wf.readframes(nframes)
    except Exception as exc:
        return False, [f"Invalid WAV file: {exc}"], ""

    if sampwidth != 2:
        errors.append(f"Expected 16-bit PCM (sampwidth=2), got {sampwidth}")
    if framerate not in (22050, 44100, 48000):
        errors.append(f"Unexpected sample rate: {framerate}")
    if nframes < int(framerate * 0.08):
        errors.append(f"Audio clip too short ({nframes} frames)")

    count = len(raw) // 2
    if count == 0:
        return False, ["Empty PCM sample buffer"], ""

    samples = struct.unpack(f"<{count}h", raw[: count * 2])
    sum_sq = sum(s * s for s in samples)
    rms = math.sqrt(sum_sq / count) / 32768.0
    if rms < 0.005:
        errors.append(f"Audio clip is near-silent (RMS={rms:.5f} < 0.005)")

    peak = max(abs(s) for s in samples) / 32768.0
    crest = peak / max(rms, 1e-6)
    if crest < 1.45:
        errors.append(f"Audio clip has unnaturally flat envelope (crest factor={crest:.2f})")

    audio_hash = hashlib.sha256(raw).hexdigest()
    return (len(errors) == 0), errors, audio_hash


def validate_audio_bank(audio_dir: str) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    if not os.path.isdir(audio_dir):
        return False, [f"Audio directory not found: {audio_dir}"]

    manifest_path = os.path.join(audio_dir, "audio_manifest.json")
    if not os.path.exists(manifest_path):
        errors.append(f"Missing audio_manifest.json in {audio_dir}")
        manifest = {}
    else:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f).get("events", {})

    seen_hashes: Dict[str, str] = {}
    for ev in REQUIRED_AUDIO_EVENTS:
        wav_path = os.path.join(audio_dir, f"{ev}.wav")
        if not os.path.exists(wav_path):
            errors.append(f"Missing required audio file: {wav_path}")
            continue
        ok, w_errs, ahash = inspect_wav(wav_path)
        if not ok:
            for e in w_errs:
                errors.append(f"[{ev}] {e}")
            continue
        if ahash in seen_hashes:
            errors.append(f"[DUPLICATE AUDIO] {ev} shares identical PCM data with {seen_hashes[ahash]}")
        else:
            seen_hashes[ahash] = ev

        if ev not in manifest:
            errors.append(f"[{ev}] Missing acoustic metadata entry in audio_manifest.json")
        else:
            m = manifest[ev]
            if "noise_radius_m" not in m or "category" not in m:
                errors.append(f"[{ev}] Incomplete acoustic metadata in audio_manifest.json")

    return (len(errors) == 0), errors


def main() -> int:
    audio_dir = sys.argv[1] if len(sys.argv) > 1 else "Assets/_Project/Audio"
    ok, errs = validate_audio_bank(audio_dir)
    if ok:
        print(
            f"[PASS] All {len(REQUIRED_AUDIO_EVENTS)} tactical audio .wav assets and manifest "
            f"in '{audio_dir}' passed acoustic & signal validation."
        )
        return 0
    else:
        print(f"[FAIL] Audio validation failed with {len(errs)} error(s):")
        for e in errs:
            print(f"  - {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
