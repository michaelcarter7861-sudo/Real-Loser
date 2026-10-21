using UnityEngine;

namespace RealLoserStudio.Tactical.Core
{
    /// <summary>
    /// Lightweight locomotion fallback for rigged GLB actors that ship without animation clips.
    /// This is procedural gameplay motion, not a substitute for authored combat/gesture animation.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class ProceduralHumanoidMotion : MonoBehaviour
    {
        [Range(8f, 32f)] public float legSwingDegrees = 22f;
        [Range(0f, 15f)] public float armSwingDegrees = 8f;
        [Range(0f, 0.08f)] public float hipBobMeters = 0.025f;

        private Transform _modelRoot;
        private Transform _hips;
        private Transform _upperArmL;
        private Transform _upperArmR;
        private Transform _upperLegL;
        private Transform _upperLegR;
        private Transform _lowerLegL;
        private Transform _lowerLegR;
        private Vector3 _hipsBasePosition;
        private Quaternion _upperArmLBase;
        private Quaternion _upperArmRBase;
        private Quaternion _upperLegLBase;
        private Quaternion _upperLegRBase;
        private Quaternion _lowerLegLBase;
        private Quaternion _lowerLegRBase;
        private Vector3 _lastWorldPosition;
        private float _phase;
        private bool _ready;

        private void Awake() => BindRig(transform);

        private void OnEnable()
        {
            // Templates are cloned inactive; re-bind on enable so each instance captures its own
            // transform baselines after RuntimeGLBAndMeshLoader has positioned it in the world.
            BindRig(transform);
        }

        public void BindRig(Transform modelRoot)
        {
            _modelRoot = modelRoot != null ? modelRoot : transform;
            Transform[] all = _modelRoot.GetComponentsInChildren<Transform>(true);
            _hips = Find(all, "Hips");
            _upperArmL = Find(all, "UpperArmL");
            _upperArmR = Find(all, "UpperArmR");
            _upperLegL = Find(all, "UpperLegL");
            _upperLegR = Find(all, "UpperLegR");
            _lowerLegL = Find(all, "LowerLegL");
            _lowerLegR = Find(all, "LowerLegR");
            if (_hips == null || _upperLegL == null || _upperLegR == null)
            {
                _ready = false;
                return;
            }

            _hipsBasePosition = _hips.localPosition;
            _upperArmLBase = _upperArmL != null ? _upperArmL.localRotation : Quaternion.identity;
            _upperArmRBase = _upperArmR != null ? _upperArmR.localRotation : Quaternion.identity;
            _upperLegLBase = _upperLegL.localRotation;
            _upperLegRBase = _upperLegR.localRotation;
            _lowerLegLBase = _lowerLegL != null ? _lowerLegL.localRotation : Quaternion.identity;
            _lowerLegRBase = _lowerLegR != null ? _lowerLegR.localRotation : Quaternion.identity;
            _lastWorldPosition = transform.position;
            _phase = 0f;
            _ready = true;
        }

        private static Transform Find(Transform[] all, string exactName)
        {
            for (int i = 0; i < all.Length; i++)
            {
                if (all[i] != null && all[i].name == exactName) return all[i];
            }
            return null;
        }

        private void LateUpdate()
        {
            if (!_ready) return;
            float dt = Time.deltaTime;
            if (dt <= 0f) return;
            Vector3 delta = transform.position - _lastWorldPosition;
            _lastWorldPosition = transform.position;
            float speed = delta.magnitude / dt;
            float moveWeight = Mathf.Clamp01((speed - 0.08f) / 1.15f);
            _phase += dt * (2.1f + speed * 1.8f);

            float swing = Mathf.Sin(_phase) * legSwingDegrees * moveWeight;
            float oppositeSwing = -swing;
            _upperLegL.localRotation = _upperLegLBase * Quaternion.AngleAxis(swing, Vector3.right);
            _upperLegR.localRotation = _upperLegRBase * Quaternion.AngleAxis(oppositeSwing, Vector3.right);

            float kneeL = Mathf.Max(0f, Mathf.Sin(_phase + 1.0f)) * 28f * moveWeight;
            float kneeR = Mathf.Max(0f, Mathf.Sin(_phase + Mathf.PI + 1.0f)) * 28f * moveWeight;
            if (_lowerLegL != null) _lowerLegL.localRotation = _lowerLegLBase * Quaternion.AngleAxis(kneeL, Vector3.right);
            if (_lowerLegR != null) _lowerLegR.localRotation = _lowerLegRBase * Quaternion.AngleAxis(kneeR, Vector3.right);

            float arm = -swing * (armSwingDegrees / Mathf.Max(1f, legSwingDegrees));
            if (_upperArmL != null) _upperArmL.localRotation = _upperArmLBase * Quaternion.AngleAxis(arm, Vector3.right);
            if (_upperArmR != null) _upperArmR.localRotation = _upperArmRBase * Quaternion.AngleAxis(-arm, Vector3.right);
            _hips.localPosition = _hipsBasePosition + Vector3.up * (Mathf.Abs(Mathf.Sin(_phase * 2f)) * hipBobMeters * moveWeight);
        }
    }
}
