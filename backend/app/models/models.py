"""SQLAlchemy 2 models. UUID PKs (string), created_at/updated_at everywhere,
FK cascades, UNIQUE(account_id, gumroad_id) on synced entities,
UNIQUE(account_id, email) on customers, indexes on (account_id, created_at)
and (status, next_run_at). SQLite + PostgreSQL compatible."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    TypeDecorator,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class AwareDateTime(TypeDecorator):
    """DateTime(timezone=True) that always returns tz-aware values.

    SQLite drops tzinfo on storage; this re-attaches UTC on load so
    comparisons never mix naive and aware datetimes. Works on PostgreSQL too.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


# Shorthand used for every timestamp column below.
DT = AwareDateTime(timezone=True)


def _uuid() -> str:
    return str(uuid.uuid4())


def _now():
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DT, default=_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DT, default=_now, onupdate=_now, nullable=False
    )


class CreatedMixin:
    created_at: Mapped[datetime] = mapped_column(
        DT, default=_now, nullable=False
    )


# ---------------------------------------------------------------- auth ----

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(String(200), default="")
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DT, nullable=True)

    gumroad_accounts: Mapped[list["GumroadAccount"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class RefreshToken(Base, CreatedMixin):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DT, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DT, nullable=True)
    replaced_by: Mapped[str | None] = mapped_column(String(36), nullable=True)


class PasswordResetToken(Base, CreatedMixin):
    __tablename__ = "password_reset_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DT, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DT, nullable=True)


class EmailVerificationToken(Base, CreatedMixin):
    __tablename__ = "email_verification_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DT, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DT, nullable=True)


class EmailVerificationCode(Base, CreatedMixin):
    """Short 6-digit numeric codes for email verification (10-min expiry).

    Only the SHA-256 hash is stored. Previous unused codes are invalidated
    when a new one is issued; attempts are capped to slow brute force.
    """
    __tablename__ = "email_verification_codes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DT, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DT, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)



# ------------------------------------------------------- gumroad ----------

class GumroadAccount(Base, TimestampMixin):
    __tablename__ = "gumroad_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # connected | needs_reconnect | error | disabled
    status: Mapped[str] = mapped_column(String(32), default="connected", nullable=False, index=True)
    auth_mode: Mapped[str] = mapped_column(String(16), default="manual", nullable=False)  # oauth|manual
    gumroad_user_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    gumroad_user_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DT, nullable=True)
    # Last Gumroad API error surfaced on the account (status + message for the dashboard).
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_error_at: Mapped[datetime | None] = mapped_column(DT, nullable=True)
    settings: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    user: Mapped["User"] = relationship(back_populates="gumroad_accounts")
    credential: Mapped["GumroadCredential | None"] = relationship(
        back_populates="account", cascade="all, delete-orphan", uselist=False
    )

    __table_args__ = (Index("ix_accounts_user_created", "user_id", "created_at"),)


class GumroadCredential(Base, TimestampMixin):
    __tablename__ = "gumroad_credentials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("gumroad_accounts.id", ondelete="CASCADE"),
        nullable=False, unique=True,
    )
    encrypted_token: Mapped[str] = mapped_column(Text, nullable=False)
    key_version: Mapped[int] = mapped_column(Integer, nullable=False)
    token_last4: Mapped[str] = mapped_column(String(8), default="****")

    account: Mapped["GumroadAccount"] = relationship(back_populates="credential")


# ------------------------------------------------------- catalog ----------

class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("gumroad_accounts.id", ondelete="CASCADE"), nullable=False
    )
    gumroad_id: Mapped[str] = mapped_column(String(200), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    price_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="usd", nullable=False)
    published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_subscription: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    subscription_duration: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_tiered_membership: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sales_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sales_usd_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    short_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        UniqueConstraint("account_id", "gumroad_id", name="uq_products_account_gumroad"),
        Index("ix_products_account_created", "account_id", "created_at"),
    )


class Variant(Base, TimestampMixin):
    __tablename__ = "variants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("gumroad_accounts.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    gumroad_id: Mapped[str] = mapped_column(String(200), nullable=False)
    category_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    price_difference_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        UniqueConstraint("account_id", "gumroad_id", name="uq_variants_account_gumroad"),
        Index("ix_variants_account_created", "account_id", "created_at"),
    )


class OfferCode(Base, TimestampMixin):
    __tablename__ = "offer_codes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("gumroad_accounts.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    gumroad_id: Mapped[str] = mapped_column(String(200), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    code: Mapped[str | None] = mapped_column(String(200), nullable=True)
    max_purchase_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        UniqueConstraint("account_id", "gumroad_id", name="uq_offercodes_account_gumroad"),
        Index("ix_offercodes_account_created", "account_id", "created_at"),
    )


class Sale(Base, TimestampMixin):
    __tablename__ = "sales"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("gumroad_accounts.id", ondelete="CASCADE"), nullable=False
    )
    gumroad_id: Mapped[str] = mapped_column(String(200), nullable=False)
    product_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True
    )
    email: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    price_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="usd", nullable=False)
    refunded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    disputed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    chargebacked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_subscription: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    license_key: Mapped[str | None] = mapped_column(String(200), nullable=True)
    gumroad_created_at: Mapped[datetime | None] = mapped_column(DT, nullable=True)
    raw: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        UniqueConstraint("account_id", "gumroad_id", name="uq_sales_account_gumroad"),
        Index("ix_sales_account_created", "account_id", "created_at"),
    )


class Customer(Base, TimestampMixin):
    """Derived from sales, deduplicated by email per account."""

    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("gumroad_accounts.id", ondelete="CASCADE"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    first_purchase_at: Mapped[datetime | None] = mapped_column(DT, nullable=True)
    total_spent_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    purchase_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        UniqueConstraint("account_id", "email", name="uq_customers_account_email"),
        Index("ix_customers_account_created", "account_id", "created_at"),
    )


class Subscriber(Base, TimestampMixin):
    __tablename__ = "subscribers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("gumroad_accounts.id", ondelete="CASCADE"), nullable=False
    )
    gumroad_id: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    product_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    gumroad_created_at: Mapped[datetime | None] = mapped_column(DT, nullable=True)
    raw: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        UniqueConstraint("account_id", "gumroad_id", name="uq_subscribers_account_gumroad"),
        Index("ix_subscribers_account_created", "account_id", "created_at"),
    )


class License(Base, TimestampMixin):
    """Derived from sales that carry a license_key (no license-list endpoint exists)."""

    __tablename__ = "licenses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("gumroad_accounts.id", ondelete="CASCADE"), nullable=False
    )
    key: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    product_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True
    )
    uses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    disabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    raw: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        UniqueConstraint("account_id", "key", name="uq_licenses_account_key"),
        Index("ix_licenses_account_created", "account_id", "created_at"),
    )


# ------------------------------------------------- buyer licenses -------

class LicenseGrant(Base, TimestampMixin):
    """Buyer-facing license verification grants.

    One row per verified Gumroad license key. The raw key is NEVER stored in
    plaintext: only its SHA-256 (for lookup) and an AES-GCM ciphertext (for
    silent re-verification) are kept. No Gumroad secrets live here — the
    seller's OAuth token stays in gumroad_credentials.
    Status: active | invalid | refunded | revoked | disabled.
    """

    __tablename__ = "license_grants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    product_permalink: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    license_key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    license_key_enc: Mapped[str] = mapped_column(Text, nullable=False)
    key_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False, index=True)
    gumroad_purchase_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    product_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    buyer_email_masked: Mapped[str | None] = mapped_column(String(320), nullable=True)
    uses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_verified_at: Mapped[datetime | None] = mapped_column(DT, nullable=True)


# ------------------------------------------------------- webhooks ---------

class WebhookSubscription(Base, TimestampMixin):
    __tablename__ = "webhook_subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("gumroad_accounts.id", ondelete="CASCADE"), nullable=False
    )
    gumroad_id: Mapped[str] = mapped_column(String(200), nullable=False)
    resource_name: Mapped[str] = mapped_column(String(100), nullable=False)
    webhook_url: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        UniqueConstraint("account_id", "gumroad_id", name="uq_websub_account_gumroad"),
        Index("ix_websub_account_created", "account_id", "created_at"),
    )


class WebhookEvent(Base, CreatedMixin):
    __tablename__ = "webhook_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("gumroad_accounts.id", ondelete="CASCADE"), nullable=False
    )
    event_id: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)  # dedupe key
    resource_name: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DT, nullable=True)

    __table_args__ = (Index("ix_webevent_account_created", "account_id", "created_at"),)


# ------------------------------------------------------- automation -------

class AutomationRule(Base, TimestampMixin):
    __tablename__ = "automation_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("gumroad_accounts.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    trigger: Mapped[str] = mapped_column(String(64), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    dry_run: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    max_actions_per_hour: Mapped[int] = mapped_column(Integer, default=10, nullable=False)

    conditions: Mapped[list["AutomationCondition"]] = relationship(
        back_populates="rule", cascade="all, delete-orphan"
    )
    actions: Mapped[list["AutomationAction"]] = relationship(
        back_populates="rule", cascade="all, delete-orphan"
    )


class AutomationCondition(Base, CreatedMixin):
    __tablename__ = "automation_conditions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    rule_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("automation_rules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    field: Mapped[str] = mapped_column(String(64), nullable=False)
    operator: Mapped[str] = mapped_column(String(16), nullable=False, default="eq")
    value: Mapped[str | None] = mapped_column(Text, nullable=True)

    rule: Mapped["AutomationRule"] = relationship(back_populates="conditions")


class AutomationAction(Base, CreatedMixin):
    __tablename__ = "automation_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    rule_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("automation_rules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    rule: Mapped["AutomationRule"] = relationship(back_populates="actions")


class AutomationExecution(Base, CreatedMixin):
    __tablename__ = "automation_executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    rule_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("automation_rules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(300), unique=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    event_id: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="completed", nullable=False)
    steps: Mapped[list | None] = mapped_column(JSON, nullable=True)


# ------------------------------------------------------- scheduler --------

class ScheduledJob(Base, TimestampMixin):
    __tablename__ = "scheduled_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("gumroad_accounts.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    job_type: Mapped[str] = mapped_column(String(32), nullable=False)  # once|interval|daily|weekly|sync|automation
    schedule_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, index=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DT, nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DT, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    __table_args__ = (Index("ix_jobs_status_next", "status", "next_run_at"),)


class JobExecution(Base, CreatedMixin):
    __tablename__ = "job_executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("scheduled_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # running|success|failed|dead
    started_at: Mapped[datetime | None] = mapped_column(DT, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DT, nullable=True)
    attempt: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class SyncHistory(Base, CreatedMixin):
    __tablename__ = "sync_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("gumroad_accounts.id", ondelete="CASCADE"), nullable=False
    )
    sync_type: Mapped[str] = mapped_column(String(32), nullable=False)  # products|sales|subscribers|full
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # running|success|failed
    started_at: Mapped[datetime | None] = mapped_column(DT, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DT, nullable=True)
    items_synced: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_synchist_account_created", "account_id", "created_at"),)


# ------------------------------------------------------- misc -------------

class Notification(Base, CreatedMixin):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("gumroad_accounts.id", ondelete="CASCADE"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    kind: Mapped[str] = mapped_column(String(64), default="info", nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DT, nullable=True)


class ActivityLog(Base, CreatedMixin):
    __tablename__ = "activity_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    account_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("gumroad_accounts.id", ondelete="CASCADE"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(200), nullable=False)
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class ErrorLog(Base, CreatedMixin):
    __tablename__ = "error_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    account_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)


class AppSetting(Base, TimestampMixin):
    __tablename__ = "app_settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String(200), nullable=False)
    value: Mapped[dict | str | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (UniqueConstraint("user_id", "key", name="uq_appsettings_user_key"),)
