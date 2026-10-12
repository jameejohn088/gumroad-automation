package com.gumroadautomation.ui.navigation

import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.NavGraphBuilder
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.gumroadautomation.ui.screens.accounts.AccountsScreen
import com.gumroadautomation.ui.screens.auth.ForgotPasswordScreen
import com.gumroadautomation.ui.screens.auth.VerifyEmailScreen
import com.gumroadautomation.ui.screens.auth.LoginScreen
import com.gumroadautomation.ui.screens.auth.ResetPasswordScreen
import com.gumroadautomation.ui.screens.auth.SignupScreen
import com.gumroadautomation.ui.screens.auth.VerifyEmailScreen
import com.gumroadautomation.ui.screens.automations.AutomationsScreen
import com.gumroadautomation.ui.screens.automations.RuleEditorScreen
import com.gumroadautomation.ui.screens.customers.CustomersScreen
import com.gumroadautomation.ui.screens.dashboard.DashboardScreen
import com.gumroadautomation.ui.screens.logs.LogsScreen
import com.gumroadautomation.ui.screens.main.MainScaffold
import com.gumroadautomation.ui.screens.main.SessionViewModel
import com.gumroadautomation.ui.screens.memberships.MembershipsScreen
import com.gumroadautomation.ui.screens.more.MoreScreen
import com.gumroadautomation.ui.screens.notifications.NotificationsScreen
import com.gumroadautomation.ui.screens.products.ProductsScreen
import com.gumroadautomation.ui.screens.sales.SalesScreen
import com.gumroadautomation.ui.screens.scheduler.JobDetailScreen
import com.gumroadautomation.ui.screens.scheduler.JobEditorScreen
import com.gumroadautomation.ui.screens.scheduler.SchedulerScreen
import com.gumroadautomation.ui.screens.settings.SettingsScreen
import com.gumroadautomation.ui.screens.subscribers.SubscribersScreen

private fun NavGraphBuilder.mainScreen(
    route: String,
    navController: NavHostController,
    sessionViewModel: SessionViewModel,
    content: @Composable () -> Unit,
) {
    composable(route) {
        MainScaffold(
            navController = navController,
            currentRoute = route,
            sessionViewModel = sessionViewModel,
            content = content,
        )
    }
}

@Composable
fun AppNavGraph() {
    val navController = rememberNavController()
    // Activity-scoped: AppNavGraph is composed directly in MainActivity's setContent,
    // so this ONE instance is shared by every screen that receives it explicitly.
    val sessionViewModel: SessionViewModel = hiltViewModel()
    val isLoggedIn by sessionViewModel.isLoggedIn.collectAsStateWithLifecycle()

    // Session died (refresh rejected) → back to login, clearing the back stack.
    LaunchedEffect(Unit) {
        sessionViewModel.logoutEvent.collect {
            navController.navigate(Routes.LOGIN) { popUpTo(0) }
        }
    }

    NavHost(
        navController = navController,
        startDestination = if (isLoggedIn) Routes.DASHBOARD else Routes.LOGIN,
    ) {
        // -- Auth -----------------------------------------------------------------
        composable(Routes.LOGIN) {
            LoginScreen(
                onLoggedIn = {
                    sessionViewModel.onLoginSuccess()
                    navController.navigate(Routes.DASHBOARD) { popUpTo(0) }
                },
                onNavigateToSignup = { navController.navigate(Routes.SIGNUP) },
                onNavigateToForgot = { navController.navigate(Routes.FORGOT_PASSWORD) },
                onNavigateToVerify = { navController.navigate(Routes.VERIFY_EMAIL_CODE) },
            )
        }
        composable(Routes.SIGNUP) {
            SignupScreen(
                onSignedUp = { navController.popBackStack() },
                onNavigateToLogin = { navController.popBackStack() },
            )
        }
        composable(Routes.FORGOT_PASSWORD) {
            ForgotPasswordScreen(onBack = { navController.popBackStack() })
        }
        composable(Routes.VERIFY_EMAIL_CODE) {
            VerifyEmailScreen(
                onBack = { navController.popBackStack() },
                onVerified = { navController.navigate(Routes.LOGIN) { popUpTo(0) } },
            )
        }
        composable(
            route = Routes.RESET_PASSWORD,
            arguments = listOf(navArgument("token") { type = NavType.StringType }),
        ) { backStackEntry ->
            ResetPasswordScreen(
                token = backStackEntry.arguments?.getString("token").orEmpty(),
                onDone = { navController.navigate(Routes.LOGIN) { popUpTo(0) } },
            )
        }
        composable(
            route = Routes.VERIFY_EMAIL,
            arguments = listOf(navArgument("token") { type = NavType.StringType }),
        ) { backStackEntry ->
            VerifyEmailScreen(
                token = backStackEntry.arguments?.getString("token").orEmpty(),
                onDone = { navController.navigate(Routes.LOGIN) { popUpTo(0) } },
            )
        }

        // -- Main tabs --------------------------------------------------------------
        mainScreen(Routes.DASHBOARD, navController, sessionViewModel) {
            DashboardScreen(
                sessionViewModel = sessionViewModel,
                onNavigateToAccounts = { navController.navigate(Routes.ACCOUNTS) },
            )
        }
        mainScreen(Routes.ACCOUNTS, navController, sessionViewModel) {
            AccountsScreen(sessionViewModel = sessionViewModel)
        }
        mainScreen(Routes.PRODUCTS, navController, sessionViewModel) {
            ProductsScreen(sessionViewModel = sessionViewModel)
        }
        mainScreen(Routes.SALES, navController, sessionViewModel) {
            SalesScreen(sessionViewModel = sessionViewModel)
        }
        mainScreen(Routes.MORE, navController, sessionViewModel) {
            MoreScreen(
                sessionViewModel = sessionViewModel,
                onNavigate = { navController.navigate(it) },
                onLogout = { /* sessionViewModel.logout() handled inside */ },
            )
        }

        // -- Secondary screens ---------------------------------------------------------
        mainScreen(Routes.CUSTOMERS, navController, sessionViewModel) {
            CustomersScreen(sessionViewModel = sessionViewModel)
        }
        mainScreen(Routes.SUBSCRIBERS, navController, sessionViewModel) {
            SubscribersScreen(sessionViewModel = sessionViewModel)
        }
        mainScreen(Routes.MEMBERSHIPS, navController, sessionViewModel) {
            MembershipsScreen(sessionViewModel = sessionViewModel)
        }
        mainScreen(Routes.AUTOMATIONS, navController, sessionViewModel) {
            AutomationsScreen(
                sessionViewModel = sessionViewModel,
                onEditRule = { navController.navigate(Routes.ruleEditor(it)) },
            )
        }
        composable(
            route = Routes.RULE_EDITOR,
            arguments = listOf(
                navArgument("ruleId") {
                    type = NavType.StringType
                    nullable = true
                    defaultValue = null
                }
            ),
        ) { backStackEntry ->
            MainScaffold(
                navController = navController,
                currentRoute = Routes.RULE_EDITOR,
                sessionViewModel = sessionViewModel,
            ) {
                RuleEditorScreen(
                    ruleId = backStackEntry.arguments?.getString("ruleId"),
                    sessionViewModel = sessionViewModel,
                    onSaved = { navController.popBackStack() },
                    onCancel = { navController.popBackStack() },
                )
            }
        }
        mainScreen(Routes.SCHEDULER, navController, sessionViewModel) {
            SchedulerScreen(
                sessionViewModel = sessionViewModel,
                onOpenJob = { navController.navigate(Routes.jobDetail(it)) },
                onEditJob = { navController.navigate(Routes.jobEditor(it)) },
                onCreateJob = { navController.navigate(Routes.jobEditor(null)) },
            )
        }
        composable(
            route = Routes.JOB_DETAIL,
            arguments = listOf(navArgument("jobId") { type = NavType.StringType }),
        ) { backStackEntry ->
            MainScaffold(
                navController = navController,
                currentRoute = Routes.JOB_DETAIL,
                sessionViewModel = sessionViewModel,
            ) {
                JobDetailScreen(jobId = backStackEntry.arguments?.getString("jobId").orEmpty())
            }
        }
        composable(
            route = Routes.JOB_EDITOR,
            arguments = listOf(
                navArgument("jobId") {
                    type = NavType.StringType
                    nullable = true
                    defaultValue = null
                }
            ),
        ) { backStackEntry ->
            MainScaffold(
                navController = navController,
                currentRoute = Routes.JOB_EDITOR,
                sessionViewModel = sessionViewModel,
            ) {
                JobEditorScreen(
                    jobId = backStackEntry.arguments?.getString("jobId"),
                    onSaved = { navController.popBackStack() },
                    onCancel = { navController.popBackStack() },
                )
            }
        }
        mainScreen(Routes.NOTIFICATIONS, navController, sessionViewModel) {
            NotificationsScreen(sessionViewModel = sessionViewModel)
        }
        mainScreen(Routes.LOGS, navController, sessionViewModel) {
            LogsScreen(sessionViewModel = sessionViewModel)
        }
        mainScreen(Routes.SETTINGS, navController, sessionViewModel) {
            SettingsScreen(sessionViewModel = sessionViewModel)
        }
    }
}
