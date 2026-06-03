import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.evaluation_service import BenchmarkRunner
from app.core.enums import BenchmarkType
from app.models.benchmark_result import BenchmarkResult


@pytest.mark.asyncio
async def test_run_security_benchmarks(db_session: AsyncSession):
    run_id = await BenchmarkRunner.run_security_benchmarks(db_session, iterations=10)
    assert run_id.startswith("sec_bench_")
    
    stmt = select(BenchmarkResult).where(BenchmarkResult.run_id == run_id)
    res = await db_session.execute(stmt)
    results = list(res.scalars().all())
    
    assert len(results) == 3
    assert all(r.benchmark_type == BenchmarkType.SECURITY.value for r in results)


@pytest.mark.asyncio
async def test_run_ml_benchmarks(db_session: AsyncSession):
    run_id = await BenchmarkRunner.run_ml_benchmarks(db_session)
    assert run_id.startswith("ml_bench_")
    
    stmt = select(BenchmarkResult).where(BenchmarkResult.run_id == run_id)
    res = await db_session.execute(stmt)
    results = list(res.scalars().all())
    
    assert len(results) == 3
    assert all(r.benchmark_type == BenchmarkType.ML.value for r in results)


@pytest.mark.asyncio
async def test_run_system_benchmarks(db_session: AsyncSession):
    run_id = await BenchmarkRunner.run_system_benchmarks(db_session)
    assert run_id.startswith("sys_bench_")


@pytest.mark.asyncio
async def test_run_trust_benchmarks(db_session: AsyncSession):
    run_id = await BenchmarkRunner.run_trust_benchmarks(db_session)
    assert run_id.startswith("trust_bench_")


@pytest.mark.asyncio
async def test_get_report(db_session: AsyncSession):
    run_id = await BenchmarkRunner.run_security_benchmarks(db_session, iterations=10)
    
    report = await BenchmarkRunner.get_report(db_session, run_id)
    
    assert report.run_id == run_id
    assert report.benchmark_type == BenchmarkType.SECURITY.value
    assert len(report.results) == 3
    
    with pytest.raises(ValueError) as exc:
        await BenchmarkRunner.get_report(db_session, "non_existent_run_id")
    
    assert "No results found" in str(exc.value)
