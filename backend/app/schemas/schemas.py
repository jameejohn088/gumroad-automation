"""Pydantic v2 request/response schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

model_config = ConfigDict(from_attributes=True)


# ------------------------------------------------------- auth -------------

class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(default="", max_length=200)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshIn(BaseModel):
    refresh_token: str


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class VerifyEmailIn(BaseModel):
    # Either the legacy long token OR the (email, code) pair for 6-digit codes.
    token: str | None = None
    email: str | None = None
    code: str | None = None


class RequestVerificationCodeIn(BaseModel):
    email: EmailStr


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    model_config = model_config
    id: str
    email: str
    name: str
    is_verified: bool
    created_at: datetime


class MeUpdateIn(BaseModel):
    name: str | None = Field(default=None, max_length=200)


# ------------------------------------------------------- accounts ---------

class GumroadAccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    auth_mode: str = Field(default="manual", pattern="^(manual|oauth)$")


class GumroadAccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    settings: dict | None = None


class GumroadAccountOut(BaseModel):
    model_config = model_config
    id: str
    name: str
    status: str
    auth_mode: str
    gumroad_user_name: str | None
    last_sync_at: datetime | None
    token_last4: str | None = None
    last_error: str | None = None
    last_error_at: datetime | None = None
    created_at: datetime


class ConnectManualIn(BaseModel):
    access_token: str = Field(min_length=8)


class SyncOut(BaseModel):
    job_id: str
    status: str = "queued"


class SyncHistoryOut(BaseModel):
    model_config = model_config
    id: str
    sync_type: str
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    items_synced: int
    error: str | None


# ------------------------------------------------------- dashboard --------

class DashboardOut(BaseModel):
    revenue_cents: int
    sales_count: int
    customers_count: int
    subscribers_count: int
    products_count: int
    recent_sales: list[dict]


# ------------------------------------------------------- catalog ----------

class PageOut(BaseModel):
    items: list[dict]
    total: int
    page: int
    per_page: int


# ------------------------------------------------------- actions ----------

class DryRunIn(BaseModel):
    dry_run: bool = True
    confirm: bool = False  # must be true to actually execute when dry_run=false


class ActionResultOut(BaseModel):
    dry_run: bool
    executed: bool
    message: str
    detail: dict | None = None


# ------------------------------------------------------- automation -------

class ConditionIn(BaseModel):
    field: str
    operator: str = "eq"
    value: str | None = None


class ActionIn(BaseModel):
    action_type: str
    params: dict | None = None
    order: int = 0


class AutomationRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    account_id: str | None = None
    trigger: str
    conditions: list[ConditionIn] = []
    actions: list[ActionIn] = []
    enabled: bool = True
    dry_run: bool = True
    max_actions_per_hour: int = Field(default=10, ge=1, le=1000)


class AutomationRuleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    account_id: str | None = None
    trigger: str | None = None
    enabled: bool | None = None
    dry_run: bool | None = None
    max_actions_per_hour: int | None = Field(default=None, ge=1, le=1000)
    conditions: list[ConditionIn] | None = None
    actions: list[ActionIn] | None = None


class AutomationRuleOut(BaseModel):
    model_config = model_config
    id: str
    name: str
    account_id: str | None
    trigger: str
    enabled: bool
    dry_run: bool
    max_actions_per_hour: int
    conditions: list[dict] = []
    actions: list[dict] = []


# ------------------------------------------------------- jobs -------------

class JobCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    job_type: str = Field(pattern="^(once|interval|daily|weekly|sync|automation)$")
    account_id: str | None = None
    # schedule_config examples:
    #  once:     {"run_at": "2026-10-06T10:00:00+00:00"}
    #  interval: {"seconds": 3600}
    #  daily:    {"hour": 9, "minute": 30}
    #  weekly:   {"day_of_week": "mon", "hour": 9, "minute": 0}
    #  sync:     {"account_id": "...", "interval_seconds": 900}
    #  automation: {"rule_id": "...", "cron": "0 9 * * *"}
    schedule_config: dict = {}
    payload: dict | None = None
    max_retries: int = Field(default=3, ge=0, le=10)


class JobUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    status: str | None = Field(default=None, pattern="^(active|paused)$")
    schedule_config: dict | None = None
    max_retries: int | None = Field(default=None, ge=0, le=10)


class JobOut(BaseModel):
    model_config = model_config
    id: str
    name: str
    job_type: str
    account_id: str | None
    schedule_config: dict | None
    status: str
    next_run_at: datetime | None
    last_run_at: datetime | None
    last_error: str | None
    retry_count: int
    max_retries: int


class JobExecutionOut(BaseModel):
    model_config = model_config
    id: str
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    attempt: int
    error: str | None
    result: dict | None


# ------------------------------------------------------- notifications ----

class NotificationOut(BaseModel):
    model_config = model_config
    id: str
    account_id: str | None
    title: str
    body: str | None
    kind: str
    read_at: datetime | None
    created_at: datetime


# ------------------------------------------------------- logs -------------

class ActivityLogOut(BaseModel):
    model_config = model_config
    id: str
    account_id: str | None
    action: str
    detail: dict | None
    created_at: datetime


class ErrorLogOut(BaseModel):
    model_config = model_config
    id: str
    correlation_id: str | None
    path: str | None
    message: str
    created_at: datetime


# ------------------------------------------------------- misc -------------

class HealthOut(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"


class ErrorOut(BaseModel):
    detail: str
    correlation_id: str | None = None
