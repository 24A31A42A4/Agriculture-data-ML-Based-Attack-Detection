"""Pydantic schemas for the Evaluation Framework API."""

from pydantic import BaseModel, ConfigDict
from datetime import datetime


class BenchmarkRunResponse(BaseModel):
    """Response containing a single benchmark result."""
    
    benchmark_name: str
    value: float
    unit: str
    metadata_: dict


class BenchmarkReportResponse(BaseModel):
    """Complete evaluation report for a given run ID."""
    
    run_id: str
    run_date: datetime
    benchmark_type: str
    results: list[BenchmarkRunResponse]

    model_config = ConfigDict(from_attributes=True)
