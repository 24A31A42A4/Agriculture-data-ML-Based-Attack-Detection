import pytest
from datetime import datetime, timezone
import uuid

from app.blockchain.block import (
    BlockData,
    compute_block_hash,
    compute_data_hash,
    create_genesis_block,
    compute_merkle_root
)
from app.core.enums import BlockEventType, RiskLevel, SecuritySeverity, AttackClassification


def test_compute_data_hash():
    data = {"sensor": "A1", "value": 12.5}
    hash1 = compute_data_hash(data)
    
    # Order shouldn't matter for dictionary representation if json.dumps uses sort_keys=True
    data2 = {"value": 12.5, "sensor": "A1"}
    hash2 = compute_data_hash(data2)
    
    assert hash1 == hash2
    assert len(hash1) == 64


def test_create_genesis_block():
    genesis = create_genesis_block()
    
    assert genesis.index == 0
    assert genesis.previous_hash == "0" * 64
    assert genesis.event_type == BlockEventType.SYSTEM_EVENT
    assert genesis.device_id is None
    assert genesis.trust_score_snapshot == 100.0


def test_compute_block_hash_determinism():
    block = BlockData(
        index=1,
        previous_hash="a" * 64,
        timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
        device_id=uuid.uuid4(),
        event_type=BlockEventType.SENSOR_DATA,
        data_hash="b" * 64,
        signature="mock_sig",
        trust_score_snapshot=85.5,
        risk_level=RiskLevel.LOW,
        attack_classification=AttackClassification.NONE,
        security_severity=SecuritySeverity.INFO,
        event_metadata={"temp": 25.0},
        nonce_value=0
    )
    
    hash1 = compute_block_hash(block)
    hash2 = compute_block_hash(block)
    
    assert hash1 == hash2
    
    # Tampering should change the hash
    block.trust_score_snapshot = 85.4
    hash3 = compute_block_hash(block)
    assert hash1 != hash3


def test_compute_merkle_root():
    # Empty list
    assert compute_merkle_root([]) == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" # SHA-256 of empty string
    
    # 1 element
    h1 = "a" * 64
    assert compute_merkle_root([h1]) == h1
    
    # 2 elements
    h2 = "b" * 64
    import hashlib
    expected_2 = hashlib.sha256((h1 + h2).encode()).hexdigest()
    assert compute_merkle_root([h1, h2]) == expected_2
    
    # 3 elements (odd count) - last element is duplicated
    h3 = "c" * 64
    expected_3_step1_1 = hashlib.sha256((h1 + h2).encode()).hexdigest()
    expected_3_step1_2 = hashlib.sha256((h3 + h3).encode()).hexdigest()
    expected_3_final = hashlib.sha256((expected_3_step1_1 + expected_3_step1_2).encode()).hexdigest()
    
    assert compute_merkle_root([h1, h2, h3]) == expected_3_final
