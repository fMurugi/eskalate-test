# routers/auth.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from utils import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/api", tags=["auth"])

@router.post("/signup", response_model=schemas.BaseResponse)
def signup(payload: schemas.UserSignup, db: Session = Depends(get_db)):
    # Check for existing email
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        return schemas.BaseResponse(success=False, message="Email already registered", errors=["Email exists"])

    user = models.User(
        name=payload.name,
        email=payload.email,
        password=hash_password(payload.password),
        role=payload.role.value,
        is_verified=True  # Mark as verified immediately
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return schemas.BaseResponse(success=True, message="User registered successfully.", object={"user_id": user.id})

@router.post("/login", response_model=schemas.BaseResponse)
def login(payload: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user:
        return schemas.BaseResponse(success=False, message="Invalid credentials", errors=["Invalid email/password"])

    if not verify_password(payload.password, user.password):
        return schemas.BaseResponse(success=False, message="Invalid credentials", errors=["Invalid email/password"])

    # No email verification check here anymore

    token = create_access_token(user.id, user.role)
    return schemas.BaseResponse(success=True, message="Login successful", object={"token": token})
