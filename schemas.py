from pydantic import BaseModel, EmailStr, constr, validator
from typing import Optional, List, Dict, Any
import re
import enum


# ======================
# Enums
# ======================
class RoleEnum(str, enum.Enum):
    applicant = "applicant"
    company = "company"

class JobStatusEnum(str, enum.Enum):
    Draft = "Draft"
    Open = "Open"
    Closed = "Closed"

class ApplicationStatusEnum(str, enum.Enum):
    Pending = "Pending"
    Reviewed = "Reviewed"
    Accepted = "Accepted"
    Rejected = "Rejected"


# ======================
# Base response schemas
# ======================
class BaseResponse(BaseModel):
    success: bool
    message: str
    object: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None

    class Config:
        orm_mode = True


class PaginatedResponse(BaseModel):
    success: bool
    message: str
    object: Dict[str, Any]  # { "items": [...], "total": int, "page": int, "size": int }
    errors: Optional[List[str]] = None

    class Config:
        orm_mode = True


# ======================
# Auth schemas
# ======================
class UserSignup(BaseModel):
    name: constr(strip_whitespace=True)
    email: EmailStr
    password: constr(min_length=8)
    role: RoleEnum

    @validator("name")
    def name_format(cls, v):
        if not re.fullmatch(r"^[A-Za-z]+ [A-Za-z]+$", v):
            raise ValueError("Full name must be two words with only alphabets and a single space between them.")
        return v

    @validator("password")
    def strong_password(cls, v):
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain an uppercase letter.")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain a lowercase letter.")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain a number.")
        if not re.search(r"[^\w\s]", v):
            raise ValueError("Password must contain a special character.")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class LoginResponseObject(BaseModel):
    token: str


# ======================
# Job schemas
# ======================
class JobCreate(BaseModel):
    title: constr(min_length=1, max_length=100)
    description: constr(min_length=20, max_length=2000)
    location: Optional[str] = None
    status: Optional[JobStatusEnum] = JobStatusEnum.Draft


class JobUpdate(BaseModel):
    title: Optional[constr(min_length=1, max_length=100)] = None
    description: Optional[constr(min_length=20, max_length=2000)] = None
    location: Optional[str] = None
    status: Optional[JobStatusEnum] = None


class JobListItem(BaseModel):
    id: int
    title: str
    description: str
    location: Optional[str]
    status: JobStatusEnum
    created_at: str
    applications_count: int

    class Config:
        orm_mode = True


class JobDetail(BaseModel):
    id: int
    title: str
    description: str
    location: Optional[str]
    status: JobStatusEnum
    created_at: str
    created_by: str

    class Config:
        orm_mode = True


# ======================
# Application schemas
# ======================
class ApplicationListItem(BaseModel):
    applicant_name: str
    resume_link: str
    cover_letter: str
    status: ApplicationStatusEnum
    applied_at: str

    class Config:
        orm_mode = True
