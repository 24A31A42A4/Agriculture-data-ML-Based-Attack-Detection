"""
Evaluation Framework API endpoints.

Provides endpoints to trigger and report on security, system, ML,
and trust benchmarks.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DbSession, require_role
from app.core.enums import UserRole
from app.schemas.evaluation import BenchmarkReportResponse
from app.services.evaluation_service import BenchmarkRunner

router = APIRouter()

ResearcherOrAdmin = Depends(require_role([UserRole.ADMIN, UserRole.RESEARCHER]))
AdminOnly = Depends(require_role([UserRole.ADMIN]))
AnyAuthenticated = Depends(require_role([UserRole.ADMIN, UserRole.RESEARCHER, UserRole.FARMER, UserRole.SECURITY_ANALYST]))


@router.post(
    "/benchmark/security",
    response_model=dict,
    summary="Run Security Benchmarks",
    dependencies=[ResearcherOrAdmin],
)
async def run_security_benchmarks(db: DbSession):
    """Run cryptographic and security pipeline timing benchmarks."""
    run_id = await BenchmarkRunner.run_security_benchmarks(db)
    return {"run_id": run_id, "message": "Security benchmarks completed"}


@router.post(
    "/benchmark/ml",
    response_model=dict,
    summary="Run ML Benchmarks",
    dependencies=[ResearcherOrAdmin],
)
async def run_ml_benchmarks(db: DbSession):
    """Run ML evaluation across all 13 models on the test set."""
    run_id = await BenchmarkRunner.run_ml_benchmarks(db)
    return {"run_id": run_id, "message": "ML benchmarks completed"}


@router.post(
    "/benchmark/system",
    response_model=dict,
    summary="Run System Benchmarks",
    dependencies=[AdminOnly],
)
async def run_system_benchmarks(db: DbSession):
    """Run system load and throughput tests."""
    run_id = await BenchmarkRunner.run_system_benchmarks(db)
    return {"run_id": run_id, "message": "System benchmarks completed"}


@router.post(
    "/benchmark/trust",
    response_model=dict,
    summary="Run Trust Metrics Benchmarks",
    dependencies=[ResearcherOrAdmin],
)
async def run_trust_benchmarks(db: DbSession):
    """Run trust evaluation and attack response benchmarks."""
    run_id = await BenchmarkRunner.run_trust_benchmarks(db)
    return {"run_id": run_id, "message": "Trust benchmarks completed"}


@router.get(
    "/results/{run_id}",
    response_model=BenchmarkReportResponse,
    summary="Get Benchmark Report",
    dependencies=[AnyAuthenticated],
)
async def get_benchmark_results(run_id: str, db: DbSession):
    """Get the complete evaluation report for a specific run ID."""
    return await BenchmarkRunner.get_report(db, run_id)
