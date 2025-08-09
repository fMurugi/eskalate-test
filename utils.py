# utils.py
import os
from datetime import datetime, timedelta
from jose import jwt, JWTError, ExpiredSignatureError
from passlib.context import CryptContext
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
VERIFICATION_TOKEN_EXPIRE_MINUTES = int(os.getenv("VERIFICATION_TOKEN_EXPIRE_MINUTES", "60"))
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8000")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# hashing
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

# verification token (email)
def create_verification_token(subject: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=VERIFICATION_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": subject, "iat": datetime.utcnow().timestamp(), "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_verification_token(token: str):
    """
    Returns dict:
      - {"valid": True, "payload": {...}}
      - {"valid": False, "expired": True, "payload": {...}} -> expired but payload may be returned if signature OK
      - {"valid": False, "expired": False, "payload": None} -> invalid/malformed
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {"valid": True, "payload": payload}
    except ExpiredSignatureError:
        # try to extract payload without verifying expiration (still requires signature validity)
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
            return {"valid": False, "expired": True, "payload": payload}
        except JWTError:
            return {"valid": False, "expired": True, "payload": None}
    except JWTError:
        return {"valid": False, "expired": False, "payload": None}

# access token (login)
def create_access_token(subject: str, role: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": subject, "role": role, "iat": datetime.utcnow().timestamp(), "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
