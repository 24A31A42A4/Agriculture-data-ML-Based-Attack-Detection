"""
Audit trail REST API endpoints.

Provides access to the immutable audit log with filtering and
manual event recording capabilities for administrators.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DbSession, get_current_user, require_role
from app.blockchain.audit_trail import AuditTrail
from app.core.enums import AuditEventType, SecuritySeverity, UserRole
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.audit import AuditEventCreate, AuditLogResponse

router = APIRouter()

AdminOnly = Depends(require_role([UserRole.ADMIN]))
ResearcherOrAdmin = Depends(require_role([UserRole.RESEARCHER, UserRole.ADMIN]))


@router.get(
    "/logs",
    response_model=list[AuditLogResponse],
    summary="List Audit Logs",
    description="Retrieve audit logs with optional filtering by event type, severity, or device.",
    dependencies=[ResearcherOrAdmin],
)
async def list_audit_logs(
    db: DbSession,
    event_type: AuditEventType | None = Query(None),
    severity: SecuritySeverity | None = Query(None),
    device_id: uuid.UUID | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
):
    """List audit logs with optional filters."""
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)

    if event_type:
        stmt = stmt.where(AuditLog.event_type == event_type.value)
    if severity:
        stmt = stmt.where(AuditLog.severity == severity.value)
    if device_id:
        stmt = stmt.where(AuditLog.device_id == device_id)

    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post(
    "/record",
    response_model=AuditLogResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record Manual Audit Event",
    description="Manually record a security event to the audit trail (admin only). Events above MEDIUM severity are automatically anchored to the blockchain.",
    dependencies=[AdminOnly],
)
async def record_audit_event(
    payload: AuditEventCreate,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Record a manual audit event with blockchain anchoring."""
    audit_log, blockchain_block = await AuditTrail.record_event(
        db=db,
        event_type=payload.event_type,
        device_id=payload.device_id,
        user_id=current_user.id,
        source_ip=payload.source_ip,
        event_details=payload.event_details,
        correlation_id=payload.correlation_id,
    )
    return audit_log
