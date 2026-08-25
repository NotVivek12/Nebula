import uuid

from pydantic import BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    email: EmailStr
    full_name: str | None = None


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    password: str | None = None


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool


class BusinessOnboard(BaseModel):
    """Schema for onboarding a new tenant Business, creating its Owner user."""

    business_name: str
    owner_email: EmailStr
    owner_password: str
    owner_full_name: str | None = None


class BusinessOnboardResponse(BaseModel):
    """Schema for onboarding response."""

    business_id: uuid.UUID
    business_name: str
    owner: UserResponse
