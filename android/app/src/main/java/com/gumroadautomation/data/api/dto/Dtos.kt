package com.gumroadautomation.data.api.dto

import com.google.gson.annotations.SerializedName

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

data class SignupRequest(
    val email: String,
    val password: String,
    val name: String,
)

data class LoginRequest(
    val email: String,
    val password: String,
)

data class RefreshRequest(
    @SerializedName("refresh_token") val refreshToken: String,
)

data class LogoutRequest(
    @SerializedName("refresh_token") val refreshToken: String,
)

data class ForgotPasswordRequest(val email: String)

data class ResetPasswordRequest(
    val token: String,
    @SerializedName("new_password") val newPassword: String,
)

data class VerifyEmailRequest(
    val token: String? = null,
    val email: String? = null,
    val code: String? = null,
)

data class RequestCodeRequest(val email: String)

data class ChangePasswordRequest(
    @SerializedName("current_password") val currentPassword: String,
    @SerializedName("new_password") val newPassword: String,
)

data class UpdateProfileRequest(val name: String? = null)

data class AuthTokens(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("refresh_token") val refreshToken: String,
    @SerializedName("token_type") val tokenType: String = "bearer",
)

data class UserDto(
    val id: String,
    val email: String,
    val name: String?,
    @SerializedName("is_verified") val emailVerified: Boolean = false,
    @SerializedName("created_at") val createdAt: String? = null,
)

data class MessageResponse(val message: String)

// ---------------------------------------------------------------------------
// Gumroad accounts
// ---------------------------------------------------------------------------

data class GumroadAccountDto(
    val id: String,
    @SerializedName("user_id") val userId: String? = null,
    val name: String,
    /** connected | needs_reconnect | error | disabled */
    val status: String,
    @SerializedName("auth_mode") val authMode: String? = null,
    @SerializedName("gumroad_user_name") val gumroadUserName: String? = null,
    @SerializedName("last_sync_at") val lastSyncAt: String? = null,
    @SerializedName("token_last4") val tokenLast4: String? = null,
    @SerializedName("last_error") val lastError: String? = null,
    @SerializedName("last_error_at") val lastErrorAt: String? = null,
    @SerializedName("created_at") val createdAt: String? = null,
    @SerializedName("updated_at") val updatedAt: String? = null,
)

data class CreateAccountRequest(val name: String)

data class UpdateAccountRequest(val name: String? = null)

data class ConnectManualRequest(
    @SerializedName("access_token") val accessToken: String,
)

data class TestConnectionResponse(
    val ok: Boolean,
    @SerializedName("gumroad_user") val gumroadUser: String? = null,
    val error: String? = null,
)

data class SyncEnqueueResponse(
    @SerializedName("job_id") val jobId: String,
)

data class SyncHistoryDto(
    val id: String,
    @SerializedName("account_id") val accountId: String,
    @SerializedName("started_at") val startedAt: String? = null,
    @SerializedName("finished_at") val finishedAt: String? = null,
    val status: String,
    val detail: String? = null,
)

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

data class DashboardDto(
    @SerializedName("revenue_cents") val revenueCents: Long = 0,
    @SerializedName("sales_count") val salesCount: Int = 0,
    @SerializedName("customers_count") val customersCount: Int = 0,
    @SerializedName("subscribers_count") val subscribersCount: Int = 0,
    @SerializedName("products_count") val productsCount: Int = 0,
    @SerializedName("recent_sales") val recentSales: List<SaleDto> = emptyList(),
)

// ---------------------------------------------------------------------------
// Catalog entities
// ---------------------------------------------------------------------------

data class PageResponse<T>(
    val items: List<T>,
    val total: Int,
    val page: Int,
    @SerializedName("per_page") val perPage: Int,
)

data class ProductDto(
    val id: String,
    @SerializedName("account_id") val accountId: String? = null,
    @SerializedName("gumroad_id") val gumroadId: String? = null,
    val name: String,
    @SerializedName("price_cents") val priceCents: Long = 0,
    val currency: String? = null,
    val published: Boolean = true,
    @SerializedName("thumbnail_url") val thumbnailUrl: String? = null,
    @SerializedName("sales_count") val salesCount: Int? = null,
)

data class SaleDto(
    val id: String,
    @SerializedName("account_id") val accountId: String? = null,
    @SerializedName("gumroad_id") val gumroadId: String? = null,
    @SerializedName("product_id") val productId: String? = null,
    @SerializedName("product_name") val productName: String? = null,
    val email: String? = null,
    @SerializedName("amount_cents") val amountCents: Long = 0,
    val currency: String? = null,
    val refunded: Boolean = false,
    val shipped: Boolean = false,
    @SerializedName("is_subscription") val isSubscription: Boolean = false,
    @SerializedName("created_at") val createdAt: String? = null,
)

data class CustomerDto(
    val id: String,
    @SerializedName("account_id") val accountId: String? = null,
    val email: String,
    val name: String? = null,
    @SerializedName("first_purchase_at") val firstPurchaseAt: String? = null,
    @SerializedName("total_spent_cents") val totalSpentCents: Long = 0,
    @SerializedName("purchase_count") val purchaseCount: Int = 0,
)

data class SubscriberDto(
    val id: String,
    @SerializedName("account_id") val accountId: String? = null,
    val email: String,
    @SerializedName("product_name") val productName: String? = null,
    val status: String? = null,
    @SerializedName("created_at") val createdAt: String? = null,
)

data class LicenseDto(
    val id: String,
    @SerializedName("account_id") val accountId: String? = null,
    @SerializedName("license_key") val licenseKey: String? = null,
    @SerializedName("product_name") val productName: String? = null,
    val email: String? = null,
    val uses: Int? = null,
    @SerializedName("max_uses") val maxUses: Int? = null,
    val enabled: Boolean = true,
)

data class MembershipDto(
    val id: String,
    @SerializedName("account_id") val accountId: String? = null,
    val email: String,
    @SerializedName("product_name") val productName: String? = null,
    /** e.g. active | cancelled | ended */
    val status: String? = null,
    @SerializedName("current_period_end") val currentPeriodEnd: String? = null,
    @SerializedName("created_at") val createdAt: String? = null,
)

data class DryRunRequest(
    @SerializedName("dry_run") val dryRun: Boolean = true,
)

data class ActionResultDto(
    val success: Boolean,
    val message: String,
    @SerializedName("dry_run") val dryRun: Boolean = false,
)

// ---------------------------------------------------------------------------
// Automation
// ---------------------------------------------------------------------------

data class RuleConditionDto(
    val field: String,
    val operator: String,
    val value: String,
)

data class RuleActionDto(
    val type: String,
    val params: Map<String, String> = emptyMap(),
)

data class AutomationRuleDto(
    val id: String,
    @SerializedName("account_id") val accountId: String? = null,
    val name: String,
    val enabled: Boolean = true,
    val trigger: String,
    val conditions: List<RuleConditionDto> = emptyList(),
    val actions: List<RuleActionDto> = emptyList(),
    @SerializedName("dry_run") val dryRun: Boolean = true,
    @SerializedName("created_at") val createdAt: String? = null,
    @SerializedName("updated_at") val updatedAt: String? = null,
)

data class AutomationRuleRequest(
    @SerializedName("account_id") val accountId: String?,
    val name: String,
    val enabled: Boolean,
    val trigger: String,
    val conditions: List<RuleConditionDto>,
    val actions: List<RuleActionDto>,
    @SerializedName("dry_run") val dryRun: Boolean,
)

// ---------------------------------------------------------------------------
// Scheduler / jobs
// ---------------------------------------------------------------------------

data class JobDto(
    val id: String,
    @SerializedName("account_id") val accountId: String? = null,
    val name: String,
    @SerializedName("job_type") val jobType: String,
    /** one_time | recurring | daily | weekly */
    val schedule: String,
    val cron: String? = null,
    @SerializedName("next_run_at") val nextRunAt: String? = null,
    @SerializedName("last_run_at") val lastRunAt: String? = null,
    val status: String,
    @SerializedName("max_retries") val maxRetries: Int = 3,
)

data class JobRequest(
    @SerializedName("account_id") val accountId: String?,
    val name: String,
    @SerializedName("job_type") val jobType: String,
    val schedule: String,
    val cron: String? = null,
    @SerializedName("max_retries") val maxRetries: Int = 3,
)

data class JobExecutionDto(
    val id: String,
    @SerializedName("job_id") val jobId: String,
    @SerializedName("started_at") val startedAt: String? = null,
    @SerializedName("finished_at") val finishedAt: String? = null,
    val status: String,
    val result: String? = null,
    val error: String? = null,
)

// ---------------------------------------------------------------------------
// Notifications & logs
// ---------------------------------------------------------------------------

data class NotificationDto(
    val id: String,
    val title: String,
    val body: String? = null,
    val read: Boolean = false,
    @SerializedName("created_at") val createdAt: String? = null,
)

data class ActivityLogDto(
    val id: String,
    @SerializedName("account_id") val accountId: String? = null,
    val action: String,
    val details: String? = null,
    @SerializedName("created_at") val createdAt: String? = null,
)

data class ErrorLogDto(
    val id: String,
    @SerializedName("account_id") val accountId: String? = null,
    val message: String,
    @SerializedName("correlation_id") val correlationId: String? = null,
    @SerializedName("created_at") val createdAt: String? = null,
)
