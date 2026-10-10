"""Dashboard aggregates — real numbers from the local DB, never mock data."""
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import get_db, resolve_accounts
from app.models.models import Customer, GumroadAccount, Product, Sale, Subscriber
from app.schemas.schemas import DashboardOut

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db),
              accounts: list[GumroadAccount] = Depends(resolve_accounts)):
    ids = [a.id for a in accounts]
    if not ids:
        return DashboardOut(revenue_cents=0, sales_count=0, customers_count=0,
                            subscribers_count=0, products_count=0, recent_sales=[])
    revenue = db.scalar(select(func.coalesce(func.sum(Sale.price_cents), 0)).where(
        Sale.account_id.in_(ids), Sale.refunded.is_(False))) or 0
    sales_count = db.scalar(select(func.count(Sale.id)).where(Sale.account_id.in_(ids))) or 0
    customers_count = db.scalar(select(func.count(Customer.id)).where(
        Customer.account_id.in_(ids))) or 0
    subscribers_count = db.scalar(select(func.count(Subscriber.id)).where(
        Subscriber.account_id.in_(ids))) or 0
    products_count = db.scalar(select(func.count(Product.id)).where(
        Product.account_id.in_(ids), Product.deleted.is_(False))) or 0
    recent = db.scalars(select(Sale).where(Sale.account_id.in_(ids))
                        .order_by(Sale.created_at.desc()).limit(10)).all()
    recent_sales = [{
        "id": s.id, "account_id": s.account_id, "email": s.email,
        "price_cents": s.price_cents, "currency": s.currency,
        "refunded": s.refunded, "created_at": s.created_at.isoformat() if s.created_at else None,
    } for s in recent]
    return DashboardOut(
        revenue_cents=revenue, sales_count=sales_count, customers_count=customers_count,
        subscribers_count=subscribers_count, products_count=products_count,
        recent_sales=recent_sales,
    )


# ------------------------------------------------------- analytics --------
from datetime import datetime, timedelta, timezone
from fastapi import Query


@router.get("/dashboard/analytics")
def dashboard_analytics(
    db: Session = Depends(get_db),
    accounts: list[GumroadAccount] = Depends(resolve_accounts),
    preset: str = Query(default="all", pattern="^(today|week|month|year|all)$"),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
):
    """Real sales analytics: gross/net/refunds, per-product revenue, daily trend.

    - preset: today | week | month | year | all (custom range via start/end_date)
    - start_date/end_date: ISO date (YYYY-MM-DD), overrides preset when both given
    - Account scoping comes from resolve_accounts (?account_id= or All Accounts).
    - All figures are in cents, computed from synced Sale rows — never mocked.
    """
    ids = [a.id for a in accounts]
    now = datetime.now(timezone.utc)

    # Resolve date range.
    start: datetime | None = None
    end: datetime | None = None
    if start_date and end_date:
        try:
            start = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
            end = (datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc)
                   + timedelta(days=1))
        except ValueError:
            start = end = None
    if start is None:
        if preset == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif preset == "week":
            start = now - timedelta(days=7)
        elif preset == "month":
            start = now - timedelta(days=30)
        elif preset == "year":
            start = now - timedelta(days=365)

    def scoped(q):
        q = q.where(Sale.account_id.in_(ids)) if ids else q.where(False)
        if start:
            q = q.where(Sale.created_at >= start)
        if end:
            q = q.where(Sale.created_at < end)
        return q

    if not ids:
        return {"gross_cents": 0, "refunded_cents": 0, "net_cents": 0,
                "sales_count": 0, "refunded_count": 0, "disputed_count": 0,
                "per_product": [], "daily_trend": [], "no_sale_products": []}

    gross = db.scalar(scoped(select(func.coalesce(func.sum(Sale.price_cents), 0)))) or 0
    refunded_cents = db.scalar(scoped(select(
        func.coalesce(func.sum(Sale.price_cents), 0)).where(Sale.refunded.is_(True)))) or 0
    sales_count = db.scalar(scoped(select(func.count(Sale.id)))) or 0
    refunded_count = db.scalar(scoped(select(func.count(Sale.id)).where(
        Sale.refunded.is_(True)))) or 0
    disputed_count = db.scalar(scoped(select(func.count(Sale.id)).where(
        Sale.disputed.is_(True)))) or 0
    net_cents = gross - refunded_cents

    # Per-product revenue (all products in scope, even with zero sales).
    products = db.scalars(select(Product).where(
        Product.account_id.in_(ids), Product.deleted.is_(False))).all()
    per_product = []
    for p in products:
        ps = scoped(select(func.coalesce(func.sum(Sale.price_cents), 0),
                           func.count(Sale.id)).where(Sale.product_id == p.id))
        row = db.execute(ps).one()
        per_product.append({
            "product_id": p.id, "name": p.name, "price_cents": p.price_cents,
            "permalink": p.permalink, "published": p.published,
            "gross_cents": row[0] or 0, "sales_count": row[1] or 0,
        })
    per_product.sort(key=lambda x: x["gross_cents"], reverse=True)
    no_sale_products = [p for p in per_product if p["sales_count"] == 0]

    # Daily trend (last 30 days or the selected range, capped at 90 buckets).
    trend_start = start or (now - timedelta(days=30))
    trend_end = end or now
    days = min((trend_end - trend_start).days + 1, 90)
    daily_trend = []
    for i in range(days):
        d0 = (trend_start + timedelta(days=i)).replace(
            hour=0, minute=0, second=0, microsecond=0)
        d1 = d0 + timedelta(days=1)
        rev = db.scalar(select(func.coalesce(func.sum(Sale.price_cents), 0)).where(
            Sale.account_id.in_(ids), Sale.created_at >= d0,
            Sale.created_at < d1)) or 0
        cnt = db.scalar(select(func.count(Sale.id)).where(
            Sale.account_id.in_(ids), Sale.created_at >= d0,
            Sale.created_at < d1)) or 0
        daily_trend.append({"date": d0.date().isoformat(),
                            "gross_cents": rev, "sales_count": cnt})

    return {
        "gross_cents": gross, "refunded_cents": refunded_cents, "net_cents": net_cents,
        "sales_count": sales_count, "refunded_count": refunded_count,
        "disputed_count": disputed_count,
        "per_product": per_product, "daily_trend": daily_trend,
        "no_sale_products": [{"product_id": p["product_id"], "name": p["name"]}
                             for p in no_sale_products],
        "range": {"preset": preset,
                  "start": start.date().isoformat() if start else None,
                  "end": (end - timedelta(days=1)).date().isoformat() if end else None},
    }


@router.get("/dashboard/account-comparison")
def account_comparison(
    db: Session = Depends(get_db),
    accounts: list[GumroadAccount] = Depends(resolve_accounts),
    preset: str = Query(default="month", pattern="^(today|week|month|year|all)$"),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
):
    """Side-by-side per-account stats over the same period — no double counting.

    Each account's figures come from its own Sale rows only; the "total" row is
    the sum of the per-account rows, so combining accounts never duplicates a
    transaction.
    """
    now = datetime.now(timezone.utc)
    start: datetime | None = None
    end: datetime | None = None
    if start_date and end_date:
        try:
            start = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
            end = (datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc)
                   + timedelta(days=1))
        except ValueError:
            start = end = None
    if start is None:
        if preset == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif preset == "week":
            start = now - timedelta(days=7)
        elif preset == "month":
            start = now - timedelta(days=30)
        elif preset == "year":
            start = now - timedelta(days=365)

    rows = []
    for a in accounts:
        q = select(Sale).where(Sale.account_id == a.id)
        if start:
            q = q.where(Sale.created_at >= start)
        if end:
            q = q.where(Sale.created_at < end)
        sales = db.scalars(q).all()
        gross = sum(s.price_cents for s in sales)
        refunded = sum(s.price_cents for s in sales if s.refunded)
        products = db.scalar(select(func.count(Product.id)).where(
            Product.account_id == a.id, Product.deleted.is_(False))) or 0
        rows.append({
            "account_id": a.id, "label": a.label, "email": a.gumroad_email,
            "status": a.status, "last_error": a.last_error,
            "last_sync_at": a.last_sync_at.isoformat() if a.last_sync_at else None,
            "gross_cents": gross, "refunded_cents": refunded,
            "net_cents": gross - refunded,
            "sales_count": len(sales),
            "refunded_count": sum(1 for s in sales if s.refunded),
            "disputed_count": sum(1 for s in sales if s.disputed),
            "products_count": products,
        })
    total = {
        "gross_cents": sum(r["gross_cents"] for r in rows),
        "refunded_cents": sum(r["refunded_cents"] for r in rows),
        "net_cents": sum(r["net_cents"] for r in rows),
        "sales_count": sum(r["sales_count"] for r in rows),
        "refunded_count": sum(r["refunded_count"] for r in rows),
        "disputed_count": sum(r["disputed_count"] for r in rows),
        "products_count": sum(r["products_count"] for r in rows),
    }
    return {"accounts": rows, "total": total,
            "range": {"preset": preset,
                      "start": start.date().isoformat() if start else None,
                      "end": (end - timedelta(days=1)).date().isoformat() if end else None}}
