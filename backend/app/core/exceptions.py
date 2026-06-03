"""
Custom exception hierarchy for the AgriIoT Security Framework.

All exceptions inherit from a common base to enable unified error handling
in FastAPI exception handlers. Each subsystem has its own exception subtree.
"""

from typing import Any


# ─── Base ────────────────────────────────────────────────────────────────────


class AgriIoTError(Exception):
    """Base exception for the entire security framework."""

    def __init__(self, message: str = "An internal error occurred", details: Any = None):
        self.message = message
        self.details = details
        super().__init__(self.message)


# ─── Authentication & Authorization ─────────────────────────────────────────


class AuthenticationError(AgriIoTError):
    """Failed to authenticate user or device."""

    def __init__(self, message: str = "Authentication failed", details: Any = None):
        super().__init__(message, details)


class AuthorizationError(AgriIoTError):
    """User lacks required role or permission."""

    def __init__(self, message: str = "Insufficient permissions", details: Any = None):
        super().__init__(message, details)


class InvalidTokenError(AuthenticationError):
    """JWT token is expired, malformed, or invalid."""

    def __init__(self, message: str = "Invalid or expired token", details: Any = None):
        super().__init__(message, details)


# ─── Device Management ──────────────────────────────────────────────────────


class DeviceError(AgriIoTError):
    """Base for device-related errors."""
    pass


class DeviceNotFoundError(DeviceError):
    """Device ID does not exist in the registry."""

    def __init__(self, device_id: str):
        super().__init__(f"Device not found: {device_id}", {"device_id": device_id})


class DeviceNotWhitelistedError(DeviceError):
    """Device exists but is not on the whitelist."""

    def __init__(self, device_id: str):
        super().__init__(
            f"Device not whitelisted: {device_id}", {"device_id": device_id}
        )


class DeviceLifecycleError(DeviceError):
    """Invalid lifecycle state transition."""

    def __init__(self, device_id: str, current_state: str, target_state: str):
        super().__init__(
            f"Cannot transition device {device_id} from '{current_state}' to '{target_state}'",
            {
                "device_id": device_id,
                "current_state": current_state,
                "target_state": target_state,
            },
        )


class DeviceBlockedError(DeviceError):
    """Device has been blocked due to low trust score."""

    def __init__(self, device_id: str, trust_score: float):
        super().__init__(
            f"Device blocked (trust={trust_score:.1f}): {device_id}",
            {"device_id": device_id, "trust_score": trust_score},
        )


# ─── Security Gateway ───────────────────────────────────────────────────────


class SecurityGatewayError(AgriIoTError):
    """Base for security gateway pipeline errors."""
    pass


class ReplayAttackError(SecurityGatewayError):
    """Nonce has already been used — replay attack detected."""

    def __init__(self, nonce: str, device_id: str):
        super().__init__(
            f"Replay attack detected for device {device_id}",
            {"nonce": nonce, "device_id": device_id},
        )


class TimestampExpiredError(SecurityGatewayError):
    """Request timestamp is outside the acceptable drift window."""

    def __init__(self, drift_seconds: float, max_drift: int):
        super().__init__(
            f"Timestamp expired: drift={drift_seconds:.1f}s, max={max_drift}s",
            {"drift_seconds": drift_seconds, "max_drift": max_drift},
        )


class RateLimitExceededError(SecurityGatewayError):
    """Request rate limit exceeded for device, user, or IP."""

    def __init__(self, scope: str, identifier: str, limit: int, window: int):
        super().__init__(
            f"Rate limit exceeded for {scope}={identifier}: {limit} req/{window}s",
            {"scope": scope, "identifier": identifier, "limit": limit, "window": window},
        )


class SignatureVerificationError(SecurityGatewayError):
    """ECC signature verification failed — data may be tampered."""

    def __init__(self, device_id: str):
        super().__init__(
            f"ECC signature verification failed for device {device_id}",
            {"device_id": device_id},
        )


class MutualAuthenticationError(SecurityGatewayError):
    """Mutual authentication challenge-response failed."""

    def __init__(self, device_id: str, reason: str = "Challenge-response mismatch"):
        super().__init__(
            f"Mutual authentication failed for device {device_id}: {reason}",
            {"device_id": device_id, "reason": reason},
        )


# ─── Cryptography ───────────────────────────────────────────────────────────


class CryptoError(AgriIoTError):
    """Base for cryptographic operation errors."""
    pass


class EncryptionError(CryptoError):
    """AES-256-GCM encryption failed."""

    def __init__(self, message: str = "Encryption failed"):
        super().__init__(message)


class DecryptionError(CryptoError):
    """AES-256-GCM decryption failed — data may be corrupted or tampered."""

    def __init__(self, message: str = "Decryption failed"):
        super().__init__(message)


class KeyVaultError(CryptoError):
    """Error accessing the encrypted key vault."""

    def __init__(self, message: str = "Key vault operation failed"):
        super().__init__(message)


# ─── Blockchain ──────────────────────────────────────────────────────────────


class BlockchainError(AgriIoTError):
    """Base for blockchain-related errors."""
    pass


class ChainIntegrityError(BlockchainError):
    """Blockchain chain validation failed — integrity compromised."""

    def __init__(self, block_index: int, reason: str):
        super().__init__(
            f"Chain integrity violation at block {block_index}: {reason}",
            {"block_index": block_index, "reason": reason},
        )


class BlockValidationError(BlockchainError):
    """Single block validation failed."""

    def __init__(self, block_index: int, reason: str):
        super().__init__(
            f"Block validation failed at index {block_index}: {reason}",
            {"block_index": block_index, "reason": reason},
        )


# ─── ML ──────────────────────────────────────────────────────────────────────


class MLError(AgriIoTError):
    """Base for ML service errors."""
    pass


class ModelNotFoundError(MLError):
    """Requested ML model is not in the registry."""

    def __init__(self, model_name: str):
        super().__init__(
            f"Model not found: {model_name}", {"model_name": model_name}
        )


class ModelLoadError(MLError):
    """Failed to load serialized model from disk."""

    def __init__(self, model_name: str, reason: str):
        super().__init__(
            f"Failed to load model '{model_name}': {reason}",
            {"model_name": model_name, "reason": reason},
        )


class PreprocessingError(MLError):
    """Feature engineering pipeline encountered an error."""

    def __init__(self, message: str = "Preprocessing failed"):
        super().__init__(message)


class DriftDetectionError(MLError):
    """Feature drift computation failed."""

    def __init__(self, feature: str, reason: str):
        super().__init__(
            f"Drift detection failed for feature '{feature}': {reason}",
            {"feature": feature, "reason": reason},
        )
