"""User business logic and CRUD operations."""

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.security.password import get_password_hash


class UserService:
    """Service for user management."""

    @staticmethod
    async def get(db: AsyncSession, user_id: uuid.UUID) -> User | None:
        """Get a user by ID."""
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> User | None:
        """Get a user by email address."""
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_multi(db: AsyncSession, skip: int = 0, limit: int = 100) -> Sequence[User]:
        """Get multiple users."""
        stmt = select(User).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def create(db: AsyncSession, obj_in: UserCreate) -> User:
        """Create a new user."""
        db_obj = User(
            email=obj_in.email,
            hashed_password=get_password_hash(obj_in.password),
            full_name=obj_in.full_name,
            role=obj_in.role,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    @staticmethod
    async def update(db: AsyncSession, db_obj: User, obj_in: UserUpdate) -> User:
        """Update a user."""
        update_data = obj_in.model_dump(exclude_unset=True)
        if "password" in update_data:
            hashed_password = get_password_hash(update_data["password"])
            del update_data["password"]
            update_data["hashed_password"] = hashed_password
            
        for field, value in update_data.items():
            setattr(db_obj, field, value)
            
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    @staticmethod
    async def delete(db: AsyncSession, user_id: uuid.UUID) -> bool:
        """Delete a user."""
        db_obj = await UserService.get(db, user_id)
        if not db_obj:
            return False
        await db.delete(db_obj)
        await db.commit()
        return True
