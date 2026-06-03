"""Tests for user service CRUD operations."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import UserRole
from app.schemas.user import UserCreate, UserUpdate
from app.security.password import verify_password
from app.services.user_service import UserService


@pytest.mark.asyncio
async def test_create_user(db_session: AsyncSession, sample_user_data: dict):
    user_in = UserCreate(**sample_user_data)
    user = await UserService.create(db_session, obj_in=user_in)
    
    assert user.email == sample_user_data["email"]
    assert hasattr(user, "hashed_password")
    assert user.hashed_password != sample_user_data["password"]
    assert verify_password(sample_user_data["password"], user.hashed_password)
    assert user.full_name == sample_user_data["full_name"]
    role_str = user.role.value if hasattr(user.role, "value") else user.role
    assert role_str == sample_user_data["role"]
    assert user.is_active is True


@pytest.mark.asyncio
async def test_authenticate_user(db_session: AsyncSession, sample_user_data: dict):
    user_in = UserCreate(**sample_user_data)
    user = await UserService.create(db_session, obj_in=user_in)
    
    authenticated_user = await UserService.get_by_email(db_session, email=user.email)
    assert authenticated_user
    assert verify_password(sample_user_data["password"], authenticated_user.hashed_password)


@pytest.mark.asyncio
async def test_update_user(db_session: AsyncSession, sample_user_data: dict):
    user_in = UserCreate(**sample_user_data)
    user = await UserService.create(db_session, obj_in=user_in)
    
    new_full_name = "Updated Name"
    new_password = "NewPassword123!"
    user_update = UserUpdate(full_name=new_full_name, password=new_password)
    
    updated_user = await UserService.update(db_session, db_obj=user, obj_in=user_update)
    assert updated_user.full_name == new_full_name
    assert verify_password(new_password, updated_user.hashed_password)
    assert updated_user.email == user.email


@pytest.mark.asyncio
async def test_get_user(db_session: AsyncSession, sample_user_data: dict):
    user_in = UserCreate(**sample_user_data)
    user = await UserService.create(db_session, obj_in=user_in)
    
    retrieved_user = await UserService.get(db_session, user_id=user.id)
    assert retrieved_user
    assert retrieved_user.id == user.id
    assert retrieved_user.email == user.email


@pytest.mark.asyncio
async def test_delete_user(db_session: AsyncSession, sample_user_data: dict):
    user_in = UserCreate(**sample_user_data)
    user = await UserService.create(db_session, obj_in=user_in)
    
    success = await UserService.delete(db_session, user_id=user.id)
    assert success is True
    
    retrieved_user = await UserService.get(db_session, user_id=user.id)
    assert retrieved_user is None
