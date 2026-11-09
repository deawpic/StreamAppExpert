# 🎯 Android TV D-pad Focus Tree & Key Event Handling

## 1. Focusability Attributes
In TV layout XML:
```xml
<androidx.cardview.widget.CardView
    android:id="@+id/series_card"
    android:layout_width="160dp"
    android:layout_height="240dp"
    android:focusable="true"
    android:focusableInTouchMode="false"
    android:clickable="true"
    android:foreground="?attr/selectableItemBackground" />
```

## 2. Key Code Interception in TV Playback Activity
```kotlin
override fun onKeyDown(keyCode: Int, event: KeyEvent?): Boolean {
    return when (keyCode) {
        KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE,
        KeyEvent.KEYCODE_DPAD_CENTER -> {
            if (player.isPlaying) player.pause() else player.play()
            true
        }
        KeyEvent.KEYCODE_MEDIA_FAST_FORWARD,
        KeyEvent.KEYCODE_DPAD_RIGHT -> {
            player.seekTo(player.currentPosition + 10_000)
            true
        }
        KeyEvent.KEYCODE_MEDIA_REWIND,
        KeyEvent.KEYCODE_DPAD_LEFT -> {
            player.seekTo((player.currentPosition - 10_000).coerceAtLeast(0))
            true
        }
        else -> super.onKeyDown(keyCode, event)
    }
}
```
