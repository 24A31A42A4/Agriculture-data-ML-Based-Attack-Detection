"""Tests for authentication API endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.schemas.user import UserCreate
from app.services.user_service import UserService


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient, sample_user_data: dict):
    settings = get_settings()
    response = await client.post(
        f"{settings.api_v1_str}/auth/register", json=sample_user_data
    )
    assert response.status_code == 200
    content = response.json()
    assert content["email"] == sample_user_data["email"]
    assert content["full_name"] == sample_user_data["full_name"]
    assert "id" in content
    assert "hashed_password" not in content


@pytest.mark.asyncio
async def test_login_access_token(
    client: AsyncClient, db_session: AsyncSession, sample_user_data: dict
):
    # Pre-create user
    user_in = UserCreate(**sample_user_data)
    await UserService.create(db_session, obj_in=user_in)
    
    settings = get_settings()
    login_data = {
        "username": sample_user_data["email"],
        "password": sample_user_data["password"],
    }
    response = await client.post(
        f"{settings.api_v1_str}/auth/login/access-token", data=login_data
    )
    assert response.status_code == 200
    tokens = response.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_read_current_user(
    client: AsyncClient, db_session: AsyncSession, sample_user_data: dict
):
    # Pre-create user
    user_in = UserCreate(**sample_user_data)
    await UserService.create(db_session, obj_in=user_in)
    
    settings = get_settings()
    
    # Login to get token
    login_data = {
        "username": sample_user_data["email"],
        "password": sample_user_data["password"],
    }
    login_response = await client.post(
        f"{settings.api_v1_str}/auth/login/access-token", data=login_data
    )
    tokens = login_response.json()
    access_token = tokens["access_token"]
    
    # Use token to get profile
    response = await client.get(
        f"{settings.api_v1_str}/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
    content = response.json()
    assert content["email"] == sample_user_data["email"]
    assert content["full_name"] == sample_user_data["full_name"]
