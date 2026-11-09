# 🛡️ Mobile Hardware Protections: Becoming Noisy & Cutout Insets

## 1. Audio Becoming Noisy Broadcast Receiver
When headphones or Bluetooth devices disconnect, Android broadcasts `ACTION_AUDIO_BECOMING_NOISY`.
A production streaming player MUST intercept this and immediately pause playback to avoid embarrassing speaker blasts in public.

```kotlin
package com.streamapp.mobile.player.guards

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.media.AudioManager
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.ui.platform.LocalContext

@Composable
fun AudioBecomingNoisyGuard(onPauseRequired: () -> Unit) {
    val context = LocalContext.current

    DisposableEffect(context) {
        val receiver = object : BroadcastReceiver() {
            override fun onReceive(ctx: Context?, intent: Intent?) {
                if (intent?.action == AudioManager.ACTION_AUDIO_BECOMING_NOISY) {
                    onPauseRequired()
                }
            }
        }
        val filter = IntentFilter(AudioManager.ACTION_AUDIO_BECOMING_NOISY)
        context.registerReceiver(receiver, filter)

        onDispose {
            try {
                context.unregisterReceiver(receiver)
            } catch (ignored: Exception) {}
        }
    }
}
```

## 2. Display Cutout & Notch Safe Insets
In fullscreen landscape video playback, camera pinholes and iPhone-style dynamic islands will obstruct video or OSD controls if cutouts aren't accounted for:
```kotlin
// In MainActivity.kt / PlaybackActivity.kt
if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
    window.attributes.layoutInDisplayCutoutMode =
        WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES
}

// In Jetpack Compose Player Scaffolding:
Box(
    modifier = Modifier
        .fillMaxSize()
        .windowInsetsPadding(WindowInsets.displayCutout)
) {
    // HUD and controls stay inside safe cutout bounds
}
```
