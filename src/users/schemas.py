from pydantic import BaseModel, EmailStr
from enum import Enum
from decimal import Decimal
from datetime import datetime, time

class RoleEnum(str, Enum):
    admin = "admin"
    manager = "manager"
    employee = "employee"

class UserCreate(BaseModel):
    email: str
    name: str
    password: str
    role: RoleEnum

class UserOut(BaseModel):
    id: int
    email: str
    name: str
    role: RoleEnum
    created_at: datetime

    class Config:
        from_attributes = True
