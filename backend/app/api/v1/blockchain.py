"""
Blockchain REST API endpoints.

Provides read-only access to the blockchain for research analysis,
chain integrity verification, and block querying.

All endpoints require authentication (Researcher or Admin role).
Write operations are performed internally via the AuditTrail service —
blocks are never created directly via the API to maintain chain integrity.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DbSession, require_role
from app.blockchain.chain import BlockchainManager
from app.blockchain.validator import validate_block_integrity
from app.core.enums import BlockEventType, SecuritySeverity, UserRole
from app.schemas.blockchain import (
    BlockIntegrityResponse,
    BlockResponse,
    ChainStatisticsResponse,
    ChainValidationResponse,
    EpochMerkleRequest,
    EpochMerkleResponse,
)

router = APIRouter()

# Require at least Researcher role for all blockchain endpoints
ResearcherOrAdmin = Depends(require_role([UserRole.RESEARCHER, UserRole.ADMIN]))


@router.get(
    "/blocks",
    response_model=list[BlockResponse],
    summary="List Blockchain Blocks",
    description="Retrieve blockchain blocks with optional filtering by event type or severity.",
    dependencies=[ResearcherOrAdmin],
)
async def list_blocks(
    db: DbSession,
    event_type: BlockEventType | None = Query(None, description="Filter by event type"),
    severity: SecuritySeverity | None = Query(None, description="Filter by severity"),
    limit: int = Query(50, ge=1, le=500, description="Max blocks to return"),
):
    """List blocks with optional filters for research analysis."""
    if event_type:
        blocks = await BlockchainManager.get_blocks_by_event_type(db, event_type, limit)
    elif severity:
        blocks = await BlockchainManager.get_blocks_by_severity(db, severity, limit)
    else:
        blocks = await BlockchainManager.get_blocks_in_range(db, 0, 999999)
        blocks = blocks[-limit:]  # Return latest N blocks
    return blocks


@router.get(
    "/blocks/{index}",
    response_model=BlockResponse,
    summary="Get Block by Index",
    description="Retrieve a single block by its chain index.",
    dependencies=[ResearcherOrAdmin],
)
async def get_block(index: int, db: DbSession):
    """Get a specific block from the chain."""
    block = await BlockchainManager.get_block(db, index)
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block #{index} not found",
        )
    return block


@router.get(
    "/blocks/{index}/verify",
    response_model=BlockIntegrityResponse,
    summary="Verify Block Integrity",
    description="Recompute the SHA-256 hash of a block and compare with the stored hash.",
    dependencies=[ResearcherOrAdmin],
)
async def verify_block(index: int, db: DbSession):
    """Verify the integrity of a single block."""
    block = await BlockchainManager.get_block(db, index)
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block #{index} not found",
        )
    return validate_block_integrity(block)


@router.get(
    "/validate",
    response_model=ChainValidationResponse,
    summary="Validate Entire Chain",
    description=(
        "Run full chain integrity validation: genesis check, hash recomputation, "
        "chain linkage verification, and index continuity."
    ),
    dependencies=[ResearcherOrAdmin],
)
async def validate_chain(db: DbSession):
    """Validate the integrity of the entire blockchain."""
    return await BlockchainManager.validate_chain(db)


@router.get(
    "/statistics",
    response_model=ChainStatisticsResponse,
    summary="Chain Statistics",
    description=(
        "Compute comprehensive chain statistics including event type distribution, "
        "severity distribution, attack classifications, and trust score analysis."
    ),
    dependencies=[ResearcherOrAdmin],
)
async def get_statistics(db: DbSession):
    """Get chain statistics for research analysis."""
    return await BlockchainManager.get_chain_statistics(db)


@router.post(
    "/merkle",
    response_model=EpochMerkleResponse,
    summary="Compute Epoch Merkle Root",
    description=(
        "Compute the Merkle root for a range of blocks. Useful for periodic "
        "integrity snapshots and lightweight verification."
    ),
    dependencies=[ResearcherOrAdmin],
)
async def compute_merkle(request: EpochMerkleRequest, db: DbSession):
    """Compute Merkle root for a block range."""
    if request.end_index < request.start_index:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_index must be >= start_index",
        )

    blocks = await BlockchainManager.get_blocks_in_range(
        db, request.start_index, request.end_index
    )
    merkle_root = await BlockchainManager.compute_epoch_merkle_root(
        db, request.start_index, request.end_index
    )

    return EpochMerkleResponse(
        start_index=request.start_index,
        end_index=request.end_index,
        merkle_root=merkle_root,
        block_count=len(blocks),
    )


@router.get(
    "/latest",
    response_model=BlockResponse,
    summary="Get Latest Block",
    description="Retrieve the most recently added block in the chain.",
    dependencies=[ResearcherOrAdmin],
)
async def get_latest_block(db: DbSession):
    """Get the latest block in the chain."""
    block = await BlockchainManager.get_latest_block(db)
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No blocks in the chain",
        )
    return block


@router.get(
    "/length",
    summary="Get Chain Length",
    description="Return the total number of blocks in the chain.",
    dependencies=[ResearcherOrAdmin],
)
async def get_chain_length(db: DbSession):
    """Get the total number of blocks."""
    length = await BlockchainManager.get_chain_length(db)
    return {"chain_length": length}
