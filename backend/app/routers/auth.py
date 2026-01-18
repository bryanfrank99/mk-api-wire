from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from ..core import security
from ..core.deps import get_session
from ..models.database import User, AuditLog
from ..schemas.token import Token
from datetime import datetime

router = APIRouter()

@router.post("/login", response_model=Token)
async def login(
    session: Session = Depends(get_session),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    statement = select(User).where(User.username == form_data.username)
    user = session.exec(statement).first()
    
    if not user or not security.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    # Audit: successful login
    session.add(
        AuditLog(
            user_id=user.id,
            action="LOGIN",
            details=f"User '{user.username}' logged in",
            created_at=datetime.utcnow(),
        )
    )
    session.commit()

    access_token = security.create_access_token(subject=user.id)
    return {"access_token": access_token, "token_type": "bearer"}
