import uuid
from sqlalchemy import Column, String, Enum, ForeignKey, Text, DateTime
from sqlalchemy.dialects.sqlite import INTEGER
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from database import Base

class UserRole(str, enum.Enum):
    applicant = "applicant"
    company = "company"

class JobStatus(str, enum.Enum):
    draft = "Draft"
    open = "Open"
    closed = "Closed"

class ApplicationStatus(str, enum.Enum):
    applied = "Applied"
    reviewed = "Reviewed"
    interview = "Interview"
    rejected = "Rejected"
    hired = "Hired"

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    is_verified = Column(INTEGER, default=0)  # 0 = false, 1 = true

    jobs = relationship("Job", back_populates="creator")
    applications = relationship("Application", back_populates="applicant")

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    location = Column(String, nullable=True)
    status = Column(Enum(JobStatus), default=JobStatus.draft)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    creator = relationship("User", back_populates="jobs")
    applications = relationship("Application", back_populates="job")

class Application(Base):
    __tablename__ = "applications"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    applicant_id = Column(String, ForeignKey("users.id"), nullable=False)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False)
    resume_link = Column(String, nullable=False)
    cover_letter = Column(Text, nullable=True)
    status = Column(Enum(ApplicationStatus), default=ApplicationStatus.applied)
    applied_at = Column(DateTime(timezone=True), server_default=func.now())

    applicant = relationship("User", back_populates="applications")
    job = relationship("Job", back_populates="applications")
