from fastapi import APIRouter

print("✅ userController loaded")

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

@router.get("/")
def get_users():
    return {"message": "Users API working"}

@router.post("/")
def create_user():
    return {"message": "User created"}