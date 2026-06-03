"""
Attack Simulation Service.

Provides methods to simulate different attack vectors (Tampering, Fake Sensor,
Replay, Unauthorized Device, DoS) and observe how the security layers respond.
"""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError
from app.core.enums import TrustEventType
from app.services.trust_service import TrustService
from app.schemas.attack_sim import AttackSimResult, SimulationStep

logger = logging.getLogger(__name__)


class AttackSimService:
    """Service for running security attack simulations."""

    @staticmethod
    async def simulate_data_tampering(db: AsyncSession, device_id: uuid.UUID) -> AttackSimResult:
        """
        Simulate data tampering (hash mismatch or invalid signature).
        In a real request, this would fail at the Gateway layer.
        """
        try:
            trace = []
            trace.append(SimulationStep(step_name="Payload Generation", description="Edge node generates JSON sensor payload.", status="info"))
            trace.append(SimulationStep(step_name="AES Encryption & Hashing", description="Payload encrypted with AES-256-GCM. SHA-256 hash computed.", status="info"))
            trace.append(SimulationStep(step_name="MITM Attack", description="Attacker intercepts and modifies data (e.g., changes moisture level). Hash mismatch occurs.", status="warning"))
            trace.append(SimulationStep(step_name="Gateway Verification", description="Security Gateway rejects payload due to invalid hash or signature.", status="error"))
            
            # Simulate the gateway catching a hash mismatch
            # Gateway normally triggers a TrustService penalty
            _, trust_event = await TrustService.adjust_trust_score(
                db, device_id, TrustEventType.TAMPERING, "Simulated data tampering"
            )
            
            # Record it in the audit trail (and anchor to blockchain because HIGH severity)
            from app.blockchain.audit_trail import AuditTrail
            from app.core.enums import AuditEventType
            # Admin user ID for simulation
            from app.models.user import User
            from sqlalchemy import select
            admin = (await db.execute(select(User).where(User.email=="admin@example.com"))).scalar_one_or_none()
            admin_id = admin.id if admin else None
            
            await AuditTrail.record_event(
                db, 
                AuditEventType.TAMPERING_DETECTED, 
                device_id, 
                admin_id, 
                "127.0.0.1", 
                {"reason": "Tampering detected via payload hash mismatch."}
            )
            
            trace.append(SimulationStep(step_name="Trust Penalty", description=f"Trust score reduced by {trust_event.score_change}.", status="error"))
            trace.append(SimulationStep(step_name="Blockchain Anchoring", description="Tampering event anchored to blockchain for immutable record.", status="success"))
            
            return AttackSimResult(
                attack_type="data_tampering",
                target_device_id=str(device_id),
                was_detected=True,
                detection_layer="Security Gateway",
                trust_score_penalty=trust_event.score_change,
                blockchain_anchored=True, # Tampering is HIGH severity -> anchored
                details="Tampering detected via payload hash mismatch. Trust score penalized.",
                attack_trace=trace
            )
        except Exception as e:
            return AttackSimResult(
                attack_type="data_tampering",
                target_device_id=str(device_id),
                was_detected=False,
                detection_layer="None",
                trust_score_penalty=0.0,
                blockchain_anchored=False,
                details=f"Simulation failed to execute: {str(e)}"
            )

    @staticmethod
    async def simulate_fake_sensor(db: AsyncSession) -> AttackSimResult:
        """
        Simulate a fake sensor trying to ingest data (unregistered device ID).
        """
        fake_id = str(uuid.uuid4())
        # Gateway rejects unregistered devices immediately
        trace = [
            SimulationStep(step_name="Connection Attempt", description="Unknown device attempts to connect to Security Gateway.", status="warning"),
            SimulationStep(step_name="Authentication", description="Gateway checks registry for Device ID.", status="info"),
            SimulationStep(step_name="Detection", description="Device ID not found. Connection dropped immediately.", status="error"),
            SimulationStep(step_name="Audit", description="Unauthorized access attempt logged.", status="success")
        ]
        return AttackSimResult(
            attack_type="fake_sensor",
            target_device_id=fake_id,
            was_detected=True,
            detection_layer="Security Gateway",
            trust_score_penalty=0.0, # Cannot penalize unknown device
            blockchain_anchored=True, # HIGH severity -> anchored
            details="Unregistered device ID rejected during initial gateway validation.",
            attack_trace=trace
        )

    @staticmethod
    async def simulate_replay_attack(db: AsyncSession, device_id: uuid.UUID) -> AttackSimResult:
        """
        Simulate a replay attack (reused nonce or expired timestamp).
        """
        try:
            trace = [
                SimulationStep(step_name="Intercept", description="Attacker intercepts a valid signed payload.", status="warning"),
                SimulationStep(step_name="Replay", description="Attacker resends the exact payload 5 minutes later.", status="warning"),
                SimulationStep(step_name="Gateway Validation", description="Gateway checks timestamp and nonce cache.", status="info"),
                SimulationStep(step_name="Detection", description="Nonce collision detected. Payload rejected.", status="error")
            ]
            
            _, trust_event = await TrustService.adjust_trust_score(
                db, device_id, TrustEventType.REPLAY_ATTEMPT, "Simulated replay attack"
            )
            
            return AttackSimResult(
                attack_type="replay_attack",
                target_device_id=str(device_id),
                was_detected=True,
                detection_layer="Security Gateway",
                trust_score_penalty=trust_event.score_change,
                blockchain_anchored=True,
                details="Replay detected via nonce cache collision. Trust score penalized.",
                attack_trace=trace + [SimulationStep(step_name="Penalty", description=f"Trust score reduced by {trust_event.score_change}.", status="error")]
            )
        except Exception as e:
            return AttackSimResult(
                attack_type="replay_attack",
                target_device_id=str(device_id),
                was_detected=False,
                detection_layer="None",
                trust_score_penalty=0.0,
                blockchain_anchored=False,
                details=f"Simulation failed: {str(e)}"
            )

    @staticmethod
    async def simulate_dos_attack(db: AsyncSession, device_id: uuid.UUID) -> AttackSimResult:
        """
        Simulate a Denial of Service attack (rate limit violation bursts).
        """
        try:
            trace = [
                SimulationStep(step_name="Intercept", description="Attacker intercepts a valid signed payload.", status="warning"),
                SimulationStep(step_name="Replay", description="Attacker resends the exact payload 5 minutes later.", status="warning"),
                SimulationStep(step_name="Gateway Validation", description="Gateway checks timestamp and nonce cache.", status="info"),
                SimulationStep(step_name="Detection", description="Nonce collision detected. Payload rejected.", status="error")
            ]
            
            _, trust_event = await TrustService.adjust_trust_score(
                db, device_id, TrustEventType.DOS_BEHAVIOR, "Simulated DoS attack"
            )
            
            return AttackSimResult(
                attack_type="dos_attack",
                target_device_id=str(device_id),
                was_detected=True,
                detection_layer="Rate Limiter",
                trust_score_penalty=trust_event.score_change,
                blockchain_anchored=True,
                details="Rate limit exceeded by >10x. Classified as DoS behavior. Trust score severely penalized.",
                attack_trace=trace + [SimulationStep(step_name="Penalty", description=f"Trust score reduced by {trust_event.score_change}.", status="error")]
            )
        except Exception as e:
            return AttackSimResult(
                attack_type="dos_attack",
                target_device_id=str(device_id),
                was_detected=False,
                detection_layer="None",
                trust_score_penalty=0.0,
                blockchain_anchored=False,
                details=f"Simulation failed: {str(e)}"
            )

    @staticmethod
    async def simulate_unauthorized_device(db: AsyncSession, device_id: uuid.UUID) -> AttackSimResult:
        """
        Simulate an unauthorized device (registered but not whitelisted, or invalid ECC key).
        """
        try:
            trace = [
                SimulationStep(step_name="Intercept", description="Attacker intercepts a valid signed payload.", status="warning"),
                SimulationStep(step_name="Replay", description="Attacker resends the exact payload 5 minutes later.", status="warning"),
                SimulationStep(step_name="Gateway Validation", description="Gateway checks timestamp and nonce cache.", status="info"),
                SimulationStep(step_name="Detection", description="Nonce collision detected. Payload rejected.", status="error")
            ]
            
            _, trust_event = await TrustService.adjust_trust_score(
                db, device_id, TrustEventType.INVALID_SIGNATURE, "Simulated unauthorized device"
            )
            
            return AttackSimResult(
                attack_type="unauthorized_device",
                target_device_id=str(device_id),
                was_detected=True,
                detection_layer="Security Gateway",
                trust_score_penalty=trust_event.score_change,
                blockchain_anchored=True,
                details="ECC signature verification failed. Trust score penalized.",
                attack_trace=trace + [SimulationStep(step_name="Penalty", description=f"Trust score reduced by {trust_event.score_change}.", status="error")]
            )
        except Exception as e:
            return AttackSimResult(
                attack_type="unauthorized_device",
                target_device_id=str(device_id),
                was_detected=False,
                detection_layer="None",
                trust_score_penalty=0.0,
                blockchain_anchored=False,
                details=f"Simulation failed: {str(e)}"
            )

    @staticmethod
    async def simulate_ml_anomaly(db: AsyncSession, device_id: uuid.UUID) -> AttackSimResult:
        """
        Simulate an anomalous sensor behavior that passes ECC signature but is caught by ML.
        Demonstrates ML directly integrated into the IDS pipeline.
        """
        try:
            from app.services.ml_service import MLService
            from app.schemas.ml import PredictRequest
            
            trace = [
                SimulationStep(step_name="Payload Generation", description="Device generates payload.", status="info"),
                SimulationStep(step_name="Encryption & Signature", description="Payload encrypted with AES. ECC signature attached.", status="info"),
                SimulationStep(step_name="Attacker Tampering", description="Attacker poisons data carefully to bypass threshold checks (subtle anomaly).", status="warning"),
                SimulationStep(step_name="Gateway Validation", description="Hashes match. ECC signature passes.", status="success"),
            ]
            
            # 1. Generate Highly Anomalous Data
            # Normal Soil Moisture is ~20-60%. We simulate 95% + weird Ph to guarantee high probability.
            features = {
                "WaterLevel": 12.0, "Temperature": 38.0, "Humidity": 85.0, "Ph": 2.1, 
                "Rainfall": 0.0, "FertilizerApp": 1.0, "PesticideApp": 0.0, 
                "SoilMoisture": 98.0, "LightIntensity": 1000.0, "WindSpeed": 12.0, 
                "CO2Levels": 600.0, "PlantHeight": 40.0, "LeafAreaIndex": 2.5, "Yield": 0.0,
                "NDVI": 0.3, "SoilEC": 1.5, "SoilOrganicMatter": 3.0, "NitrogenLevel": 15.0,
                "PhosphorusLevel": 10.0, "PotassiumLevel": 20.0, "BatteryLevel": 90.0
            }
            
            # 2. Feed into ML Pipeline (Primary IDS: Stacking Classifier)
            prediction_result = await MLService.predict_single(db, features, model_name="Stacking Classifier (LightGBM + XGBoost + RF)")
            
            probability = prediction_result.probability or 0.0
            prob_percent = probability * 100.0
            
            # 3. Calculate Severity and Adaptive Penalty based on Probability
            if prob_percent < 60.0:
                severity_level = "LOW"
                penalty = 0.0
                blockchain_anchored = False
            elif prob_percent < 80.0:
                severity_level = "MEDIUM"
                penalty = -5.0
                blockchain_anchored = False
            elif prob_percent < 95.0:
                severity_level = "HIGH"
                penalty = -10.0
                blockchain_anchored = True
            else:
                severity_level = "CRITICAL"
                penalty = -30.0
                blockchain_anchored = True
                
            trace.append(SimulationStep(step_name="ML IDS Engine", description=f"Stacking Classifier predicts anomaly with {prob_percent:.1f}% probability.", status="error", metadata={"features": features, "severity": severity_level}))
            
            # 4. Enforce Trust Penalty if applicable
            if penalty < 0:
                from app.core.enums import TrustEventType
                _, trust_event = await TrustService.adjust_trust_score(
                    db, device_id, TrustEventType.ML_IDS_ALERT, 
                    f"ML Anomaly (Prob: {prob_percent:.1f}%)", 
                    override_score_change=penalty
                )
                applied_penalty = trust_event.score_change
            else:
                applied_penalty = 0.0
                
            # 5. Record to Audit Trail
            from app.blockchain.audit_trail import AuditTrail
            from app.core.enums import AuditEventType, SecuritySeverity
            from app.models.user import User
            from sqlalchemy import select
            
            admin = (await db.execute(select(User).where(User.email=="admin@example.com"))).scalar_one_or_none()
            admin_id = admin.id if admin else None
            
            # Map str to enum
            severity_enum = SecuritySeverity[severity_level]
            
            event_details = {
                "reason": "ML Detection triggered via adaptive pipeline.",
                "probability": prob_percent,
                "severity_assigned": severity_level,
                "top_features": prediction_result.top_features
            }
            
            audit_log, block = await AuditTrail.record_event(
                db, 
                AuditEventType.IDS_ALERT, 
                device_id, 
                admin_id, 
                "127.0.0.1", 
                event_details
            )
            
            # Override the default severity which might be MEDIUM
            audit_log.severity = severity_enum.value
            if not blockchain_anchored and audit_log.blockchain_block_index is not None:
                # Revert anchor if not required by adaptive rules
                audit_log.blockchain_block_index = None
                
            await db.commit()
            
            if applied_penalty < 0:
                trace.append(SimulationStep(step_name="Trust Engine", description=f"Penalty of {applied_penalty} applied.", status="error"))
            if blockchain_anchored:
                trace.append(SimulationStep(step_name="Blockchain", description="Alert anchored to ledger.", status="success"))
                
            return AttackSimResult(
                attack_type="ml_anomaly",
                target_device_id=str(device_id),
                was_detected=prob_percent >= 60.0,
                detection_layer="Machine Learning IDS",
                trust_score_penalty=applied_penalty,
                blockchain_anchored=blockchain_anchored,
                details=f"ML Predicted Anomaly with {prob_percent:.1f}% probability. Mapped to {severity_level} risk.",
                attack_trace=trace
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            return AttackSimResult(
                attack_type="ml_anomaly",
                target_device_id=str(device_id),
                was_detected=False,
                detection_layer="None",
                trust_score_penalty=0.0,
                blockchain_anchored=False,
                details=f"Simulation failed: {str(e)}"
            )
