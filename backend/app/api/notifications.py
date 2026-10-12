"""Notifications, activity logs, error logs (all user-scoped)."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.models import ActivityLog, ErrorLog, Notification, User
from app.schemas.schemas import ActivityLogOut, ErrorLogOut, NotificationOut, PageOut

router = APIRouter(tags=["notifications", "logs"])


@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(db: Session = Depends(get_db),
                       user: User = Depends(get_current_user),
                       unread_only: bool = Query(default=False),
                       limit: int = Query(default=50, ge=1, le=200)):
    q = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        q = q.where(Notification.read_at.is_(None))
    rows = db.scalars(q.order_by(Notification.created_at.desc()).limit(limit)).all()
    return rows


@router.post("/notifications/read-all")
def mark_all_read(db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    """Mark all of the user's notifications as read."""
    from app.core.security import utcnow
    now = utcnow()
    rows = db.scalars(select(Notification).where(
        Notification.user_id == user.id, Notification.read_at.is_(None))).all()
    for n in rows:
        n.read_at = now
    db.commit()
    return {"ok": True, "marked": len(rows)}


@router.post("/notifications/{notification_id}/read")
def mark_read(notification_id: str, db: Session = Depends(get_db),
              user: User = Depends(get_current_user)):
    n = db.get(Notification, notification_id)
    if not n or n.user_id != user.id:
        raise HTTPException(status_code=404, detail="Notification not found")
    from app.core.security import utcnow
    n.read_at = utcnow()
    db.commit()
    return {"ok": True}


@router.get("/notifications/unread-count")
def unread_count(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    n = db.scalar(select(func.count(Notification.id)).where(
        Notification.user_id == user.id, Notification.read_at.is_(None))) or 0
    return {"unread": n}


@router.get("/activity-logs", response_model=PageOut)
def activity_logs(db: Session = Depends(get_db),
                  user: User = Depends(get_current_user),
                  account_id: str | None = Query(default=None),
                  page: int = Query(default=1, ge=1),
                  per_page: int = Query(default=50, ge=1, le=500)):
    q = select(ActivityLog).where(ActivityLog.user_id == user.id)
    if account_id:
        q = q.where(ActivityLog.account_id == account_id)
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = db.scalars(q.order_by(ActivityLog.created_at.desc())
                      .offset((page - 1) * per_page).limit(per_page)).all()
    return PageOut(
        items=[ActivityLogOut.model_validate(r).model_dump(mode="json") for r in rows],
        total=total, page=page, per_page=per_page,
    )


@router.get("/error-logs", response_model=PageOut)
def error_logs(db: Session = Depends(get_db),
               user: User = Depends(get_current_user),
               account_id: str | None = Query(default=None),
               page: int = Query(default=1, ge=1),
               per_page: int = Query(default=50, ge=1, le=500)):
    q = select(ErrorLog).where(ErrorLog.user_id == user.id)
    if account_id:
        q = q.where(ErrorLog.account_id == account_id)
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = db.scalars(q.order_by(ErrorLog.created_at.desc())
                      .offset((page - 1) * per_page).limit(per_page)).all()
    return PageOut(
        items=[ErrorLogOut.model_validate(r).model_dump(mode="json") for r in rows],
        total=total, page=page, per_page=per_page,
    )
