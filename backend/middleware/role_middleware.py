from fastapi import Depends, HTTPException, status
from middleware.auth_middleware import get_current_user

def require_roles(*allowed_roles):
    def role_checker(user = Depends(get_current_user)):
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action"
            )
        return user
    return role_checker
