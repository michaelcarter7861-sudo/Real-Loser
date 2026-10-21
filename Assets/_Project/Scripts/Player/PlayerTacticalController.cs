using System;
using System.Collections.Generic;
using UnityEngine;

namespace RealLoserStudio.Tactical.Player
{
    public enum PlayerPosture
    {
        Stand = 0,
        Crouch = 1,
        Prone = 2
    }

    public enum TraversalMode
    {
        Grounded = 0,
        Ladder = 1,
        Elevator = 2,
        ZipLine = 3
    }

    public enum HidingSpotType
    {
        MetalLocker,       // prop_locker_metal_a
        MetalDumpster,     // prop_dumpster_metal_a
        VentShaft,         // vent
        Closet,            // closet
        TallStealthBush    // tall_stealth_bush
    }

    [Serializable]
    public struct PostureProfile
    {
        public PlayerPosture posture;
        public float capsuleHeight;
        public float eyeHeight;
        public float moveSpeed;
        public float sprintSpeed;
        public float noiseMultiplier;      // Stand=1.0, Crouch=0.45 (-55%), Prone=0.15 (-85%)
        public float visibilityMultiplier; // Stand=1.0, Crouch=0.65 (-35%), Prone=0.30 (-70%)
    }

    /// <summary>
    /// Component attached to body-stashing containers (prop_locker_metal_a, prop_dumpster_metal_a, vents, closets, bushes).
    /// </summary>
    public class HidingSpotContainer : MonoBehaviour
    {
        public string spotId = "prop_locker_metal_a";
        public HidingSpotType spotType = HidingSpotType.MetalLocker;
        public int maxCapacity = 2;
        public Transform stashAnchor;
        private readonly List<GameObject> _stashedBodies = new List<GameObject>(2);

        public bool CanStashBody => _stashedBodies.Count < maxCapacity;
        public int StashedCount => _stashedBodies.Count;

        public bool TryStashBody(GameObject bodyObject)
        {
            if (!CanStashBody || bodyObject == null) return false;
            _stashedBodies.Add(bodyObject);
            if (stashAnchor != null)
            {
                bodyObject.transform.SetParent(stashAnchor, true);
                bodyObject.transform.localPosition = Vector3.zero;
            }
            bodyObject.SetActive(false); // Concealed from AI sightlines
            return true;
        }
    }

    /// <summary>
    /// First-Person Tactical Controller for Project Real Loser (Unity 2022.3.40f1 LTS, URP Android ARM64).
    /// Implements exact posture heights/stealth modifiers, ±18° corner lean, Ladders/Elevators/ZipLines,
    /// and Dead/Knocked-Out body carrying & hiding.
    /// </summary>
    [RequireComponent(typeof(CharacterController))]
    public class PlayerTacticalController : MonoBehaviour
    {
        [Header("References")]
        public Transform cameraPivot;
        public Transform leanPivot;
        public Camera firstPersonCamera;
        public Transform carryBodyAnchor;

        [Header("Posture Profiles (Exact Phase 0 Spec)")]
        public PostureProfile standProfile = new PostureProfile
        {
            posture = PlayerPosture.Stand,
            capsuleHeight = 1.80f,
            eyeHeight = 1.68f,
            moveSpeed = 4.2f,
            sprintSpeed = 6.4f,
            noiseMultiplier = 1.00f,
            visibilityMultiplier = 1.00f
        };

        public PostureProfile crouchProfile = new PostureProfile
        {
            posture = PlayerPosture.Crouch,
            capsuleHeight = 1.10f,
            eyeHeight = 0.98f,
            moveSpeed = 2.4f,
            sprintSpeed = 3.4f,
            noiseMultiplier = 0.45f,       // -55% noise
            visibilityMultiplier = 0.65f   // -35% visibility
        };

        public PostureProfile proneProfile = new PostureProfile
        {
            posture = PlayerPosture.Prone,
            capsuleHeight = 0.45f,
            eyeHeight = 0.34f,
            moveSpeed = 1.05f,             // < 1.2 m/s to evade T6 Motion Sensor
            sprintSpeed = 1.18f,
            noiseMultiplier = 0.15f,       // -85% noise
            visibilityMultiplier = 0.30f   // -70% visibility
        };

        [Header("Corner Lean Settings (±18 Degrees)")]
        public float maxLeanAngleDegrees = 18.0f;
        public float maxLeanLateralOffset = 0.38f;
        public float leanTransitionSpeed = 9.0f;
        public LayerMask leanObstructionMask = ~0;

        [Header("Jump & Gravity")]
        public float jumpHeightMeters = 1.05f; // Clears T7 Pressure Plate (1.0m)
        public float gravity = -19.62f;

        [Header("Traversal Settings")]
        public bool enableZipLinesInMission = true;
        public float ladderClimbSpeed = 2.4f;
        public float zipLineSpeed = 11.5f;

        [Header("Body Carry Settings")]
        public float bodyCarrySpeedMultiplier = 0.68f;

        private CharacterController _cc;
        private PlayerPosture _currentPosture = PlayerPosture.Stand;
        private TraversalMode _traversalMode = TraversalMode.Grounded;
        private float _targetLeanInput; // -1 = Left, 0 = Center, +1 = Right
        private float _currentLeanNormalized;
        private Vector3 _velocity;
        private float _pitchDegrees;

        // Active traversal anchors
        private Transform _ladderTop;
        private Transform _ladderBottom;
        private Transform _zipLineStart;
        private Transform _zipLineEnd;
        private float _zipLineProgress;
        private Transform _activeElevatorPlatform;
        private Vector3 _lastElevatorPosition;

        // Carried body reference
        private GameObject _carriedBody;

        public PlayerPosture CurrentPosture => _currentPosture;
        public TraversalMode CurrentTraversal => _traversalMode;
        public bool IsCarryingBody => _carriedBody != null;
        public float CurrentHorizontalSpeed { get; private set; }
        public float CurrentLeanDegrees => -_currentLeanNormalized * maxLeanAngleDegrees;

        public PostureProfile ActiveProfile
        {
            get
            {
                switch (_currentPosture)
                {
                    case PlayerPosture.Crouch: return crouchProfile;
                    case PlayerPosture.Prone: return proneProfile;
                    default: return standProfile;
                }
            }
        }

        private void Awake()
        {
            _cc = GetComponent<CharacterController>();
            ApplyPostureImmediate(PlayerPosture.Stand);
        }

        public void SetPosture(PlayerPosture targetPosture)
        {
            if (_currentPosture == targetPosture) return;

            // If standing up from crouch/prone, verify overhead clearance
            float targetHeight = GetProfile(targetPosture).capsuleHeight;
            if (targetHeight > _cc.height)
            {
                float castDist = targetHeight - _cc.height;
                Vector3 rayOrigin = transform.position + Vector3.up * (_cc.height - 0.1f);
                if (Physics.SphereCast(rayOrigin, _cc.radius * 0.85f, Vector3.up, out _, castDist, leanObstructionMask, QueryTriggerInteraction.Ignore))
                {
                    return; // Blocked overhead (e.g., inside vent or under low obstacle)
                }
            }

            // Cannot go Prone while carrying a body
            if (targetPosture == PlayerPosture.Prone && IsCarryingBody)
            {
                targetPosture = PlayerPosture.Crouch;
            }

            _currentPosture = targetPosture;
        }

        public void SetLeanInput(float leanDirection)
        {
            _targetLeanInput = Mathf.Clamp(leanDirection, -1f, 1f);
        }

        public void TryJump()
        {
            if (_traversalMode != TraversalMode.Grounded || !_cc.isGrounded) return;
            if (_currentPosture != PlayerPosture.Stand)
            {
                SetPosture(PlayerPosture.Stand);
                return;
            }
            _velocity.y = Mathf.Sqrt(jumpHeightMeters * -2f * gravity);
        }

        public void UpdateMovement(Vector2 moveInput, Vector2 lookDelta, bool isSprinting, float deltaTime)
        {
            // 1. Update Look Rotation
            transform.Rotate(Vector3.up, lookDelta.x, Space.Self);
            _pitchDegrees = Mathf.Clamp(_pitchDegrees - lookDelta.y, -85f, 85f);
            if (cameraPivot != null)
            {
                cameraPivot.localRotation = Quaternion.Euler(_pitchDegrees, 0f, 0f);
            }

            // 2. Smoothly interpolate capsule & eye height for active posture
            PostureProfile profile = ActiveProfile;
            _cc.height = Mathf.Lerp(_cc.height, profile.capsuleHeight, deltaTime * 10f);
            _cc.center = new Vector3(0f, _cc.height * 0.5f, 0f);
            if (cameraPivot != null)
            {
                Vector3 camPos = cameraPivot.localPosition;
                camPos.y = Mathf.Lerp(camPos.y, profile.eyeHeight, deltaTime * 10f);
                cameraPivot.localPosition = camPos;
            }

            // 3. Update Corner Lean (±18° roll + lateral offset with wall-clip prevention)
            UpdateCornerLean(deltaTime);

            // 4. Handle Traversal Mode
            switch (_traversalMode)
            {
                case TraversalMode.Ladder:
                    UpdateLadderTraversal(moveInput, deltaTime);
                    break;
                case TraversalMode.ZipLine:
                    UpdateZipLineTraversal(deltaTime);
                    break;
                case TraversalMode.Elevator:
                    UpdateElevatorMotion();
                    UpdateGroundedMovement(moveInput, isSprinting, profile, deltaTime);
                    break;
                default:
                    UpdateGroundedMovement(moveInput, isSprinting, profile, deltaTime);
                    break;
            }
        }

        private void UpdateGroundedMovement(Vector2 moveInput, bool isSprinting, PostureProfile profile, float deltaTime)
        {
            if (_cc.isGrounded && _velocity.y < 0f)
            {
                _velocity.y = -2f;
            }

            float speed = (isSprinting && _currentPosture == PlayerPosture.Stand && !IsCarryingBody)
                ? profile.sprintSpeed
                : profile.moveSpeed;

            if (IsCarryingBody)
            {
                speed *= bodyCarrySpeedMultiplier;
            }

            Vector3 wishDir = (transform.right * moveInput.x + transform.forward * moveInput.y);
            if (wishDir.sqrMagnitude > 1f) wishDir.Normalize();

            Vector3 horizontalVel = wishDir * speed;
            CurrentHorizontalSpeed = new Vector2(horizontalVel.x, horizontalVel.z).magnitude;

            _velocity.y += gravity * deltaTime;
            Vector3 finalDisp = (horizontalVel + Vector3.up * _velocity.y) * deltaTime;
            _cc.Move(finalDisp);
        }

        private void UpdateCornerLean(float deltaTime)
        {
            float permittedLean = _targetLeanInput;
            if (Mathf.Abs(permittedLean) > 0.01f && cameraPivot != null)
            {
                Vector3 sideDir = transform.right * Mathf.Sign(permittedLean);
                if (Physics.SphereCast(cameraPivot.position, 0.14f, sideDir, out RaycastHit hit, maxLeanLateralOffset + 0.1f, leanObstructionMask, QueryTriggerInteraction.Ignore))
                {
                    float allowedRatio = Mathf.Clamp01((hit.distance - 0.1f) / maxLeanLateralOffset);
                    permittedLean *= allowedRatio;
                }
            }

            _currentLeanNormalized = Mathf.Lerp(_currentLeanNormalized, permittedLean, deltaTime * leanTransitionSpeed);
            if (leanPivot != null)
            {
                leanPivot.localPosition = new Vector3(_currentLeanNormalized * maxLeanLateralOffset, 0f, 0f);
                leanPivot.localRotation = Quaternion.Euler(0f, 0f, -_currentLeanNormalized * maxLeanAngleDegrees);
            }
        }

        // --- Ladder, Elevator, and Zip-Line Traversal ---

        public void AttachToLadder(Transform bottomAnchor, Transform topAnchor)
        {
            if (IsCarryingBody) DropCarriedBody();
            SetPosture(PlayerPosture.Stand);
            _ladderBottom = bottomAnchor;
            _ladderTop = topAnchor;
            _traversalMode = TraversalMode.Ladder;
            _velocity = Vector3.zero;
        }

        private void UpdateLadderTraversal(Vector2 moveInput, float deltaTime)
        {
            if (_ladderBottom == null || _ladderTop == null)
            {
                _traversalMode = TraversalMode.Grounded;
                return;
            }
            Vector3 climbDisp = Vector3.up * (moveInput.y * ladderClimbSpeed * deltaTime);
            _cc.Move(climbDisp);
            CurrentHorizontalSpeed = Mathf.Abs(moveInput.y * ladderClimbSpeed);

            if (transform.position.y >= _ladderTop.position.y - 0.15f && moveInput.y > 0.1f)
            {
                transform.position = _ladderTop.position + _ladderTop.forward * 0.6f;
                _traversalMode = TraversalMode.Grounded;
            }
            else if (transform.position.y <= _ladderBottom.position.y + 0.1f && moveInput.y < -0.1f)
            {
                _traversalMode = TraversalMode.Grounded;
            }
        }

        public bool TryAttachToZipLine(Transform startAnchor, Transform endAnchor)
        {
            if (!enableZipLinesInMission || IsCarryingBody || startAnchor == null || endAnchor == null)
                return false;

            SetPosture(PlayerPosture.Stand);
            _zipLineStart = startAnchor;
            _zipLineEnd = endAnchor;
            _zipLineProgress = 0f;
            _traversalMode = TraversalMode.ZipLine;
            _velocity = Vector3.zero;
            return true;
        }

        private void UpdateZipLineTraversal(float deltaTime)
        {
            if (_zipLineStart == null || _zipLineEnd == null)
            {
                _traversalMode = TraversalMode.Grounded;
                return;
            }

            float totalDist = Vector3.Distance(_zipLineStart.position, _zipLineEnd.position);
            if (totalDist < 0.1f)
            {
                _traversalMode = TraversalMode.Grounded;
                return;
            }

            _zipLineProgress += (zipLineSpeed / totalDist) * deltaTime;
            Vector3 targetPos = Vector3.Lerp(_zipLineStart.position, _zipLineEnd.position, Mathf.Clamp01(_zipLineProgress)) + Vector3.down * 1.4f;
            _cc.Move(targetPos - transform.position);
            CurrentHorizontalSpeed = zipLineSpeed;

            if (_zipLineProgress >= 1.0f)
            {
                _traversalMode = TraversalMode.Grounded;
            }
        }

        public void EnterElevatorPlatform(Transform elevatorPlatform)
        {
            _activeElevatorPlatform = elevatorPlatform;
            _lastElevatorPosition = elevatorPlatform.position;
            _traversalMode = TraversalMode.Elevator;
        }

        public void ExitElevatorPlatform()
        {
            _activeElevatorPlatform = null;
            if (_traversalMode == TraversalMode.Elevator)
                _traversalMode = TraversalMode.Grounded;
        }

        private void UpdateElevatorMotion()
        {
            if (_activeElevatorPlatform == null) return;
            Vector3 platformDelta = _activeElevatorPlatform.position - _lastElevatorPosition;
            if (platformDelta.sqrMagnitude > 1e-6f)
            {
                _cc.Move(platformDelta);
            }
            _lastElevatorPosition = _activeElevatorPlatform.position;
        }

        // --- Dead / Knocked-Out Body Carry & Hiding ---

        public bool TryPickUpBody(GameObject bodyObject)
        {
            if (IsCarryingBody || bodyObject == null || _traversalMode != TraversalMode.Grounded)
                return false;

            if (_currentPosture == PlayerPosture.Prone)
                SetPosture(PlayerPosture.Crouch);

            _carriedBody = bodyObject;
            if (carryBodyAnchor != null)
            {
                _carriedBody.transform.SetParent(carryBodyAnchor, false);
                _carriedBody.transform.localPosition = Vector3.zero;
                _carriedBody.transform.localRotation = Quaternion.identity;
            }
            return true;
        }

        public GameObject DropCarriedBody()
        {
            if (_carriedBody == null) return null;
            GameObject dropped = _carriedBody;
            _carriedBody = null;
            dropped.transform.SetParent(null, true);
            dropped.transform.position = transform.position + transform.forward * 0.85f;
            return dropped;
        }

        public bool TryStashCarriedBody(HidingSpotContainer container)
        {
            if (!IsCarryingBody || container == null || !container.CanStashBody)
                return false;

            GameObject body = _carriedBody;
            _carriedBody = null;
            return container.TryStashBody(body);
        }

        private PostureProfile GetProfile(PlayerPosture p)
        {
            switch (p)
            {
                case PlayerPosture.Crouch: return crouchProfile;
                case PlayerPosture.Prone: return proneProfile;
                default: return standProfile;
            }
        }

        private void ApplyPostureImmediate(PlayerPosture p)
        {
            _currentPosture = p;
            PostureProfile prof = GetProfile(p);
            _cc.height = prof.capsuleHeight;
            _cc.center = new Vector3(0f, prof.capsuleHeight * 0.5f, 0f);
            if (cameraPivot != null)
            {
                cameraPivot.localPosition = new Vector3(0f, prof.eyeHeight, 0f);
            }
        }
    }
}
