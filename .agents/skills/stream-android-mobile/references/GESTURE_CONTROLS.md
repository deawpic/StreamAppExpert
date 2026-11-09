# 👆 Mobile Player Touch Gestures (VLC & MX Player Style)

## Architecture Overview
In Jetpack Compose, gestures are handled via `pointerInput` on the full player surface. The screen width is bifurcated into:
- Left Half: Screen Brightness
- Right Half: Audio Volume
- Horizontal axis: Seeking / Scrubbing preview

## Complete Production Implementation
```kotlin
package com.streamapp.mobile.player.gestures

import android.app.Activity
import android.content.Context
import android.media.AudioManager
import android.view.WindowManager
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import kotlin.math.abs

enum class GestureType { NONE, BRIGHTNESS, VOLUME, SCRUBBING }

@Composable
fun PlayerGestureOverlay(
    isLocked: Boolean,
    onSingleTap: () -> Unit,
    onDoubleTapSeek: (forward: Boolean) -> Unit,
    onScrubSeek: (deltaMs: Long) -> Unit,
    modifier: Modifier = Modifier,
    content: @Composable () -> Unit
) {
    val context = LocalContext.current
    val activity = context as? Activity
    val audioManager = remember { context.getSystemService(Context.AUDIO_SERVICE) as AudioManager }

    var gestureType by remember { mutableStateOf(GestureType.NONE) }
    var touchStartX by remember { mutableFloatStateOf(0f) }
    var touchStartY by remember { mutableFloatStateOf(0f) }
    var totalDragDistanceY by remember { mutableFloatStateOf(0f) }
    var totalDragDistanceX by remember { mutableFloatStateOf(0f) }

    Box(
        modifier = modifier
            .fillMaxSize()
            .pointerInput(isLocked) {
                if (isLocked) {
                    detectTapGestures(onTap = { onSingleTap() })
                } else {
                    detectTapGestures(
                        onTap = { onSingleTap() },
                        onDoubleTap = { offset ->
                            val isRightSide = offset.x > size.width / 2
                            onDoubleTapSeek(isRightSide)
                        }
                    )
                }
            }
            .pointerInput(isLocked) {
                if (!isLocked) {
                    detectDragGestures(
                        onDragStart = { offset ->
                            touchStartX = offset.x
                            touchStartY = offset.y
                            totalDragDistanceX = 0f
                            totalDragDistanceY = 0f
                            gestureType = GestureType.NONE
                        },
                        onDragEnd = {
                            gestureType = GestureType.NONE
                        },
                        onDragCancel = {
                            gestureType = GestureType.NONE
                        },
                        onDrag = { change, dragAmount ->
                            change.consume()
                            totalDragDistanceX += dragAmount.x
                            totalDragDistanceY += dragAmount.y

                            if (gestureType == GestureType.NONE) {
                                if (abs(totalDragDistanceX) > 40f && abs(totalDragDistanceX) > abs(totalDragDistanceY)) {
                                    gestureType = GestureType.SCRUBBING
                                } else if (abs(totalDragDistanceY) > 40f) {
                                    gestureType = if (touchStartX < size.width / 2) GestureType.BRIGHTNESS else GestureType.VOLUME
                                }
                            }

                            when (gestureType) {
                                GestureType.BRIGHTNESS -> {
                                    activity?.let { act ->
                                        val delta = -dragAmount.y / (size.height * 0.75f)
                                        val lp = act.window.attributes
                                        val currentBrightness = if (lp.screenBrightness < 0f) 0.5f else lp.screenBrightness
                                        lp.screenBrightness = (currentBrightness + delta).coerceIn(0.01f, 1.0f)
                                        act.window.attributes = lp
                                    }
                                }
                                GestureType.VOLUME -> {
                                    val maxVol = audioManager.getStreamMaxVolume(AudioManager.STREAM_MUSIC)
                                    val delta = -dragAmount.y / (size.height * 0.75f) * maxVol
                                    val currVol = audioManager.getStreamVolume(AudioManager.STREAM_MUSIC)
                                    val targetVol = (currVol + delta.toInt()).coerceIn(0, maxVol)
                                    audioManager.setStreamVolume(AudioManager.STREAM_MUSIC, targetVol, 0)
                                }
                                GestureType.SCRUBBING -> {
                                    val deltaMs = (dragAmount.x / size.width * 120_000L).toLong() // +/- up to 120s
                                    onScrubSeek(deltaMs)
                                }
                                GestureType.NONE -> {}
                            }
                        }
                    )
                }
            }
    ) {
        content()
    }
}
```
