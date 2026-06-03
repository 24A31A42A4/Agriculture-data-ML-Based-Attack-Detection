import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.blockchain.audit_trail import AuditTrail, classify_severity
from app.core.enums import AuditEventType, SecuritySeverity, RiskLevel
from app.models.audit_log import AuditLog
from app.models.blockchain import BlockchainBlock


def test_classify_severity():
    # Base classification
    assert classify_severity(AuditEventType.DEVICE_REGISTERED) == SecuritySeverity.INFO
    assert classify_severity(AuditEventType.AUTH_FAILURE) == SecuritySeverity.LOW
    assert classify_severity(AuditEventType.REPLAY_ATTACK) == SecuritySeverity.HIGH
    
    # Context escalation: repeated failures
    assert classify_severity(AuditEventType.AUTH_FAILURE, {"consecutive_failures": 3}) == SecuritySeverity.MEDIUM
    
    # Context escalation: low trust
    assert classify_severity(AuditEventType.RATE_LIMIT_EXCEEDED, {"trust_score": 25.0}) == SecuritySeverity.HIGH
    
    # Context escalation: concurrent alerts
    assert classify_severity(AuditEventType.TAMPERING_DETECTED, {"concurrent_alerts": 5}) == SecuritySeverity.CRITICAL


@pytest.mark.asyncio
async def test_record_event_info_no_anchor(db_session: AsyncSession):
    # INFO events should NOT be anchored to the blockchain
    device_id = uuid.uuid4()
    
    audit_log, block = await AuditTrail.record_event(
        db=db_session,
        event_type=AuditEventType.AUTH_SUCCESS,
        device_id=device_id
    )
    
    assert audit_log is not None
    assert audit_log.severity == SecuritySeverity.INFO.value
    assert audit_log.blockchain_block_index is None
    
    assert block is None


@pytest.mark.asyncio
async def test_record_event_high_anchored(db_session: AsyncSession):
    # HIGH events SHOULD be anchored to the blockchain
    device_id = uuid.uuid4()
    
    audit_log, block = await AuditTrail.record_event(
        db=db_session,
        event_type=AuditEventType.REPLAY_ATTACK,
        device_id=device_id,
        event_details={"nonce": "used_nonce"}
    )
    
    assert audit_log is not None
    assert audit_log.severity == SecuritySeverity.HIGH.value
    assert audit_log.blockchain_block_index is not None
    
    assert block is not None
    assert block.security_severity == SecuritySeverity.HIGH.value
    assert block.risk_level == RiskLevel.HIGH.value
    
    # Verify the linkage
    assert audit_log.blockchain_block_index == block.index
    
    # Verify we can fetch it back
    stmt = select(BlockchainBlock).where(BlockchainBlock.index == block.index)
    res = await db_session.execute(stmt)
    fetched_block = res.scalar_one()
    
    assert fetched_block.event_metadata["audit_log_id"] == str(audit_log.id)
