# 🖼️ Picture-in-Picture (PiP) Engine for Android 8.0 to 16 (API 26 - 36)

## 1. Android 12+ (API 31+) Seamless Auto-PiP
On Android 12+, apps can enter PiP smoothly when the user performs the swipe-home gesture, without stuttering or needing an explicit button press:
```kotlin
package com.streamapp.mobile.player.pip

import android.app.Activity
import android.app.PictureInPictureParams
import android.app.RemoteAction
import android.content.Context
import android.content.pm.PackageManager
import android.graphics.Rect
import android.os.Build
import android.util.Rational

object PipManager {

    fun supportsPip(context: Context): Boolean {
        return Build.VERSION.SDK_INT >= Build.VERSION_CODES.O &&
                context.packageManager.hasSystemFeature(PackageManager.FEATURE_PICTURE_IN_PICTURE)
    }

    fun updatePipParams(activity: Activity, videoAspectRatio: Rational? = Rational(16, 9), sourceRect: Rect? = null) {
        if (!supportsPip(activity)) return

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val validRatio = videoAspectRatio?.let {
                // Rational aspect ratio must be between 1:2.39 and 2.39:1
                val floatRatio = it.toFloat()
                if (floatRatio in 0.41841f..2.39f) it else Rational(16, 9)
            } ?: Rational(16, 9)

            val builder = PictureInPictureParams.Builder()
                .setAspectRatio(validRatio)

            sourceRect?.let { builder.setSourceRectHint(it) }

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                // Seamless home gesture auto-enter (Android 12+)
                builder.setAutoEnterEnabled(true)
                builder.setSeamlessResizeEnabled(true)
            }

            try {
                activity.setPictureInPictureParams(builder.build())
            } catch (ignored: Exception) {}
        }
    }

    fun enterPip(activity: Activity, videoAspectRatio: Rational? = Rational(16, 9)) {
        if (!supportsPip(activity)) return

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val builder = PictureInPictureParams.Builder()
                .setAspectRatio(videoAspectRatio ?: Rational(16, 9))
            try {
                activity.enterPictureInPictureMode(builder.build())
            } catch (e: Exception) {
                activity.enterPictureInPictureMode()
            }
        }
    }
}
```

## 2. Compose PiP UI Mode Observer
```kotlin
@Composable
fun rememberIsInPipMode(): Boolean {
    val activity = LocalContext.current as? ComponentActivity ?: return false
    var isInPip by remember { mutableStateOf(activity.isInPictureInPictureMode) }

    DisposableEffect(activity) {
        val consumer = androidx.core.util.Consumer<androidx.core.app.PictureInPictureModeData> { data ->
            isInPip = data.isInPictureInPictureMode
        }
        activity.addOnPictureInPictureModeChangedListener(consumer)
        onDispose {
            activity.removeOnPictureInPictureModeChangedListener(consumer)
        }
    }
    return isInPip
}
```
In PiP mode, hide all controls, overlays, and action buttons (`if (!isInPip) { PlayerControls() }`).
