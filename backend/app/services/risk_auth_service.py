"""
Risk-Based Authentication Service.

Evaluates device access requests against their current trust score and risk tier.
Enforces the risk-based authentication policy.
"""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError
from app.services.trust_service import TrustService, get_risk_level_for_score

logger = logging.getLogger(__name__)


class RiskAuthService:
    """Service to enforce risk-based authentication tiers."""

    @staticmethod
    async def evaluate_access(db: AsyncSession, device_id: uuid.UUID) -> dict:
        """
        Evaluate if a device is allowed to access the system based on its risk tier.

        Policy:
          - > 80: Full Access
          - 50-80: Restricted Access (Allowed but heavily monitored)
          - 20-50: Limited Access (Ingestion rejected, investigation required)
          - < 20: Blocked (Device revoked)
          
        Args:
            db: Database session
            device_id: Device ID to evaluate

        Returns:
            Dictionary with access decision and risk context.

        Raises:
            AuthorizationError: If the device is blocked or limited.
        """
        trust_response = await TrustService.get_device_trust_score(db, device_id)
        score = trust_response.trust_score
        risk_level = trust_response.risk_level

        decision = {
            "device_id": str(device_id),
            "trust_score": score,
            "risk_level": risk_level,
            "access_granted": False,
            "access_tier": "blocked",
            "message": ""
        }

        if score > 80.0:
            decision["access_granted"] = True
            decision["access_tier"] = "full"
            decision["message"] = "Full access granted"
            
        elif score >= 50.0:
            decision["access_granted"] = True
            decision["access_tier"] = "restricted"
            decision["message"] = "Restricted access granted (warning zone)"
            logger.warning("Device %s granted restricted access (score: %.1f)", device_id, score)
            
        elif score >= 20.0:
            decision["access_granted"] = False
            decision["access_tier"] = "limited"
            decision["message"] = "Access limited due to low trust score. Sensor data rejected."
            logger.error("Device %s access limited (score: %.1f)", device_id, score)
            raise AuthorizationError(decision["message"])
            
        else:
            decision["access_granted"] = False
            decision["access_tier"] = "blocked"
            decision["message"] = "Access blocked. Device revoked due to critical trust level."
            logger.error("Device %s access BLOCKED (score: %.1f)", device_id, score)
            raise AuthorizationError(decision["message"])

        return decision
