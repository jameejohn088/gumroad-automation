package com.gumroadautomation.ui.navigation

/** All navigation routes. Arguments use the {name} template convention. */
object Routes {
    const val LOGIN = "login"
    const val SIGNUP = "signup"
    const val FORGOT_PASSWORD = "forgot_password"
    const val RESET_PASSWORD = "reset_password/{token}"
    const val VERIFY_EMAIL = "verify_email/{token}"
    const val VERIFY_EMAIL_CODE = "verify_email_code"

    const val DASHBOARD = "dashboard"
    const val ACCOUNTS = "accounts"
    const val PRODUCTS = "products"
    const val SALES = "sales"
    const val MORE = "more"

    const val CUSTOMERS = "customers"
    const val SUBSCRIBERS = "subscribers"
    const val MEMBERSHIPS = "memberships"
    const val AUTOMATIONS = "automations"
    const val RULE_EDITOR = "rule_editor?ruleId={ruleId}"
    const val SCHEDULER = "scheduler"
    const val JOB_DETAIL = "job_detail/{jobId}"
    const val JOB_EDITOR = "job_editor?jobId={jobId}"
    const val NOTIFICATIONS = "notifications"
    const val LOGS = "logs"
    const val SETTINGS = "settings"

    fun resetPassword(token: String) = "reset_password/$token"
    fun verifyEmail(token: String) = "verify_email/$token"
    fun ruleEditor(ruleId: String?) = if (ruleId == null) "rule_editor" else "rule_editor?ruleId=$ruleId"
    fun jobDetail(jobId: String) = "job_detail/$jobId"
    fun jobEditor(jobId: String?) = if (jobId == null) "job_editor" else "job_editor?jobId=$jobId"

    /** Bottom-navigation tabs shown in the main scaffold. */
    val bottomTabs = listOf(DASHBOARD, ACCOUNTS, PRODUCTS, SALES, MORE)
}
