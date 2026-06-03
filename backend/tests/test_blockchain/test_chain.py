import pytest
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from app.blockchain.chain import BlockchainManager
from app.core.enums import BlockEventType, RiskLevel, SecuritySeverity, AttackClassification
from app.models.blockchain import BlockchainBlock


@pytest.mark.asyncio
async def test_initialize_chain(db_session: AsyncSession):
    # Initialize genesis block
    genesis = await BlockchainManager.initialize_chain(db_session)
    
    assert genesis.index == 0
    assert genesis.previous_hash == "0" * 64
    
    # Initializing again should return the same genesis block (idempotency)
    genesis2 = await BlockchainManager.initialize_chain(db_session)
    assert genesis.index == genesis2.index
    assert genesis.current_hash == genesis2.current_hash


@pytest.mark.asyncio
async def test_add_block_and_validate(db_session: AsyncSession):
    # Genesis will be created automatically if chain is empty
    device_id = uuid.uuid4()
    
    block1 = await BlockchainManager.add_block(
        db=db_session,
        event_type=BlockEventType.SENSOR_DATA,
        data_hash="a" * 64,
        signature="mock_sig_1",
        device_id=device_id,
        trust_score_snapshot=90.0,
        risk_level=RiskLevel.NONE,
        attack_classification=AttackClassification.NONE,
        security_severity=SecuritySeverity.INFO,
        event_metadata={"test": "data"}
    )
    
    assert block1.index == 1
    assert block1.event_type == BlockEventType.SENSOR_DATA.value
    
    block2 = await BlockchainManager.add_block(
        db=db_session,
        event_type=BlockEventType.SECURITY_ALERT,
        data_hash="b" * 64,
        signature="mock_sig_2",
        device_id=device_id,
        trust_score_snapshot=40.0,
        risk_level=RiskLevel.HIGH,
        attack_classification=AttackClassification.REPLAY,
        security_severity=SecuritySeverity.HIGH,
        event_metadata={"alert": "replay attack"}
    )
    
    assert block2.index == 2
    assert block2.previous_hash == block1.current_hash
    
    # Run full chain validation
    report = await BlockchainManager.validate_chain(db_session)
    assert report["is_valid"] is True
    assert report["total_blocks"] == 3  # Genesis + 2
    assert len(report["errors"]) == 0


@pytest.mark.asyncio
async def test_chain_tampering_detection(db_session: AsyncSession):
    # Setup chain
    block1 = await BlockchainManager.add_block(
        db=db_session,
        event_type=BlockEventType.TRUST_UPDATE,
        data_hash="x" * 64,
        signature="sig"
    )
    
    # Tamper with block data via ORM
    block1.trust_score_snapshot = 0.0
    await db_session.commit()
    
    # Validation should fail
    report = await BlockchainManager.validate_chain(db_session)
    assert report["is_valid"] is False
    assert len(report["errors"]) > 0
    
    # We should have a hash mismatch error
    assert any("Hash mismatch" in err["error"] for err in report["errors"])


@pytest.mark.asyncio
async def test_chain_statistics(db_session: AsyncSession):
    await BlockchainManager.add_block(
        db=db_session,
        event_type=BlockEventType.SECURITY_ALERT,
        data_hash="y" * 64,
        signature="sig",
        security_severity=SecuritySeverity.CRITICAL,
        attack_classification=AttackClassification.DOS,
        trust_score_snapshot=10.0
    )
    
    stats = await BlockchainManager.get_chain_statistics(db_session)
    assert stats["total_blocks"] > 0
    assert stats["severity_distribution"].get(SecuritySeverity.CRITICAL.value, 0) >= 1
    assert stats["attack_classification_distribution"].get(AttackClassification.DOS.value, 0) >= 1
