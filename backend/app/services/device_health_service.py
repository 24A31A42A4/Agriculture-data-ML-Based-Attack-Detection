"""
Device Health Monitoring Service.

Calculates composite health scores based on authentication reliability,
trust score, trust trend (linear regression), and recency.
"""

import logging
import uuid
from datetime import datetime, timezone

import numpy as np
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device
from app.models.device_health import DeviceHealth
from app.models.trust_event import TrustEvent

logger = logging.getLogger(__name__)


class DeviceHealthService:
    """Service to track and compute device health metrics."""

    @staticmethod
    async def get_or_create_health(db: AsyncSession, device_id: uuid.UUID) -> DeviceHealth:
        """Fetch or create a health record for a device."""
        stmt = select(DeviceHealth).where(DeviceHealth.device_id == device_id)
        result = await db.execute(stmt)
        health = result.scalar_one_or_none()

        if not health:
            health = DeviceHealth(device_id=device_id)
            db.add(health)
            await db.commit()
            await db.refresh(health)

        return health

    @staticmethod
    async def record_auth_event(
        db: AsyncSession, device_id: uuid.UUID, success: bool
    ) -> DeviceHealth:
        """
        Record an authentication attempt and update auth rates.
        """
        # Note: In a high-throughput system, this would be updated async or batched,
        # but we do it synchronously here for the research prototype.
        health = await DeviceHealthService.get_or_create_health(db, device_id)

        health.total_auth_attempts += 1
        now = datetime.now(timezone.utc)

        if success:
            health.auth_successes += 1
            health.consecutive_failures = 0
            health.last_successful_auth = now
        else:
            health.auth_failures += 1
            health.consecutive_failures += 1
            health.last_failed_auth = now

        health.auth_success_rate = health.auth_successes / health.total_auth_attempts
        health.auth_failure_rate = health.auth_failures / health.total_auth_attempts

        # Recompute overall health score
        await DeviceHealthService._recompute_health_score(db, health)

        await db.commit()
        await db.refresh(health)
        return health

    @staticmethod
    async def compute_trust_trend(db: AsyncSession, device_id: uuid.UUID, window: int = 50) -> float:
        """
        Compute the linear regression slope of the last N trust score values.
        Positive slope = trust improving.
        Negative slope = trust degrading.
        Returns slope normalized to [-1.0, +1.0].
        """
        stmt = (
            select(TrustEvent.score_after)
            .where(TrustEvent.device_id == device_id)
            .order_by(TrustEvent.created_at.desc())
            .limit(window)
        )
        result = await db.execute(stmt)
        scores = list(result.scalars().all())
        
        # We queried descending, so reverse to chronological order
        scores.reverse()

        if len(scores) < 2:
            return 0.0

        x = np.arange(len(scores))
        # Fit a line: y = mx + c. polyfit returns [m, c]
        slope, _ = np.polyfit(x, scores, 1)
        
        # Clip slope between -1.0 and 1.0 (a slope of 1.0 means +1 trust per event)
        return float(np.clip(slope, -1.0, 1.0))

    @staticmethod
    async def _recompute_health_score(db: AsyncSession, health: DeviceHealth) -> None:
        """
        Compute composite health score combining authentication reliability,
        trust trajectory, and operational status.
        
        Components (weighted):
            40% — Authentication success rate
            30% — Trust score (normalized)
            20% — Trust trend (positive = healthy)
            10% — Recency (time since last seen)
        """
        # 1. Fetch current trust score and trend
        stmt = select(Device.trust_score).where(Device.id == health.device_id)
        result = await db.execute(stmt)
        trust_score = result.scalar_one_or_none() or 100.0

        trend = await DeviceHealthService.compute_trust_trend(db, health.device_id)
        health.trust_trend = trend

        # 2. Authentication component (0-100)
        if health.total_auth_attempts == 0:
            auth_component = 50.0  # neutral for new devices
        else:
            auth_component = health.auth_success_rate * 100.0

        # 3. Trust trend component (-1.0 to +1.0 normalized to 0-100)
        trend_component = max(0.0, min(100.0, (trend + 1.0) * 50.0))

        # 4. Recency component (100 if seen recently, decays 2 pts per hour)
        if health.last_successful_auth:
            now = datetime.now(timezone.utc)
            last_auth = health.last_successful_auth
            if last_auth.tzinfo is None:
                last_auth = last_auth.replace(tzinfo=timezone.utc)
            hours_since_seen = (now - last_auth).total_seconds() / 3600.0
            recency_component = max(0.0, 100.0 - (hours_since_seen * 2.0))
        else:
            recency_component = 0.0

        # Weighted calculation
        score = (
            0.40 * auth_component +
            0.30 * trust_score +
            0.20 * trend_component +
            0.10 * recency_component
        )
        
        health.health_score = round(max(0.0, min(100.0, score)), 2)

    @staticmethod
    async def get_device_health(db: AsyncSession, device_id: uuid.UUID) -> DeviceHealth:
        """Get current health for a device, recomputing it on the fly."""
        health = await DeviceHealthService.get_or_create_health(db, device_id)
        await DeviceHealthService._recompute_health_score(db, health)
        await db.commit()
        await db.refresh(health)
        return health

    @staticmethod
    async def get_health_summary(db: AsyncSession) -> dict:
        """Get summary of all device health scores."""
        # Note: For accuracy we should trigger a background job to update all health scores,
        # but for this API we use the latest stored values.
        stmt = select(DeviceHealth.health_score)
        result = await db.execute(stmt)
        scores = list(result.scalars().all())

        total = len(scores)
        if total == 0:
            return {
                "average_health_score": 0.0,
                "healthy_devices_count": 0,
                "warning_devices_count": 0,
                "degraded_devices_count": 0,
                "total_devices_evaluated": 0,
            }

        avg = sum(scores) / total
        healthy = sum(1 for s in scores if s >= 80.0)
        warning = sum(1 for s in scores if 50.0 <= s < 80.0)
        degraded = sum(1 for s in scores if s < 50.0)

        return {
            "average_health_score": round(avg, 2),
            "healthy_devices_count": healthy,
            "warning_devices_count": warning,
            "degraded_devices_count": degraded,
            "total_devices_evaluated": total,
        }

    @staticmethod
    async def get_degraded_devices(db: AsyncSession) -> list[DeviceHealth]:
        """Get list of devices with health < 50."""
        stmt = select(DeviceHealth).where(DeviceHealth.health_score < 50.0)
        result = await db.execute(stmt)
        return list(result.scalars().all())
