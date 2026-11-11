# 🔊 SoundBoostManager: Hardware LoudnessEnhancer & Real TV Crash Guard

## 1. Why Sub-Mastered Streams Need Volume Boost
- Web scraped streams often have dialogues recorded at low decibel levels (-18dB to -24dB LUFS).
- Multiplying raw PCM samples without bounds causes clipping, harmonic distortion, and speaker crackling.
- Android provides `android.media.audiofx.LoudnessEnhancer`, a hardware-accelerated DSP effect designed to compress dynamic range and boost perceived dialogue loudness cleanly.

## 2. Real TV Hardware Pitfalls (`IllegalStateException` & Audio Write Failed)
On real Android TV hardware (Amlogic, MediaTek, MStar) or when HDMI eARC / S/PDIF passthrough is active:
1. `LoudnessEnhancer(sessionId).apply { enabled = true }` in constructor will throw `IllegalStateException` or crash native AudioFlinger.
2. In ExoPlayer, this manifests as `ExoPlaybackException` with `ERROR_CODE_AUDIO_TRACK_WRITE_FAILED` or unexpected 1004.
3. **Mandatory Guard Rules**:
   - Wrap ALL `LoudnessEnhancer` invocations in `Throwable` catch blocks (never just `Exception`).
   - Start with `enabled = false`.
   - Provide a dual-path fallback to `exoPlayer.volume = multiplier` if the hardware effect fails.
   - Auto-recover in `Player.Listener.onPlayerError`.

```kotlin
package com.streamapp.player

import android.media.audiofx.LoudnessEnhancer
import android.util.Log
import androidx.media3.common.C
import androidx.media3.exoplayer.ExoPlayer

enum class SoundBoostLevel(val title: String, val gainMilliBels: Int, val multiplier: Float) {
    OFF("ปิดบูสต์เสียง", 0, 1.0f),
    BOOST_125("1.25x (+2.5 dB)", 250, 1.25f),
    BOOST_150("1.50x (+5.0 dB)", 500, 1.50f),
    BOOST_175("1.75x (+7.0 dB)", 700, 1.75f),
    BOOST_200("2.00x (+8.5 dB)", 850, 2.00f),
    BOOST_MAX("MAX (+12.0 dB)", 1200, 2.50f);

    fun next(): SoundBoostLevel {
        val values = entries
        return values[(ordinal + 1) % values.size]
    }
}

class SoundBoostManager(private val player: ExoPlayer) {
    private var loudnessEnhancer: LoudnessEnhancer? = null
    var currentLevel: SoundBoostLevel = SoundBoostLevel.OFF
        private set

    fun attachToAudioSession(audioSessionId: Int) {
        release()
        if (audioSessionId == 0 || audioSessionId == C.AUDIO_SESSION_ID_UNSET) return

        try {
            loudnessEnhancer = LoudnessEnhancer(audioSessionId).apply {
                enabled = false // NEVER enable in constructor!
            }
            applyGain()
        } catch (t: Throwable) {
            Log.w("SoundBoostManager", "Hardware LoudnessEnhancer unavailable on this TV box, using software fallback", t)
            loudnessEnhancer = null
            applyFallback()
        }
    }

    fun setLevel(level: SoundBoostLevel) {
        currentLevel = level
        applyGain()
    }

    private fun applyGain() {
        var hardwareSuccess = false
        val enhancer = loudnessEnhancer
        if (enhancer != null && currentLevel != SoundBoostLevel.OFF) {
            try {
                enhancer.setTargetGain(currentLevel.gainMilliBels)
                enhancer.enabled = true
                hardwareSuccess = true
            } catch (t: Throwable) {
                Log.w("SoundBoostManager", "LoudnessEnhancer failed to apply gain, disabling hardware effect", t)
                try { enhancer.enabled = false } catch (_: Throwable) {}
                hardwareSuccess = false
            }
        } else {
            try { enhancer?.enabled = false } catch (_: Throwable) {}
        }

        if (!hardwareSuccess) {
            applyFallback()
        } else {
            try { player.volume = 1.0f } catch (_: Throwable) {}
        }
    }

    private fun applyFallback() {
        try {
            player.volume = currentLevel.multiplier
        } catch (_: Throwable) {}
    }

    fun cycleNext(): SoundBoostLevel {
        val next = currentLevel.next()
        setLevel(next)
        return next
    }

    fun release() {
        try {
            loudnessEnhancer?.enabled = false
        } catch (_: Throwable) {}
        try {
            loudnessEnhancer?.release()
        } catch (_: Throwable) {}
        loudnessEnhancer = null
    }
}
```
