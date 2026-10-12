package com.gumroadautomation.data.api

import com.gumroadautomation.data.datastore.SessionManager
import com.gumroadautomation.util.GistUrlFetcher
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import okhttp3.Interceptor
import okhttp3.Response
import java.io.IOException
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Automatically recovers from tunnel URL rotations mid-session.
 *
 * When a request fails with a network error (tunnel died/rotated), this
 * interceptor refreshes the backend URL from the public gist. If the URL
 * changed, it rewrites the failed request to the new host and retries once.
 *
 * This means Anna never sees "offline" just because the tunnel URL changed —
 * the app heals itself transparently.
 */
@Singleton
class GistRefreshInterceptor @Inject constructor(
    private val sessionManager: SessionManager,
) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()
        try {
            return chain.proceed(request)
        } catch (e: IOException) {
            // Network failed — maybe the tunnel URL rotated. Try to refresh.
            val changed = runBlocking {
                try {
                    GistUrlFetcher.refresh(sessionManager)
                } catch (_: Exception) {
                    false
                }
            }
            if (!changed) throw e
            // URL changed — retry the same request against the new host.
            val newBase = runBlocking { sessionManager.baseUrl.first() }
                .trim().removeSuffix("/")
            val newUrl = request.url.newBuilder()
                .scheme(newBase.substringBefore("://"))
                .host(newBase.substringAfter("://").substringBefore("/"))
                .build()
            val newRequest = request.newBuilder().url(newUrl).build()
            return chain.proceed(newRequest)
        }
    }
}
