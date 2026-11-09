# 📦 Ultra-Lean Minimal APK Optimization Guide

## 1. Goal
Produce the smallest possible APK footprint (< 12MB) while bundling Media3 ExoPlayer, OkHttp, Retrofit, Coil, and Compose, signed with a debug keystore for seamless sideloading on Android TV boxes and mobile devices.

## 2. Build Configuration (`build.gradle.kts`)
```kotlin
android {
    compileSdk = 36

    defaultConfig {
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "1.0.0"

        // Keep only Thai and English strings/resources
        resourceConfigurations += setOf("th", "en")

        ndk {
            abiFilters += setOf("armeabi-v7a", "arm64-v8a")
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            // Zero-friction sideloading without custom keystore
            signingConfig = signingConfigs.getByName("debug")
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_21
        targetCompatibility = JavaVersion.VERSION_21
    }
}
```

## 3. Essential ProGuard Rules (`proguard-rules.pro`)
```proguard
# Media3 ExoPlayer
-keep class androidx.media3.** { *; }
-dontwarn androidx.media3.**

# OkHttp & Retrofit
-dontwarn okhttp3.**
-dontwarn okio.**
-keepattributes Signature
-keepattributes *Annotation*

# Coil Image Loading
-keep class coil.** { *; }
-dontwarn coil.**

# Strip debug logging in release
-assumenosideeffects class android.util.Log {
    public static boolean isLoggable(java.lang.String, int);
    public static int v(...);
    public static int d(...);
}
```
