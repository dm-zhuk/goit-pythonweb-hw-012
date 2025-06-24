# src/schemas/schemas.py
"""Data Validation with Pydantic - ensures data sent to API is valid"""

from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import date
from typing import Optional

from src.database.models import Role


# Contact Schemas
class ContactBase(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: str
    birthday: date
    additional_data: Optional[str] = None


class ContactCreate(ContactBase):
    pass


class ContactUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    birthday: Optional[date] = None
    additional_data: Optional[str] = None


class ContactResponse(ContactBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class BirthdayResponse(BaseModel):
    message: str


# User Schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    avatar: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    is_verified: bool
    avatar_url: Optional[str] = None
    roles: Role
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RequestEmail(BaseModel):
    email: EmailStr


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str
