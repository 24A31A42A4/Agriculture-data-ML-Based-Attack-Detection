"""
Trust Score & Risk Engine service.

Manages dynamic trust calculation, trust event history, and risk-based access control.
Implements the v2 scoring matrix with automatic lifecycle transitions (e.g., auto-suspend
if trust drops below 50, auto-revoke if below 20).
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import DeviceLifecycleStatus, TrustEventType
from app.models.device import Device
from app.models.trust_event import TrustEvent
from app.schemas.trust import TrustScoreResponse

logger = logging.getLogger(__name__)

# ── Score Adjustment Matrix ───────────────────────────────────────────

TRUST_SCORE_MATRIX: dict[TrustEventType, float] = {
    TrustEventType.AUTH_SUCCESS: 1.0,
    TrustEventType.NORMAL_OPERATION: 0.5,
    TrustEventType.MUTUAL_AUTH_SUCCESS: 1.5,
    TrustEventType.AUTH_FAILURE: -10.0,
    TrustEventType.RATE_LIMIT_VIOLATION: -5.0,
    TrustEventType.CONSECUTIVE_AUTH_FAILURES: -15.0,
    TrustEventType.REPLAY_ATTEMPT: -15.0,
    TrustEventType.TAMPERING: -20.0,
    TrustEventType.INVALID_SIGNATURE: -20.0,
    TrustEventType.FAKE_SENSOR: -25.0,
    TrustEventType.ML_IDS_ALERT: -5.0,
    TrustEventType.DRIFT_ANOMALY: -2.0,
    TrustEventType.DOS_BEHAVIOR: -30.0,
}


def get_risk_level_for_score(score: float) -> str:
    """Map trust score to risk access tier."""
    if score > 80:
        return "none"  # Full Access
    if score >= 50:
        return "low"   # Restricted
    if score >= 20:
        return "medium" # Limited
    return "high"      # Blocked


class TrustService:
    """Service for managing device trust scores and risk-based auth."""

    @staticmethod
    async def adjust_trust_score(
        db: AsyncSession,
        device_id: uuid.UUID,
        event_type: TrustEventType,
        reason_override: str | None = None,
        override_score_change: float | None = None,
    ) -> tuple[Device, TrustEvent]:
        """
        Adjust a device's trust score based on an event.

        Flow:
          1. Lookup device.
          2. Calculate score delta from matrix.
          3. Apply delta (clamp between 0 and 100).
          4. Record TrustEvent.
          5. Evaluate automatic lifecycle transitions (suspend/revoke).

        Args:
            db: Database session.
            device_id: Target device.
            event_type: Type of event triggering the adjustment.
            reason_override: Optional custom reason for the audit trail.

        Returns:
            Tuple of (Updated Device, Created TrustEvent).
        """
        # 1. Fetch device
        stmt = select(Device).where(Device.id == device_id).with_for_update()
        result = await db.execute(stmt)
        device = result.scalar_one_or_none()

        if not device:
            raise ValueError(f"Device not found: {device_id}")

        # Trust score is frozen if device is suspended/revoked
        # Exception: Recovering a device or manual administrative resets
        if device.lifecycle_status in (
            DeviceLifecycleStatus.SUSPENDED,
            DeviceLifecycleStatus.REVOKED,
        ):
            # Device is suspended/revoked. We freeze positive trust gains,
            # but still allow negative penalties so a suspended device can be revoked
            # if it continues malicious behavior.
            delta = TRUST_SCORE_MATRIX.get(event_type, 0.0)
            if delta > 0:
                delta = 0.0
                status_val = device.lifecycle_status.value if hasattr(device.lifecycle_status, 'value') else device.lifecycle_status
                logger.info("Positive trust gain frozen for %s device %s", status_val, device_id)
        else:
            # 2. Calculate delta
            if override_score_change is not None:
                delta = override_score_change
            else:
                delta = TRUST_SCORE_MATRIX.get(event_type, 0.0)

        # 3. Apply delta with clamping
        score_before = device.trust_score
        score_after = max(0.0, min(100.0, score_before + delta))

        # 4. Record event
        reason = reason_override or f"Auto-adjustment for {event_type.value}"
        trust_event = TrustEvent(
            device_id=device.id,
            event_type=event_type,
            score_before=score_before,
            score_change=score_after - score_before,
            score_after=score_after,
            reason=reason,
        )

        device.trust_score = score_after
        db.add(trust_event)

        # 5. Evaluate automatic lifecycle transitions
        await TrustService._evaluate_lifecycle_transitions(device, score_after)

        await db.commit()
        await db.refresh(device)
        await db.refresh(trust_event)

        logger.info(
            "Trust adjusted for device %s: %.1f -> %.1f (delta: %+.1f, event: %s)",
            device.device_id,
            score_before,
            score_after,
            trust_event.score_change,
            event_type.value,
        )

        return device, trust_event

    @staticmethod
    async def _evaluate_lifecycle_transitions(device: Device, new_score: float) -> None:
        """Evaluate and apply automatic lifecycle state changes based on trust thresholds."""
        if device.lifecycle_status in (
            DeviceLifecycleStatus.REGISTERED,
            DeviceLifecycleStatus.REVOKED,
        ):
            return

        now = datetime.now(timezone.utc)

        if new_score < 20.0 and device.lifecycle_status != DeviceLifecycleStatus.REVOKED:
            logger.warning(
                "CRITICAL: Trust score < 20 for device %s. Auto-revoking.",
                device.device_id,
            )
            device.lifecycle_status = DeviceLifecycleStatus.REVOKED
            device.revoked_at = now
            device.revocation_reason = "Trust score dropped below critical threshold (20.0)"
            
        elif new_score < 50.0 and device.lifecycle_status not in (DeviceLifecycleStatus.SUSPENDED, DeviceLifecycleStatus.REVOKED):
            logger.warning(
                "WARNING: Trust score < 50 for device %s. Auto-suspending.",
                device.device_id,
            )
            device.lifecycle_status = DeviceLifecycleStatus.SUSPENDED
            device.suspended_at = now
            device.suspension_reason = "Trust score dropped below warning threshold (50.0)"

    @staticmethod
    async def get_device_trust_score(db: AsyncSession, device_id: uuid.UUID) -> TrustScoreResponse:
        """Get the current trust score and risk level for a device."""
        stmt = select(Device).where(Device.id == device_id)
        result = await db.execute(stmt)
        device = result.scalar_one_or_none()
        
        if not device:
            raise ValueError(f"Device not found: {device_id}")
            
        return TrustScoreResponse(
            device_id=device.id,
            trust_score=device.trust_score,
            risk_level=get_risk_level_for_score(device.trust_score),
            last_updated=device.updated_at
        )

    @staticmethod
    async def get_trust_history(
        db: AsyncSession, device_id: uuid.UUID, limit: int = 50
    ) -> list[TrustEvent]:
        """Get the recent trust event history for a device."""
        stmt = (
            select(TrustEvent)
            .where(TrustEvent.device_id == device_id)
            .order_by(TrustEvent.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_system_analytics(db: AsyncSession) -> dict[str, Any]:
        """Compute system-wide trust analytics."""
        # Get all devices
        stmt = select(Device.trust_score)
        result = await db.execute(stmt)
        scores = list(result.scalars().all())
        
        device_count = len(scores)
        if device_count == 0:
            return {
                "average_trust_score": 0.0,
                "device_count": 0,
                "risk_distribution": {
                    "none": 0, "low": 0, "medium": 0, "high": 0
                },
                "recent_events_count": 0
            }
            
        avg_score = sum(scores) / device_count
        
        # Risk distribution
        distribution = {"none": 0, "low": 0, "medium": 0, "high": 0}
        for score in scores:
            distribution[get_risk_level_for_score(score)] += 1
            
        # Recent events count (last 24 hours)
        # Assuming simple count for now without complex time filters
        evt_stmt = select(func.count()).select_from(TrustEvent)
        evt_res = await db.execute(evt_stmt)
        recent_count = evt_res.scalar_one()
        
        return {
            "average_trust_score": round(avg_score, 2),
            "device_count": device_count,
            "risk_distribution": distribution,
            "recent_events_count": recent_count
        }
