package com.gumroadautomation.ui.screens.main

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.gumroadautomation.data.api.dto.GumroadAccountDto
import com.gumroadautomation.data.datastore.SessionManager
import com.gumroadautomation.data.repository.AccountRepository
import com.gumroadautomation.data.repository.AuthRepository
import com.gumroadautomation.data.repository.OpsRepository
import com.gumroadautomation.util.ApiResult
import com.gumroadautomation.util.GistUrlFetcher
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject

/**
 * App-wide session state: login status, Gumroad accounts, selected account,
 * unread notification count. Shared by the nav graph and the main scaffold.
 */
@HiltViewModel
class SessionViewModel @Inject constructor(
    private val authRepository: AuthRepository,
    private val accountRepository: AccountRepository,
    private val opsRepository: OpsRepository,
    private val sessionManager: SessionManager,
) : ViewModel() {

    private val _isLoggedIn = MutableStateFlow(authRepository.isLoggedIn)
    val isLoggedIn: StateFlow<Boolean> = _isLoggedIn.asStateFlow()

    val selectedAccountId: StateFlow<String?> = sessionManager.selectedAccountId
        .stateIn(viewModelScope, SharingStarted.Eagerly, null)

    private val _accounts = MutableStateFlow<List<GumroadAccountDto>>(emptyList())
    val accounts: StateFlow<List<GumroadAccountDto>> = _accounts.asStateFlow()

    private val _unreadCount = MutableStateFlow(0)
    val unreadCount: StateFlow<Int> = _unreadCount.asStateFlow()

    private val _logoutEvent = MutableSharedFlow<Unit>(extraBufferCapacity = 1)
    val logoutEvent = _logoutEvent.asSharedFlow()

    init {
        viewModelScope.launch {
            authRepository.unauthorizedEvents.collect {
                // Refresh token rejected — hard logout and return to login.
                authRepository.logout()
                _isLoggedIn.value = false
                _logoutEvent.emit(Unit)
            }
        }
        if (_isLoggedIn.value) {
            // Pick up a rotated tunnel URL before any API call, so the app
            // never shows "disconnected" after a rotation.
            viewModelScope.launch {
                GistUrlFetcher.refresh(sessionManager)
                refreshAccounts()
                refreshUnread()
            }
        }
    }

    fun onLoginSuccess() {
        _isLoggedIn.value = true
        viewModelScope.launch {
            GistUrlFetcher.refresh(sessionManager)
            refreshAccounts()
            refreshUnread()
        }
    }

    fun refreshAccounts() {
        viewModelScope.launch {
            accountRepository.accounts().collect { result ->
                if (result is ApiResult.Success) _accounts.value = result.data
            }
        }
    }

    fun refreshUnread() {
        viewModelScope.launch {
            opsRepository.unreadCount().collect { result ->
                if (result is ApiResult.Success) {
                    _unreadCount.value = result.data
                }
            }
        }
    }

    fun selectAccount(accountId: String?) {
        viewModelScope.launch { sessionManager.setSelectedAccountId(accountId) }
    }

    fun logout() {
        viewModelScope.launch {
            authRepository.logout()
            _isLoggedIn.value = false
            _accounts.value = emptyList()
            _unreadCount.value = 0
            _logoutEvent.emit(Unit)
        }
    }
}
