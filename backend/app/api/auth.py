"""Authentication routes. Generic messages everywhere — no user enumeration."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import check_rate_limit, get_current_user, get_db
from app.models.models import User
from app.schemas.schemas import (
    ChangePasswordIn,
    ForgotPasswordIn,
    LoginIn,
    MeUpdateIn,
    RefreshIn,
    RequestVerificationCodeIn,
    ResetPasswordIn,
    SignupIn,
    TokenPair,
    UserOut,
    VerifyEmailIn,
)
from app.services import auth_service
from app.services.notify_service import log_activity

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post("/signup", response_model=UserOut, status_code=201)
def signup(body: SignupIn, db: Session = Depends(get_db)):
    try:
        user = auth_service.signup(db, body.email, body.password, body.name)
    except auth_service._Exists:
        # No enumeration: return a valid UserOut shape (not {"detail": ...})
        # so clients parsing the 201 response don't break. The email is the
        # one the caller just supplied, so nothing is leaked.
        from datetime import datetime, timezone
        return UserOut(
            id="00000000-0000-0000-0000-000000000000",
            email=body.email.strip().lower(),
            name=body.name.strip(),
            is_verified=False,
            created_at=datetime.now(timezone.utc),
        )
    log_activity(db, "auth.signup", user_id=user.id)
    return user


@router.post("/login", response_model=TokenPair)
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else "unknown"
    check_rate_limit(f"login:{ip}:{body.email.lower()}", limit=5, window_seconds=900)
    user = auth_service.authenticate(db, body.email, body.password)
    if not user:
        # Generic — never reveal whether the email exists or the account is locked.
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail=auth_service.GENERIC_LOGIN_ERROR)
    access, refresh = auth_service.issue_token_pair(db, user, settings.REFRESH_TOKEN_DAYS)
    log_activity(db, "auth.login", user_id=user.id)
    return TokenPair(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenPair)
def refresh(body: RefreshIn, db: Session = Depends(get_db)):
    pair = auth_service.rotate_refresh_token(db, body.refresh_token, settings.REFRESH_TOKEN_DAYS)
    if not pair:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid or expired refresh token")
    return TokenPair(access_token=pair[0], refresh_token=pair[1])


@router.post("/logout")
def logout(body: RefreshIn, db: Session = Depends(get_db),
           user: User = Depends(get_current_user)):
    auth_service.revoke_refresh_token(db, body.refresh_token)
    log_activity(db, "auth.logout", user_id=user.id)
    return {"ok": True}


@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordIn, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else "unknown"
    check_rate_limit(f"forgot:{ip}", limit=5, window_seconds=3600)
    # Always 200 with a generic message — no enumeration.
    auth_service.request_password_reset(db, body.email)
    return {"message": auth_service.GENERIC_FORGOT_MESSAGE}


@router.post("/reset-password")
def reset_password(body: ResetPasswordIn, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else "unknown"
    check_rate_limit(f"reset:{ip}", limit=10, window_seconds=3600)
    ok = auth_service.reset_password(db, body.token, body.new_password)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    return {"ok": True}


@router.post("/verify-email")
def verify_email(body: VerifyEmailIn, db: Session = Depends(get_db)):
    if body.token:
        ok = auth_service.verify_email(db, body.token)
        if not ok:
            raise HTTPException(status_code=400, detail="Invalid or expired verification token")
        return {"ok": True}
    if body.email and body.code:
        ok = auth_service.verify_email_code(db, body.email, body.code)
        if not ok:
            raise HTTPException(status_code=400, detail="Invalid or expired verification code")
        return {"ok": True}
    raise HTTPException(
        status_code=422,
        detail="Provide either 'token' or both 'email' and 'code'.",
    )


@router.post("/verify-email/request-code")
def request_verification_code(body: RequestVerificationCodeIn, request: Request,
                              db: Session = Depends(get_db)):
    ip = request.client.host if request.client else "unknown"
    email = body.email.lower().strip()
    # Max 3 code requests per 10 minutes per email (plus per-IP guard).
    check_rate_limit(f"verifycode:{email}", limit=3, window_seconds=600)
    check_rate_limit(f"verifycode:ip:{ip}", limit=10, window_seconds=600)
    auth_service.request_verification_code(db, email)
    # Generic: never reveal whether the account exists.
    return {"ok": True, "message": auth_service.GENERIC_CODE_MESSAGE}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserOut)
def update_me(body: MeUpdateIn, db: Session = Depends(get_db),
              user: User = Depends(get_current_user)):
    if body.name is not None:
        user.name = body.name
        db.commit()
        db.refresh(user)
    log_activity(db, "auth.profile_updated", user_id=user.id)
    return user


@router.post("/change-password")
def change_password(body: ChangePasswordIn, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    ok = auth_service.change_password(db, user, body.current_password, body.new_password)
    if not ok:
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    log_activity(db, "auth.password_changed", user_id=user.id)
    return {"ok": True}
