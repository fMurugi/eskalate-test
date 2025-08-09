# routers/jobs.py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from utils import decode_access_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List
from uuid import UUID
from sqlalchemy import func
from fastapi import File, UploadFile
from datetime import datetime
# from utils import upload_to_cloudinary, send_email  # You'll need to implement these helpers

# Use HTTPBearer
bearer_scheme = HTTPBearer()

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme), db: Session = Depends(get_db)) -> models.User:
    token = credentials.credentials  # Extract raw token
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user_id = payload.get("sub")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


@router.post("/", response_model=schemas.BaseResponse)
def create_job(payload: schemas.JobCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role != models.UserRole.company:
        return schemas.BaseResponse(success=False, message="Only companies can create jobs", errors=["Unauthorized"])

    job = models.Job(
        title=payload.title,
        description=payload.description,
        location=payload.location,
        status=payload.status.value if payload.status else models.JobStatus.Draft,
        created_by=current_user.id
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return schemas.BaseResponse(success=True, message="Job created", object={"job_id": job.id})


@router.put("/{job_id}", response_model=schemas.BaseResponse)
def update_job(job_id: UUID, payload: schemas.JobUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    job = db.query(models.Job).filter(models.Job.id == str(job_id)).first()
    if not job:
        return schemas.BaseResponse(success=False, message="Job not found", errors=["No job"])

    if job.created_by != current_user.id:
        return schemas.BaseResponse(success=False, message="Unauthorized access", errors=["Unauthorized"])

    # forward-only status progression
    if payload.status:
        order = ["Draft", "Open", "Closed"]
        old_idx = order.index(job.status.value)
        new_idx = order.index(payload.status.value)
        if new_idx < old_idx:
            return schemas.BaseResponse(success=False, message="Invalid status transition (cannot go backwards)", errors=["Invalid transition"])
        job.status = payload.status.value

    if payload.title is not None:
        job.title = payload.title
    if payload.description is not None:
        job.description = payload.description
    if payload.location is not None:
        job.location = payload.location

    db.commit()
    db.refresh(job)
    return schemas.BaseResponse(success=True, message="Job updated", object={"job_id": job.id})


@router.delete("/{job_id}", response_model=schemas.BaseResponse)
def delete_job(job_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    job = db.query(models.Job).filter(models.Job.id == str(job_id)).first()
    if not job:
        return schemas.BaseResponse(success=False, message="Job not found", errors=["No job"])

    if job.created_by != current_user.id:
        return schemas.BaseResponse(success=False, message="Unauthorized access", errors=["Unauthorized"])

    db.delete(job)
    db.commit()
    return schemas.BaseResponse(success=True, message="Job deleted")


@router.get("/browse", response_model=schemas.PaginatedResponse)
def browse_jobs(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    title: str = Query(None),
    location: str = Query(None),
    company_name: str = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100)
):
    query = db.query(models.Job).join(models.User, models.Job.owner_id == models.User.id)

    if title:
        query = query.filter(models.Job.title.ilike(f"%{title}%"))
    if location:
        query = query.filter(models.Job.location.ilike(f"%{location}%"))
    if company_name:
        query = query.filter(models.User.name.ilike(f"%{company_name}%"))

    total = query.count()
    jobs = query.offset((page - 1) * size).limit(size).all()

    return schemas.PaginatedResponse(
        success=True,
        message="Jobs fetched successfully",
        object={
            "items": jobs,
            "total": total,
            "page": page,
            "size": size,
            "pages": (total + size - 1) // size
        }
    )


@router.get("/my", response_model=schemas.PaginatedResponse)
def view_my_jobs(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    status_filter: models.JobStatus = Query(None, description="Filter by job status"),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100)
):
    if current_user.role != models.UserRole.company:
        return schemas.PaginatedResponse(success=False, message="Only companies can view their posted jobs")

    query = (
        db.query(models.Job, func.count(models.Application.id).label("applications_count"))
        .outerjoin(models.Application, models.Application.job_id == models.Job.id)
        .filter(models.Job.created_by == current_user.id)
        .group_by(models.Job.id)
    )

    if status_filter:
        query = query.filter(models.Job.status == status_filter)

    total = query.count()
    results = query.offset((page - 1) * size).limit(size).all()

    jobs_list = [
        {
            "title": job.title,
            "description": job.description,
            "location": job.location,
            "status": job.status,
            "created_at": job.created_at,
            "applications_count": applications_count
        }
        for job, applications_count in results
    ]

    return schemas.PaginatedResponse(
        success=True,
        message="My jobs fetched successfully",
        object={
            "items": jobs_list,
            "total": total,
            "page": page,
            "size": size,
            "pages": (total + size - 1) // size
        }
    )


@router.get("/{job_id}", response_model=schemas.BaseResponse)
def view_job_details(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    job = db.query(models.Job).filter(models.Job.id == str(job_id)).first()
    if not job:
        return schemas.BaseResponse(success=False, message="Job not found", errors=["No job"])

    job_data = {
        "id": job.id,
        "title": job.title,
        "description": job.description,
        "location": job.location,
        "status": job.status,
        "created_at": job.created_at,
        "created_by": job.created_by
    }

    return schemas.BaseResponse(success=True, message="Job details fetched", object=job_data)


@router.get("/{job_id}/applications", response_model=schemas.PaginatedResponse)
def view_job_applications(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    status_filter: models.ApplicationStatus = Query(None, description="Filter by application status"),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100)
):
    job = db.query(models.Job).filter(models.Job.id == str(job_id)).first()
    if not job:
        return schemas.PaginatedResponse(success=False, message="Job not found")

    if job.created_by != current_user.id or current_user.role != models.UserRole.company:
        return schemas.PaginatedResponse(success=False, message="Unauthorized access")

    query = db.query(models.Application).join(models.User, models.User.id == models.Application.user_id)
    query = query.filter(models.Application.job_id == str(job_id))

    if status_filter:
        query = query.filter(models.Application.status == status_filter)

    total = query.count()
    applications = query.offset((page - 1) * size).limit(size).all()

    app_list = [
        {
            "applicant_name": app.user.name,
            "resume_link": app.resume_link,
            "cover_letter": app.cover_letter,
            "status": app.status,
            "applied_at": app.created_at
        }
        for app in applications
    ]

    return schemas.PaginatedResponse(
        success=True,
        message="Applications fetched successfully",
        object={
            "items": app_list,
            "total": total,
            "page": page,
            "size": size,
            "pages": (total + size - 1) // size
        }
    )


@router.post("/{job_id}/apply", response_model=schemas.BaseResponse)
def apply_for_job(
    job_id: UUID,
    cover_letter: str = Query(None, max_length=200),
    resume_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # 1. Check role
    if current_user.role != models.UserRole.applicant:
        return schemas.BaseResponse(success=False, message="Only applicants can apply", errors=["Unauthorized"])

    # 2. Validate job exists
    job = db.query(models.Job).filter(models.Job.id == str(job_id)).first()
    if not job:
        return schemas.BaseResponse(success=False, message="Job not found", errors=["No job"])

    # 3. Prevent duplicate applications
    existing_app = db.query(models.Application).filter(
        models.Application.job_id == str(job_id),
        models.Application.user_id == current_user.id
    ).first()
    if existing_app:
        return schemas.BaseResponse(success=False, message="You have already applied to this job", errors=["Duplicate application"])

    # 4. Validate resume file format
    allowed_types = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
    if resume_file.content_type not in allowed_types:
        return schemas.BaseResponse(success=False, message="Unsupported file type", errors=["Invalid resume format"])

    # 5. Upload resume to Cloudinary (TODO: implement upload_to_cloudinary)
    resume_url = upload_to_cloudinary(resume_file)

    # 6. Create application
    application = models.Application(
        job_id=str(job_id),
        user_id=current_user.id,
        resume_link=resume_url,
        cover_letter=cover_letter,
        status=models.ApplicationStatus.Applied,
        created_at=datetime.utcnow()
    )
    db.add(application)
    db.commit()
    db.refresh(application)

    # 7. Send email notification to company (you need to implement send_email)
    company_user = db.query(models.User).filter(models.User.id == job.created_by).first()
    if company_user and company_user.email:
        send_email(
            to_email=company_user.email,
            subject="New Job Application Received",
            body=f"{current_user.name} has applied for your job '{job.title}'."
        )

    return schemas.BaseResponse(
        success=True,
        message="Application submitted successfully",
        object={
            "application_id": application.id,
            "job_id": job_id,
            "resume_link": resume_url,
            "cover_letter": cover_letter,
            "status": application.status,
            "applied_at": application.created_at
        }
    )
