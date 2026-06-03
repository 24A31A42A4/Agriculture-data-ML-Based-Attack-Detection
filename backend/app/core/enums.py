"""
Project-wide enumerations.

All enums used across the security framework are centralized here to ensure
consistency between database models, API schemas, service logic, and tests.
"""

from enum import Enum


# ─── User Roles ──────────────────────────────────────────────────────────────


class UserRole(str, Enum):
    """User role for RBAC enforcement."""

    ADMIN = "admin"
    RESEARCHER = "researcher"
    FARMER = "farmer"
    SECURITY_ANALYST = "security_analyst"


# ─── Device Management ──────────────────────────────────────────────────────


class DeviceType(str, Enum):
    """Physical sensor or gateway type."""

    SOIL_MOISTURE = "soil_moisture"
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    WATER_LEVEL = "water_level"
    GATEWAY = "gateway"


class DeviceLifecycleStatus(str, Enum):
    """
    Device lifecycle state machine.

    Transitions:
        registered → active       (admin activates after physical verification)
        active     → suspended    (manual or automatic: trust < 50)
        active     → revoked      (confirmed compromise)
        suspended  → active       (recovery after investigation)
        suspended  → revoked      (investigation confirms compromise)
        revoked    → recovered    (admin issues new keys + re-verification)
        recovered  → active       (successful mutual auth)
    """

    REGISTERED = "registered"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    RECOVERED = "recovered"


# ─── Security Severity ──────────────────────────────────────────────────────


class SecuritySeverity(str, Enum):
    """
    5-tier security severity classification.

    INFO     — Routine operations (device registered, auth success)
    LOW      — Minor anomalies (single auth failure, key rotated)
    MEDIUM   — Suspicious activity (rate limit exceeded, repeated failures)
    HIGH     — Active threat (replay attack, tampering, signature invalid)
    CRITICAL — System compromise (DoS, chain tampering, coordinated attack)
    """

    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ─── Blockchain ─────────────────────────────────────────────────────────────


class BlockEventType(str, Enum):
    """Event type recorded in blockchain blocks."""

    SENSOR_DATA = "sensor_data"
    DEVICE_REGISTRATION = "device_registration"
    AUTH_EVENT = "auth_event"
    SECURITY_ALERT = "security_alert"
    TRUST_UPDATE = "trust_update"
    DRIFT_ALERT = "drift_alert"
    SYSTEM_EVENT = "system_event"


class RiskLevel(str, Enum):
    """Risk level assigned to blockchain events."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AttackClassification(str, Enum):
    """ML or rule-based attack classification labels."""

    NORMAL = "normal"
    TAMPERING = "tampering"
    REPLAY = "replay"
    FAKE_SENSOR = "fake_sensor"
    UNAUTHORIZED = "unauthorized"
    DOS = "dos"
    ANOMALY = "anomaly"
    NONE = "none"


# ─── Audit Trail ────────────────────────────────────────────────────────────


class AuditEventType(str, Enum):
    """Exhaustive list of auditable security events."""

    # Device lifecycle
    DEVICE_REGISTERED = "device_registered"
    DEVICE_ACTIVATED = "device_activated"
    DEVICE_SUSPENDED = "device_suspended"
    DEVICE_REVOKED = "device_revoked"
    DEVICE_RECOVERED = "device_recovered"

    # Authentication
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"
    MUTUAL_AUTH_FAILURE = "mutual_auth_failure"

    # Security incidents
    TAMPERING_DETECTED = "tampering_detected"
    REPLAY_ATTACK = "replay_attack"
    SIGNATURE_INVALID = "signature_invalid"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    IDS_ALERT = "ids_alert"

    # Trust system
    TRUST_UPDATE = "trust_update"
    DEVICE_BLOCKED = "device_blocked"

    # ML & Drift
    DRIFT_DETECTED = "drift_detected"

    # Key management
    KEY_ROTATED = "key_rotated"
    KEY_REVOKED = "key_revoked"


# ─── Trust Events ───────────────────────────────────────────────────────────


class TrustEventType(str, Enum):
    """Events that cause trust score adjustments."""

    AUTH_SUCCESS = "auth_success"
    MUTUAL_AUTH_SUCCESS = "mutual_auth_success"
    AUTH_FAILURE = "auth_failure"
    CONSECUTIVE_AUTH_FAILURES = "consecutive_auth_failures"
    REPLAY_ATTEMPT = "replay_attempt"
    TAMPERING = "tampering"
    INVALID_SIGNATURE = "invalid_signature"
    FAKE_SENSOR = "fake_sensor"
    SUSPICIOUS_BEHAVIOR = "suspicious_behavior"
    NORMAL_OPERATION = "normal_operation"
    RATE_LIMIT_VIOLATION = "rate_limit_violation"
    DRIFT_ANOMALY = "drift_anomaly"
    ML_IDS_ALERT = "ml_ids_alert"
    DOS_BEHAVIOR = "dos_behavior"


# ─── Risk-Based Authentication ──────────────────────────────────────────────


class AccessLevel(str, Enum):
    """Access level determined by trust score thresholds."""

    FULL = "full_access"           # trust > 80
    RESTRICTED = "restricted"      # trust 50–80
    LIMITED = "limited"            # trust 20–50
    BLOCKED = "blocked"            # trust < 20


# ─── Benchmark Types ────────────────────────────────────────────────────────


class BenchmarkType(str, Enum):
    """Categories of evaluation benchmarks."""

    SECURITY = "security"
    ML = "ml"
    SYSTEM = "system"
    TRUST = "trust"


# ─── ML Model Types ─────────────────────────────────────────────────────────


class ModelType(str, Enum):
    """Machine learning model architecture categories."""

    LINEAR = "linear"
    TREE = "tree"
    ENSEMBLE_BAGGING = "ensemble_bagging"
    ENSEMBLE_BOOSTING = "ensemble_boosting"
    INSTANCE_BASED = "instance_based"
    KERNEL_BASED = "kernel_based"
    META_ENSEMBLE = "meta_ensemble"
