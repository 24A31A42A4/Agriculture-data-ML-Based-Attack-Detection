"""
Aggregated API v1 router.

All v1 endpoint routers are included here and mounted
onto the main FastAPI app under /api/v1.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1")

# ── Routers will be included as they are implemented ─────────────────────────
#
# Phase 2:
from app.api.v1.auth import router as auth_router
router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
#
# Phase 3:
from app.api.v1.devices import router as devices_router
router.include_router(devices_router, prefix="/devices", tags=["Devices"])
#
# Phase 4:
from app.api.v1.sensors import router as sensors_router
router.include_router(sensors_router, prefix="/sensors", tags=["Sensors"])
#
# Phase 5/6:
from app.api.v1.blockchain import router as blockchain_router
router.include_router(blockchain_router, prefix="/blockchain", tags=["Blockchain"])
#
from app.api.v1.audit import router as audit_router
router.include_router(audit_router, prefix="/audit", tags=["Audit Trail"])
# Phase 8:
from app.api.v1.trust import router as trust_router
router.include_router(trust_router, prefix="/trust", tags=["Trust & Risk"])
# Phase 9:
from app.api.v1.device_health import router as health_router
router.include_router(health_router, prefix="/devices", tags=["Device Health"])
# Phase 10:
from app.api.v1.ml_inference import router as ml_router
router.include_router(ml_router, prefix="/ml", tags=["ML Inference"])
# Phase 11:
from app.api.v1.drift import router as drift_router
router.include_router(drift_router, prefix="/drift", tags=["Feature Drift"])
# Phase 12:
from app.api.v1.attack_sim import router as attack_router
router.include_router(attack_router, prefix="/attack-sim", tags=["Attack Simulation"])
# Phase 13:
from app.api.v1.evaluation import router as eval_router
router.include_router(eval_router, prefix="/evaluation", tags=["Evaluation"])
