package com.gumroadautomation.data.api

import com.gumroadautomation.data.api.dto.RefreshRequest
import com.gumroadautomation.data.datastore.SecureTokenStore
import com.gumroadautomation.data.datastore.SessionManager
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import okhttp3.Authenticator
import okhttp3.Request
import okhttp3.Response
import okhttp3.Route
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import javax.inject.Inject
import javax.inject.Singleton

/**
 * OkHttp [Authenticator] that transparently refreshes the short-lived access token
 * when the backend answers 401.
 *
 * - Runs at most once per request chain (responseCount guard) to avoid retry loops.
 * - Uses a dedicated Retrofit instance WITHOUT this authenticator to avoid recursion.
 * - If refresh fails (refresh token expired/revoked), tokens are wiped and an
 *   unauthorized event is emitted so the UI returns to the login screen.
 */
@Singleton
class TokenAuthenticator @Inject constructor(
    private val tokenStore: SecureTokenStore,
    private val sessionManager: SessionManager,
    private val authEventBus: AuthEventBus,
) : Authenticator {

    override fun authenticate(route: Route?, response: Response): Request? {
        if (responseCount(response) >= 2) return null // already retried once

        val newAccessToken: String? = runBlocking {
            tryRefresh()
        } ?: run {
            // Refresh failed: hard logout.
            tokenStore.clear()
            authEventBus.emitUnauthorized()
            return null
        }

        return response.request.newBuilder()
            .header("Authorization", "Bearer $newAccessToken")
            .build()
    }

    private suspend fun tryRefresh(): String? {
        val refreshToken = tokenStore.getRefreshToken() ?: return null
        return try {
            val baseUrl = sessionManager.baseUrl.first()
            // Explicit timeouts: this runs inside runBlocking on an OkHttp
            // thread, so a hung refresh must never block it indefinitely.
            val refreshClient = okhttp3.OkHttpClient.Builder()
                .connectTimeout(10, java.util.concurrent.TimeUnit.SECONDS)
                .readTimeout(15, java.util.concurrent.TimeUnit.SECONDS)
                .writeTimeout(15, java.util.concurrent.TimeUnit.SECONDS)
                .callTimeout(30, java.util.concurrent.TimeUnit.SECONDS)
                .build()
            val retrofit = Retrofit.Builder()
                .baseUrl(baseUrl.trimEnd('/') + "/")
                .client(refreshClient)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
            val api = retrofit.create(ApiService::class.java)
            val res = api.refresh(RefreshRequest(refreshToken))
            if (res.isSuccessful) {
                val tokens = res.body() ?: return null
                tokenStore.saveTokens(tokens.accessToken, tokens.refreshToken)
                tokens.accessToken
            } else {
                null
            }
        } catch (_: Exception) {
            null
        }
    }

    private fun responseCount(response: Response): Int {
        var result = 1
        var prior = response.priorResponse
        while (prior != null) {
            result++
            prior = prior.priorResponse
        }
        return result
    }
}
