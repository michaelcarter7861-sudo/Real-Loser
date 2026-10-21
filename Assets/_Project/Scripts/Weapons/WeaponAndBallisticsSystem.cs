using System;
using System.Collections.Generic;
using UnityEngine;
using RealLoserStudio.Tactical.Stealth;
using RealLoserStudio.Tactical.AI;
using RealLoserStudio.Tactical.Traps;

namespace RealLoserStudio.Tactical.Weapons
{
    public enum WeaponSlotCategory
    {
        Sidearm = 0,
        SMG = 1,
        AssaultRifle = 2,
        Shotgun = 3,
        SniperRifle = 4,
        HeavyWeapon = 5,
        MeleeStealth = 6
    }

    [Serializable]
    public struct WeaponDefinition
    {
        public string weaponId;
        public string displayName;
        public WeaponSlotCategory category;
        public float baseDamage;
        public float roundsPerMinute;
        public int magazineCapacity;
        public float reloadSeconds;
        public float effectiveRangeMeters;
        public float noiseRadiusMeters;
        public bool isSuppressed;
    }

    /// <summary>
    /// Runtime binding for each procedural `.glb` weapon with 4 articulated sub-meshes
    /// and 6 required reference empties (`GripR`, `GripL`, `Muzzle`, `Eject`, `Mag`, `SightAnchor`).
    /// </summary>
    public class ArticulatedWeaponRig : MonoBehaviour
    {
        [Header("4 Articulated Sub-Meshes")]
        public Transform subMesh0Receiver;
        public Transform subMesh1ActionSlideBolt;
        public Transform subMesh2Magazine;
        public Transform subMesh3BarrelSight;

        [Header("6 Required Reference Empties")]
        public Transform gripR;
        public Transform gripL;
        public Transform muzzle;
        public Transform eject;
        public Transform mag;
        public Transform sightAnchor;

        public void AnimateSlideReciprocation(float normalizedCycle)
        {
            if (subMesh1ActionSlideBolt != null)
            {
                float zOffset = -Mathf.Sin(normalizedCycle * Mathf.PI) * 0.045f;
                subMesh1ActionSlideBolt.localPosition = new Vector3(0f, 0f, zOffset);
            }
        }
    }

    /// <summary>
    /// Master Weapon & Ballistics System registering all 26 weapons (24 firearms + knife + garrote).
    /// </summary>
    public class WeaponAndBallisticsSystem : MonoBehaviour
    {
        public static readonly WeaponDefinition[] All26Weapons = new WeaponDefinition[]
        {
            // 5 Pistols & Sidearms
            new WeaponDefinition { weaponId = "wpn_m9_beretta", displayName = "M9 Beretta 9mm", category = WeaponSlotCategory.Sidearm, baseDamage = 28f, roundsPerMinute = 420f, magazineCapacity = 15, reloadSeconds = 1.8f, effectiveRangeMeters = 45f, noiseRadiusMeters = 38f, isSuppressed = false },
            new WeaponDefinition { weaponId = "wpn_glock17_tactical", displayName = "G17 Tactical", category = WeaponSlotCategory.Sidearm, baseDamage = 26f, roundsPerMinute = 480f, magazineCapacity = 17, reloadSeconds = 1.7f, effectiveRangeMeters = 45f, noiseRadiusMeters = 38f, isSuppressed = false },
            new WeaponDefinition { weaponId = "wpn_usp45_suppressed", displayName = "USP .45 Suppressed", category = WeaponSlotCategory.Sidearm, baseDamage = 34f, roundsPerMinute = 380f, magazineCapacity = 12, reloadSeconds = 1.9f, effectiveRangeMeters = 40f, noiseRadiusMeters = 8.5f, isSuppressed = true },
            new WeaponDefinition { weaponId = "wpn_makarov_pm", displayName = "Makarov PM", category = WeaponSlotCategory.Sidearm, baseDamage = 25f, roundsPerMinute = 390f, magazineCapacity = 8, reloadSeconds = 1.7f, effectiveRangeMeters = 35f, noiseRadiusMeters = 36f, isSuppressed = false },
            new WeaponDefinition { weaponId = "wpn_deagle_50ae", displayName = "Desert Eagle .50 AE", category = WeaponSlotCategory.Sidearm, baseDamage = 68f, roundsPerMinute = 210f, magazineCapacity = 7, reloadSeconds = 2.3f, effectiveRangeMeters = 60f, noiseRadiusMeters = 65f, isSuppressed = false },

            // 5 SMGs
            new WeaponDefinition { weaponId = "wpn_mp5sd_integral", displayName = "MP5SD3 Integral Suppressed", category = WeaponSlotCategory.SMG, baseDamage = 24f, roundsPerMinute = 800f, magazineCapacity = 30, reloadSeconds = 2.2f, effectiveRangeMeters = 65f, noiseRadiusMeters = 9.5f, isSuppressed = true },
            new WeaponDefinition { weaponId = "wpn_mp5a3_tactical", displayName = "MP5A3 Tactical", category = WeaponSlotCategory.SMG, baseDamage = 27f, roundsPerMinute = 800f, magazineCapacity = 30, reloadSeconds = 2.1f, effectiveRangeMeters = 75f, noiseRadiusMeters = 45f, isSuppressed = false },
            new WeaponDefinition { weaponId = "wpn_uzi_pro", displayName = "Micro Uzi 9mm", category = WeaponSlotCategory.SMG, baseDamage = 22f, roundsPerMinute = 950f, magazineCapacity = 32, reloadSeconds = 2.0f, effectiveRangeMeters = 50f, noiseRadiusMeters = 46f, isSuppressed = false },
            new WeaponDefinition { weaponId = "wpn_pp19_bizon", displayName = "PP-19 Bizon Helical", category = WeaponSlotCategory.SMG, baseDamage = 25f, roundsPerMinute = 680f, magazineCapacity = 64, reloadSeconds = 2.8f, effectiveRangeMeters = 70f, noiseRadiusMeters = 44f, isSuppressed = false },
            new WeaponDefinition { weaponId = "wpn_p90_pdw", displayName = "FN P90 5.7mm", category = WeaponSlotCategory.SMG, baseDamage = 26f, roundsPerMinute = 900f, magazineCapacity = 50, reloadSeconds = 2.5f, effectiveRangeMeters = 85f, noiseRadiusMeters = 42f, isSuppressed = false },

            // 6 Assault Rifles & Carbines
            new WeaponDefinition { weaponId = "wpn_m4a1_sopmod", displayName = "M4A1 SOPMOD", category = WeaponSlotCategory.AssaultRifle, baseDamage = 36f, roundsPerMinute = 780f, magazineCapacity = 30, reloadSeconds = 2.3f, effectiveRangeMeters = 160f, noiseRadiusMeters = 14f, isSuppressed = true },
            new WeaponDefinition { weaponId = "wpn_ak47_m", displayName = "AKM 7.62x39", category = WeaponSlotCategory.AssaultRifle, baseDamage = 44f, roundsPerMinute = 600f, magazineCapacity = 30, reloadSeconds = 2.5f, effectiveRangeMeters = 175f, noiseRadiusMeters = 68f, isSuppressed = false },
            new WeaponDefinition { weaponId = "wpn_ak74u_krinkov", displayName = "AKS-74U Compact", category = WeaponSlotCategory.AssaultRifle, baseDamage = 34f, roundsPerMinute = 700f, magazineCapacity = 30, reloadSeconds = 2.3f, effectiveRangeMeters = 120f, noiseRadiusMeters = 62f, isSuppressed = false },
            new WeaponDefinition { weaponId = "wpn_g36c_commando", displayName = "G36C Commando", category = WeaponSlotCategory.AssaultRifle, baseDamage = 35f, roundsPerMinute = 750f, magazineCapacity = 30, reloadSeconds = 2.2f, effectiveRangeMeters = 150f, noiseRadiusMeters = 58f, isSuppressed = false },
            new WeaponDefinition { weaponId = "wpn_aug_a2", displayName = "Steyr AUG A2 Optical", category = WeaponSlotCategory.AssaultRifle, baseDamage = 37f, roundsPerMinute = 680f, magazineCapacity = 30, reloadSeconds = 2.6f, effectiveRangeMeters = 190f, noiseRadiusMeters = 58f, isSuppressed = false },
            new WeaponDefinition { weaponId = "wpn_galil_ace", displayName = "Galil ACE 32", category = WeaponSlotCategory.AssaultRifle, baseDamage = 42f, roundsPerMinute = 650f, magazineCapacity = 35, reloadSeconds = 2.4f, effectiveRangeMeters = 170f, noiseRadiusMeters = 64f, isSuppressed = false },

            // 3 Shotguns
            new WeaponDefinition { weaponId = "wpn_spas12_tactical", displayName = "SPAS-12 Combat", category = WeaponSlotCategory.Shotgun, baseDamage = 96f, roundsPerMinute = 180f, magazineCapacity = 8, reloadSeconds = 3.8f, effectiveRangeMeters = 28f, noiseRadiusMeters = 72f, isSuppressed = false },
            new WeaponDefinition { weaponId = "wpn_m870_breacher", displayName = "M870 Breacher", category = WeaponSlotCategory.Shotgun, baseDamage = 105f, roundsPerMinute = 85f, magazineCapacity = 6, reloadSeconds = 3.4f, effectiveRangeMeters = 25f, noiseRadiusMeters = 74f, isSuppressed = false },
            new WeaponDefinition { weaponId = "wpn_saiga12_auto", displayName = "Saiga-12K Box Mag", category = WeaponSlotCategory.Shotgun, baseDamage = 84f, roundsPerMinute = 300f, magazineCapacity = 10, reloadSeconds = 2.7f, effectiveRangeMeters = 26f, noiseRadiusMeters = 70f, isSuppressed = false },

            // 3 Sniper & Marksman Rifles
            new WeaponDefinition { weaponId = "wpn_svd_dragunov", displayName = "SVD Dragunov 7.62x54R", category = WeaponSlotCategory.SniperRifle, baseDamage = 95f, roundsPerMinute = 140f, magazineCapacity = 10, reloadSeconds = 2.8f, effectiveRangeMeters = 380f, noiseRadiusMeters = 85f, isSuppressed = false },
            new WeaponDefinition { weaponId = "wpn_awm_l115a3", displayName = "AWM .338 Lapua", category = WeaponSlotCategory.SniperRifle, baseDamage = 145f, roundsPerMinute = 42f, magazineCapacity = 5, reloadSeconds = 3.2f, effectiveRangeMeters = 500f, noiseRadiusMeters = 95f, isSuppressed = false },
            new WeaponDefinition { weaponId = "wpn_m82_barrett", displayName = "Barrett M82A1 .50 BMG", category = WeaponSlotCategory.SniperRifle, baseDamage = 210f, roundsPerMinute = 90f, magazineCapacity = 10, reloadSeconds = 3.9f, effectiveRangeMeters = 650f, noiseRadiusMeters = 125f, isSuppressed = false },

            // 2 Heavy Weapons
            new WeaponDefinition { weaponId = "wpn_m249_saw", displayName = "M249 SAW Para", category = WeaponSlotCategory.HeavyWeapon, baseDamage = 38f, roundsPerMinute = 800f, magazineCapacity = 100, reloadSeconds = 5.2f, effectiveRangeMeters = 200f, noiseRadiusMeters = 78f, isSuppressed = false },
            new WeaponDefinition { weaponId = "wpn_rpg7_launcher", displayName = "RPG-7V Anti-Armor", category = WeaponSlotCategory.HeavyWeapon, baseDamage = 350f, roundsPerMinute = 15f, magazineCapacity = 1, reloadSeconds = 4.5f, effectiveRangeMeters = 220f, noiseRadiusMeters = 140f, isSuppressed = false },

            // 2 Melee & Stealth Takedown Weapons
            new WeaponDefinition { weaponId = "wpn_knife_mesh", displayName = "KA-BAR Tactical Knife", category = WeaponSlotCategory.MeleeStealth, baseDamage = 150f, roundsPerMinute = 90f, magazineCapacity = 1, reloadSeconds = 0f, effectiveRangeMeters = 1.9f, noiseRadiusMeters = 2.5f, isSuppressed = true },
            new WeaponDefinition { weaponId = "wpn_garrote_mesh", displayName = "Silent Fiber Garrote", category = WeaponSlotCategory.MeleeStealth, baseDamage = 200f, roundsPerMinute = 30f, magazineCapacity = 1, reloadSeconds = 0f, effectiveRangeMeters = 1.5f, noiseRadiusMeters = 0.8f, isSuppressed = true }
        };

        public int activeWeaponIndex;
        public ArticulatedWeaponRig currentRig;

        [Header("Runtime Ammunition") ]
        [Min(0)] public int reserveRounds = 180;
        public int currentMagazineRounds { get; private set; }
        public bool IsReloading => _reloadRemaining > 0f;

        private int _loadedWeaponIndex = -1;
        private float _nextAllowedFireTime;
        private float _reloadRemaining;

        public WeaponDefinition ActiveWeapon => All26Weapons[Mathf.Clamp(activeWeaponIndex, 0, All26Weapons.Length - 1)];

        private void Update()
        {
            if (_reloadRemaining <= 0f) return;
            _reloadRemaining -= Time.deltaTime;
            if (_reloadRemaining > 0f) return;

            WeaponDefinition def = ActiveWeapon;
            int needed = def.magazineCapacity - currentMagazineRounds;
            int loaded = Mathf.Min(needed, Mathf.Max(0, reserveRounds));
            currentMagazineRounds += loaded;
            reserveRounds -= loaded;
        }

        private void EnsureMagazineReady()
        {
            if (_loadedWeaponIndex == activeWeaponIndex) return;
            _loadedWeaponIndex = activeWeaponIndex;
            currentMagazineRounds = ActiveWeapon.magazineCapacity;
            _reloadRemaining = 0f;
        }

        public bool ReloadActiveWeapon()
        {
            EnsureMagazineReady();
            if (IsReloading || currentMagazineRounds >= ActiveWeapon.magazineCapacity || reserveRounds <= 0) return false;
            _reloadRemaining = Mathf.Max(0.01f, ActiveWeapon.reloadSeconds);
            return true;
        }

        /// <summary>
        /// Authoritative player shot path. It enforces magazine/cadence, emits noise, raycasts,
        /// and applies damage through the owning gameplay components. UI must call this method.
        /// </summary>
        public bool TryFireActiveWeapon(Vector3 muzzleOrigin, Vector3 aimDirection, out RaycastHit hit)
        {
            hit = default(RaycastHit);
            EnsureMagazineReady();
            WeaponDefinition def = ActiveWeapon;
            if (IsReloading || Time.time < _nextAllowedFireTime) return false;
            if (currentMagazineRounds <= 0)
            {
                ReloadActiveWeapon();
                return false;
            }

            Vector3 direction = aimDirection.sqrMagnitude > 0.0001f ? aimDirection.normalized : transform.forward;
            currentMagazineRounds--;
            _nextAllowedFireTime = Time.time + (60.0f / Mathf.Max(def.roundsPerMinute, 0.01f));

            NoiseCategory nCat = def.isSuppressed ? NoiseCategory.SuppressedGunshot : NoiseCategory.UnsuppressedGunshot;
            StealthAndDetectionSystem.Instance?.EmitNoise(muzzleOrigin, def.noiseRadiusMeters, nCat, !def.isSuppressed && def.noiseRadiusMeters >= 60f);

            if (Physics.Raycast(muzzleOrigin, direction, out hit, def.effectiveRangeMeters, ~0, QueryTriggerInteraction.Ignore))
            {
                EnemyAIFSMSystem enemy = hit.collider.GetComponentInParent<EnemyAIFSMSystem>();
                if (enemy != null) enemy.ApplyDamage(def.baseDamage);

                TrapAndHazardSystem trap = hit.collider.GetComponentInParent<TrapAndHazardSystem>();
                if (trap != null) trap.ApplyBallisticDamage(def.baseDamage);
            }
            return true;
        }

        // Compatibility entry point for non-UI callers; all gameplay still routes through TryFireActiveWeapon.
        public void FireActiveWeapon(Vector3 muzzleOrigin, Vector3 aimDirection)
        {
            TryFireActiveWeapon(muzzleOrigin, aimDirection, out _);
        }
    }
}
