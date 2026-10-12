package com.gumroadautomation.ui.screens.auth

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.gumroadautomation.ui.components.EmailField
import com.gumroadautomation.ui.components.PasswordField

@Composable
private fun AuthScaffold(
    title: String,
    subtitle: String,
    error: String?,
    info: String?,
    busy: Boolean,
    content: @Composable () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(title, style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(8.dp))
        Text(
            subtitle,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Spacer(Modifier.height(24.dp))
        error?.let {
            Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodyMedium)
            Spacer(Modifier.height(8.dp))
        }
        info?.let {
            Text(it, color = MaterialTheme.colorScheme.primary, style = MaterialTheme.typography.bodyMedium)
            Spacer(Modifier.height(8.dp))
        }
        content()
        if (busy) {
            Spacer(Modifier.height(16.dp))
            CircularProgressIndicator()
        }
    }
}

@Composable
fun BackendUrlField(viewModel: AuthViewModel) {
    val backendUrl by viewModel.backendUrl.collectAsState()
    val urlSaved by viewModel.urlSaved.collectAsState()

    LaunchedEffect(Unit) { viewModel.loadBackendUrl() }

    OutlinedTextField(
        value = backendUrl, onValueChange = { viewModel.backendUrl.value = it },
        label = { Text("Backend base URL") }, singleLine = true,
        modifier = Modifier.fillMaxWidth(),
        placeholder = { Text("https://.../api/v1") },
    )
    Spacer(Modifier.height(8.dp))
    OutlinedButton(
        onClick = { viewModel.saveBackendUrl() },
        modifier = Modifier.fillMaxWidth(),
    ) { Text(if (urlSaved) "Backend URL saved ✓" else "Save backend URL") }
    Spacer(Modifier.height(8.dp))
    // Auto-update fallback: if the tunnel rotated, one tap fetches the fresh URL.
    TextButton(
        onClick = { viewModel.checkForUrlUpdate() },
        modifier = Modifier.fillMaxWidth(),
    ) { Text("Check for updated URL") }
    Spacer(Modifier.height(12.dp))
}

@Composable
fun LoginScreen(
    onLoggedIn: () -> Unit,
    onNavigateToSignup: () -> Unit,
    onNavigateToForgot: () -> Unit,
    onNavigateToVerify: () -> Unit,
    viewModel: AuthViewModel = hiltViewModel(),
) {
    val email by viewModel.email.collectAsState()
    val password by viewModel.password.collectAsState()
    val busy by viewModel.busy.collectAsState()
    val error by viewModel.error.collectAsState()

    LaunchedEffect(Unit) { viewModel.clearMessages() }

    AuthScaffold(
        title = "Welcome back",
        subtitle = "Log in to manage your Gumroad automation",
        error = error, info = null, busy = busy,
    ) {
        BackendUrlField(viewModel)
        EmailField(value = email, onValueChange = { viewModel.email.value = it }, error = null)
        Spacer(Modifier.height(12.dp))
        PasswordField(value = password, onValueChange = { viewModel.password.value = it })
        Spacer(Modifier.height(16.dp))
        Button(
            onClick = { viewModel.login(onLoggedIn) },
            enabled = !busy,
            modifier = Modifier.fillMaxWidth(),
        ) { Text("Log in") }
        TextButton(onClick = onNavigateToForgot) { Text("Forgot password?") }
        TextButton(onClick = onNavigateToVerify) { Text("Verify email with code") }
        TextButton(onClick = onNavigateToSignup) { Text("Don't have an account? Sign up") }
    }
}

@Composable
fun SignupScreen(
    onSignedUp: () -> Unit,
    onNavigateToLogin: () -> Unit,
    viewModel: AuthViewModel = hiltViewModel(),
) {
    val name by viewModel.name.collectAsState()
    val email by viewModel.email.collectAsState()
    val password by viewModel.password.collectAsState()
    val busy by viewModel.busy.collectAsState()
    val error by viewModel.error.collectAsState()
    val info by viewModel.info.collectAsState()

    LaunchedEffect(Unit) { viewModel.clearMessages() }

    AuthScaffold(
        title = "Create account",
        subtitle = "Your Gumroad tokens stay encrypted on the backend",
        error = error, info = info, busy = busy,
    ) {
        BackendUrlField(viewModel)
        OutlinedTextField(
            value = name, onValueChange = { viewModel.name.value = it },
            label = { Text("Name") }, singleLine = true, modifier = Modifier.fillMaxWidth(),
        )
        Spacer(Modifier.height(12.dp))
        EmailField(value = email, onValueChange = { viewModel.email.value = it }, error = null)
        Spacer(Modifier.height(12.dp))
        PasswordField(value = password, onValueChange = { viewModel.password.value = it })
        Spacer(Modifier.height(16.dp))
        Button(
            onClick = { viewModel.signup(onSignedUp) },
            enabled = !busy,
            modifier = Modifier.fillMaxWidth(),
        ) { Text("Sign up") }
        TextButton(onClick = onNavigateToLogin) { Text("Already have an account? Log in") }
    }
}

@Composable
fun ForgotPasswordScreen(
    onBack: () -> Unit,
    viewModel: AuthViewModel = hiltViewModel(),
) {
    val email by viewModel.email.collectAsState()
    val busy by viewModel.busy.collectAsState()
    val error by viewModel.error.collectAsState()
    val info by viewModel.info.collectAsState()

    LaunchedEffect(Unit) { viewModel.clearMessages() }

    AuthScaffold(
        title = "Forgot password",
        subtitle = "Enter your email to receive a reset link",
        error = error, info = info, busy = busy,
    ) {
        EmailField(value = email, onValueChange = { viewModel.email.value = it }, error = null)
        Spacer(Modifier.height(16.dp))
        Button(
            onClick = { viewModel.forgotPassword() },
            enabled = !busy,
            modifier = Modifier.fillMaxWidth(),
        ) { Text("Send reset link") }
        TextButton(onClick = onBack) { Text("Back to login") }
    }
}

@Composable
fun VerifyEmailScreen(
    onBack: () -> Unit,
    onVerified: () -> Unit,
    viewModel: AuthViewModel = hiltViewModel(),
) {
    val email by viewModel.email.collectAsState()
    val busy by viewModel.busy.collectAsState()
    val error by viewModel.error.collectAsState()
    val info by viewModel.info.collectAsState()
    var code by remember { mutableStateOf("") }
    var codeSent by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) { viewModel.clearMessages() }

    AuthScaffold(
        title = "Verify email",
        subtitle = "We'll send a 6-digit code to your email",
        error = error, info = info, busy = busy,
    ) {
        EmailField(value = email, onValueChange = { viewModel.email.value = it }, error = null)
        Spacer(Modifier.height(12.dp))
        Button(
            onClick = {
                viewModel.requestVerificationCode()
                codeSent = true
            },
            enabled = !busy && email.isNotBlank(),
            modifier = Modifier.fillMaxWidth(),
        ) { Text(if (codeSent) "Resend code" else "Send code") }

        if (codeSent) {
            Spacer(Modifier.height(16.dp))
            OutlinedTextField(
                value = code,
                onValueChange = { if (it.length <= 6 && it.all { c -> c.isDigit() }) code = it },
                label = { Text("6-digit code") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(Modifier.height(12.dp))
            Button(
                onClick = { viewModel.verifyEmailCode(code, onVerified) },
                enabled = !busy && code.length == 6,
                modifier = Modifier.fillMaxWidth(),
            ) { Text("Verify") }
        }
        TextButton(onClick = onBack) { Text("Back to login") }
    }
}

@Composable
fun ResetPasswordScreen(
    token: String,
    onDone: () -> Unit,
    viewModel: AuthViewModel = hiltViewModel(),
) {
    val newPassword by viewModel.newPassword.collectAsState()
    val confirmPassword by viewModel.confirmPassword.collectAsState()
    val busy by viewModel.busy.collectAsState()
    val error by viewModel.error.collectAsState()

    LaunchedEffect(Unit) { viewModel.clearMessages() }

    AuthScaffold(
        title = "Reset password",
        subtitle = "Choose a new password",
        error = error, info = null, busy = busy,
    ) {
        PasswordField(
            value = newPassword, onValueChange = { viewModel.newPassword.value = it },
            label = "New password",
        )
        Spacer(Modifier.height(12.dp))
        PasswordField(
            value = confirmPassword, onValueChange = { viewModel.confirmPassword.value = it },
            label = "Confirm new password",
        )
        Spacer(Modifier.height(16.dp))
        Button(
            onClick = { viewModel.resetPassword(token, onDone) },
            enabled = !busy,
            modifier = Modifier.fillMaxWidth(),
        ) { Text("Reset password") }
    }
}

@Composable
fun VerifyEmailScreen(
    token: String,
    onDone: () -> Unit,
    viewModel: AuthViewModel = hiltViewModel(),
) {
    val busy by viewModel.busy.collectAsState()
    val error by viewModel.error.collectAsState()
    val info by viewModel.info.collectAsState()

    LaunchedEffect(token) { viewModel.verifyEmail(token) }

    AuthScaffold(
        title = "Verify email",
        subtitle = "Confirming your email address…",
        error = error, info = info, busy = busy,
    ) {
        if (info != null) {
            Spacer(Modifier.height(8.dp))
            Button(onClick = onDone, modifier = Modifier.fillMaxWidth()) { Text("Continue to login") }
        } else if (error != null) {
            Spacer(Modifier.height(8.dp))
            TextButton(onClick = onDone) { Text("Back to login") }
        }
    }
}

