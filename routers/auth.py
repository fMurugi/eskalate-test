# routers/auth.py
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from utils import hash_password, verify_password, create_verification_token, verify_verification_token, create_access_token
from services import send_verification_email

router = APIRouter(prefix="/api", tags=["auth"])

@router.post("/signup", response_model=schemas.BaseResponse)
def signup(payload: schemas.UserSignup, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # unique email
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        return schemas.BaseResponse(success=False, message="Email already registered", errors=["Email exists"])

    user = models.User(
        name=payload.name,
        email=payload.email,
        password=hash_password(payload.password),
        role=payload.role.value,
        is_verified=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_verification_token(user.id)
    # send in background (here it prints)
    background_tasks.add_task(send_verification_email, user.email, token)

    return schemas.BaseResponse(success=True, message="User registered. Verification email sent.", object={"user_id": user.id})

@router.get("/verify-email", response_model=schemas.BaseResponse)
def verify_email(token: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    res = verify_verification_token(token)

    if res["valid"]:
        payload = res["payload"]
        user_id = payload.get("sub")
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            return schemas.BaseResponse(success=False, message="User not found", errors=["No user"])
        if user.is_verified:
            return schemas.BaseResponse(success=True, message="Email already verified")
        user.is_verified = True
        db.commit()
        return schemas.BaseResponse(success=True, message="Email verified successfully", object={"user_id": user.id})

    # token invalid or expired
    if res.get("expired"):
        payload = res.get("payload")
        if payload and payload.get("sub"):
            user_id = payload.get("sub")
            user = db.query(models.User).filter(models.User.id == user_id).first()
            if user:
                # generate a fresh token and send again
                new_token = create_verification_token(user.id)
                background_tasks.add_task(send_verification_email, user.email, new_token)
                return schemas.BaseResponse(success=False, message="Verification token expired. A new verification email was sent.", object={"user_id": user.id})

        return schemas.BaseResponse(success=False, message="Verification token expired and user not found", errors=["Expired token"])

    return schemas.BaseResponse(success=False, message="Invalid token", errors=["Invalid token"])

@router.post("/login", response_model=schemas.BaseResponse)
def login(payload: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user:
        return schemas.BaseResponse(success=False, message="Invalid credentials", errors=["Invalid email/password"])

    if not verify_password(payload.password, user.password):
        return schemas.BaseResponse(success=False, message="Invalid credentials", errors=["Invalid email/password"])

    if not user.is_verified:
        return schemas.BaseResponse(success=False, message="Email not verified. Please verify before logging in.", errors=["Email not verified"])

    token = create_access_token(user.id, user.role)
    return schemas.BaseResponse(success=True, message="Login successful", object={"token": token})
