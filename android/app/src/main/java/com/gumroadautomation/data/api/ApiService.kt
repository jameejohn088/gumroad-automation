package com.gumroadautomation.data.api

import com.gumroadautomation.data.api.dto.ActionResultDto
import com.gumroadautomation.data.api.dto.ActivityLogDto
import com.gumroadautomation.data.api.dto.AuthTokens
import com.gumroadautomation.data.api.dto.AutomationRuleDto
import com.gumroadautomation.data.api.dto.AutomationRuleRequest
import com.gumroadautomation.data.api.dto.ChangePasswordRequest
import com.gumroadautomation.data.api.dto.ConnectManualRequest
import com.gumroadautomation.data.api.dto.CreateAccountRequest
import com.gumroadautomation.data.api.dto.CustomerDto
import com.gumroadautomation.data.api.dto.DashboardDto
import com.gumroadautomation.data.api.dto.DryRunRequest
import com.gumroadautomation.data.api.dto.ErrorLogDto
import com.gumroadautomation.data.api.dto.ForgotPasswordRequest
import com.gumroadautomation.data.api.dto.GumroadAccountDto
import com.gumroadautomation.data.api.dto.JobDto
import com.gumroadautomation.data.api.dto.JobExecutionDto
import com.gumroadautomation.data.api.dto.JobRequest
import com.gumroadautomation.data.api.dto.LicenseDto
import com.gumroadautomation.data.api.dto.LoginRequest
import com.gumroadautomation.data.api.dto.LogoutRequest
import com.gumroadautomation.data.api.dto.MembershipDto
import com.gumroadautomation.data.api.dto.MessageResponse
import com.gumroadautomation.data.api.dto.NotificationDto
import com.gumroadautomation.data.api.dto.PageResponse
import com.gumroadautomation.data.api.dto.ProductDto
import com.gumroadautomation.data.api.dto.RefreshRequest
import com.gumroadautomation.data.api.dto.ResetPasswordRequest
import com.gumroadautomation.data.api.dto.SaleDto
import com.gumroadautomation.data.api.dto.SignupRequest
import com.gumroadautomation.data.api.dto.SubscriberDto
import com.gumroadautomation.data.api.dto.SyncEnqueueResponse
import com.gumroadautomation.data.api.dto.SyncHistoryDto
import com.gumroadautomation.data.api.dto.TestConnectionResponse
import com.gumroadautomation.data.api.dto.UpdateAccountRequest
import com.gumroadautomation.data.api.dto.UpdateProfileRequest
import com.gumroadautomation.data.api.dto.UserDto
import com.gumroadautomation.data.api.dto.VerifyEmailRequest
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

/**
 * Backend API contract (base path /api/v1).
 * Every call goes to OUR backend — the Gumroad token never leaves the server.
 */
interface ApiService {

    // -- Auth ----------------------------------------------------------------
    @POST("auth/signup")
    suspend fun signup(@Body body: SignupRequest): Response<UserDto>

    @POST("auth/login")
    suspend fun login(@Body body: LoginRequest): Response<AuthTokens>

    @POST("auth/refresh")
    suspend fun refresh(@Body body: RefreshRequest): Response<AuthTokens>

    @POST("auth/logout")
    suspend fun logout(@Body body: LogoutRequest): Response<MessageResponse>

    @POST("auth/forgot-password")
    suspend fun forgotPassword(@Body body: ForgotPasswordRequest): Response<MessageResponse>

    @POST("auth/reset-password")
    suspend fun resetPassword(@Body body: ResetPasswordRequest): Response<MessageResponse>

    @POST("auth/verify-email")
    suspend fun verifyEmail(@Body body: VerifyEmailRequest): Response<MessageResponse>

    @POST("auth/verify-email/request-code")
    suspend fun requestVerificationCode(@Body body: RequestCodeRequest): Response<MessageResponse>

    @GET("auth/me")
    suspend fun me(): Response<UserDto>

    @PATCH("auth/me")
    suspend fun updateMe(@Body body: UpdateProfileRequest): Response<UserDto>

    @POST("auth/change-password")
    suspend fun changePassword(@Body body: ChangePasswordRequest): Response<MessageResponse>

    // -- Gumroad accounts ----------------------------------------------------
    @GET("gumroad-accounts")
    suspend fun listAccounts(): Response<List<GumroadAccountDto>>

    @POST("gumroad-accounts")
    suspend fun createAccount(@Body body: CreateAccountRequest): Response<GumroadAccountDto>

    @GET("gumroad-accounts/{id}")
    suspend fun getAccount(@Path("id") id: String): Response<GumroadAccountDto>

    @PATCH("gumroad-accounts/{id}")
    suspend fun updateAccount(
        @Path("id") id: String,
        @Body body: UpdateAccountRequest,
    ): Response<GumroadAccountDto>

    @DELETE("gumroad-accounts/{id}")
    suspend fun deleteAccount(@Path("id") id: String): Response<MessageResponse>

    @POST("gumroad-accounts/{id}/connect-manual")
    suspend fun connectManual(
        @Path("id") id: String,
        @Body body: ConnectManualRequest,
    ): Response<GumroadAccountDto>

    @POST("gumroad-accounts/{id}/disconnect")
    suspend fun disconnect(@Path("id") id: String): Response<GumroadAccountDto>

    @POST("gumroad-accounts/{id}/reconnect")
    suspend fun reconnect(@Path("id") id: String): Response<GumroadAccountDto>

    @POST("gumroad-accounts/{id}/test-connection")
    suspend fun testConnection(@Path("id") id: String): Response<TestConnectionResponse>

    @POST("gumroad-accounts/{id}/enable")
    suspend fun enable(@Path("id") id: String): Response<GumroadAccountDto>

    @POST("gumroad-accounts/{id}/disable")
    suspend fun disable(@Path("id") id: String): Response<GumroadAccountDto>

    @POST("gumroad-accounts/{id}/sync")
    suspend fun syncAccount(@Path("id") id: String): Response<SyncEnqueueResponse>

    @GET("gumroad-accounts/{id}/sync-history")
    suspend fun syncHistory(@Path("id") id: String): Response<List<SyncHistoryDto>>

    // -- Dashboard ------------------------------------------------------------
    @GET("dashboard")
    suspend fun dashboard(@Query("account_id") accountId: String?): Response<DashboardDto>

    // -- Catalog ---------------------------------------------------------------
    @GET("products")
    suspend fun products(
        @Query("account_id") accountId: String?,
        @Query("q") q: String?,
        @Query("page") page: Int,
        @Query("per_page") perPage: Int,
    ): Response<PageResponse<ProductDto>>

    @GET("sales")
    suspend fun sales(
        @Query("account_id") accountId: String?,
        @Query("q") q: String?,
        @Query("page") page: Int,
        @Query("per_page") perPage: Int,
    ): Response<PageResponse<SaleDto>>

    @GET("customers")
    suspend fun customers(
        @Query("account_id") accountId: String?,
        @Query("q") q: String?,
        @Query("page") page: Int,
        @Query("per_page") perPage: Int,
    ): Response<PageResponse<CustomerDto>>

    @GET("subscribers")
    suspend fun subscribers(
        @Query("account_id") accountId: String?,
        @Query("q") q: String?,
        @Query("page") page: Int,
        @Query("per_page") perPage: Int,
    ): Response<PageResponse<SubscriberDto>>

    @GET("licenses")
    suspend fun licenses(
        @Query("account_id") accountId: String?,
        @Query("q") q: String?,
        @Query("page") page: Int,
        @Query("per_page") perPage: Int,
    ): Response<PageResponse<LicenseDto>>

    @GET("memberships")
    suspend fun memberships(
        @Query("account_id") accountId: String?,
        @Query("q") q: String?,
        @Query("page") page: Int,
        @Query("per_page") perPage: Int,
    ): Response<PageResponse<MembershipDto>>

    @POST("sales/{sale_id}/refund")
    suspend fun refundSale(
        @Path("sale_id") saleId: String,
        @Body body: DryRunRequest,
    ): Response<ActionResultDto>

    @POST("sales/{sale_id}/mark-shipped")
    suspend fun markShipped(
        @Path("sale_id") saleId: String,
        @Body body: DryRunRequest,
    ): Response<ActionResultDto>

    @POST("sales/{sale_id}/resend-receipt")
    suspend fun resendReceipt(
        @Path("sale_id") saleId: String,
        @Body body: DryRunRequest,
    ): Response<ActionResultDto>

    // -- Automation rules -------------------------------------------------------
    @GET("automation-rules")
    suspend fun listRules(@Query("account_id") accountId: String?): Response<List<AutomationRuleDto>>

    @POST("automation-rules")
    suspend fun createRule(@Body body: AutomationRuleRequest): Response<AutomationRuleDto>

    @GET("automation-rules/{id}")
    suspend fun getRule(@Path("id") id: String): Response<AutomationRuleDto>

    @PATCH("automation-rules/{id}")
    suspend fun updateRule(
        @Path("id") id: String,
        @Body body: AutomationRuleRequest,
    ): Response<AutomationRuleDto>

    @DELETE("automation-rules/{id}")
    suspend fun deleteRule(@Path("id") id: String): Response<MessageResponse>

    // -- Jobs -------------------------------------------------------------------
    @GET("jobs")
    suspend fun listJobs(@Query("account_id") accountId: String?): Response<List<JobDto>>

    @POST("jobs")
    suspend fun createJob(@Body body: JobRequest): Response<JobDto>

    @GET("jobs/{id}")
    suspend fun getJob(@Path("id") id: String): Response<JobDto>

    @PATCH("jobs/{id}")
    suspend fun updateJob(
        @Path("id") id: String,
        @Body body: JobRequest,
    ): Response<JobDto>

    @DELETE("jobs/{id}")
    suspend fun deleteJob(@Path("id") id: String): Response<MessageResponse>

    @POST("jobs/{id}/run-now")
    suspend fun runJob(@Path("id") id: String): Response<MessageResponse>

    @GET("jobs/{id}/executions")
    suspend fun jobExecutions(@Path("id") id: String): Response<List<JobExecutionDto>>

    @POST("jobs/executions/{exec_id}/retry")
    suspend fun retryExecution(
        @Path("exec_id") execId: String,
    ): Response<MessageResponse>

    // -- Notifications -----------------------------------------------------------
    @GET("notifications")
    suspend fun notifications(): Response<List<NotificationDto>>

    @POST("notifications/{id}/read")
    suspend fun markNotificationRead(@Path("id") id: String): Response<MessageResponse>

    @POST("notifications/read-all")
    suspend fun markAllNotificationsRead(): Response<MessageResponse>

    @GET("notifications/unread-count")
    suspend fun unreadCount(): Response<Map<String, Int>>

    // -- Logs ---------------------------------------------------------------------
    @GET("activity-logs")
    suspend fun activityLogs(
        @Query("account_id") accountId: String?,
        @Query("page") page: Int,
        @Query("per_page") perPage: Int,
    ): Response<PageResponse<ActivityLogDto>>

    @GET("error-logs")
    suspend fun errorLogs(
        @Query("account_id") accountId: String?,
        @Query("page") page: Int,
        @Query("per_page") perPage: Int,
    ): Response<PageResponse<ErrorLogDto>>
}
