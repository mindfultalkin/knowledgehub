from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta

from database import get_db
from models.user import User
from utils.hashing_password import hash_password
from utils.hashing_password import verify_password
from utils.jwt_token_util import create_access_token

from middleware.auth_middleware import get_current_user
from middleware.role_middleware import require_roles

from pydantic import BaseModel, EmailStr


router = APIRouter(prefix="/users", tags=["Users"])
IST = timezone(timedelta(hours=5, minutes=30))


# ==================== REQUEST MODELS ====================

class LoginRequest(BaseModel):
    email: str
    password: str

class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str | None = None
    last_name: str | None = None
    role: str  # MASTER / STANDARD

class UpdateUserRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


# ==================== ADMIN CREATION API ====================

@router.post("/bootstrap-admin")
def create_admin_user(db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.role == "ADMIN").first()
    if existing:
        raise HTTPException(status_code=400, detail="Admin already exists")

    admin = User(
        email="QLPartners@knowledgehub.com",
        hashed_password=hash_password("QLPartners@001"),
        first_name="System",
        last_name="Admin",
        role="ADMIN",
        is_active=True
    )

    db.add(admin)
    db.commit()
    db.refresh(admin)

    return {
        "message": "Admin user created",
        "email": admin.email
    }


# ==================== USER APIs ====================

@router.post("/login")
def login_user(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Login user using email & password.
    Returns JWT access token.
    """

    # 1️⃣ Fetch user by email
    user = db.query(User).filter(User.email == payload.email).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # 2️⃣ Check if user is active
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is deactivated")

    # 3️⃣ Verify password
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # 4️⃣ Update last_login
    user.last_login = datetime.now(IST)
    db.commit()

    # 5️⃣ Create JWT access token (15 mins)
    access_token = create_access_token(
        data={
            "user_id": str(user.id),
            "email": user.email,
            "role": user.role
        }
    )

    # 6️⃣ Response
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "last_login": user.last_login
        }
    }

@router.post("/logout")
def logout():
    return {"message": "Logout successful. Delete token on client."}

@router.post("", dependencies=[Depends(require_roles("ADMIN"))])
def create_user(
    payload: CreateUserRequest,
    db: Session = Depends(get_db)
):
    if payload.role not in ["MASTER", "STANDARD"]:
        raise HTTPException(status_code=400, detail="Invalid role")

    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="User already exists")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        first_name=payload.first_name,
        last_name=payload.last_name,
        role=payload.role,
        is_active=True
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {"message": "User created", "id": user.id}

@router.get("", dependencies=[Depends(require_roles("ADMIN"))])
def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users

@router.get("/me")
def get_me(current_user = Depends(get_current_user)):
    return current_user

@router.put("/{user_id}")
def update_user(
    user_id: int,
    payload: UpdateUserRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if current_user.role != "ADMIN" and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not allowed")

    if payload.first_name is not None:
        user.first_name = payload.first_name
    if payload.last_name is not None:
        user.last_name = payload.last_name

    db.commit()
    return {"message": "User updated"}

@router.patch("/{user_id}/activate", dependencies=[Depends(require_roles("ADMIN"))])
def activate_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).get(user_id)
    user.is_active = True
    db.commit()
    return {"message": "User activated"}

@router.patch("/{user_id}/deactivate", dependencies=[Depends(require_roles("ADMIN"))])
def deactivate_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).get(user_id)
    user.is_active = False
    db.commit()
    return {"message": "User deactivated"}

@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if not verify_password(payload.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Wrong old password")

    current_user.hashed_password = hash_password(payload.new_password)
    db.commit()
    return {"message": "Password changed"}
