from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from utils.hashing_password import hash_password

router = APIRouter(prefix="/users", tags=["Users"])


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

