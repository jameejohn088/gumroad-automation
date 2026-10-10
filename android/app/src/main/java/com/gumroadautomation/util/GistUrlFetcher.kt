package com.gumroadautomation.util

import com.gumroadautomation.data.datastore.SessionManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.withContext
import java.net.HttpURLConnection
import java.net.URL

/**
 * Fetches the current backend URL from the public gist (kept fresh by the
 * server watchdog) and updates [SessionManager] when it changed.
 *
 * Used on the login screen AND on every logged-in app launch, so Anna never
 * has to paste the rotating tunnel URL manually.
 *
 * Returns true when the stored URL was changed.
 */
object GistUrlFetcher {
    suspend fun refresh(sessionManager: SessionManager): Boolean {
        val gistUrl = Constants.GIST_RAW_URL
        if (gistUrl.isBlank()) return false
        return try {
            val raw = withContext(Dispatchers.IO) {
                val conn = URL(gistUrl).openConnection() as HttpURLConnection
                conn.connectTimeout = 10000
                conn.readTimeout = 10000
                conn.requestMethod = "GET"
                try {
                    conn.inputStream.bufferedReader().readText().trim()
                } finally {
                    conn.disconnect()
                }
            }
            if (!raw.startsWith("https://")) return false
            val apiUrl = "$raw/api/v1"
            val current = sessionManager.baseUrl.first()
            if (current != apiUrl) {
                sessionManager.setBaseUrl(apiUrl)
                true
            } else false
        } catch (_: Exception) {
            // Keep the existing URL — gist unreachable or tunnel mid-rotation.
            false
        }
    }
}
