from datetime import datetime, time
from enum import Enum
from uuid import UUID

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum as SqlEnum, Numeric, Time
from sqlalchemy.orm import relationship
from src.database import Base, metadata

class UserRole(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    WAREHOUSE = "warehouse"
    CLIENT = "client"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(SqlEnum(UserRole), nullable=False, default=UserRole.CLIENT)

    # Google subject (openid "sub")
    google_sub = Column(String, unique=True, nullable=True, index=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
