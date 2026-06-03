"""
Project-wide constants.

Numeric thresholds, trust score deltas, cryptographic parameters,
and other magic numbers are centralized here to avoid scattered literals.
"""


# ─── Trust Score Adjustments ─────────────────────────────────────────────────

class TrustScoreDeltas:
    """Score changes for each trust-affecting event."""

    AUTH_SUCCESS = +1.0
    DATA_TRANSMISSION_SUCCESS = +0.5
    MUTUAL_AUTH_SUCCESS = +1.5

    AUTH_FAILURE = -10.0
    RATE_LIMIT_EXCEEDED = -5.0
    CONSECUTIVE_AUTH_FAILURES = -15.0  # 3+ consecutive
    REPLAY_ATTACK = -15.0
    TAMPERING_DETECTED = -20.0
    SIGNATURE_INVALID = -20.0
    FAKE_SENSOR = -25.0
    ML_IDS_ALERT = -5.0
    DRIFT_ANOMALY = -2.0
    DOS_DETECTED = -30.0


# ─── Risk-Based Authentication Thresholds ────────────────────────────────────

class TrustThresholds:
    """Trust score boundaries for risk-based access decisions."""

    FULL_ACCESS = 80.0        # trust > 80 → full access
    RESTRICTED_ACCESS = 50.0  # trust 50–80 → additional verification
    LIMITED_ACCESS = 20.0     # trust 20–50 → read-only, device suspended
    BLOCKED = 20.0            # trust < 20 → device revoked


# ─── Device Health Weights ───────────────────────────────────────────────────

class HealthWeights:
    """Weights for composite device health score computation."""

    AUTH_RATE = 0.40
    TRUST_SCORE = 0.30
    TRUST_TREND = 0.20
    RECENCY = 0.10


# ─── Cryptographic Parameters ───────────────────────────────────────────────

class CryptoParams:
    """Cryptographic algorithm constants."""

    AES_KEY_SIZE_BITS = 256
    AES_KEY_SIZE_BYTES = 32
    AES_GCM_IV_SIZE_BYTES = 12     # 96-bit IV (NIST recommended)
    AES_GCM_TAG_SIZE_BYTES = 16    # 128-bit authentication tag

    ECC_CURVE_NAME = "SECP256R1"

    SHA256_DIGEST_SIZE = 32

    # HKDF parameters for key vault derivation
    HKDF_HASH_ALGORITHM = "SHA256"
    HKDF_INFO = b"agri-iot-key-vault-v1"


# ─── Blockchain ──────────────────────────────────────────────────────────────

GENESIS_BLOCK_PREVIOUS_HASH = "0" * 64  # 64 hex chars = 256-bit zero hash


# ─── Rate Limiting ───────────────────────────────────────────────────────────

RATE_LIMIT_ESCALATION_WINDOW = 600  # seconds (10 min) for violation escalation
RATE_LIMIT_ESCALATION_COUNT = 3     # violations within window → HIGH severity


# ─── Feature Drift ───────────────────────────────────────────────────────────

class DriftThresholds:
    """PSI thresholds for drift severity classification."""

    STABLE = 0.1           # PSI < 0.1 → INFO (no drift)
    MODERATE = 0.2         # 0.1–0.2 → LOW
    SIGNIFICANT = 0.25     # 0.2–0.25 → MEDIUM
    SEVERE = 0.5           # 0.25–0.5 → HIGH
    # > 0.5 → CRITICAL


# ─── Consecutive Failure Thresholds ──────────────────────────────────────────

CONSECUTIVE_FAILURE_ESCALATION = 3  # failures before severity escalation
RECOVERED_DEVICE_INITIAL_TRUST = 50.0  # trust score after recovery
RECOVERED_DEVICE_TIMEOUT_SECONDS = 1800  # 30 min timeout in recovered state
