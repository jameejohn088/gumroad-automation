package com.gumroadautomation.di

import android.content.Context
import androidx.room.Room
import com.google.gson.Gson
import com.gumroadautomation.data.api.AuthInterceptor
import com.gumroadautomation.data.api.GistRefreshInterceptor
import com.gumroadautomation.data.api.TokenAuthenticator
import com.gumroadautomation.data.datastore.SessionManager
import com.gumroadautomation.data.db.AppDatabase
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import java.util.concurrent.TimeUnit
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object AppModule {

    @Provides
    @Singleton
    fun provideGson(): Gson = Gson()

    @Provides
    @Singleton
    fun provideOkHttpClient(
        authInterceptor: AuthInterceptor,
        tokenAuthenticator: TokenAuthenticator,
        sessionManager: SessionManager,
    ): OkHttpClient {
        // BASIC level only, and the Authorization header is redacted: tokens and
        // request bodies (which may contain emails) are never written to logs.
        val logging = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BASIC
            redactHeader("Authorization")
        }
        return OkHttpClient.Builder()
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            // Total cap for a call including interceptor retries, so a dead
            // tunnel can never leave a button spinning for minutes.
            .callTimeout(60, TimeUnit.SECONDS)
            .addInterceptor(authInterceptor)
            .addInterceptor(GistRefreshInterceptor(sessionManager))
            .authenticator(tokenAuthenticator)
            .addInterceptor(logging)
            .build()
    }

    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): AppDatabase =
        Room.databaseBuilder(context, AppDatabase::class.java, "gumroad_automation.db")
            // v1: no migrations yet. Add real migrations (never destructive) before
            // changing the schema once the app is on real devices.
            .fallbackToDestructiveMigration()
            .build()

    @Provides
    fun provideAccountDao(db: AppDatabase) = db.accountDao()

    @Provides
    fun provideProductDao(db: AppDatabase) = db.productDao()

    @Provides
    fun provideSaleDao(db: AppDatabase) = db.saleDao()

    @Provides
    fun provideCustomerDao(db: AppDatabase) = db.customerDao()

    @Provides
    fun provideSubscriberDao(db: AppDatabase) = db.subscriberDao()

    @Provides
    fun provideDashboardDao(db: AppDatabase) = db.dashboardDao()
}
