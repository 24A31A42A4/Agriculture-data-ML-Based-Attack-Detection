"""
Blockchain audit trail bridge.

Connects security events to the blockchain by:
  1. Classifying event severity using a rule-based system.
  2. Recording audit log entries to PostgreSQL.
  3. Anchoring significant events to the blockchain.

The audit trail provides dual-write semantics:
  - PostgreSQL audit_logs: Fast, queryable, mutable (for operational use)
  - Blockchain blocks: Slow, immutable, tamper-evident (for forensic use)

Severity-based anchoring policy:
  - INFO events: Audit log only (no blockchain write)
  - LOW events: Audit log only
  - MEDIUM events: Audit log + blockchain anchor
  - HIGH events: Audit log + blockchain anchor (priority)
  - CRITICAL events: Audit log + blockchain anchor (immediate)

This selective anchoring keeps the chain lightweight while ensuring that
all security-relevant events above a configurable threshold are immutably
recorded.
"""

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.blockchain.block import compute_data_hash
from app.blockchain.chain import BlockchainManager
from app.core.enums import (
    AttackClassification,
    AuditEventType,
    BlockEventType,
    RiskLevel,
    SecuritySeverity,
)
from app.models.audit_log import AuditLog
from app.models.blockchain import BlockchainBlock

logger = logging.getLogger(__name__)


# ── Severity Classification Matrix ───────────────────────────────────────────

# Base severity for each audit event type (from the research design)
_SEVERITY_MAP: dict[AuditEventType, SecuritySeverity] = {
    # Device lifecycle — routine operations
    AuditEventType.DEVICE_REGISTERED: SecuritySeverity.INFO,
    AuditEventType.DEVICE_ACTIVATED: SecuritySeverity.INFO,
    AuditEventType.DEVICE_SUSPENDED: SecuritySeverity.MEDIUM,
    AuditEventType.DEVICE_REVOKED: SecuritySeverity.HIGH,
    AuditEventType.DEVICE_RECOVERED: SecuritySeverity.LOW,
    # Authentication
    AuditEventType.AUTH_SUCCESS: SecuritySeverity.INFO,
    AuditEventType.AUTH_FAILURE: SecuritySeverity.LOW,
    AuditEventType.MUTUAL_AUTH_FAILURE: SecuritySeverity.HIGH,
    # Security incidents
    AuditEventType.TAMPERING_DETECTED: SecuritySeverity.HIGH,
    AuditEventType.REPLAY_ATTACK: SecuritySeverity.HIGH,
    AuditEventType.SIGNATURE_INVALID: SecuritySeverity.HIGH,
    AuditEventType.RATE_LIMIT_EXCEEDED: SecuritySeverity.MEDIUM,
    AuditEventType.IDS_ALERT: SecuritySeverity.HIGH,
    # Trust system
    AuditEventType.TRUST_UPDATE: SecuritySeverity.INFO,
    AuditEventType.DEVICE_BLOCKED: SecuritySeverity.HIGH,
    # ML & Drift
    AuditEventType.DRIFT_DETECTED: SecuritySeverity.MEDIUM,
    # Key management
    AuditEventType.KEY_ROTATED: SecuritySeverity.LOW,
    AuditEventType.KEY_REVOKED: SecuritySeverity.HIGH,
}

# Map audit event types to blockchain event types
_BLOCK_EVENT_MAP: dict[AuditEventType, BlockEventType] = {
    AuditEventType.DEVICE_REGISTERED: BlockEventType.DEVICE_REGISTRATION,
    AuditEventType.DEVICE_ACTIVATED: BlockEventType.DEVICE_REGISTRATION,
    AuditEventType.DEVICE_SUSPENDED: BlockEventType.SECURITY_ALERT,
    AuditEventType.DEVICE_REVOKED: BlockEventType.SECURITY_ALERT,
    AuditEventType.DEVICE_RECOVERED: BlockEventType.DEVICE_REGISTRATION,
    AuditEventType.AUTH_SUCCESS: BlockEventType.AUTH_EVENT,
    AuditEventType.AUTH_FAILURE: BlockEventType.AUTH_EVENT,
    AuditEventType.MUTUAL_AUTH_FAILURE: BlockEventType.SECURITY_ALERT,
    AuditEventType.TAMPERING_DETECTED: BlockEventType.SECURITY_ALERT,
    AuditEventType.REPLAY_ATTACK: BlockEventType.SECURITY_ALERT,
    AuditEventType.SIGNATURE_INVALID: BlockEventType.SECURITY_ALERT,
    AuditEventType.RATE_LIMIT_EXCEEDED: BlockEventType.SECURITY_ALERT,
    AuditEventType.IDS_ALERT: BlockEventType.SECURITY_ALERT,
    AuditEventType.TRUST_UPDATE: BlockEventType.TRUST_UPDATE,
    AuditEventType.DEVICE_BLOCKED: BlockEventType.SECURITY_ALERT,
    AuditEventType.DRIFT_DETECTED: BlockEventType.DRIFT_ALERT,
    AuditEventType.KEY_ROTATED: BlockEventType.DEVICE_REGISTRATION,
    AuditEventType.KEY_REVOKED: BlockEventType.SECURITY_ALERT,
}

# Map audit event types to attack classifications
_ATTACK_MAP: dict[AuditEventType, AttackClassification] = {
    AuditEventType.TAMPERING_DETECTED: AttackClassification.TAMPERING,
    AuditEventType.REPLAY_ATTACK: AttackClassification.REPLAY,
    AuditEventType.SIGNATURE_INVALID: AttackClassification.TAMPERING,
    AuditEventType.IDS_ALERT: AttackClassification.ANOMALY,
    AuditEventType.RATE_LIMIT_EXCEEDED: AttackClassification.DOS,
    AuditEventType.MUTUAL_AUTH_FAILURE: AttackClassification.UNAUTHORIZED,
}

# Minimum severity level for blockchain anchoring
BLOCKCHAIN_ANCHOR_THRESHOLD = SecuritySeverity.MEDIUM

# Severity ordering for comparison
_SEVERITY_ORDER = {
    SecuritySeverity.INFO: 0,
    SecuritySeverity.LOW: 1,
    SecuritySeverity.MEDIUM: 2,
    SecuritySeverity.HIGH: 3,
    SecuritySeverity.CRITICAL: 4,
}


def classify_severity(
    event_type: AuditEventType,
    context: dict[str, Any] | None = None,
) -> SecuritySeverity:
    """
    Classify event severity using the rule-based system with context escalation.

    The base severity is looked up from the classification matrix. Then
    contextual factors can escalate (but never de-escalate) the severity:
      - Consecutive auth failures >= 3 → escalate LOW to MEDIUM
      - Low trust score (< 30) → escalate to at least HIGH
      - Multiple concurrent alerts (>= 5) → escalate HIGH to CRITICAL

    Args:
        event_type: The type of audit event.
        context: Optional dictionary with contextual escalation factors.

    Returns:
        The classified SecuritySeverity.
    """
    if context is None:
        context = {}

    base = _SEVERITY_MAP.get(event_type, SecuritySeverity.INFO)

    # Context-based escalation (never de-escalate)
    consecutive_failures = context.get("consecutive_failures", 0)
    trust_score = context.get("trust_score", 100.0)
    concurrent_alerts = context.get("concurrent_alerts", 0)

    severity = base

    # Escalate: repeated auth failures
    if consecutive_failures >= 3 and _SEVERITY_ORDER[severity] < _SEVERITY_ORDER[SecuritySeverity.MEDIUM]:
        severity = SecuritySeverity.MEDIUM

    # Escalate: low trust device
    if trust_score < 30 and _SEVERITY_ORDER[severity] < _SEVERITY_ORDER[SecuritySeverity.HIGH]:
        severity = SecuritySeverity.HIGH

    # Escalate: multiple simultaneous threats
    if concurrent_alerts >= 5 and severity == SecuritySeverity.HIGH:
        severity = SecuritySeverity.CRITICAL

    return severity


def _severity_meets_threshold(
    severity: SecuritySeverity,
    threshold: SecuritySeverity = BLOCKCHAIN_ANCHOR_THRESHOLD,
) -> bool:
    """Check if a severity meets or exceeds the anchoring threshold."""
    return _SEVERITY_ORDER[severity] >= _SEVERITY_ORDER[threshold]


def _map_severity_to_risk_level(severity: SecuritySeverity) -> RiskLevel:
    """Map 5-tier severity to risk level."""
    mapping = {
        SecuritySeverity.INFO: RiskLevel.NONE,
        SecuritySeverity.LOW: RiskLevel.LOW,
        SecuritySeverity.MEDIUM: RiskLevel.MEDIUM,
        SecuritySeverity.HIGH: RiskLevel.HIGH,
        SecuritySeverity.CRITICAL: RiskLevel.CRITICAL,
    }
    return mapping.get(severity, RiskLevel.NONE)


class AuditTrail:
    """
    Audit trail service with blockchain anchoring.

    Provides a unified interface for recording security events with
    automatic severity classification and selective blockchain anchoring.
    """

    @staticmethod
    async def record_event(
        db: AsyncSession,
        event_type: AuditEventType,
        device_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        source_ip: str | None = None,
        event_details: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        trust_score: float = 100.0,
        signature: str = "SYSTEM",
        context: dict[str, Any] | None = None,
    ) -> tuple[AuditLog, BlockchainBlock | None]:
        """
        Record a security event to the audit log with optional blockchain anchoring.

        Flow:
          1. Classify severity using rule-based system.
          2. Write audit log entry to PostgreSQL.
          3. If severity >= MEDIUM, anchor to blockchain.
          4. Back-link the audit log to the blockchain block index.

        Args:
            db: Database session.
            event_type: The type of security event.
            device_id: Associated device UUID (if applicable).
            user_id: Associated user UUID (if applicable).
            source_ip: Source IP address of the event.
            event_details: Structured event context payload.
            correlation_id: ID to group related events.
            trust_score: Current device trust score.
            signature: ECC signature for non-repudiation.
            context: Contextual factors for severity escalation.

        Returns:
            Tuple of (AuditLog, BlockchainBlock or None).
        """
        if event_details is None:
            event_details = {}

        # 1. Classify severity
        severity = classify_severity(event_type, context)

        # 2. Write audit log entry
        audit_log = AuditLog(
            event_type=event_type,
            severity=severity,
            device_id=device_id,
            user_id=user_id,
            source_ip=source_ip,
            event_details=event_details,
            correlation_id=correlation_id,
        )
        db.add(audit_log)
        await db.flush()  # Get the ID before potential blockchain write

        logger.info(
            "Audit event recorded: type=%s, severity=%s, device=%s",
            event_type.value,
            severity.value,
            device_id,
        )

        # 3. Conditionally anchor to blockchain
        blockchain_block = None
        if _severity_meets_threshold(severity):
            # Compute data hash of the event details
            data_hash = compute_data_hash({
                "audit_id": str(audit_log.id),
                "event_type": event_type.value,
                "severity": severity.value,
                "device_id": str(device_id) if device_id else None,
                "event_details": event_details,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            # Determine blockchain event type and attack classification
            block_event_type = _BLOCK_EVENT_MAP.get(
                event_type, BlockEventType.SYSTEM_EVENT
            )
            attack_class = _ATTACK_MAP.get(
                event_type, AttackClassification.NONE
            )
            risk_level = _map_severity_to_risk_level(severity)

            blockchain_block = await BlockchainManager.add_block(
                db=db,
                event_type=block_event_type,
                data_hash=data_hash,
                signature=signature,
                device_id=device_id,
                trust_score_snapshot=trust_score,
                risk_level=risk_level,
                attack_classification=attack_class,
                security_severity=severity,
                event_metadata={
                    "audit_log_id": str(audit_log.id),
                    "event_type": event_type.value,
                    **event_details,
                },
            )

            # 4. Back-link the audit log to the blockchain block
            audit_log.blockchain_block_index = blockchain_block.index
            db.add(audit_log)

            logger.info(
                "Event anchored to blockchain: block #%d (severity=%s)",
                blockchain_block.index,
                severity.value,
            )

        await db.commit()
        await db.refresh(audit_log)

        return audit_log, blockchain_block
