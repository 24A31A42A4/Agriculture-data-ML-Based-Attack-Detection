"""
Shared pytest fixtures for the AgriIoT Security Framework test suite.

Provides:
- Async test database sessions (SQLite in-memory for speed)
- FastAPI test client
- Redis mock
- Factory fixtures for common test objects
"""

import asyncio
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

import pytest
import pytest_asyncio
import redis.asyncio as redis
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Settings, get_settings
from app.core.enums import DeviceLifecycleStatus, DeviceType, UserRole
from app.database.session import get_db
from app.database.redis import get_redis
from app.main import create_app
from app.models.base import Base


# ─── Override Settings for Testing ───────────────────────────────────────────

def get_test_settings() -> Settings:
    """Return settings configured for testing."""
    return Settings(
        debug=True,
        log_level="DEBUG",
        database_url="sqlite+aiosqlite:///",  # In-memory SQLite
        redis_url="redis://localhost:6379/1",  # Separate Redis DB for tests
        jwt_secret_key="test-secret-key-for-testing-only-not-for-production",
        vault_master_secret="a" * 64,
        api_v1_str="/api/v1",
    )


# ─── Database Fixtures ───────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Create a fresh in-memory SQLite database for each test."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


class MockRedis:
    def __init__(self):
        self.data = {}
    
    async def get(self, key):
        return self.data.get(key)
        
    async def set(self, key, value, nx=False, ex=None):
        if nx and key in self.data:
            return None
        self.data[key] = value
        return True
        
    async def incr(self, key):
        val = int(self.data.get(key, 0)) + 1
        self.data[key] = str(val)
        return val
        
    async def expire(self, key, time):
        return True
        
    async def flushdb(self):
        self.data.clear()
        
    async def aclose(self):
        pass

@pytest_asyncio.fixture
async def redis_client() -> AsyncGenerator[MockRedis, None]:
    """Provide a mocked Redis client for testing."""
    client = MockRedis()
    yield client
    await client.flushdb()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional database session for a test."""
    session_factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


# ─── FastAPI Test Client ─────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP test client with overridden dependencies."""
    app = create_app()

    # Override database dependency
    async def override_get_db():
        yield db_session

    async def override_get_redis():
        client = MockRedis()
        yield client
        await client.flushdb()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ─── Factory Fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def sample_user_data() -> dict:
    """Return sample user registration data."""
    return {
        "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
        "password": "SecurePassword123!",
        "full_name": "Test Researcher",
        "role": UserRole.RESEARCHER.value,
    }


@pytest.fixture
def sample_device_data() -> dict:
    """Return sample device registration data."""
    return {
        "device_id": f"sensor-{uuid.uuid4().hex[:8]}",
        "device_name": "Soil Moisture Sensor A1",
        "device_type": DeviceType.SOIL_MOISTURE.value,
    }


@pytest.fixture
def sample_sensor_reading() -> dict:
    """Return sample raw sensor data matching the Smart-Farm-IDS schema."""
    return {
        "WaterLevel": 12.5,
        "WaterPumpToTank": "Inactive",
        "WaterPumpFromTank": "Inactive",
        "WaterTemperature": 27.3,
        "Ec": 741.0,
        "Tds": 277,
        "LightIntensity": 450.5,
        "Humidity": 62.1,
        "Temperature": 28.5,
        "HeatIndex": 24.1,
        "AirQuality": 457,
        "SoilHumidity1": 14.7,
        "SoilHumidity2": 17.0,
        "Light": "On",
        "Timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ─── Test Subdirectory Init Markers ──────────────────────────────────────────
# pytest collects tests from subdirectories automatically
