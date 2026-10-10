package com.gumroadautomation.ui.screens.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.gumroadautomation.data.datastore.SessionManager
import com.gumroadautomation.data.repository.AuthRepository
import com.gumroadautomation.util.ApiResult
import com.gumroadautomation.util.Constants
import com.gumroadautomation.util.GistUrlFetcher
import com.gumroadautomation.util.Validators
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import javax.inject.Inject

/** Shared ViewModel for all auth screens (login/signup/forgot/reset/verify). */
@HiltViewModel
class AuthViewModel @Inject constructor(
    private val authRepository: AuthRepository,
    private val sessionManager: SessionManager,
) : ViewModel() {

    var email = MutableStateFlow("")
    var password = MutableStateFlow("")
    var name = MutableStateFlow("")
    var newPassword = MutableStateFlow("")
    var confirmPassword = MutableStateFlow("")
    var backendUrl = MutableStateFlow("")

    private val _busy = MutableStateFlow(false)
    val busy: StateFlow<Boolean> = _busy.asStateFlow()

    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error.asStateFlow()

    private val _info = MutableStateFlow<String?>(null)
    val info: StateFlow<String?> = _info.asStateFlow()

    private val _urlSaved = MutableStateFlow(false)
    val urlSaved: StateFlow<Boolean> = _urlSaved.asStateFlow()

    fun loadBackendUrl() {
        viewModelScope.launch {
            backendUrl.value = sessionManager.baseUrl.first()
            // Silently pick up a rotated tunnel URL so Anna never has to paste it.
            refreshBackendUrlFromGist(quiet = true)
        }
    }

    /**
     * Fetches the current backend URL from the public gist (kept fresh by the
     * server watchdog). If it differs from the stored URL, updates storage and
     * the text field. Returns true when the URL was changed.
     */
    suspend fun refreshBackendUrlFromGist(quiet: Boolean = false): Boolean {
        val changed = GistUrlFetcher.refresh(sessionManager)
        if (changed) {
            backendUrl.value = sessionManager.baseUrl.first()
            if (!quiet) {
                _info.value = "Backend URL auto-updated. You can log in now."
                _urlSaved.value = true
            }
        }
        return changed
    }

    /** Manual "check for new URL" hook for the UI (used after a connection error). */
    fun checkForUrlUpdate() {
        viewModelScope.launch {
            _busy.value = true
            _error.value = null
            val changed = refreshBackendUrlFromGist(quiet = false)
            _busy.value = false
            if (!changed && _info.value == null) {
                _info.value = "Backend URL is already up to date."
            }
        }
    }

    fun saveBackendUrl() {
        val url = backendUrl.value.trim()
        if (url.isEmpty()) {
            _error.value = "Please enter the backend URL"
            return
        }
        viewModelScope.launch {
            sessionManager.setBaseUrl(url)
            _urlSaved.value = true
            _info.value = "Backend URL saved. You can now log in or sign up."
        }
    }

    fun clearMessages() {
        _error.value = null
        _info.value = null
    }

    fun login(onSuccess: () -> Unit) {
        val emailErr = Validators.emailError(email.value)
        val passErr = if (password.value.isEmpty()) "Password is required" else null
        if (emailErr != null || passErr != null) {
            _error.value = listOfNotNull(emailErr, passErr).joinToString("\n")
            return
        }
        viewModelScope.launch {
            _busy.value = true
            _error.value = null
            authRepository.login(email.value, password.value).collect { result ->
                when (result) {
                    is ApiResult.Loading -> Unit
                    is ApiResult.Success -> {
                        _busy.value = false
                        onSuccess()
                    }
                    is ApiResult.Error -> {
                        _busy.value = false
                        _error.value = result.message
                    }
                }
            }
        }
    }

    fun signup(onSuccess: () -> Unit) {
        val nameErr = if (name.value.isBlank()) "Name is required" else null
        val emailErr = Validators.emailError(email.value)
        val passErr = Validators.passwordError(password.value)
        if (nameErr != null || emailErr != null || passErr != null) {
            _error.value = listOfNotNull(nameErr, emailErr, passErr).joinToString("\n")
            return
        }
        viewModelScope.launch {
            _busy.value = true
            _error.value = null
            authRepository.signup(name.value, email.value, password.value).collect { result ->
                when (result) {
                    is ApiResult.Loading -> Unit
                    is ApiResult.Success -> {
                        _busy.value = false
                        _info.value = "Account created. Please log in."
                            .let {
                                if (result.data.emailVerified) it
                                else "$it Check your email to verify your address."
                            }
                        onSuccess()
                    }
                    is ApiResult.Error -> {
                        _busy.value = false
                        _error.value = result.message
                    }
                }
            }
        }
    }

    fun forgotPassword() {
        val emailErr = Validators.emailError(email.value)
        if (emailErr != null) {
            _error.value = emailErr
            return
        }
        viewModelScope.launch {
            _busy.value = true
            _error.value = null
            // Response is generic by design (no user enumeration).
            authRepository.forgotPassword(email.value).collect { result ->
                _busy.value = false
                when (result) {
                    is ApiResult.Loading -> Unit
                    is ApiResult.Success ->
                        _info.value = result.data.ifEmpty {
                            "If an account exists for this email, a reset link was sent."
                        }
                    is ApiResult.Error -> _error.value = result.message
                }
            }
        }
    }

    fun resetPassword(token: String, onSuccess: () -> Unit) {
        val passErr = Validators.passwordError(newPassword.value)
        val confirmErr =
            if (newPassword.value != confirmPassword.value) "Passwords do not match" else null
        if (passErr != null || confirmErr != null) {
            _error.value = listOfNotNull(passErr, confirmErr).joinToString("\n")
            return
        }
        viewModelScope.launch {
            _busy.value = true
            _error.value = null
            authRepository.resetPassword(token, newPassword.value).collect { result ->
                _busy.value = false
                when (result) {
                    is ApiResult.Loading -> Unit
                    is ApiResult.Success -> onSuccess()
                    is ApiResult.Error -> _error.value = result.message
                }
            }
        }
    }

    fun verifyEmail(token: String) {
        viewModelScope.launch {
            _busy.value = true
            _error.value = null
            authRepository.verifyEmail(token).collect { result ->
                _busy.value = false
                when (result) {
                    is ApiResult.Loading -> Unit
                    is ApiResult.Success -> _info.value = result.data.ifEmpty {
                        "Email verified. You can log in now."
                    }
                    is ApiResult.Error -> _error.value = result.message
                }
            }
        }
    }
}

