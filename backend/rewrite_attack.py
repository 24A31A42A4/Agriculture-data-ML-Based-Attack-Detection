import re

path = r"c:\Users\Alisha\Desktop\Agri_another\Agriculture-data-ML-Based-Attack-Detection\backend\app\services\attack_sim_service.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Add SimulationStep to import
content = content.replace("from app.schemas.attack_sim import AttackSimResult", "from app.schemas.attack_sim import AttackSimResult, SimulationStep")

# Tampering
content = content.replace('        try:\n            # Simulate the gateway catching a hash mismatch\n            # Gateway normally triggers a TrustService penalty', '''        try:
            trace = []
            trace.append(SimulationStep(step_name="Payload Generation", description="Edge node generates JSON sensor payload.", status="info"))
            trace.append(SimulationStep(step_name="AES Encryption & Hashing", description="Payload encrypted with AES-256-GCM. SHA-256 hash computed.", status="info"))
            trace.append(SimulationStep(step_name="MITM Attack", description="Attacker intercepts and modifies data (e.g., changes moisture level). Hash mismatch occurs.", status="warning"))
            trace.append(SimulationStep(step_name="Gateway Verification", description="Security Gateway rejects payload due to invalid hash or signature.", status="error"))
            
            # Simulate the gateway catching a hash mismatch
            # Gateway normally triggers a TrustService penalty''')
content = content.replace('''            return AttackSimResult(
                attack_type="data_tampering",
                target_device_id=str(device_id),
                was_detected=True,
                detection_layer="Security Gateway",
                trust_score_penalty=trust_event.score_change,
                blockchain_anchored=True, # Tampering is HIGH severity -> anchored
                details="Tampering detected via payload hash mismatch. Trust score penalized."
            )''', '''            trace.append(SimulationStep(step_name="Trust Penalty", description=f"Trust score reduced by {trust_event.score_change}.", status="error"))
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
            )''')

# Fake Sensor
content = content.replace('''        # Gateway rejects unregistered devices immediately
        return AttackSimResult(''', '''        # Gateway rejects unregistered devices immediately
        trace = [
            SimulationStep(step_name="Connection Attempt", description="Unknown device attempts to connect to Security Gateway.", status="warning"),
            SimulationStep(step_name="Authentication", description="Gateway checks registry for Device ID.", status="info"),
            SimulationStep(step_name="Detection", description="Device ID not found. Connection dropped immediately.", status="error"),
            SimulationStep(step_name="Audit", description="Unauthorized access attempt logged.", status="success")
        ]
        return AttackSimResult(''')
content = content.replace('''            blockchain_anchored=True, # HIGH severity -> anchored
            details="Unregistered device ID rejected during initial gateway validation."
        )''', '''            blockchain_anchored=True, # HIGH severity -> anchored
            details="Unregistered device ID rejected during initial gateway validation.",
            attack_trace=trace
        )''')

# Replay Attack
content = content.replace('''        try:
            _, trust_event = await TrustService.adjust_trust_score(''', '''        try:
            trace = [
                SimulationStep(step_name="Intercept", description="Attacker intercepts a valid signed payload.", status="warning"),
                SimulationStep(step_name="Replay", description="Attacker resends the exact payload 5 minutes later.", status="warning"),
                SimulationStep(step_name="Gateway Validation", description="Gateway checks timestamp and nonce cache.", status="info"),
                SimulationStep(step_name="Detection", description="Nonce collision detected. Payload rejected.", status="error")
            ]
            
            _, trust_event = await TrustService.adjust_trust_score(''')
content = content.replace('''                trust_score_penalty=trust_event.score_change,
                blockchain_anchored=True,
                details="Replay detected via nonce cache collision. Trust score penalized."
            )''', '''                trust_score_penalty=trust_event.score_change,
                blockchain_anchored=True,
                details="Replay detected via nonce cache collision. Trust score penalized.",
                attack_trace=trace + [SimulationStep(step_name="Penalty", description=f"Trust score reduced by {trust_event.score_change}.", status="error")]
            )''')

# DoS Attack
content = content.replace('''        try:
            _, trust_event = await TrustService.adjust_trust_score(''', '''        try:
            trace = [
                SimulationStep(step_name="Traffic Spike", description="Device starts sending 1000 requests per second.", status="warning"),
                SimulationStep(step_name="Rate Limiting", description="API Gateway Rate Limiter triggered.", status="info"),
                SimulationStep(step_name="Detection", description="DoS behavior identified. Connection throttled.", status="error")
            ]
            _, trust_event = await TrustService.adjust_trust_score(''')
content = content.replace('''                trust_score_penalty=trust_event.score_change,
                blockchain_anchored=True,
                details="Rate limit exceeded by >10x. Classified as DoS behavior. Trust score severely penalized."
            )''', '''                trust_score_penalty=trust_event.score_change,
                blockchain_anchored=True,
                details="Rate limit exceeded by >10x. Classified as DoS behavior. Trust score severely penalized.",
                attack_trace=trace + [SimulationStep(step_name="Penalty", description=f"Trust score reduced by {trust_event.score_change}.", status="error")]
            )''')

# Unauthorized Device
content = content.replace('''        try:
            _, trust_event = await TrustService.adjust_trust_score(''', '''        try:
            trace = [
                SimulationStep(step_name="Payload Sent", description="Device sends payload with an invalid or spoofed ECC signature.", status="warning"),
                SimulationStep(step_name="Gateway Validation", description="Gateway verifies ECC signature using public key.", status="info"),
                SimulationStep(step_name="Detection", description="ECC signature verification failed.", status="error")
            ]
            _, trust_event = await TrustService.adjust_trust_score(''')
content = content.replace('''                trust_score_penalty=trust_event.score_change,
                blockchain_anchored=True,
                details="ECC signature verification failed. Trust score penalized."
            )''', '''                trust_score_penalty=trust_event.score_change,
                blockchain_anchored=True,
                details="ECC signature verification failed. Trust score penalized.",
                attack_trace=trace + [SimulationStep(step_name="Penalty", description=f"Trust score reduced by {trust_event.score_change}.", status="error")]
            )''')

# ML Anomaly
content = content.replace('''        try:
            from app.services.ml_service import MLService
            from app.schemas.ml import PredictRequest
            
            # 1. Generate Highly Anomalous Data''', '''        try:
            from app.services.ml_service import MLService
            from app.schemas.ml import PredictRequest
            
            trace = [
                SimulationStep(step_name="Payload Generation", description="Device generates payload.", status="info"),
                SimulationStep(step_name="Encryption & Signature", description="Payload encrypted with AES. ECC signature attached.", status="info"),
                SimulationStep(step_name="Attacker Tampering", description="Attacker poisons data carefully to bypass threshold checks (subtle anomaly).", status="warning"),
                SimulationStep(step_name="Gateway Validation", description="Hashes match. ECC signature passes.", status="success"),
            ]
            
            # 1. Generate Highly Anomalous Data''')

content = content.replace('''            # 4. Enforce Trust Penalty if applicable''', '''            trace.append(SimulationStep(step_name="ML IDS Engine", description=f"Stacking Classifier predicts anomaly with {prob_percent:.1f}% probability.", status="error", metadata={"features": features, "severity": severity_level}))
            
            # 4. Enforce Trust Penalty if applicable''')

content = content.replace('''            return AttackSimResult(
                attack_type="ml_anomaly",
                target_device_id=str(device_id),
                was_detected=prob_percent >= 60.0,
                detection_layer="Machine Learning IDS",
                trust_score_penalty=applied_penalty,
                blockchain_anchored=blockchain_anchored,
                details=f"ML Predicted Anomaly with {prob_percent:.1f}% probability. Mapped to {severity_level} risk."
            )''', '''            if applied_penalty < 0:
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
            )''')

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
