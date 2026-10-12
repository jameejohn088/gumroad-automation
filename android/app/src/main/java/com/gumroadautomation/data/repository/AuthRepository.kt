package com.gumroadautomation.data.repository

import com.gumroadautomation.data.api.ApiProvider
import com.gumroadautomation.data.api.AuthEventBus
import com.gumroadautomation.data.api.dto.ChangePasswordRequest
import com.gumroadautomation.data.api.dto.ForgotPasswordRequest
import com.gumroadautomation.data.api.dto.LoginRequest
import com.gumroadautomation.data.api.dto.LogoutRequest
import com.gumroadautomation.data.api.dto.RefreshRequest
import com.gumroadautomation.data.api.dto.ResetPasswordRequest
import com.gumroadautomation.data.api.dto.SignupRequest
import com.gumroadautomation.data.api.dto.UpdateProfileRequest
import com.gumroadautomation.data.api.dto.UserDto
import com.gumroadautomation.data.api.dto.RequestCodeRequest
import com.gumroadautomation.data.api.dto.VerifyEmailRequest
import com.gumroadautomation.data.datastore.SecureTokenStore
import com.gumroadautomation.data.datastore.SessionManager
import com.gumroadautomation.data.db.AppDatabase
import com.gumroadautomation.util.ApiResult
import com.gumroadautomation.worker.SyncScheduler
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.flowOn
import java.io.IOException
import javax.inject.Inject
import javax.inject.Singleton

/**
 * App-user authentication (separate from Gumroad OAuth).
 * Tokens live in [SecureTokenStore]; a failed refresh wipes them and the UI
 * observes [AuthEventBus.unauthorized] to return to login.
 */
@Singleton
class AuthRepository @Inject constructor(
    private val apiProvider: ApiProvider,
    private val tokenStore: SecureTokenStore,
    private val sessionManager: SessionManager,
    private val database: AppDatabase,
    private val syncScheduler: SyncScheduler,
    private val authEventBus: AuthEventBus,
) {
    val isLoggedIn: Boolean get() = tokenStore.hasTokens()
    val unauthorizedEvents = authEventBus.unauthorized

    fun login(email: String, password: String): Flow<ApiResult<Unit>> = flow {
        emit(ApiResult.Loading)
        try {
            val res = apiProvider.service().login(LoginRequest(email.trim(), password))
            if (res.isSuccessful) {
                val tokens = res.body()!!
                tokenStore.saveTokens(tokens.accessToken, tokens.refreshToken)
                syncScheduler.schedule()
                emit(ApiResult.Success(Unit))
            } else {
                // No user enumeration: backend returns a generic message for bad credentials.
                emit(ApiResult.Error(parseError(res)))
            }
        } catch (e: IOException) {
            emit(ApiResult.Error(networkError(e)))
        } catch (_: Exception) {
            emit(ApiResult.Error("Login failed. Please try again."))
        }
    }.flowOn(Dispatchers.IO)

    fun signup(name: String, email: String, password: String): Flow<ApiResult<UserDto>> = flow {
        emit(ApiResult.Loading)
        try {
            val res = apiProvider.service()
                .signup(SignupRequest(email.trim(), password, name.trim()))
            if (res.isSuccessful) emit(ApiResult.Success(res.body()!!))
            else emit(ApiResult.Error(parseError(res)))
        } catch (e: IOException) {
            emit(ApiResult.Error(networkError(e)))
        } catch (_: Exception) {
            emit(ApiResult.Error("Sign up failed. Please try again."))
        }
    }.flowOn(Dispatchers.IO)

    /** Secure logout: revoke server-side, wipe tokens, cancel sync, clear local cache. */
    suspend fun logout() {
        try {
            tokenStore.getRefreshToken()?.let {
                apiProvider.service().logout(LogoutRequest(it))
            }
        } catch (_: Exception) {
            // Best effort — local wipe happens regardless.
        }
        tokenStore.clear()
        sessionManager.setSelectedAccountId(null)
        syncScheduler.cancel()
        try {
            database.clearAllTables()
        } catch (_: Exception) {
        }
    }

    fun forgotPassword(email: String): Flow<ApiResult<String>> = flow {
        emit(ApiResult.Loading)
        try {
            // Generic response by design — never reveals whether the email exists.
            val res = apiProvider.service().forgotPassword(ForgotPasswordRequest(email.trim()))
            if (res.isSuccessful) emit(ApiResult.Success(res.body()?.message.orEmpty()))
            else emit(ApiResult.Error(parseError(res)))
        } catch (e: IOException) {
            emit(ApiResult.Error(networkError(e)))
        } catch (_: Exception) {
            emit(ApiResult.Error("Request failed. Please try again."))
        }
    }.flowOn(Dispatchers.IO)

    fun resetPassword(token: String, newPassword: String): Flow<ApiResult<String>> = flow {
        emit(ApiResult.Loading)
        try {
            val res = apiProvider.service()
                .resetPassword(ResetPasswordRequest(token.trim(), newPassword))
            if (res.isSuccessful) emit(ApiResult.Success(res.body()?.message.orEmpty()))
            else emit(ApiResult.Error(parseError(res)))
        } catch (e: IOException) {
            emit(ApiResult.Error(networkError(e)))
        } catch (_: Exception) {
            emit(ApiResult.Error("Request failed. Please try again."))
        }
    }.flowOn(Dispatchers.IO)

    fun verifyEmail(token: String): Flow<ApiResult<String>> = flow {
        emit(ApiResult.Loading)
        try {
            val res = apiProvider.service().verifyEmail(VerifyEmailRequest(token = token.trim()))
            if (res.isSuccessful) emit(ApiResult.Success(res.body()?.message.orEmpty()))
            else emit(ApiResult.Error(parseError(res)))
        } catch (e: IOException) {
            emit(ApiResult.Error(networkError(e)))
        } catch (_: Exception) {
            emit(ApiResult.Error("Verification failed. Please try again."))
        }
    }.flowOn(Dispatchers.IO)

    fun requestVerificationCode(email: String): Flow<ApiResult<String>> = flow {
        emit(ApiResult.Loading)
        try {
            val res = apiProvider.service().requestVerificationCode(RequestCodeRequest(email.trim()))
            if (res.isSuccessful) emit(ApiResult.Success("Code sent! Check your email."))
            else emit(ApiResult.Error(parseError(res)))
        } catch (e: IOException) {
            emit(ApiResult.Error(networkError(e)))
        } catch (_: Exception) {
            emit(ApiResult.Error("Could not send code. Please try again."))
        }
    }.flowOn(Dispatchers.IO)

    fun verifyEmailCode(email: String, code: String): Flow<ApiResult<String>> = flow {
        emit(ApiResult.Loading)
        try {
            val res = apiProvider.service().verifyEmail(
                VerifyEmailRequest(email = email.trim(), code = code.trim()))
            if (res.isSuccessful) emit(ApiResult.Success("Email verified!"))
            else emit(ApiResult.Error(parseError(res)))
        } catch (e: IOException) {
            emit(ApiResult.Error(networkError(e)))
        } catch (_: Exception) {
            emit(ApiResult.Error("Verification failed. Please try again."))
        }
    }.flowOn(Dispatchers.IO)

    fun me(): Flow<ApiResult<UserDto>> = flow {
        emit(ApiResult.Loading)
        try {
            val res = apiProvider.service().me()
            if (res.isSuccessful) emit(ApiResult.Success(res.body()!!))
            else emit(ApiResult.Error(parseError(res)))
        } catch (e: IOException) {
            emit(ApiResult.Error(networkError(e)))
        } catch (_: Exception) {
            emit(ApiResult.Error("Could not load profile."))
        }
    }.flowOn(Dispatchers.IO)

    fun updateProfile(name: String): Flow<ApiResult<UserDto>> = flow {
        emit(ApiResult.Loading)
        try {
            val res = apiProvider.service().updateMe(UpdateProfileRequest(name.trim().ifEmpty { null }))
            if (res.isSuccessful) emit(ApiResult.Success(res.body()!!))
            else emit(ApiResult.Error(parseError(res)))
        } catch (e: IOException) {
            emit(ApiResult.Error(networkError(e)))
        } catch (_: Exception) {
            emit(ApiResult.Error("Could not update profile."))
        }
    }.flowOn(Dispatchers.IO)

    fun changePassword(current: String, new: String): Flow<ApiResult<String>> = flow {
        emit(ApiResult.Loading)
        try {
            val res = apiProvider.service().changePassword(ChangePasswordRequest(current, new))
            if (res.isSuccessful) emit(ApiResult.Success(res.body()?.message.orEmpty()))
            else emit(ApiResult.Error(parseError(res)))
        } catch (e: IOException) {
            emit(ApiResult.Error(networkError(e)))
        } catch (_: Exception) {
            emit(ApiResult.Error("Could not change password."))
        }
    }.flowOn(Dispatchers.IO)

    suspend fun manualRefresh(): Boolean {
        val refreshToken = tokenStore.getRefreshToken() ?: return false
        return try {
            val res = apiProvider.service().refresh(RefreshRequest(refreshToken))
            if (res.isSuccessful) {
                val tokens = res.body()!!
                tokenStore.saveTokens(tokens.accessToken, tokens.refreshToken)
                true
            } else {
                false
            }
        } catch (_: Exception) {
            false
        }
    }
}
